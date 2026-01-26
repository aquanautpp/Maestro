#!/usr/bin/env python3
"""
Detector de turnos conversacionais em tempo real.

Usa o microfone do computador para detectar fala de criança/adulto
e verificar se o adulto responde dentro de 5 segundos.

Uso:
    python realtime_detector.py
    python realtime_detector.py --threshold 300

Requisitos:
    pip install sounddevice webrtcvad numpy flask
"""

import argparse
import time
import threading
import uuid
from datetime import datetime
import numpy as np
import sounddevice as sd
import webrtcvad
from flask import Flask, jsonify, request
from flask_cors import CORS

# Configurações
SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SIZE = SAMPLE_RATE * FRAME_MS // 1000  # 480 samples

# Cores ANSI
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

# Flask app
app = Flask(__name__)
CORS(app)  # Permite requisições do Lovable

# Estado global da sessão (thread-safe)
session_state = {
    "listening": False,
    "current_speaker": None,  # "ADT", "CHI", ou None
    "current_pitch": None,
    "last_speech_time": None,
    "session_id": None,
    "turns": 0,
    "missed": 0,
    "response_times": [],  # Para calcular média
    "events": [],
    "start_time": None,
    "lock": threading.Lock(),
}

# Referência ao stream de áudio (para start/stop)
audio_stream = None
detector_state = None
detector_args = None


# ============ API REST ============

@app.route('/api/status', methods=['GET'])
def api_status():
    """Retorna estado atual da escuta."""
    with session_state["lock"]:
        seconds_since = None
        if session_state["last_speech_time"]:
            seconds_since = round(time.time() - session_state["last_speech_time"], 1)

        return jsonify({
            "listening": session_state["listening"],
            "current_speaker": session_state["current_speaker"],
            "current_pitch": session_state["current_pitch"],
            "seconds_since_last_speech": seconds_since
        })


@app.route('/api/session', methods=['GET'])
def api_session():
    """Retorna dados completos da sessão."""
    with session_state["lock"]:
        turns = session_state["turns"]
        missed = session_state["missed"]
        total = turns + missed
        response_rate = (turns / total * 100) if total > 0 else 0
        avg_response = sum(session_state["response_times"]) / len(session_state["response_times"]) if session_state["response_times"] else 0
        duration = time.time() - session_state["start_time"] if session_state["start_time"] else 0
        started_at = datetime.fromtimestamp(session_state["start_time"]).isoformat() + "Z" if session_state["start_time"] else None

        return jsonify({
            "session_id": session_state["session_id"],
            "started_at": started_at,
            "duration_seconds": round(duration, 1),
            "turns": turns,
            "missed": missed,
            "response_rate": round(response_rate, 1),
            "avg_response_time": round(avg_response, 2),
            "events": session_state["events"][-50:]  # Últimos 50 eventos
        })


@app.route('/api/start', methods=['POST'])
def api_start():
    """Inicia sessão de escuta."""
    global audio_stream

    with session_state["lock"]:
        if session_state["listening"]:
            return jsonify({"error": "Já está escutando"}), 400

        # Reset da sessão
        new_session_id = str(uuid.uuid4())[:8]
        session_state["session_id"] = new_session_id
        session_state["listening"] = True
        session_state["current_speaker"] = None
        session_state["current_pitch"] = None
        session_state["last_speech_time"] = None
        session_state["turns"] = 0
        session_state["missed"] = 0
        session_state["response_times"] = []
        session_state["events"] = []
        session_state["start_time"] = time.time()

    # Inicia stream de áudio em thread separada
    threading.Thread(target=start_audio_stream, daemon=True).start()

    return jsonify({"session_id": new_session_id, "status": "started"})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Para sessão de escuta."""
    global audio_stream

    with session_state["lock"]:
        if not session_state["listening"]:
            return jsonify({"error": "Não está escutando"}), 400

        session_state["listening"] = False
        session_state["current_speaker"] = None
        session_state["current_pitch"] = None

        # Calcula resumo
        turns = session_state["turns"]
        missed = session_state["missed"]
        total = turns + missed
        response_rate = (turns / total * 100) if total > 0 else 0
        duration = time.time() - session_state["start_time"] if session_state["start_time"] else 0
        sid = session_state["session_id"]

    if audio_stream:
        audio_stream.stop()
        audio_stream.close()
        audio_stream = None

    return jsonify({
        "session_id": sid,
        "status": "stopped",
        "summary": {
            "duration_seconds": round(duration, 1),
            "turns": turns,
            "missed": missed,
            "response_rate": round(response_rate, 1)
        }
    })


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reseta contadores mantendo escuta ativa."""
    with session_state["lock"]:
        session_state["turns"] = 0
        session_state["missed"] = 0
        session_state["events"] = []
        session_state["start_time"] = time.time() if session_state["listening"] else None

    return jsonify({"status": "reset"})


def add_event(event_type, speaker=None, latency=None, pitch=None):
    """Adiciona evento à lista (thread-safe)."""
    with session_state["lock"]:
        # Calcula tempo relativo ao início da sessão
        elapsed = time.time() - session_state["start_time"] if session_state["start_time"] else 0

        event = {
            "time": round(elapsed, 1),
            "type": event_type,  # "speech", "turn", "missed"
        }
        if speaker is not None:
            event["speaker"] = speaker
        if latency is not None:
            event["response_time"] = round(latency, 2)
        if pitch is not None:
            event["pitch"] = int(pitch)

        session_state["events"].append(event)

        # Limita a 100 eventos
        if len(session_state["events"]) > 100:
            session_state["events"] = session_state["events"][-100:]


# ============ DETECÇÃO DE PITCH ============

def yin_pitch(samples, sr=SAMPLE_RATE, fmin=75, fmax=500):
    """
    Estima pitch usando algoritmo YIN simplificado.

    YIN é mais robusto que autocorrelação simples porque
    normaliza a diferença, evitando erros de oitava.

    Retorna None se não detectar voz (unvoiced).
    """
    # Limites de busca em samples
    tau_min = sr // fmax  # 32 para 500Hz
    tau_max = sr // fmin  # 213 para 75Hz

    if len(samples) < tau_max * 2:
        return None

    # Normaliza
    samples = samples.astype(np.float64)
    samples = samples - np.mean(samples)
    if np.max(np.abs(samples)) < 0.01:
        return None

    # Função de diferença (YIN step 2)
    # d(tau) = sum((x[j] - x[j+tau])^2)
    length = len(samples) - tau_max
    diff = np.zeros(tau_max)

    for tau in range(1, tau_max):
        diff[tau] = np.sum((samples[:length] - samples[tau:tau + length]) ** 2)

    # Função de diferença normalizada cumulativa (YIN step 3)
    # Isso evita o problema de sempre escolher tau=0
    diff_norm = np.zeros(tau_max)
    diff_norm[0] = 1
    cumsum = 0

    for tau in range(1, tau_max):
        cumsum += diff[tau]
        diff_norm[tau] = diff[tau] * tau / cumsum if cumsum > 0 else 1

    # Busca o primeiro mínimo abaixo do threshold (YIN step 4)
    threshold = 0.15
    tau_estimate = None

    for tau in range(tau_min, tau_max - 1):
        if diff_norm[tau] < threshold:
            # Verifica se é mínimo local
            if diff_norm[tau] < diff_norm[tau - 1] and diff_norm[tau] <= diff_norm[tau + 1]:
                tau_estimate = tau
                break

    # Se não achou abaixo do threshold, pega o mínimo global
    if tau_estimate is None:
        search = diff_norm[tau_min:tau_max]
        if len(search) == 0 or np.min(search) > 0.5:
            return None  # Provavelmente unvoiced
        tau_estimate = np.argmin(search) + tau_min

    # Interpolação parabólica para precisão sub-sample (YIN step 5)
    if 0 < tau_estimate < tau_max - 1:
        s0 = diff_norm[tau_estimate - 1]
        s1 = diff_norm[tau_estimate]
        s2 = diff_norm[tau_estimate + 1]
        adjustment = (s2 - s0) / (2 * (2 * s1 - s2 - s0 + 1e-10))
        tau_estimate = tau_estimate + adjustment

    if tau_estimate <= 0:
        return None

    return sr / tau_estimate


def estimate_pitch_median(samples, sr=SAMPLE_RATE):
    """Estima pitch usando mediana de várias janelas de 50ms."""
    window = sr * 50 // 1000  # 800 samples
    hop = sr * 25 // 1000     # 400 samples

    pitches = []
    for i in range(0, len(samples) - window, hop):
        p = yin_pitch(samples[i:i + window], sr)
        if p is not None and 75 < p < 500:
            pitches.append(p)

    if not pitches:
        return None

    return float(np.median(pitches))


def classify_speaker(pitch, child_threshold):
    """
    Classifica falante pelo pitch.

    Ranges típicos:
    - Homem: 85-180 Hz
    - Mulher: 165-255 Hz
    - Criança 2-5 anos: 250-400 Hz

    Usamos threshold alto (~280Hz) para evitar
    confundir mulher com criança.
    """
    if pitch is None:
        return "???"
    if pitch >= child_threshold:
        return "CHI"  # Criança
    if pitch < 165:
        return "ADT"  # Adulto (provavelmente homem)
    return "ADT"      # Adulto (mulher ou homem agudo)


def start_audio_stream():
    """Inicia o stream de áudio (chamado pela API)."""
    global audio_stream, detector_state

    vad = webrtcvad.Vad(detector_args.vad)
    detector_state = {
        "in_speech": False,
        "frames": [],
        "silence_count": 0,
        "waiting": False,
        "child_end": 0,
    }

    def on_speech_end():
        """Chamado quando termina um segmento de fala."""
        samples = np.concatenate(detector_state["frames"])
        pitch = estimate_pitch_median(samples)
        speaker = classify_speaker(pitch, detector_args.threshold)

        pitch_str = f"{pitch:.0f}Hz" if pitch else "N/A"

        if speaker == "CHI":
            print(f"{CYAN}[CHI]{RESET} Fala detectada (pitch: {pitch_str})")
            detector_state["waiting"] = True
            detector_state["child_end"] = time.time()

            with session_state["lock"]:
                session_state["current_speaker"] = "CHI"
                session_state["current_pitch"] = int(pitch) if pitch else None
                session_state["last_speech_time"] = time.time()
            add_event("speech", speaker="CHI", pitch=pitch)

        elif speaker == "ADT":
            print(f"{YELLOW}[ADT]{RESET} Fala detectada (pitch: {pitch_str})")

            with session_state["lock"]:
                session_state["current_speaker"] = "ADT"
                session_state["current_pitch"] = int(pitch) if pitch else None
                session_state["last_speech_time"] = time.time()

            if detector_state["waiting"]:
                latency = time.time() - detector_state["child_end"]
                print(f"{GREEN}✓ TURN - resposta em {latency:.1f}s{RESET}")
                detector_state["waiting"] = False

                with session_state["lock"]:
                    session_state["turns"] += 1
                    session_state["response_times"].append(latency)
                add_event("turn", speaker="ADT", latency=latency, pitch=pitch)
            else:
                add_event("speech", speaker="ADT", pitch=pitch)

        else:
            print(f"[???] Fala detectada (pitch: {pitch_str})")

    def audio_callback(indata, frames, time_info, status):
        """Callback do sounddevice - processa áudio em tempo real."""
        if not session_state["listening"]:
            return

        audio = indata[:, 0].astype(np.float32)

        for i in range(0, len(audio) - FRAME_SIZE + 1, FRAME_SIZE):
            frame = audio[i:i + FRAME_SIZE]
            frame_bytes = (frame * 32767).astype(np.int16).tobytes()
            is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)

            if is_speech:
                if not detector_state["in_speech"]:
                    detector_state["in_speech"] = True
                    detector_state["frames"] = []
                    detector_state["silence_count"] = 0
                detector_state["frames"].append(frame.copy())
                detector_state["silence_count"] = 0

            elif detector_state["in_speech"]:
                detector_state["silence_count"] += 1
                if detector_state["silence_count"] > 13:  # ~400ms de silêncio
                    if len(detector_state["frames"]) > 5:  # mínimo ~150ms de fala
                        on_speech_end()
                    detector_state["in_speech"] = False
                    detector_state["frames"] = []

                    # Limpa current_speaker após silêncio
                    with session_state["lock"]:
                        session_state["current_speaker"] = None

    # Inicia stream
    audio_stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=audio_callback,
        blocksize=FRAME_SIZE
    )
    audio_stream.start()

    # Loop de timeout checking
    while session_state["listening"]:
        time.sleep(0.1)
        if detector_state["waiting"] and time.time() - detector_state["child_end"] > detector_args.timeout:
            print(f"{RED}✗ MISSED OPPORTUNITY ({detector_args.timeout:.1f}s sem resposta){RESET}")
            detector_state["waiting"] = False

            with session_state["lock"]:
                session_state["missed"] += 1
            add_event("missed")


def run_flask():
    """Roda servidor Flask em thread separada."""
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)


def main():
    global detector_args

    parser = argparse.ArgumentParser(description="Detector de turnos em tempo real")
    parser.add_argument("--threshold", type=float, default=280.0,
                        help="Pitch mínimo para classificar como criança (default: 280Hz)")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="Segundos para considerar oportunidade perdida (default: 5.0)")
    parser.add_argument("--vad", type=int, default=2, choices=[0, 1, 2, 3],
                        help="Agressividade do VAD 0-3 (default: 2)")
    parser.add_argument("--port", type=int, default=5000,
                        help="Porta da API REST (default: 5000)")
    parser.add_argument("--autostart", action="store_true",
                        help="Inicia escuta automaticamente")
    detector_args = parser.parse_args()

    print("=" * 50)
    print("MAESTRO - Detector de Turnos com API REST")
    print("=" * 50)
    print(f"Threshold criança: >= {detector_args.threshold:.0f}Hz")
    print(f"Timeout resposta: {detector_args.timeout:.1f}s")
    print(f"API REST: http://0.0.0.0:{detector_args.port}")
    print("-" * 50)
    print("Endpoints:")
    print("  GET  /api/status  → estado atual")
    print("  GET  /api/session → dados da sessão")
    print("  POST /api/start   → inicia escuta")
    print("  POST /api/stop    → para escuta")
    print("  POST /api/reset   → reseta contadores")
    print("=" * 50)

    # Inicia Flask em thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Autostart se solicitado
    if detector_args.autostart:
        print("\nIniciando escuta automaticamente...")
        with session_state["lock"]:
            session_state["session_id"] = str(uuid.uuid4())[:8]
            session_state["listening"] = True
            session_state["start_time"] = time.time()
        threading.Thread(target=start_audio_stream, daemon=True).start()

    print("\nAguardando comandos via API... (Ctrl+C para sair)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando...")
        session_state["listening"] = False


if __name__ == "__main__":
    main()
