#!/usr/bin/env python3
"""
MAESTRO - Detector de Momentos de Conversa

Um coach gentil que celebra conexoes entre pais e filhos.
Detecta momentos de conversa (crianca e adulto falando em sequencia)
e oferece feedback positivo sutil.

Filosofia:
- Celebra acertos, nunca aponta erros
- Aceita que audio so captura parte da interacao
- Tom sempre esperancoso e encorajador
- 100% offline, funciona em qualquer lugar

Uso:
    python realtime_detector.py --autostart
"""

import argparse
import time
import threading
import uuid
import json
import os
import random
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import sounddevice as sd
import webrtcvad
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

# OpenAI API for coaching (optional)
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# GPIO para Raspberry Pi (opcional)
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

# ============ CONFIGURACOES ============

# Audio
SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SIZE = SAMPLE_RATE * FRAME_MS // 1000  # 480 samples

# Deteccao CONSERVADORA (alta confianca, sem falsos positivos)
MIN_SPEECH_DURATION_MS = 500    # Minimo 0.5s para contar como fala
MIN_SPEECH_FRAMES = int(MIN_SPEECH_DURATION_MS / FRAME_MS)
IGNORE_DURATION_MS = 300        # Ignora sons < 0.3s
IGNORE_FRAMES = int(IGNORE_DURATION_MS / FRAME_MS)
CONVERSATION_WINDOW_S = 15.0    # Janela GENEROSA de 15 segundos
PITCH_CONFIDENCE_MIN = 0.85     # 85% confianca para classificar

# Cores ANSI (para console)
GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"

# GPIO (LED verde para feedback positivo)
LED_PIN = 17
LED_DURATION_MS = 2000  # LED suave por 2 segundos


# ============ GPIO / LED (FEEDBACK POSITIVO) ============

def led_init():
    """Inicializa GPIO para LED de feedback positivo (só no Pi)."""
    if not HAS_GPIO:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)


def led_success(duration_ms=LED_DURATION_MS):
    """
    Acende LED verde para feedback positivo.

    No Raspberry Pi: acende LED por 2 segundos.
    No PC: não faz nada (feedback só no console).
    """
    if HAS_GPIO:
        def pulse():
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(duration_ms / 1000.0)
            GPIO.output(LED_PIN, GPIO.LOW)
        threading.Thread(target=pulse, daemon=True).start()


def gpio_cleanup():
    """Limpa GPIO ao encerrar."""
    if HAS_GPIO:
        GPIO.cleanup()


# ============ PERSISTENCIA LOCAL (OFFLINE-FIRST) ============

# Diretorios
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data" / "sessions"
CONTENT_DIR = SCRIPT_DIR / "content"

# Supabase (opcional)


# ============ CONTEUDO EDUCACIONAL ============

def load_weekly_content():
    """Carrega dicas e frases do arquivo JSON."""
    content_file = CONTENT_DIR / "weekly_tips.json"
    if content_file.exists():
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    # Fallback se arquivo nao existir
    return {
        "tips": [
            {"week": 1, "tip": "Quando seu filho apontar pra algo, diga o nome do objeto", "title": "Nomeie o mundo"},
            {"week": 2, "tip": "Tente narrar o que voces estao fazendo juntos", "title": "Narre o momento"},
            {"week": 3, "tip": "Deixe seu filho liderar a brincadeira por 5 minutos", "title": "Siga a lideranca"},
            {"week": 4, "tip": "Faca uma pausa e espere ele responder antes de falar de novo", "title": "Espere a resposta"},
            {"week": 5, "tip": "Quando ele mudar de atividade, descreva a transicao", "title": "Descreva transicoes"},
        ],
        "encouragements": [
            "Voces estao construindo conexao!",
            "Cada conversa importa.",
            "Voce esta fazendo a diferenca.",
        ],
        "positive_trends": {
            "up": ["Que semana incrivel! {percent}% mais momentos de conversa!"],
            "stable": ["Consistencia e chave! Voces mantiveram o ritmo."],
            "down": ["Semana corrida? Normal! O importante e continuar."]
        }
    }


def get_week_number():
    """Retorna numero da semana do ano (1-52)."""
    return datetime.now().isocalendar()[1]


def get_current_tip():
    """Retorna a dica da semana atual (rotaciona a cada 7 dias)."""
    content = load_weekly_content()
    tips = content.get("tips", [])
    if not tips:
        return None
    # Rotaciona baseado na semana do ano
    week_num = get_week_number()
    tip_index = (week_num - 1) % len(tips)
    return tips[tip_index]


def get_encouragement():
    """Retorna uma frase de encorajamento aleatoria."""
    content = load_weekly_content()
    phrases = content.get("encouragements", ["Voces estao construindo conexao!"])
    return random.choice(phrases)


def get_trend_message(trend, percent_change):
    """Retorna mensagem positiva baseada na tendencia."""
    content = load_weekly_content()
    trends = content.get("positive_trends", {})
    messages = trends.get(trend, ["Continue assim!"])
    message = random.choice(messages)
    return message.replace("{percent}", str(abs(int(percent_change))))
try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


def ensure_data_dir():
    """Cria diretório de dados se não existir."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_session_filepath(start_time=None):
    """Retorna path do arquivo JSON para a sessão atual."""
    if start_time is None:
        start_time = session_state.get("start_time", time.time())
    dt = datetime.fromtimestamp(start_time)
    filename = dt.strftime("%Y-%m-%d_%H-%M") + ".json"
    return DATA_DIR / filename


def save_session_to_json():
    """Salva sessao atual em arquivo JSON local."""
    with session_state["lock"]:
        if not session_state["start_time"]:
            return None

        moments = session_state["moments"]
        child_speech = session_state["child_speech"]
        adult_speech = session_state["adult_speech"]
        duration = time.time() - session_state["start_time"]
        hours = duration / 3600 if duration > 0 else 0

        data = {
            "session_id": session_state["session_id"],
            "started_at": datetime.fromtimestamp(session_state["start_time"]).isoformat() + "Z",
            "ended_at": datetime.now().isoformat() + "Z",
            "duration_seconds": round(duration, 1),
            "duration_minutes": round(duration / 60, 1),
            "moments": moments,
            "child_speech": child_speech,
            "adult_speech": adult_speech,
            "moments_per_hour": round(moments / hours, 1) if hours > 0.01 else 0,
            "response_times": [round(t, 2) for t in session_state["response_times"]],
            "events": session_state["events"],
            "synced": False
        }

    ensure_data_dir()
    filepath = get_session_filepath()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"{GREEN}[SAVE]{RESET} Sessao salva: {filepath.name}")
    return filepath


def load_session_from_json(filepath):
    """Carrega sessão de arquivo JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_local_sessions():
    """Lista todas as sessões salvas localmente."""
    ensure_data_dir()
    sessions = []
    for f in sorted(DATA_DIR.glob("*.json"), reverse=True):
        try:
            data = load_session_from_json(f)
            sessions.append({
                "filename": f.name,
                "session_id": data.get("session_id"),
                "started_at": data.get("started_at"),
                "duration_minutes": data.get("duration_minutes", round(data.get("duration_seconds", 0) / 60, 1)),
                "moments": data.get("moments", data.get("verbal_turns", data.get("turns", 0))),
                "synced": data.get("synced", False)
            })
        except Exception as e:
            print(f"Erro ao ler {f.name}: {e}")
    return sessions


def get_unsynced_sessions():
    """Retorna sessões que ainda não foram sincronizadas."""
    ensure_data_dir()
    unsynced = []
    for f in DATA_DIR.glob("*.json"):
        try:
            data = load_session_from_json(f)
            if not data.get("synced", False):
                unsynced.append((f, data))
        except:
            pass
    return unsynced


def sync_to_supabase():
    """Sincroniza sessões não sincronizadas com Supabase."""
    if not HAS_SUPABASE:
        return {"error": "Supabase nao instalado (pip install supabase)"}

    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"error": "SUPABASE_URL e SUPABASE_KEY nao configurados"}

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return {"error": f"Erro ao conectar: {e}"}

    unsynced = get_unsynced_sessions()
    synced_count = 0
    errors = []

    for filepath, data in unsynced:
        try:
            # Remove campos locais antes de enviar
            sync_data = {k: v for k, v in data.items() if k != "synced"}

            # Insere no Supabase
            client.table("sessions").upsert(sync_data, on_conflict="session_id").execute()

            # Marca como sincronizado
            data["synced"] = True
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            synced_count += 1
            print(f"{GREEN}[SYNC]{RESET} {filepath.name} sincronizado")

        except Exception as e:
            errors.append(f"{filepath.name}: {e}")
            print(f"[SYNC ERROR] {filepath.name}: {e}")

    return {
        "synced": synced_count,
        "pending": len(unsynced) - synced_count,
        "errors": errors if errors else None
    }


# ============ AGREGAÇÃO DE DADOS (SUMMARY) ============

def get_sessions_in_date_range(start_date, end_date):
    """Retorna sessões dentro de um período de datas."""
    ensure_data_dir()
    sessions = []
    for f in DATA_DIR.glob("*.json"):
        try:
            # Extrai data do nome do arquivo (YYYY-MM-DD_HH-MM.json)
            file_date_str = f.stem[:10]  # "2026-01-27"
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d").date()

            if start_date <= file_date <= end_date:
                data = load_session_from_json(f)
                data["_file_date"] = file_date.isoformat()
                sessions.append(data)
        except Exception:
            pass
    return sessions


def aggregate_sessions(sessions):
    """Agrega dados de multiplas sessoes (terminologia positiva)."""
    if not sessions:
        return {
            "total_minutes": 0,
            "moments": 0,
            "child_speech": 0,
            "adult_speech": 0,
            "moments_per_hour": 0,
            "session_count": 0
        }

    total_seconds = sum(s.get("duration_seconds", 0) for s in sessions)
    # Suporta formatos antigos e novos
    total_moments = sum(s.get("moments", s.get("verbal_turns", s.get("turns", 0))) for s in sessions)
    total_child = sum(s.get("child_speech", s.get("child_serves", 0)) for s in sessions)
    total_adult = sum(s.get("adult_speech", 0) for s in sessions)

    hours = total_seconds / 3600 if total_seconds > 0 else 0

    return {
        "total_minutes": round(total_seconds / 60, 1),
        "moments": total_moments,
        "child_speech": total_child,
        "adult_speech": total_adult,
        "moments_per_hour": round(total_moments / hours, 1) if hours > 0.01 else 0,
        "session_count": len(sessions)
    }


def get_best_day_of_week(sessions):
    """Encontra o dia da semana com mais interações (tom positivo)."""
    from collections import defaultdict

    # Agrupa por dia da semana
    days = defaultdict(lambda: {"moments": 0, "minutes": 0})
    day_names = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]

    for s in sessions:
        try:
            started = s.get("started_at", "")
            if started:
                dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                weekday = dt.weekday()
                days[weekday]["moments"] += s.get("moments", s.get("verbal_turns", s.get("turns", 0)))
                days[weekday]["minutes"] += s.get("duration_seconds", 0) / 60
        except:
            pass

    # Encontra o dia com mais momentos (positivo)
    best_day = None
    most_moments = 0

    for weekday, data in days.items():
        if data["moments"] > most_moments:
            most_moments = data["moments"]
            hours = data["minutes"] / 60 if data["minutes"] > 0 else 0
            best_day = {
                "day": day_names[weekday],
                "moments": data["moments"],
                "minutes": round(data["minutes"], 1),
                "moments_per_hour": round(data["moments"] / hours, 1) if hours > 0.01 else 0
            }

    return best_day


def get_weekly_summary(include_previous=False):
    """Retorna resumo da semana atual e opcionalmente da anterior (tom positivo)."""
    today = datetime.now().date()

    # Semana atual (segunda a domingo)
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = today

    current_sessions = get_sessions_in_date_range(week_start, week_end)
    current_summary = aggregate_sessions(current_sessions)
    current_summary["highlight_day"] = get_best_day_of_week(current_sessions)
    current_summary["period"] = {
        "start": week_start.isoformat(),
        "end": week_end.isoformat()
    }

    result = {"current_week": current_summary}

    if include_previous:
        # Semana anterior
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start - timedelta(days=1)

        prev_sessions = get_sessions_in_date_range(prev_week_start, prev_week_end)
        prev_summary = aggregate_sessions(prev_sessions)
        prev_summary["period"] = {
            "start": prev_week_start.isoformat(),
            "end": prev_week_end.isoformat()
        }

        result["previous_week"] = prev_summary

        # Calcula evolução (tom neutro/positivo)
        if prev_summary["session_count"] > 0 and current_summary["session_count"] > 0:
            comparison = {}

            # Tempo de interação
            if prev_summary["total_minutes"] > 0:
                minutes_change = ((current_summary["total_minutes"] - prev_summary["total_minutes"]) / prev_summary["total_minutes"]) * 100
                comparison["time_change_percent"] = round(minutes_change, 1)

            # Mudança em momentos por hora (métrica mais justa)
            if prev_summary["moments_per_hour"] > 0:
                rate_change = current_summary["moments_per_hour"] - prev_summary["moments_per_hour"]
                comparison["moments_per_hour_change"] = round(rate_change, 1)

            # Total de momentos
            moments_change = current_summary["moments"] - prev_summary["moments"]
            comparison["moments_change"] = moments_change

            result["comparison"] = comparison

    return result


# Auto-save thread
auto_save_enabled = True

def auto_save_loop():
    """Loop de auto-save a cada 30 segundos."""
    while auto_save_enabled:
        time.sleep(30)
        if session_state["listening"] and session_state["start_time"]:
            save_session_to_json()


# Flask app
app = Flask(__name__)
CORS(app)  # Permite requisições do Lovable
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Estado global da sessão (thread-safe)
session_state = {
    "listening": False,
    "current_speaker": None,  # "ADT", "CHI", ou None
    "current_pitch": None,
    "last_speech_time": None,
    "session_id": None,
    "moments": 0,            # Momentos de conversa detectados (crianca + adulto)
    "child_speech": 0,       # Vezes que crianca falou
    "adult_speech": 0,       # Vezes que adulto falou
    "response_times": [],    # Para estatisticas (sem julgamento)
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
    """Retorna dados da sessao atual (tom positivo)."""
    with session_state["lock"]:
        moments = session_state["moments"]
        child_speech = session_state["child_speech"]
        adult_speech = session_state["adult_speech"]
        duration = time.time() - session_state["start_time"] if session_state["start_time"] else 0
        started_at = datetime.fromtimestamp(session_state["start_time"]).isoformat() + "Z" if session_state["start_time"] else None

        hours = duration / 3600 if duration > 0 else 0
        moments_per_hour = round(moments / hours, 1) if hours > 0.01 else 0

        return jsonify({
            "session_id": session_state["session_id"],
            "started_at": started_at,
            "duration_minutes": round(duration / 60, 1),
            "moments": moments,
            "child_speech": child_speech,
            "adult_speech": adult_speech,
            "moments_per_hour": moments_per_hour,
            "events": session_state["events"][-50:]
        })


@app.route('/api/start', methods=['POST'])
def api_start():
    """Inicia sessao de escuta."""
    global audio_stream

    with session_state["lock"]:
        if session_state["listening"]:
            return jsonify({"message": "Ja esta escutando", "session_id": session_state["session_id"]}), 200

        # Nova sessao
        new_session_id = str(uuid.uuid4())[:8]
        session_state["session_id"] = new_session_id
        session_state["listening"] = True
        session_state["current_speaker"] = None
        session_state["current_pitch"] = None
        session_state["last_speech_time"] = None
        session_state["moments"] = 0
        session_state["child_speech"] = 0
        session_state["adult_speech"] = 0
        session_state["response_times"] = []
        session_state["events"] = []
        session_state["start_time"] = time.time()

    threading.Thread(target=start_audio_stream, daemon=True).start()

    return jsonify({"session_id": new_session_id, "status": "started"})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Para sessao e salva dados localmente."""
    global audio_stream

    saved_file = save_session_to_json()

    with session_state["lock"]:
        if not session_state["listening"]:
            return jsonify({"message": "Nao estava escutando"}), 200

        session_state["listening"] = False
        session_state["current_speaker"] = None
        session_state["current_pitch"] = None

        moments = session_state["moments"]
        duration = time.time() - session_state["start_time"] if session_state["start_time"] else 0
        sid = session_state["session_id"]

    if audio_stream:
        audio_stream.stop()
        audio_stream.close()
        audio_stream = None

    hours = duration / 3600 if duration > 0 else 0
    encouragement = get_encouragement()

    return jsonify({
        "session_id": sid,
        "status": "stopped",
        "saved_to": saved_file.name if saved_file else None,
        "summary": {
            "duration_minutes": round(duration / 60, 1),
            "moments": moments,
            "moments_per_hour": round(moments / hours, 1) if hours > 0.01 else 0
        },
        "encouragement": encouragement
    })


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reseta contadores mantendo escuta ativa."""
    with session_state["lock"]:
        session_state["moments"] = 0
        session_state["child_speech"] = 0
        session_state["adult_speech"] = 0
        session_state["response_times"] = []
        session_state["events"] = []
        session_state["start_time"] = time.time() if session_state["listening"] else None

    return jsonify({"status": "reset", "message": "Pronto para novos momentos!"})


@app.route('/api/sessions', methods=['GET'])
def api_list_sessions():
    """Lista todas as sessões salvas localmente."""
    sessions = list_local_sessions()
    return jsonify({
        "sessions": sessions,
        "total": len(sessions),
        "data_dir": str(DATA_DIR)
    })


@app.route('/api/sessions/<filename>', methods=['GET'])
def api_get_session(filename):
    """Retorna dados de uma sessão salva específica."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return jsonify({"error": "Sessao nao encontrada"}), 404
    try:
        data = load_session_from_json(filepath)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sync', methods=['POST'])
def api_sync():
    """Sincroniza sessões pendentes com Supabase."""
    result = sync_to_supabase()
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/save', methods=['POST'])
def api_save():
    """Força salvamento da sessão atual."""
    if not session_state["listening"]:
        return jsonify({"error": "Nenhuma sessao ativa"}), 400
    filepath = save_session_to_json()
    return jsonify({
        "status": "saved",
        "filename": filepath.name if filepath else None
    })


@app.route('/api/weekly', methods=['GET'])
def api_weekly():
    """
    Resumo semanal com tom positivo e dica educacional.

    Retorna:
    - moments: numero de momentos de conversa da semana
    - trend: "up", "down", ou "stable"
    - tip: dica da semana (rotaciona automaticamente)
    - encouragement: frase positiva
    """
    today = datetime.now().date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    # Semana atual
    current_sessions = get_sessions_in_date_range(week_start, today)
    current_data = aggregate_sessions(current_sessions)
    current_moments = current_data.get("moments", current_data.get("verbal_turns", 0))
    current_minutes = current_data.get("total_minutes", 0)

    # Semana anterior
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)
    prev_sessions = get_sessions_in_date_range(prev_week_start, prev_week_end)
    prev_data = aggregate_sessions(prev_sessions)
    prev_moments = prev_data.get("moments", prev_data.get("verbal_turns", 0))

    # Calcula tendencia (sempre positiva)
    if prev_moments == 0:
        trend = "stable"
        percent_change = 0
    elif current_moments > prev_moments:
        trend = "up"
        percent_change = ((current_moments - prev_moments) / prev_moments) * 100
    elif current_moments < prev_moments:
        trend = "down"
        percent_change = ((prev_moments - current_moments) / prev_moments) * 100
    else:
        trend = "stable"
        percent_change = 0

    # Conteudo educacional
    tip = get_current_tip()
    encouragement = get_encouragement()
    trend_message = get_trend_message(trend, percent_change)

    # Momentos por hora (metrica justa)
    hours = current_minutes / 60 if current_minutes > 0 else 0
    moments_per_hour = round(current_moments / hours, 1) if hours > 0.1 else 0

    # Atividade sugerida do Harvard CDC
    cdc_data = load_harvard_cdc()
    suggested_activity = None
    if cdc_data and "activities_by_area" in cdc_data:
        areas = list(cdc_data["activities_by_area"].values())
        area = random.choice(areas)
        if area.get("activities"):
            activity = random.choice(area["activities"])
            suggested_activity = {
                "area": area.get("description", ""),
                "title": activity["title"],
                "description": activity["description"],
                "why": activity["why"],
                "ages": activity["ages"]
            }

    return jsonify({
        "week": {
            "start": week_start.isoformat(),
            "end": today.isoformat(),
            "moments": current_moments,
            "minutes": round(current_minutes, 1),
            "moments_per_hour": moments_per_hour,
            "sessions": current_data.get("session_count", 0)
        },
        "trend": trend,
        "trend_message": trend_message,
        "tip": {
            "title": tip.get("title") if tip else "Conecte-se",
            "text": tip.get("tip") if tip else "Cada momento de conversa conta!",
            "example": tip.get("example") if tip else None
        },
        "encouragement": encouragement,
        "comparison": {
            "previous_moments": prev_moments,
            "change_percent": round(percent_change, 1) if trend != "stable" else 0
        },
        "activity": suggested_activity
    })


@app.route('/api/summary', methods=['GET'])
def api_summary():
    """
    Resumo da sessao atual e dados da semana (tom positivo).

    Query params:
        - weekly: "true" para forçar resumo semanal (default: só domingos)
        - compare: "true" para incluir comparação com semana anterior
    """
    force_weekly = request.args.get("weekly", "").lower() == "true"
    include_compare = request.args.get("compare", "").lower() == "true"

    is_sunday = datetime.now().weekday() == 6

    result = {}

    # 1. Sessão atual
    with session_state["lock"]:
        if session_state["listening"] and session_state["start_time"]:
            duration = time.time() - session_state["start_time"]
            moments = session_state["moments"]
            hours = duration / 3600 if duration > 0 else 0

            result["current_session"] = {
                "active": True,
                "session_id": session_state["session_id"],
                "minutes": round(duration / 60, 1),
                "moments": moments,
                "child_speech": session_state["child_speech"],
                "moments_per_hour": round(moments / hours, 1) if hours > 0.01 else 0
            }
        else:
            result["current_session"] = {"active": False}

    # 2. Resumo semanal (domingos ou quando solicitado)
    if is_sunday or force_weekly:
        weekly = get_weekly_summary(include_previous=include_compare or is_sunday)
        result["weekly"] = weekly
        result["show_weekly"] = True
        result["weekly_reason"] = "domingo" if is_sunday else "solicitado"
    else:
        result["show_weekly"] = False
        result["weekly_hint"] = "Use ?weekly=true para ver resumo semanal"

    # 3. Hoje
    today = datetime.now().date()
    today_sessions = get_sessions_in_date_range(today, today)
    result["today"] = aggregate_sessions(today_sessions)

    return jsonify(result)


def load_harvard_cdc():
    """Carrega base de conhecimento do Harvard CDC."""
    cdc_file = CONTENT_DIR / "harvard_cdc.json"
    if cdc_file.exists():
        try:
            with open(cdc_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None


def build_coaching_context(cdc_data, tip):
    """Monta contexto educacional para o coaching baseado no Harvard CDC."""
    parts = []

    # Serve-and-return steps
    if cdc_data and "serve_and_return" in cdc_data:
        sr = cdc_data["serve_and_return"]
        steps_text = "\n".join(
            f"  {s['step']}. {s['name']}: {s['description']}"
            for s in sr["steps"]
        )
        parts.append(f"OS 5 PASSOS DE SERVE-AND-RETURN (Harvard CDC):\n{steps_text}")

    # Brain architecture facts
    if cdc_data and "brain_architecture" in cdc_data:
        facts = "\n".join(f"  - {f}" for f in cdc_data["brain_architecture"]["key_facts"][:3])
        parts.append(f"ARQUITETURA CEREBRAL:\n{facts}")

    # Pick a random activity from the knowledge base
    if cdc_data and "activities_by_area" in cdc_data:
        areas = list(cdc_data["activities_by_area"].values())
        area = random.choice(areas)
        if area.get("activities"):
            activity = random.choice(area["activities"])
            parts.append(
                f"ATIVIDADE SUGERIDA ({area['description']}):\n"
                f"  {activity['title']} (idades {activity['ages']}): {activity['description']}\n"
                f"  Por que funciona: {activity['why']}"
            )

    # Three principles
    if cdc_data and "three_principles" in cdc_data:
        principle = random.choice(cdc_data["three_principles"]["principles"])
        parts.append(
            f"PRINCIPIO HARVARD CDC: {principle['name']}\n"
            f"  {principle['description']}\n"
            f"  Para o Maestro: {principle['for_maestro']}"
        )

    # Current weekly tip
    if tip:
        parts.append(f"DICA DA SEMANA: {tip.get('title', '')} - {tip.get('tip', '')}")

    return "\n\n".join(parts)


@app.route('/api/coaching', methods=['POST'])
def api_coaching():
    """Gera dica personalizada usando OpenAI API com base no Harvard CDC."""
    if not HAS_OPENAI:
        return jsonify({"error": "openai nao instalado (pip install openai)"}), 400

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY nao configurada"}), 400

    # Coleta dados da sessao
    with session_state["lock"]:
        moments = session_state["moments"]
        child_speech = session_state["child_speech"]
        adult_speech = session_state["adult_speech"]
        duration = time.time() - session_state["start_time"] if session_state["start_time"] else 0
        events = session_state["events"][-30:]

    hours = duration / 3600 if duration > 0 else 0
    moments_per_hour = round(moments / hours, 1) if hours > 0.01 else 0

    # Carrega conhecimento Harvard CDC e dica da semana
    cdc_data = load_harvard_cdc()
    tip = get_current_tip()
    educational_context = build_coaching_context(cdc_data, tip)

    system_prompt = """Voce e o Maestro, um coach gentil de conexao familiar baseado na ciencia do
Harvard Center on the Developing Child.

SUA BASE CIENTIFICA:
- Serve-and-return: interacoes responsivas constroem a arquitetura cerebral
- Mais de 1 milhao de conexoes neurais se formam por segundo nos primeiros anos
- Funcao executiva (planejar, focar, lembrar) se desenvolve atraves de interacoes
- Relacoes responsivas sao a influencia MAIS IMPORTANTE no desenvolvimento
- Estresse toxico e prevenido por conexoes afetivas estaveis

COMO USAR A CIENCIA:
- Conecte a dica a um dos 5 passos de serve-and-return quando relevante
- Sugira atividades concretas e simples baseadas na faixa etaria
- Explique brevemente POR QUE a atividade funciona (a ciencia por tras)
- Use a linguagem do Harvard CDC: "momentos de conexao", "arquitetura cerebral", "serve-and-return"

REGRAS ABSOLUTAS:
- Responda SEMPRE em portugues brasileiro
- Tom SEMPRE positivo, encorajador, esperancoso
- NUNCA use palavras negativas: "perdeu", "falhou", "errou", "faltou"
- NUNCA julgue ou critique o pai/mae
- Celebre o que JA ESTA SENDO FEITO antes de sugerir algo novo
- Reconheca que audio so captura PARTE da interacao (olhares e toques tambem contam!)
- Maximo 4 frases curtas
- Inclua UMA sugestao pratica de atividade quando possivel"""

    user_prompt = f"""DADOS DA SESSAO:
- Momentos de conversa detectados: {moments}
- Fala da crianca: {child_speech} vezes
- Fala do adulto: {adult_speech} vezes
- Duracao: {round(duration / 60, 1)} minutos
- Momentos por hora: {moments_per_hour}

CONTEXTO EDUCACIONAL:
{educational_context}

Baseado nos dados da sessao e no contexto educacional acima, gere UMA dica personalizada
e encorajadora. Conecte com a ciencia do Harvard CDC e sugira uma atividade pratica."""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        coaching_text = response.choices[0].message.content
        return jsonify({"coaching": coaching_text})
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar coaching: {e}"}), 500


@app.route('/api/activities', methods=['GET'])
def api_activities():
    """Retorna atividades do Harvard CDC filtradas por area ou idade."""
    cdc_data = load_harvard_cdc()
    if not cdc_data:
        return jsonify({"error": "Base de conhecimento nao encontrada"}), 404

    area = request.args.get("area")  # linguagem, cognitivo, socioemocional, motor
    age = request.args.get("age")    # e.g. "0-1", "1-3", "3-6"

    activities = cdc_data.get("activities_by_area", {})

    if area and area in activities:
        return jsonify({"area": area, "activities": activities[area]})

    # Return all areas with optional age filtering
    result = {}
    for area_key, area_data in activities.items():
        area_activities = area_data.copy()
        if age:
            area_activities["activities"] = [
                a for a in area_data.get("activities", [])
                if age in a.get("ages", "")
            ]
        result[area_key] = area_activities

    return jsonify({
        "activities": result,
        "milestones": cdc_data.get("developmental_milestones", {}),
        "executive_function": cdc_data.get("executive_function", {})
    })


@app.route('/api/science', methods=['GET'])
def api_science():
    """Retorna conteudo cientifico do Harvard CDC para a UI."""
    cdc_data = load_harvard_cdc()
    if not cdc_data:
        return jsonify({"error": "Base de conhecimento nao encontrada"}), 404

    return jsonify({
        "serve_and_return": cdc_data.get("serve_and_return", {}),
        "brain_architecture": cdc_data.get("brain_architecture", {}),
        "three_principles": cdc_data.get("three_principles", {}),
        "stress_responses": cdc_data.get("stress_responses", {})
    })


def add_event(event_type, speaker=None, latency=None, pitch=None, note=None):
    """Adiciona evento à lista (thread-safe)."""
    with session_state["lock"]:
        elapsed = time.time() - session_state["start_time"] if session_state["start_time"] else 0

        event = {
            "time": round(elapsed, 1),
            "type": event_type,  # "serve", "turn", "speech", "silence", "uncertain"
        }
        if speaker is not None:
            event["speaker"] = speaker
        if latency is not None:
            event["response_time"] = round(latency, 2)
        if pitch is not None:
            event["pitch"] = int(pitch)
        if note is not None:
            event["note"] = note

        session_state["events"].append(event)

        # Limita a 200 eventos para análise posterior
        if len(session_state["events"]) > 200:
            session_state["events"] = session_state["events"][-200:]


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
    Classifica falante pelo pitch com nível de confiança.

    Ranges típicos:
    - Homem: 85-180 Hz
    - Mulher: 165-255 Hz
    - Criança 2-5 anos: 250-400 Hz

    Retorna (speaker, confidence) onde confidence é 0.0-1.0.
    Só classifica como CHI se confiança >= PITCH_CONFIDENCE_THRESHOLD.
    """
    if pitch is None:
        return "???", 0.0

    # Confiança aumenta quanto mais longe do limiar
    if pitch >= child_threshold:
        # Quanto mais alto o pitch, mais certeza de criança
        # 280Hz = 80% confiança, 350Hz+ = 100%
        confidence = min(1.0, 0.8 + (pitch - child_threshold) / 350)
        if confidence >= PITCH_CONFIDENCE_MIN:
            return "CHI", confidence
        else:
            return "???", confidence  # Incerto, não classifica

    elif pitch < 165:
        # Claramente adulto (homem)
        confidence = min(1.0, (165 - pitch) / 80 + 0.7)
        return "ADT", confidence

    else:
        # Zona ambígua (165-280Hz) - provavelmente mulher
        # Menor confiança, mas classifica como adulto
        distance_from_child = child_threshold - pitch
        confidence = 0.5 + (distance_from_child / (child_threshold - 165)) * 0.3
        return "ADT", confidence


def start_audio_stream():
    """Inicia o stream de audio - detecta momentos de conversa."""
    global audio_stream, detector_state

    vad = webrtcvad.Vad(detector_args.vad)
    detector_state = {
        "in_speech": False,
        "frames": [],
        "silence_count": 0,
        "awaiting_conversation": False,  # Crianca falou, aguardando adulto
        "child_speech_time": 0,
    }

    def on_speech_end():
        """Chamado quando termina um segmento de fala."""
        num_frames = len(detector_state["frames"])

        # Ignora sons muito curtos (< 0.3s)
        if num_frames < IGNORE_FRAMES:
            return

        samples = np.concatenate(detector_state["frames"])
        pitch = estimate_pitch_median(samples)
        speaker, confidence = classify_speaker(pitch, detector_args.threshold)

        pitch_str = f"{pitch:.0f}Hz" if pitch else "?"
        duration_ms = num_frames * FRAME_MS

        # CRIANCA detectada (alta confianca + duracao minima)
        if speaker == "CHI" and num_frames >= MIN_SPEECH_FRAMES and confidence >= PITCH_CONFIDENCE_MIN:
            # Log discreto
            print(f"{DIM}[crianca] {duration_ms}ms {pitch_str}{RESET}")

            detector_state["awaiting_conversation"] = True
            detector_state["child_speech_time"] = time.time()

            with session_state["lock"]:
                session_state["current_speaker"] = "CHI"
                session_state["current_pitch"] = int(pitch) if pitch else None
                session_state["last_speech_time"] = time.time()
                session_state["child_speech"] += 1

            add_event("child", pitch=pitch)

            socketio.emit("speech", {
                "speaker": "CHI",
                "pitch": int(pitch) if pitch else None,
                "duration_ms": duration_ms,
                "time": round(time.time() - session_state["start_time"], 1) if session_state["start_time"] else 0
            })

        # ADULTO detectado
        elif speaker == "ADT":
            # Log discreto
            print(f"{DIM}[adulto] {duration_ms}ms {pitch_str}{RESET}")

            with session_state["lock"]:
                session_state["current_speaker"] = "ADT"
                session_state["current_pitch"] = int(pitch) if pitch else None
                session_state["last_speech_time"] = time.time()
                session_state["adult_speech"] += 1

            # MOMENTO DE CONVERSA detectado!
            if detector_state["awaiting_conversation"]:
                response_time = time.time() - detector_state["child_speech_time"]
                detector_state["awaiting_conversation"] = False

                # FEEDBACK POSITIVO
                print(f"{GREEN}[MOMENTO] Conversa detectada!{RESET}")

                with session_state["lock"]:
                    session_state["moments"] += 1
                    session_state["response_times"].append(response_time)

                add_event("moment", latency=response_time)

                socketio.emit("moment", {
                    "moments": session_state["moments"],
                    "response_time": round(response_time, 2),
                    "time": round(time.time() - session_state["start_time"], 1) if session_state["start_time"] else 0
                })

                # LED verde suave (2s) - feedback positivo visual
                led_success()
            else:
                add_event("adult", pitch=pitch)

            socketio.emit("speech", {
                "speaker": "ADT",
                "pitch": int(pitch) if pitch else None,
                "duration_ms": duration_ms,
                "time": round(time.time() - session_state["start_time"], 1) if session_state["start_time"] else 0
            })

        # Som incerto - loga silenciosamente
        else:
            add_event("sound", pitch=pitch, note="uncertain")

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
                    on_speech_end()
                    detector_state["in_speech"] = False
                    detector_state["frames"] = []

                    with session_state["lock"]:
                        session_state["current_speaker"] = None

                    socketio.emit("silence", {})

    # Inicia stream
    audio_stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=audio_callback,
        blocksize=FRAME_SIZE
    )
    audio_stream.start()

    # Loop silencioso - SEM feedback negativo
    heartbeat_counter = 0
    while session_state["listening"]:
        time.sleep(0.1)
        heartbeat_counter += 1

        # Heartbeat a cada 2 segundos (20 * 0.1s)
        if heartbeat_counter >= 20:
            heartbeat_counter = 0
            with session_state["lock"]:
                duration = time.time() - session_state["start_time"] if session_state["start_time"] else 0
                socketio.emit("status", {
                    "listening": True,
                    "moments": session_state["moments"],
                    "child_speech": session_state["child_speech"],
                    "adult_speech": session_state["adult_speech"],
                    "duration_seconds": round(duration, 1),
                    "current_speaker": session_state["current_speaker"]
                })

        # Apos janela generosa (15s), apenas reseta estado
        # NENHUM feedback negativo - apenas continua escutando
        if detector_state["awaiting_conversation"]:
            elapsed = time.time() - detector_state["child_speech_time"]
            if elapsed > CONVERSATION_WINDOW_S:
                detector_state["awaiting_conversation"] = False
                # Loga silenciosamente para analise (sem feedback ao usuario)
                add_event("window_closed", note="ready_for_next")


def run_flask():
    """Roda servidor Flask + SocketIO em thread separada."""
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)


def main():
    global detector_args

    parser = argparse.ArgumentParser(description="Detector de turnos em tempo real")
    parser.add_argument("--threshold", type=float, default=280.0,
                        help="Pitch mínimo para classificar como criança (default: 280Hz)")
    parser.add_argument("--timeout", type=float, default=15.0,
                        help="Janela de conversa em segundos (default: 15.0)")
    parser.add_argument("--vad", type=int, default=2, choices=[0, 1, 2, 3],
                        help="Agressividade do VAD 0-3 (default: 2)")
    parser.add_argument("--port", type=int, default=5000,
                        help="Porta da API REST (default: 5000)")
    parser.add_argument("--autostart", action="store_true",
                        help="Inicia escuta automaticamente")
    detector_args = parser.parse_args()

    # Inicializa GPIO para LED (se disponível)
    led_init()

    # Garante que diretório de dados existe
    ensure_data_dir()

    print("=" * 50)
    print("MAESTRO - Momentos de Conversa")
    print("Um coach gentil para conexao familiar")
    print("=" * 50)
    print(f"Deteccao: conservadora (alta confianca)")
    print(f"Janela: {detector_args.timeout:.0f}s (generosa)")
    print(f"Feedback: apenas positivo (LED verde)")
    print(f"Modo: 100% offline")
    print(f"Dados: {DATA_DIR}")
    print(f"API: http://0.0.0.0:{detector_args.port}")
    print("-" * 50)
    print("Endpoints:")
    print("  GET  /api/status   - estado atual")
    print("  GET  /api/session  - sessao ativa")
    print("  GET  /api/weekly   - resumo semanal + dica")
    print("  GET  /api/sessions - historico")
    print("  POST /api/start    - iniciar")
    print("  POST /api/stop     - parar")
    print("=" * 50)

    # Inicia auto-save em thread separada
    autosave_thread = threading.Thread(target=auto_save_loop, daemon=True)
    autosave_thread.start()

    # Autostart se solicitado
    if detector_args.autostart:
        print("\nIniciando escuta automaticamente...")
        with session_state["lock"]:
            session_state["session_id"] = str(uuid.uuid4())[:8]
            session_state["listening"] = True
            session_state["start_time"] = time.time()
        threading.Thread(target=start_audio_stream, daemon=True).start()

    # Mostra sessões existentes
    existing = list_local_sessions()
    if existing:
        print(f"\nSessoes salvas: {len(existing)} arquivos")

    print("\nAguardando comandos via API... (Ctrl+C para sair)")

    try:
        # SocketIO runs on the main thread (required for WebSocket support)
        socketio.run(app, host='0.0.0.0', port=detector_args.port, use_reloader=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nEncerrando...")
        # Salva sessão antes de sair
        if session_state["listening"] and session_state["start_time"]:
            print("Salvando sessao...")
            save_session_to_json()
        session_state["listening"] = False
    finally:
        global auto_save_enabled
        auto_save_enabled = False
        gpio_cleanup()


if __name__ == "__main__":
    main()
