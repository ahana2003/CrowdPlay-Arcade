"""CrowdPlay Arcade: small Twitch chat games for stream communities."""
from __future__ import annotations

import logging
import os
import random
import re
import threading
import time
import urllib.request
import webbrowser
from collections import deque
from pathlib import Path
from typing import Any

import websocket
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("crowdplay")
app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")

CHANNEL = os.getenv("TWITCH_CHANNEL", "").strip().lstrip("#").lower()
BOT_USERNAME = os.getenv("TWITCH_USERNAME", "").strip().lower()
TOKEN = os.getenv("TWITCH_TOKEN", "").strip()
TWITCH_CONFIGURED = bool(CHANNEL and BOT_USERNAME and TOKEN and "PASTE_" not in TOKEN.upper())

LOCK = threading.RLock()
EVENTS: deque[dict[str, Any]] = deque(maxlen=250)
EVENT_ID = 0
DEMO_INDEX = 0
WORKER_STARTED = False
WORKER_LOCK = threading.Lock()
TWITCH_STATE = "connecting" if TWITCH_CONFIGURED else "demo"
TWITCH_ERROR = ""

GAMES = {
    "ttt": {"name": "Tic-Tac-Toe", "emoji": "❎", "description": "Two players take turns placing X and O. Get three in a row.", "command": "!join then !move 1–9"},
    "word": {"name": "Guess the Word", "emoji": "🔤", "description": "Reveal the hidden word, one letter at a time. You have six misses.", "command": "!letter <letter> or !word <answer>"},
    "math": {"name": "Math Challenge", "emoji": "➗", "description": "Solve the math problem. First correct answer wins.", "command": "!answer <number>"},
}
WORDS = ["stream", "gamer", "planet", "puzzle", "dragon", "twitch", "arcade", "victory"]
GAME: dict[str, Any] = {"key": None, "round": 0, "active": False, "message": "Start a random round to play.",
                        "target": None, "word": "", "guessed": [], "misses": 0, "question": "", "board": [],
                        "players": {}, "turn": "X", "winner": None, "scores": {}}


def snapshot_locked() -> dict[str, Any]:
    key = GAME["key"]
    state = {name: value for name, value in GAME.items() if name not in {"target", "word"}}
    state["game"] = GAMES.get(key) if key else None
    reveal_word = key == "word" and (GAME["winner"] or not GAME["active"])
    state["revealed"] = GAME["word"] if reveal_word else None
    state["display_word"] = " ".join(letter if letter in GAME["guessed"] or reveal_word else "_" for letter in GAME["word"]) if key == "word" else ""
    state["answer"] = GAME["target"] if key == "math" and GAME["winner"] else None
    return state


def push_event_locked(kind: str, username: str, message: str) -> None:
    global EVENT_ID
    EVENT_ID += 1
    EVENTS.append({"id": EVENT_ID, "type": kind, "username": username[:32], "message": message[:180], "state": snapshot_locked()})


def start_game_locked(key: str | None = None, local_players: bool = False) -> dict[str, Any]:
    if key not in GAMES:
        key = random.choice(tuple(GAMES))
    GAME.update({"key": key, "round": GAME["round"] + 1, "active": True, "target": None,
                 "word": "", "guessed": [], "misses": 0, "question": "", "board": [""] * 9,
                 "players": {}, "turn": "X", "winner": None, "message": "Round started!"})
    if key == "ttt":
        if local_players:
            GAME["players"] = {"X": "LocalPlayer 1", "O": "LocalPlayer 2"}
            GAME["message"] = "Two-player local game. X moves first; click any empty square."
        else:
            GAME["active"] = False
            GAME["message"] = "Type !join in chat to take X or O. Two players are needed to start."
    elif key == "word":
        GAME["word"] = random.choice(WORDS)
        GAME["message"] = "Guess a letter or the whole word. Six wrong guesses allowed."
    elif key == "math":
        left, right = random.randint(2, 20), random.randint(2, 12)
        op = random.choice(("+", "−", "×"))
        GAME["target"] = left + right if op == "+" else left - right if op == "−" else left * right
        GAME["question"] = f"{left} {op} {right} = ?"
        GAME["message"] = "Enter your answer. First correct answer wins!"
    return snapshot_locked()


def apply_command_locked(username: str, message: str) -> bool:
    parts = message.strip().split(maxsplit=1)
    command = parts[0].lower().rstrip(".,!?") if parts else ""
    argument = parts[1].strip().lower() if len(parts) > 1 else ""
    display = (username or "viewer")[:32]

    if command == "!arcade":
        start_game_locked()
        if GAME["key"] != "ttt":
            GAME["message"] = f"{display} started {GAMES[GAME['key']]['name']}!"
        push_event_locked("round", display, "started a random game")
        return True
    if GAME["key"] == "ttt" and command == "!join":
        if display.casefold() in {name.casefold() for name in GAME["players"].values()} or len(GAME["players"]) >= 2:
            return False
        mark = "X" if "X" not in GAME["players"] else "O"
        GAME["players"][mark] = display
        GAME["active"] = len(GAME["players"]) == 2
        GAME["message"] = f"{display} joined as {mark}. X goes first." if GAME["active"] else f"{display} joined as X. Waiting for one more player to type !join."
        push_event_locked("play", display, f"joined Tic-Tac-Toe as {mark}")
        return True
    if not GAME["active"] or GAME["winner"]:
        return False

    key = GAME["key"]
    result = ""
    if key == "ttt" and command == "!move":
        try: cell = int(argument) - 1
        except ValueError: return False
        mark = next((m for m, player in GAME["players"].items() if player.casefold() == display.casefold()), None)
        if mark != GAME["turn"] or not 0 <= cell < 9 or GAME["board"][cell]: return False
        GAME["board"][cell] = mark
        result = f"placed {mark} in square {cell + 1}"
        lines = ((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))
        if any(all(GAME["board"][i] == mark for i in line) for line in lines):
            GAME["winner"] = display; GAME["active"] = False
            GAME["scores"][display] = GAME["scores"].get(display, 0) + 1
            GAME["message"] = f"{display} wins Tic-Tac-Toe as {mark}!"
        elif all(GAME["board"]):
            GAME["active"] = False; GAME["message"] = "It’s a draw! Start a new round with !arcade."
        else:
            GAME["turn"] = "O" if mark == "X" else "X"
            GAME["message"] = f"{GAME['players'][GAME['turn']]} ({GAME['turn']}) is up."
    elif key == "word" and command in {"!letter", "!word"}:
        if command == "!letter":
            if len(argument) != 1 or not argument.isalpha() or argument in GAME["guessed"]: return False
            GAME["guessed"].append(argument)
            if argument not in GAME["word"]: GAME["misses"] += 1
            result = f"guessed letter {argument.upper()}"
        else:
            if not argument: return False
            if argument == GAME["word"]:
                GAME["guessed"] = list(set(GAME["guessed"]) | set(GAME["word"]))
                result = "guessed the whole word"
            else:
                GAME["misses"] += 1; result = "tried a word and missed"
        if all(letter in GAME["guessed"] for letter in GAME["word"]):
            GAME["winner"] = display; GAME["active"] = False
            GAME["scores"][display] = GAME["scores"].get(display, 0) + 1
            GAME["message"] = f"{display} solved the word! It was {GAME['word']}."
        elif GAME["misses"] >= 6:
            GAME["active"] = False; GAME["message"] = f"Out of tries! The word was {GAME['word']}."
        else:
            GAME["message"] = f"{display} guessed. {6 - GAME['misses']} misses left."
    elif key == "math" and command == "!answer":
        try: answer = int(argument)
        except ValueError: return False
        if answer == GAME["target"]:
            GAME["winner"] = display; GAME["active"] = False
            GAME["scores"][display] = GAME["scores"].get(display, 0) + 1
            GAME["message"] = f"{display} solved it! {GAME['question']} {answer} is correct."
            result = "solved the math challenge!"
        else:
            GAME["message"] = f"{display} answered {answer}. Not quite—try again!"
            result = f"tried answer {answer}"
    else:
        return False

    push_event_locked("play", display, result)
    return True


@app.get("/")
def index():
    # Serve plain HTML directly. Do not pass it through Jinja; CSS/JS braces stay untouched.
    return send_from_directory(ROOT / "static", "index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True, "twitch_configured": TWITCH_CONFIGURED, "twitch_state": TWITCH_STATE,
                    "error": TWITCH_ERROR, "mode": "twitch" if TWITCH_CONFIGURED else "demo"})


@app.get("/api/state")
def get_state():
    with LOCK:
        return jsonify(snapshot_locked())


@app.get("/api/events")
def get_events():
    try:
        after = max(0, int(request.args.get("after", "0")))
    except ValueError:
        after = 0
    with LOCK:
        return jsonify({"events": [event for event in EVENTS if event["id"] > after], "latest": EVENT_ID})


@app.post("/api/game/start")
def start_random_game():
    with LOCK:
        state = start_game_locked(local_players=not TWITCH_CONFIGURED)
        state["message"] = GAME["message"]
        push_event_locked("round", "Host", "started a random game")
        return jsonify({"ok": True, "state": state})


@app.post("/api/demo/round")
def demo_round():
    """Run a self-contained sample round; the demo does not require Twitch."""
    global DEMO_INDEX
    with LOCK:
        key = tuple(GAMES)[DEMO_INDEX % len(GAMES)]
        DEMO_INDEX += 1
        start_game_locked(key)
        if key == "ttt":
            moves = [("XPlayer", "!join"), ("OPlayer", "!join"), ("XPlayer", "!move 1"), ("OPlayer", "!move 4"), ("XPlayer", "!move 2"), ("OPlayer", "!move 5"), ("XPlayer", "!move 3")]
            for username, command in moves:
                apply_command_locked(username, command)
        elif key == "word":
            for letter in sorted(set(GAME["word"])):
                apply_command_locked("WordWizard", f"!letter {letter}")
        else:
            apply_command_locked("MathWhiz", f"!answer {GAME['target']}")
        return jsonify({"ok": True, "state": snapshot_locked()})


@app.post("/api/local/action")
def local_action():
    """Accept mouse/touch game actions while Twitch credentials are absent."""
    if TWITCH_CONFIGURED:
        return jsonify({"ok": False, "error": "Local controls are disabled while Twitch chat is configured."}), 403
    data = request.get_json(silent=True) or {}
    command = str(data.get("command", ""))[:80]
    with LOCK:
        username = GAME["players"].get(GAME["turn"], "LocalPlayer") if GAME["key"] == "ttt" else "LocalPlayer"
        accepted = apply_command_locked(username, command)
        state = snapshot_locked()
        if not accepted:
            return jsonify({"ok": False, "error": "That action is not valid for this round.", "state": state}), 400
        return jsonify({"ok": True, "state": state})


def parse_privmsg(line: str) -> tuple[str, str] | None:
    match = re.search(r"(?:^| )PRIVMSG #[^ ]+ :(.*)$", line)
    if not match:
        return None
    name_match = re.search(r"(?:^|;)display-name=([^; ]*)", line) or re.match(r":([^! ]+)!", line)
    name = (name_match.group(1) if name_match else "viewer") or "viewer"
    return name[:32], match.group(1).strip()


def twitch_worker() -> None:
    global TWITCH_STATE, TWITCH_ERROR
    url = "wss://irc-ws.chat.twitch.tv:443"
    while True:
        ws = None
        try:
            TWITCH_STATE = "connecting"
            TWITCH_ERROR = ""
            ws = websocket.create_connection(url, timeout=90, enable_multithread=True)
            ws.settimeout(90)
            ws.send(f"PASS oauth:{TOKEN.removeprefix('oauth:')}\r\n")
            ws.send(f"NICK {BOT_USERNAME}\r\n")
            ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n")
            ws.send(f"JOIN #{CHANNEL}\r\n")
            TWITCH_STATE = "connected"
            log.info("Connected to Twitch chat for #%s", CHANNEL)
            while True:
                try:
                    payload = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.ping("crowdplay")
                    continue
                if not payload:
                    raise ConnectionError("Twitch IRC closed the connection")
                for line in str(payload).split("\r\n"):
                    if not line:
                        continue
                    if line.startswith("PING "):
                        ws.send("PONG " + line[5:] + "\r\n")
                    elif "Login authentication failed" in line:
                        raise RuntimeError("Twitch rejected the access token. Check the username and chat:read permission.")
                    else:
                        parsed = parse_privmsg(line)
                        if parsed:
                            with LOCK:
                                apply_command_locked(*parsed)
        except Exception as exc:
            TWITCH_STATE = "error" if "rejected the access token" in str(exc).lower() else "reconnecting"
            TWITCH_ERROR = str(exc)[:200]
            log.warning("Twitch connection ended (%s); retrying in 5 seconds", exc)
            time.sleep(5)
        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass


def start_worker_once() -> None:
    global WORKER_STARTED
    if not TWITCH_CONFIGURED:
        return
    with WORKER_LOCK:
        if not WORKER_STARTED:
            WORKER_STARTED = True
            threading.Thread(target=twitch_worker, daemon=True, name="twitch-chat").start()


@app.before_request
def maybe_start_twitch():
    start_worker_once()


def open_browser_after_ready(port: int) -> None:
    url = f"http://127.0.0.1:{port}/?demo=1"
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(0.25)
    log.error("Browser did not open because the local health check never succeeded. Visit %s", url)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5055"))
    threading.Thread(target=open_browser_after_ready, args=(port,), daemon=True, name="open-browser").start()
    log.info("Starting CrowdPlay Arcade at http://127.0.0.1:%s", port)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
