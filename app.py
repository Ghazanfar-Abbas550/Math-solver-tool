import hashlib
import secrets
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from datetime import timedelta
from faq_data import faq_data
from fuzzywuzzy import process
import re
import math
from sympy import Eq, solve, simplify, sympify
import json
import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------
# App config
# ------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Do NOT use permanent sessions by default (prevents "signed in for 7 days" behavior).
app.config['SESSION_PERMANENT'] = False
app.permanent_session_lifetime = timedelta(days=7)

PEOPLE_FILE = "people.json"
CHATS_FILE = "chats.json"

# Gemini configuration (HTTP approach)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if GEMINI_API_KEY:
    logger.info("Gemini API key found in environment; will use Gemini model: %s", GEMINI_MODEL)
else:
    logger.info("No Gemini API key found in environment; AI endpoints will return 503 until configured.")

# ------------------------------------
# Password hashing helpers
# ------------------------------------
SALT_SIZE = 16
HASH_ROUNDS = 200000
HASH_ALGORITHM = 'sha256'


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_SIZE)
    hashed = hashlib.pbkdf2_hmac(HASH_ALGORITHM, password.encode('utf-8'), salt, HASH_ROUNDS)
    return f"{salt.hex()}${hashed.hex()}"


def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        salt_hex, hash_hex = stored_password.split('$')
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)
    except Exception:
        return False
    provided_hash = hashlib.pbkdf2_hmac(HASH_ALGORITHM, provided_password.encode('utf-8'), salt, HASH_ROUNDS)
    return secrets.compare_digest(provided_hash, stored_hash)


def load_people():
    if not os.path.exists(PEOPLE_FILE):
        return []
    try:
        with open(PEOPLE_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_people(data):
    with open(PEOPLE_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def validate_password(password):
    if not (8 <= len(password) <= 16):
        return "Password must be between 8 and 16 characters long."
    if not re.search(r'[A-Z]', password):
        return "Password must include at least one capital letter."
    if not re.search(r'[a-z]', password):
        return "Password must include at least one small letter."
    if not re.search(r'[0-9]', password):
        return "Password must include at least one number."
    # allow common special characters
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}\\|;:"\',.<>/?~`]', password):
        return "Password must include at least one special character."
    return None


# ------------------------------------
# Chats storage helpers (per-user)
# ------------------------------------
def _load_chats_file():
    if not os.path.exists(CHATS_FILE):
        return {}
    try:
        with open(CHATS_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_chats_file(data):
    # data must be a dict mapping user_id -> chat-structure
    try:
        with open(CHATS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.exception("Failed to save chats file: %s", e)


def load_user_chats(user_id):
    all_chats = _load_chats_file()
    key = str(user_id)
    if key in all_chats:
        return all_chats[key]
    # default structure
    default = {"active": {"Chat 1": []}, "archived": {}, "meta": {}}
    all_chats[key] = default
    _save_chats_file(all_chats)
    return default


def save_user_chats(user_id, data):
    if not isinstance(data, dict):
        raise ValueError("data must be a dict")
    all_chats = _load_chats_file()
    all_chats[str(user_id)] = data
    _save_chats_file(all_chats)


# ------------------------------------
# Request hook to load logged in user
# ------------------------------------
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    g.username = None
    if user_id is not None:
        people = load_people()
        user = next((p for p in people if p.get('user_id') == user_id), None)
        if user:
            g.user = user
            g.username = user.get('username')


# ------------------------------------
# Auth routes
# ------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == "POST":
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()
        people = load_people()
        user = next((p for p in people if p.get('email') == identifier or p.get('username') == identifier), None)
        if user and verify_password(user['password'], password):
            # Do NOT set session.permanent here. That avoids the 7-day persistent cookie.
            session['user_id'] = user['user_id']
            session.permanent = False
            return redirect(url_for('index'))
        else:
            error = "Invalid username/email or password."
    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == "POST":
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        people = load_people()
        if any(p.get('email') == email for p in people):
            error = "Email already registered."
        elif any(p.get('username') == username for p in people):
            error = "Username already taken."
        else:
            pass_error = validate_password(password)
            if pass_error:
                error = pass_error
            else:
                hashed_password = hash_password(password)
                new_user_id = max([p.get('user_id', 0) for p in people] + [0]) + 1
                new_user = {'user_id': new_user_id, 'email': email, 'username': username, 'password': hashed_password}
                people.append(new_user)
                save_people(people)
                # initialize empty per-user chats
                save_user_chats(new_user_id, {"active": {"Chat 1": []}, "archived": {}, "meta": {}})
                session['user_id'] = new_user['user_id']
                session.permanent = False
                return redirect(url_for('index'))
    return render_template("signup.html", error=error)


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route("/")
def index():
    if g.user is None:
        return redirect(url_for('login'))
    return render_template("index.html", username=g.username)


# ------------------------------------
# API endpoints for chats (per-user)
# ------------------------------------
@app.route("/api/chats", methods=["GET"])
def api_get_chats():
    if g.user is None:
        return jsonify({"error": "Authentication required"}), 401
    user_id = g.user['user_id']
    data = load_user_chats(user_id)
    return jsonify(data)


@app.route("/api/chats", methods=["POST"])
def api_save_chats():
    if g.user is None:
        return jsonify({"error": "Authentication required"}), 401
    payload = request.json or {}
    # Basic validation: expect dict with active and archived keys
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid payload"}), 400
    active = payload.get("active", {})
    archived = payload.get("archived", {})
    meta = payload.get("meta", {})
    if not isinstance(active, dict) or not isinstance(archived, dict) or not isinstance(meta, dict):
        return jsonify({"error": "Invalid data structure"}), 400
    user_id = g.user['user_id']
    save_user_chats(user_id, {"active": active, "archived": archived, "meta": meta})
    return jsonify({"ok": True})


# ------------------------------------
# Math & FAQ logic
# ------------------------------------
faq_questions = []
faq_answers = []
for entry in faq_data:
    for q in entry["questions"]:
        faq_questions.append(q.lower())
        faq_answers.append(entry["answer"])


def faq_lookup(text):
    if not faq_questions:
        return None
    best, score = process.extractOne(text.lower(), faq_questions)
    if score >= 30:
        idx = faq_questions.index(best)
        return faq_answers[idx]
    return None


def parse_hcf_lcm(text):
    nums = [int(n) for n in re.findall(r"\d+", text)]
    if not nums:
        return None
    if "hcf" in text.lower() or "gcd" in text.lower():
        g = nums[0]
        for n in nums[1:]:
            g = math.gcd(g, n)
        return {"type": "hcf", "answer": f"The HCF of the numbers is: {g}"}
    if "lcm" in text.lower():
        def lcm(a, b):
            return a * b // math.gcd(a, b)
        l = nums[0]
        for n in nums[1:]:
            l = lcm(l, n)
        return {"type": "lcm", "answer": f"The LCM of the numbers is: {l}"}
    return None


def normalize_input(text):
    text = (text.replace("−", "-").replace("–", "-").replace("—", "-"))
    text = re.sub(r'(\d)([A-Za-z])', r'\1*\2', text)
    return text


def parse_equation(eq_string):
    L, R = eq_string.split('=', 1)
    return sympify(L) - sympify(R)


def generate_steps_for_equation(L_start, R_start):
    BR = "<br>"
    steps = []

    def clean_expr_str(expr):
        return str(expr).replace('*', '')

    L = simplify(L_start)
    R = simplify(R_start)

    steps.append(f"Given:{BR}<strong>{clean_expr_str(L)} = {clean_expr_str(R)}</strong>")

    R_vars = R - R.subs({v: 0 for v in R.free_symbols})
    L_new = L
    R_new = R

    if R_vars != 0:
        L_new = simplify(L - R_vars)
        R_new = simplify(R - R_vars)

        R_vars_display = clean_expr_str(R_vars)

        steps.append(f"<strong>Step 1:</strong> Move all variable terms from the right side to the left side.")
        steps.append(f"Subtract <strong>{R_vars_display}</strong> from both sides:")
        steps.append(f"Resulting equation: <strong>{clean_expr_str(L_new)} = {R_new}</strong>")

    L_const = L_new.subs({v: 0 for v in L_new.free_symbols})
    L_vars = simplify(L_new - L_const)

    L_final = L_vars
    R_final = R_new

    if L_const != 0:
        L_final = simplify(L_vars)
        R_final = simplify(R_new - L_const)

        steps.append(
            f"<strong>Step 2:</strong> Move the constant term (<strong>{L_const}</strong>) from the left side to the right side.")

        op_text = "Subtract" if L_const > 0 else "Add"

        steps.append(f"{op_text} <strong>{abs(L_const)}</strong> from both sides:")
        steps.append(f"Resulting equation: <strong>{clean_expr_str(L_final)} = {R_final}</strong>")

    coeffs = []
    for term in L_final.as_ordered_terms():
        if not term.is_number:
            coeff = term.as_coeff_Mul()[0] if term.is_Mul else (1 if term.is_symbol else term)
            try:
                if isinstance(coeff, (int, float)) and coeff == int(coeff):
                    coeffs.append(abs(coeff))
            except Exception:
                pass

    if isinstance(R_final, (int, float)) and R_final == int(R_final):
        coeffs.append(abs(R_final))

    int_coeffs = [int(c) for c in coeffs if c != 0]

    g = 1
    if int_coeffs:
        g = int_coeffs[0]
        for n in int_coeffs[1:]:
            g = math.gcd(g, n)

    if g > 1:
        L_simp = simplify(L_final / g)
        R_simp = simplify(R_final / g)

        steps.append(
            f"<strong>Step 3:</strong> Simplify the equation by dividing all terms by their Greatest Common Divisor (<strong>{g}</strong>).")
        steps.append(f"Resulting equation: <strong>{clean_expr_str(L_simp)} = {R_simp}</strong>")

        L_final = L_simp
        R_final = R_simp

    formatted_steps = []
    formatted_steps.extend(steps)

    if L_final.free_symbols:
        formatted_steps.append(
            f"<strong>Final simplified form:</strong>{BR}<strong>{clean_expr_str(L_final)} = {R_final}</strong>")
    else:
        final_solution_text = f"<strong>Result:</strong>{BR}<strong>{clean_expr_str(L_final)} = {R_final}</strong>"

        if len(L_start.free_symbols) == 1:
            x = list(L_start.free_symbols)[0]
            sol = solve(Eq(L_start, R_start), x)
            if sol:
                final_solution_text = f"<strong>Final Solution:</strong>{BR}<strong>{x} = {sol[0]}</strong>"

        formatted_steps.append(final_solution_text)

    return "Let's solve the equation step by step:<br><br>" + "<br><br>".join(formatted_steps)


def algebra_detect_and_handle(text):
    if not text or not text.strip():
        return None

    t = normalize_input(text)

    if not re.search(r'[=+\-*/\d]', t):
        return None

    # 1. Check for system of two equations
    if ',' in t and t.count('=') >= 2:
        try:
            eq_strings = [eq.strip() for eq in t.split(',') if '=' in eq]
            if len(eq_strings) == 2:
                expr1 = parse_equation(eq_strings[0])
                expr2 = parse_equation(eq_strings[1])
                vars_all = sorted(list(expr1.free_symbols.union(expr2.free_symbols)), key=str)

                if len(vars_all) == 2:
                    solution = solve((expr1, expr2), vars_all)
                    if solution:
                        sol_text = ", ".join([f"{str(v)} = {solution[v]}" for v in vars_all])
                        return {"type": "algebra_solve_system",
                                "answer": f"Solution to the system of equations is: {sol_text}"}
                    else:
                        return {"type": "algebra_error",
                                "answer": "The system of equations has no unique solution (either infinite solutions or none)."}
                else:
                    return {"type": "algebra_error",
                            "answer": "To solve a system, please provide two equations with exactly two variables."}
        except Exception:
            pass

    # 2. Single Equation or Expression Handling
    if '=' in t:
        try:
            L_str, R_str = t.split('=', 1)
            left = sympify(L_str)
            right = sympify(R_str)

            vars_all = sorted([str(v) for v in (left - right).free_symbols])

            if len(vars_all) == 2:
                return {
                    "type": "algebra_options",
                    "answer": f"I found a multi-variable equation: {text}<br><br>What would you like to do with it?",
                    "expr": text
                }

            steps_output = generate_steps_for_equation(left, right)
            return {"type": "algebra_solve_steps", "answer": steps_output}

        except Exception:
            return {"type": "algebra_error",
                    "answer": "Cannot parse algebra equation. Check formatting like 2x+3=7 or 2x+3y=10."}

    # 3. Expression (no equal sign)
    try:
        expr = sympify(t)
        simp = simplify(expr)

        return {"type": "algebra_simplify", "answer": f"The expression is: {t}<br><br>Simplified form: {str(simp)}"}

    except Exception:
        return None


# ------------------------------------
# Helpers for parsing model outputs
# ------------------------------------
def _extract_json_from_text(t):
    if not isinstance(t, str):
        return None
    t = t.strip()
    # Try to extract a JSON array first
    start = t.find('[')
    end = t.rfind(']')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(t[start:end + 1])
        except Exception:
            pass
    # Try object
    start = t.find('{')
    end = t.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(t[start:end + 1])
        except Exception:
            pass
    return None


def _find_first_text_in_response(obj):
    """
    Defensive search for the first generated text in a Gemini response structure.
    Returns the first string it finds or None.
    """
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        for item in obj:
            res = _find_first_text_in_response(item)
            if res:
                return res
    if isinstance(obj, dict):
        # common keys that may contain generated text
        for k in ('content', 'text', 'output', 'candidates', 'response', 'message', 'messages', 'parts'):
            if k in obj:
                res = _find_first_text_in_response(obj[k])
                if res:
                    return res
        for v in obj.values():
            res = _find_first_text_in_response(v)
            if res:
                return res
    return None


# ------------------------------------
# Gemini HTTP call helper (TRANSLATES client messages -> Gemini REST format)
# ------------------------------------
def call_gemini_generate(messages, temperature=0.2, max_output_tokens=400, timeout=20):
    """
    Calls Gemini HTTP API and attempts several extraction strategies for returned text.
    Returns (ok:bool, text_or_err:str, raw_response_or_none)
    """
    if not GEMINI_API_KEY:
        return False, "No GEMINI_API_KEY configured", None

    # Convert old message schema -> new Gemini parts schema
    contents = []
    try:
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            parts = []

            c = m.get("content")
            if isinstance(c, list) and len(c) > 0:
                for item in c:
                    if isinstance(item, dict) and item.get("text"):
                        parts.append({"text": item["text"]})
            elif isinstance(c, str):
                parts.append({"text": c})
            else:
                parts.append({"text": ""})

            contents.append({"role": role, "parts": parts})

    except Exception as e:
        return False, f"Normalization error: {e}", None

    body = {
        "contents": contents,
        "generationConfig": {
            "temperature": float(temperature),
            "maxOutputTokens": int(max_output_tokens)
        }
    }

    endpoint = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(endpoint, headers=headers, data=json.dumps(body), timeout=timeout)
    except Exception as e:
        return False, f"Network error: {e}", None

    if resp.status_code != 200:
        # return body so caller can inspect error details
        return False, f"Gemini API error: status {resp.status_code}; body: {resp.text}", resp.text

    try:
        js = resp.json()
    except Exception:
        # return raw text to help debugging
        return False, "Invalid JSON from Gemini", resp.text

    # 1) Primary extraction path
    try:
        text = js["candidates"][0]["content"]["parts"][0]["text"]
        if text:
            return True, text, js
    except Exception:
        pass

    # 2) Defensive extraction: search whole object for any text
    text = _find_first_text_in_response(js)
    if text:
        return True, text, js

    # 3) Last resort: stringify part of JSON for debugging
    try:
        fallback_debug = json.dumps(js)[:2000]
    except Exception:
        fallback_debug = str(js)[:2000]
    return False, "No text in Gemini response", fallback_debug


# ------------------------------------
# /new_ai_chat endpoint (uses call_gemini_generate)
# ------------------------------------
@app.route("/new_ai_chat", methods=["POST"])
def new_ai_chat():
    if g.user is None:
        return jsonify({"error": "Authentication required"}), 401

    payload = request.json or {}
    topic = (payload.get("topic") or "").strip()
    chat_name = f"AI Chat — {topic[:30]}" if topic else "AI Chat"

    system_prompt = (
        "You are a Math Tutor assistant. RETURN ONLY a JSON array of message objects. "
        "Each object must have two string fields: 'user' and 'bot'. "
        "User fields must be short machine-friendly prompts (e.g. '2x+3=7' or 'HCF of 12 and 18'). "
        "Bot fields are the assistant's response (may include simple HTML <strong>, <br>, <code>). "
        "Create 4 exchanges: greeting, HCF/GCD example, algebra example with a step-by-step solution, and a short limitations note."
    )
    user_prompt = f"Produce a starter chat tailored to topic: '{topic}'." if topic else "Produce a starter chat."

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
    ]

    ok, text_or_err, raw = call_gemini_generate(messages, temperature=0.2, max_output_tokens=400)
    if not ok:
        # Log the issue for server-side debugging
        logger.warning("Gemini new_ai_chat returned no valid text (ok=False): %s", text_or_err)

        # Build a small local fallback starter chat so the UI can still create an AI chat
        fallback_msgs = [
            {"user": "Hello", "bot": "<p>👋 Hi! I'm a Math Tutor. Ask me an equation like <code>2x+3=7</code> or request <code>HCF of 12 and 18</code>.</p>"},
            {"user": "HCF of 12 and 18", "bot": "<p>The HCF of 12 and 18 is <strong>6</strong>.</p>"},
            {"user": "Solve 2x+3=7", "bot": "<p>Let's solve: 2x + 3 = 7<br><strong>Step 1:</strong> Subtract 3 from both sides => 2x = 4<br><strong>Step 2:</strong> Divide both sides by 2 => x = 2</p>"},
            {"user": "Limitations", "bot": "<p>⚠️ I work best with integer arithmetic and basic algebra. Advanced calculus and symbolic edge-cases may not be supported.</p>"}
        ]

        return jsonify({"chat_name": chat_name, "messages": fallback_msgs})

    # try to parse JSON array from the returned text
    parsed = _extract_json_from_text(text_or_err)
    if parsed and isinstance(parsed, list):
        msgs = []
        for item in parsed:
            if isinstance(item, dict):
                user_msg = item.get("user", "")
                bot_msg = item.get("bot", "")
                msgs.append({"user": user_msg, "bot": bot_msg})
        if msgs:
            return jsonify({"chat_name": chat_name, "messages": msgs})

    # If parsing failed but we did receive some textual content, send it as a single bot message
    if isinstance(text_or_err, str) and text_or_err.strip():
        return jsonify({"chat_name": chat_name, "messages": [{"user": "Hello", "bot": text_or_err}]})

    # Last fallback: same local starter
    fallback_msgs = [
        {"user": "Hello", "bot": "<p>👋 Hi! I'm a Math Tutor. Ask me an equation like <code>2x+3=7</code> or request <code>HCF of 12 and 18</code>.</p>"},
        {"user": "HCF of 12 and 18", "bot": "<p>The HCF of 12 and 18 is <strong>6</strong>.</p>"},
        {"user": "Solve 2x+3=7", "bot": "<p>Let's solve: 2x + 3 = 7<br><strong>Step 1:</strong> Subtract 3 from both sides => 2x = 4<br><strong>Step 2:</strong> Divide both sides by 2 => x = 2</p>"},
        {"user": "Limitations", "bot": "<p>⚠️ I work best with integer arithmetic and basic algebra. Advanced calculus and symbolic edge-cases may not be supported.</p>"}
    ]
    return jsonify({"chat_name": chat_name, "messages": fallback_msgs})


# ------------------------------------
# /ai_reply endpoint - proxy last user message to Gemini and return assistant reply
# ------------------------------------
@app.route("/ai_reply", methods=["POST"])
def ai_reply():
    if g.user is None:
        return jsonify({"error": "Authentication required"}), 401

    if not GEMINI_API_KEY:
        return jsonify({"error": "Server not configured with GEMINI_API_KEY"}), 503

    payload = request.json or {}
    messages = payload.get("messages")
    if not messages or not isinstance(messages, list):
        return jsonify({"error": "Invalid request, missing messages"}), 400

    # Extract the last user message text (we will send only the last user to Gemini)
    last_user_text = None
    for m in reversed(messages):
        if m.get("role") == "user" or m.get("author") == "user":
            content = m.get("content")
            if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                last_user_text = content[0].get("text", "")
            elif isinstance(content, str):
                last_user_text = content
            if last_user_text:
                break

    if not last_user_text:
        return jsonify({"error": "No user content to answer"}), 400

    # Build a minimal safe request: system + last user message
    system_prompt = (
        "You are a precise and concise Math Tutor. ALWAYS attempt to answer the user's last message. "
        "If the user's message contains numbers or an equation, treat it as a math question and provide a correct solution with steps. "
        "Return the assistant reply as plain text (you may include simple HTML like <strong>, <br>, <code>). "
        "Do not return JSON or extra metadata—only the assistant's content."
    )

    gemini_messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "text", "text": last_user_text}]}
    ]

    ok, text_or_err, raw = call_gemini_generate(gemini_messages, temperature=0.2, max_output_tokens=600)
    if not ok:
        logger.info("Gemini ai_reply failed: %s", text_or_err)
        return jsonify({"error": f"Gemini API error: {text_or_err}"}), 502

    assistant_reply = text_or_err
    return jsonify({"reply": assistant_reply})


# ------------------------------------
# Existing rule-based /send endpoint
# ------------------------------------
@app.route("/send", methods=["POST"])
def send():
    if g.user is None:
        return jsonify({"reply": "Authentication required. Please log in.", "type": "auth_error"}), 401
    data = request.json
    text = data.get("message", "").strip() if data else ""
    if not text:
        return jsonify({"reply": "Please type a message.", "type": "fallback"})

    # 1) HCF/LCM
    h = parse_hcf_lcm(text)
    if h:
        return jsonify({"reply": h["answer"], "type": h["type"]})

    # 2) Algebra (expressions/equations/systems)
    alg = algebra_detect_and_handle(text)
    if alg:
        response = {"reply": alg.get("answer", ""), "type": alg["type"]}
        for k, v in alg.items():
            if k not in ['answer', 'type']:
                response[k] = v
        return jsonify(response)

    # 3) FAQ
    f = faq_lookup(text)
    if f:
        return jsonify({"reply": f, "type": "faq"})

    fallback = next((e["answer"] for e in faq_data if any(q.lower() == "fallback" for q in e.get("questions", []))),
                    "I couldn't understand that.")
    return jsonify({"reply": fallback, "type": "fallback"})


if __name__ == "__main__":
    # ensure storage files exist
    if not os.path.exists(PEOPLE_FILE):
        save_people([])
    if not os.path.exists(CHATS_FILE):
        _save_chats_file({})
    app.run(debug=True)