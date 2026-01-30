#!/usr/bin/env python3
"""
Detector de turnos para Raspberry Pi Zero 2 W.

Funciona standalone (vibra) e serve webapp com dashboard.

Hardware:
    - Pi Zero 2 W
    - Microfone USB ou INMP441 (I2S)
    - Motor vibracall no GPIO 17 (via transistor 2N2222)

Uso:
    python pi_detector.py                 # Inicia detector + webapp
    python pi_detector.py --no-web        # Só detector, sem webapp
    python pi_detector.py --test-vibrate  # Testa motor

Webapp:
    http://<ip-do-pi>:5000

Requisitos:
    pip install sounddevice numpy flask
    # Para GPIO (já vem no Pi):
    # pip install RPi.GPIO
"""

import argparse
import time
import json
import threading
from datetime import datetime
from collections import deque

import numpy as np
import sounddevice as sd

# Tenta importar GPIO (só funciona no Pi)
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("AVISO: RPi.GPIO não disponível (não é Pi?). Vibração desabilitada.")

# Tenta importar Flask
try:
    from flask import Flask, render_template_string, jsonify, request
    from flask_cors import CORS
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("AVISO: Flask não disponível. Webapp desabilitada.")

import uuid


# =============================================================================
# Configuração
# =============================================================================

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SIZE = SAMPLE_RATE * FRAME_MS // 1000

# GPIO
VIBRATE_PIN = 17
VIBRATE_DURATION = 0.3  # segundos

# Detecção
CHILD_PITCH_THRESHOLD = 280  # Hz
MISSED_TIMEOUT = 5.0  # segundos

# Cores terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


# =============================================================================
# Estado Global
# =============================================================================

class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset_session()

    def reset_session(self):
        self.in_speech = False
        self.frames = []
        self.silence_count = 0
        self.waiting_for_adult = False
        self.child_end_time = 0
        self.total_turns = 0
        self.total_missed = 0
        self.total_child_speech = 0
        self.events = deque(maxlen=100)  # Últimos 100 eventos
        self.response_times = []  # Para calcular média
        # API state
        self.session_id = str(uuid.uuid4())[:8]
        self.session_active = True
        self.listening = True
        self.start_time = time.time()
        self.current_speaker = None  # "CHI", "ADT", ou None
        self.current_pitch = None
        self.last_speech_time = None

state = State()


# =============================================================================
# Vibração (GPIO)
# =============================================================================

def vibrate_init():
    """Inicializa GPIO para motor."""
    if not HAS_GPIO:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(VIBRATE_PIN, GPIO.OUT)
    GPIO.output(VIBRATE_PIN, GPIO.LOW)
    print(f"GPIO {VIBRATE_PIN} configurado para vibração")

def vibrate_pulse(duration=VIBRATE_DURATION):
    """Pulso de vibração."""
    if not HAS_GPIO:
        print("[VIBRA - simulado]")
        return
    GPIO.output(VIBRATE_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(VIBRATE_PIN, GPIO.LOW)

def vibrate_cleanup():
    """Limpa GPIO."""
    if HAS_GPIO:
        GPIO.cleanup()


# =============================================================================
# VAD Simples (energia)
# =============================================================================

def is_speech(frame, threshold=0.003):
    """Detecta fala por energia RMS."""
    rms = np.sqrt(np.mean(frame ** 2))
    return rms > threshold


# =============================================================================
# Pitch (YIN)
# =============================================================================

def yin_pitch(samples, sr=SAMPLE_RATE, fmin=75, fmax=500):
    """Estima pitch usando YIN."""
    tau_min = sr // fmax
    tau_max = sr // fmin

    if len(samples) < tau_max * 2:
        return None

    samples = samples.astype(np.float64)
    samples = samples - np.mean(samples)
    if np.max(np.abs(samples)) < 0.01:
        return None

    # Diferença
    length = len(samples) - tau_max
    diff = np.zeros(tau_max)
    for tau in range(1, tau_max):
        diff[tau] = np.sum((samples[:length] - samples[tau:tau + length]) ** 2)

    # Normalização cumulativa
    diff_norm = np.ones(tau_max)
    cumsum = 0
    for tau in range(1, tau_max):
        cumsum += diff[tau]
        if cumsum > 0:
            diff_norm[tau] = diff[tau] * tau / cumsum

    # Busca mínimo
    threshold = 0.15
    for tau in range(tau_min, tau_max - 1):
        if diff_norm[tau] < threshold:
            if diff_norm[tau] < diff_norm[tau - 1] and diff_norm[tau] <= diff_norm[tau + 1]:
                # Interpolação
                if 0 < tau < tau_max - 1:
                    s0, s1, s2 = diff_norm[tau - 1], diff_norm[tau], diff_norm[tau + 1]
                    tau += (s2 - s0) / (2 * (2 * s1 - s2 - s0 + 1e-10))
                return sr / tau if tau > 0 else None

    # Fallback: mínimo global
    search = diff_norm[tau_min:tau_max]
    if len(search) > 0 and np.min(search) < 0.5:
        tau = np.argmin(search) + tau_min
        return sr / tau if tau > 0 else None

    return None


def estimate_pitch(samples):
    """Estima pitch com mediana de várias janelas."""
    window = SAMPLE_RATE * 50 // 1000
    hop = window // 2

    pitches = []
    for i in range(0, len(samples) - window, hop):
        p = yin_pitch(samples[i:i + window])
        if p and 75 < p < 500:
            pitches.append(p)

    return float(np.median(pitches)) if pitches else None


def classify(pitch):
    """Classifica falante."""
    if pitch is None:
        return "???"
    return "CHI" if pitch >= CHILD_PITCH_THRESHOLD else "ADT"


# =============================================================================
# Lógica de Turnos
# =============================================================================

def add_event(event_type, speaker=None, pitch=None, latency=None):
    """Adiciona evento ao histórico."""
    with state.lock:
        elapsed = time.time() - state.start_time if state.start_time else 0
        event = {
            "time": round(elapsed, 1),
            "type": event_type,
        }
        if speaker is not None:
            event["speaker"] = speaker
        if pitch is not None:
            event["pitch"] = int(pitch)
        if latency is not None:
            event["response_time"] = round(latency, 2)
        state.events.append(event)
        print(f"[EVENT] Added: {event}, total events: {len(state.events)}")
        sys.stdout.flush()
        return event


def on_speech_end():
    """Chamado quando termina segmento de fala."""
    samples = np.concatenate(state.frames)
    pitch = estimate_pitch(samples)
    speaker = classify(pitch)

    pitch_str = f"{pitch:.0f}Hz" if pitch else "N/A"

    if speaker == "CHI":
        print(f"{CYAN}[CHI]{RESET} Fala detectada (pitch: {pitch_str})")
        state.waiting_for_adult = True
        state.child_end_time = time.time()
        state.total_child_speech += 1

        with state.lock:
            state.current_speaker = "CHI"
            state.current_pitch = int(pitch) if pitch else None
            state.last_speech_time = time.time()
        add_event("speech", speaker="CHI", pitch=pitch)

    elif speaker == "ADT":
        print(f"{YELLOW}[ADT]{RESET} Fala detectada (pitch: {pitch_str})")

        with state.lock:
            state.current_speaker = "ADT"
            state.current_pitch = int(pitch) if pitch else None
            state.last_speech_time = time.time()

        if state.waiting_for_adult:
            latency = time.time() - state.child_end_time
            print(f"{GREEN}✓ TURN - resposta em {latency:.1f}s{RESET}")
            state.total_turns += 1
            state.waiting_for_adult = False

            with state.lock:
                state.response_times.append(latency)
            add_event("turn", speaker="ADT", pitch=pitch, latency=latency)
        else:
            add_event("speech", speaker="ADT", pitch=pitch)
    else:
        print(f"[???] Fala detectada (pitch: {pitch_str})")


def check_missed():
    """Verifica timeout de resposta."""
    if state.waiting_for_adult:
        elapsed = time.time() - state.child_end_time
        if elapsed > MISSED_TIMEOUT:
            print(f"{RED}✗ MISSED OPPORTUNITY ({MISSED_TIMEOUT:.0f}s sem resposta){RESET}")
            state.total_missed += 1
            state.waiting_for_adult = False
            add_event("missed")

            # VIBRA!
            threading.Thread(target=vibrate_pulse, daemon=True).start()


def clear_speaker_after_silence():
    """Limpa current_speaker após silêncio."""
    with state.lock:
        state.current_speaker = None
        state.current_pitch = None


# =============================================================================
# Callback de Áudio
# =============================================================================

import sys
debug_counter = [0]

def audio_callback(indata, frames, time_info, status):
    """Processa áudio em tempo real."""
    if not state.listening:
        return

    audio = indata[:, 0].astype(np.float32)

    # Debug: show RMS every 50 frames
    debug_counter[0] += 1
    rms = np.sqrt(np.mean(audio ** 2))
    if debug_counter[0] % 50 == 0:
        print(f"[DEBUG] Frame {debug_counter[0]}, RMS: {rms:.4f}, in_speech: {state.in_speech}")
        sys.stdout.flush()

    for i in range(0, len(audio) - FRAME_SIZE + 1, FRAME_SIZE):
        frame = audio[i:i + FRAME_SIZE]
        speech = is_speech(frame)

        if speech:
            if not state.in_speech:
                state.in_speech = True
                state.frames = []
                state.silence_count = 0
            state.frames.append(frame.copy())
            state.silence_count = 0

        elif state.in_speech:
            state.silence_count += 1
            if state.silence_count > 13:  # ~400ms
                if len(state.frames) > 5:  # ~150ms mínimo
                    on_speech_end()
                state.in_speech = False
                state.frames = []
                clear_speaker_after_silence()


# =============================================================================
# Webapp (Flask)
# =============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Maestro - Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #1a1a2e; color: #eee;
            padding: 20px; min-height: 100vh;
        }
        h1 { text-align: center; margin-bottom: 20px; color: #fff; }
        .stats {
            display: grid; grid-template-columns: repeat(3, 1fr);
            gap: 15px; margin-bottom: 30px;
        }
        .stat {
            background: #16213e; padding: 20px; border-radius: 12px;
            text-align: center;
        }
        .stat-value { font-size: 2.5em; font-weight: bold; }
        .stat-label { color: #888; margin-top: 5px; }
        .turns .stat-value { color: #4ade80; }
        .missed .stat-value { color: #f87171; }
        .rate .stat-value { color: #60a5fa; }
        .events {
            background: #16213e; border-radius: 12px; padding: 20px;
        }
        .events h2 { margin-bottom: 15px; font-size: 1.1em; }
        .event {
            padding: 10px; border-bottom: 1px solid #2a2a4a;
            display: flex; justify-content: space-between;
        }
        .event:last-child { border-bottom: none; }
        .event-turn { color: #4ade80; }
        .event-missed { color: #f87171; }
        .event-child { color: #60a5fa; }
        .event-time { color: #666; font-size: 0.9em; }
        .status {
            text-align: center; padding: 10px;
            color: #4ade80; margin-bottom: 20px;
        }
        .status.offline { color: #f87171; }
    </style>
</head>
<body>
    <h1>Maestro</h1>
    <div class="status" id="status">Conectado</div>

    <div class="stats">
        <div class="stat turns">
            <div class="stat-value" id="turns">0</div>
            <div class="stat-label">Turnos</div>
        </div>
        <div class="stat missed">
            <div class="stat-value" id="missed">0</div>
            <div class="stat-label">Perdidos</div>
        </div>
        <div class="stat rate">
            <div class="stat-value" id="rate">-</div>
            <div class="stat-label">Taxa</div>
        </div>
    </div>

    <div class="events">
        <h2>Eventos recentes</h2>
        <div id="events-list"></div>
    </div>

    <script>
        function update() {
            fetch('/api/session')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('turns').textContent = data.turns;
                    document.getElementById('missed').textContent = data.missed;
                    document.getElementById('rate').textContent = data.response_rate.toFixed(0) + '%';
                    document.getElementById('status').textContent = 'Conectado';
                    document.getElementById('status').className = 'status';

                    const list = document.getElementById('events-list');
                    list.innerHTML = data.events.slice(-10).reverse().map(e => {
                        let cls = 'event-child';
                        let text = 'Criança falou';
                        if (e.type === 'turn') { cls = 'event-turn'; text = '✓ Turno (' + (e.response_time || 0).toFixed(1) + 's)'; }
                        if (e.type === 'missed') { cls = 'event-missed'; text = '✗ Oportunidade perdida'; }
                        if (e.type === 'speech' && e.speaker === 'ADT') { cls = 'event-child'; text = 'Adulto falou'; }
                        const mins = Math.floor(e.time / 60);
                        const secs = Math.floor(e.time % 60);
                        const timeStr = mins + ':' + secs.toString().padStart(2, '0');
                        return '<div class="event ' + cls + '"><span>' + text + '</span><span class="event-time">' + timeStr + '</span></div>';
                    }).join('');
                })
                .catch(() => {
                    document.getElementById('status').textContent = 'Desconectado';
                    document.getElementById('status').className = 'status offline';
                });
        }
        update();
        setInterval(update, 1000);
    </script>
</body>
</html>
"""

def create_app():
    """Cria app Flask."""
    app = Flask(__name__)
    CORS(app)  # Permite requisições do Lovable

    @app.route('/')
    def index():
        return render_template_string(DASHBOARD_HTML)

    @app.route('/api/status', methods=['GET'])
    def api_status():
        """Retorna estado atual em tempo real."""
        with state.lock:
            seconds_since = None
            if state.last_speech_time:
                seconds_since = round(time.time() - state.last_speech_time, 1)

            return jsonify({
                "listening": state.listening,
                "current_speaker": state.current_speaker,
                "current_pitch": state.current_pitch,
                "seconds_since_last_speech": seconds_since
            })

    @app.route('/api/session', methods=['GET'])
    def api_session():
        """Retorna resumo da sessão atual."""
        with state.lock:
            turns = state.total_turns
            missed = state.total_missed
            total = turns + missed
            response_rate = (turns / total * 100) if total > 0 else 0
            avg_response = sum(state.response_times) / len(state.response_times) if state.response_times else 0
            duration = time.time() - state.start_time if state.start_time else 0
            started_at = datetime.fromtimestamp(state.start_time).isoformat() + "Z" if state.start_time else None

            return jsonify({
                "session_id": state.session_id,
                "started_at": started_at,
                "duration_seconds": round(duration, 1),
                "turns": turns,
                "missed": missed,
                "response_rate": round(response_rate, 1),
                "avg_response_time": round(avg_response, 2),
                "events": list(state.events)[-50:]
            })

    @app.route('/api/start', methods=['POST'])
    def api_start():
        """Inicia nova sessão de escuta."""
        with state.lock:
            if state.listening:
                return jsonify({"error": "Já está escutando"}), 400

            state.reset_session()
            return jsonify({
                "session_id": state.session_id,
                "status": "started"
            })

    @app.route('/api/stop', methods=['POST'])
    def api_stop():
        """Para sessão atual e retorna resumo."""
        with state.lock:
            if not state.listening:
                return jsonify({"error": "Não está escutando"}), 400

            state.listening = False
            turns = state.total_turns
            missed = state.total_missed
            total = turns + missed
            response_rate = (turns / total * 100) if total > 0 else 0
            duration = time.time() - state.start_time if state.start_time else 0

            return jsonify({
                "session_id": state.session_id,
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
        was_listening = state.listening
        state.reset_session()
        state.listening = was_listening
        return jsonify({"status": "reset", "session_id": state.session_id})

    # Endpoint legado para compatibilidade com dashboard
    @app.route('/api/legacy_status', methods=['GET'])
    def api_legacy_status():
        total = state.total_turns + state.total_missed
        rate = f"{100 * state.total_turns / total:.0f}%" if total > 0 else "-"
        return jsonify({
            "turns": state.total_turns,
            "missed": state.total_missed,
            "child_speech": state.total_child_speech,
            "rate": rate,
            "events": list(state.events),
            "uptime": int(time.time() - state.start_time),
        })

    return app


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Detector de turnos para Pi Zero")
    parser.add_argument("--no-web", action="store_true", help="Não iniciar webapp")
    parser.add_argument("--port", type=int, default=5000, help="Porta da webapp")
    parser.add_argument("--test-vibrate", action="store_true", help="Testar motor e sair")
    parser.add_argument("--threshold", type=float, default=280, help="Threshold de pitch (Hz)")
    args = parser.parse_args()

    global CHILD_PITCH_THRESHOLD
    CHILD_PITCH_THRESHOLD = args.threshold

    # Teste de vibração
    if args.test_vibrate:
        print("Testando vibração...")
        vibrate_init()
        vibrate_pulse(0.5)
        print("Feito!")
        vibrate_cleanup()
        return

    # Inicializa
    vibrate_init()

    print("=" * 50)
    print("MAESTRO - Detector de Turnos com API REST")
    print("=" * 50)
    print(f"Threshold criança: >= {CHILD_PITCH_THRESHOLD}Hz")
    print(f"Timeout resposta: {MISSED_TIMEOUT}s")

    # Inicia webapp em thread separada
    if HAS_FLASK and not args.no_web:
        import socket
        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname + ".local")
        except:
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except:
                ip = "localhost"

        print(f"API REST: http://{ip}:{args.port}")
        print("-" * 50)
        print("Endpoints:")
        print("  GET  /api/status  - estado atual")
        print("  GET  /api/session - dados da sessao")
        print("  POST /api/start   - inicia escuta")
        print("  POST /api/stop    - para escuta")
        print("  POST /api/reset   - reseta contadores")

        app = create_app()
        web_thread = threading.Thread(
            target=lambda: app.run(host='0.0.0.0', port=args.port, debug=False, use_reloader=False),
            daemon=True
        )
        web_thread.start()

    print("=" * 50)
    print("Escutando... (Ctrl+C para parar)")
    print()

    try:
        # device=1 para usar Intel Microphone Array no Windows
        with sd.InputStream(
            device=1,
            samplerate=SAMPLE_RATE,
            channels=1,
            callback=audio_callback,
            blocksize=FRAME_SIZE
        ):
            while True:
                sd.sleep(100)
                check_missed()

    except KeyboardInterrupt:
        print("\nParando...")
    finally:
        vibrate_cleanup()
        print(f"\nResumo da sessão:")
        print(f"  Turnos completados: {state.total_turns}")
        print(f"  Oportunidades perdidas: {state.total_missed}")
        total = state.total_turns + state.total_missed
        if total > 0:
            print(f"  Taxa de sucesso: {100 * state.total_turns / total:.0f}%")


if __name__ == "__main__":
    main()
