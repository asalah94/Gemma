import json
import re
import uuid
import ast
from medgemma import medgemma_get_text_response
from langdetect import detect  # هتحتاج تثبت المكتبة: pip install langdetect

# In-memory session store  { session_id: { ... } }
sessions: dict = {}


def _normalize_response(obj) -> str:
    """Normalize various model return types into plain text.

    Handles dicts, lists, JSON strings, and Python-literal strings that
    sometimes contain [{'type':'text','text':'...'}] wrappers.
    """
    if obj is None:
        return ""

    # Bytes -> decode
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode('utf-8', errors='ignore').strip()
        except Exception:
            return str(obj)

    # Direct string: try to un-wrap common encodings
    if isinstance(obj, str):
        s = obj.strip()

        # Remove internal debugging tokens
        s = re.sub(r'<unused\d+>.*?</unused\d+>', '', s, flags=re.DOTALL)

        # Try JSON
        try:
            parsed = json.loads(s)
            return _normalize_response(parsed)
        except Exception:
            pass

        # Try Python literal (e.g., "[{'type': 'text', 'text': '...'}]")
        try:
            parsed = ast.literal_eval(s)
            return _normalize_response(parsed)
        except Exception:
            pass

        # Extract common 'text' fields from serialized dicts
        m = re.search(r"['\"]text['\"]\s*:\s*['\"](.+?)['\"]", s, flags=re.DOTALL)
        if m:
            return m.group(1).strip()

        # Remove role prefixes like 'ASSISTANT: '
        s = re.sub(r'^[A-Z_ ]{2,20}:\s*', '', s)

        return s.strip()

    # List -> join normalized elements
    if isinstance(obj, list):
        parts = []
        for el in obj:
            parts.append(_normalize_response(el))
        return ' '.join(p for p in (p.strip() for p in parts) if p)

    # Dict -> pick common keys
    if isinstance(obj, dict):
        for key in ("response", "text", "content", "message"):
            if key in obj:
                return _normalize_response(obj[key])

        # If values are present, try to normalize them
        return _normalize_response(list(obj.values()))

    # Fallback
    return str(obj).strip()


def detect_patient_language(text: str) -> str:
    """كشف لغة المريض من النص"""
    try:
        lang = detect(text)
        language_map = {
            'ar': 'Arabic',
            'en': 'English',
            'fr': 'French',
            'es': 'Spanish',
            'de': 'German',
            'it': 'Italian',
            'tr': 'Turkish',
            'ur': 'Urdu',
            'fa': 'Farsi',
            'he': 'Hebrew'
        }
        return language_map.get(lang, 'English')
    except Exception:
        return 'English'


def interviewer_roleplay_instructions(patient_name, patient_language="English"):
    """Returns instructions for the LLM clinical assistant with language flexibility."""
    return f"""
SYSTEM INSTRUCTION: Always think silently before responding.

### Persona & Objective ###
You are a clinical assistant. Your objective is to interview a patient, {patient_name}, and build a comprehensive and detailed report for their PCP.

### Critical Rules ###
- **No Assessments:** You are NOT authorized to provide medical advice, diagnoses, or express any form of assessment to the patient.
- **Question Format:** Ask only ONE question at a time. Do not enumerate your questions.
- **Question Length:** Each question must be 20 words or less.
- **Question Limit:** You have a maximum of 20 questions.
- **No Repeated Questions:** NEVER ask the same question twice. Each question must be completely unique and must build on the patient's previous answers. If you already asked about a symptom, move on to a different aspect.
- **Track Asked Questions:** Keep track of every question you have asked. Do not repeat any question, even in slightly different wording.
- **No Greetings After First Response:** NEVER use greeting phrases like "أهلاً بك", "مرحباً", "Hello", "Hi", "Welcome", or ANY welcoming phrase after your very first response. For every response after the first, go DIRECTLY to your question with zero preamble.
- **Language Rule:** The patient will start the conversation. You MUST respond in the SAME LANGUAGE the patient uses. If they speak in {patient_language}, you respond in {patient_language}. Be consistent throughout the interview.

### Interview Strategy ###
- **Clinical Reasoning:** Based on the patient's responses, actively consider potential diagnoses.
- **Differentiate:** Formulate your questions strategically to help differentiate between possibilities.
- **Probe Critical Clues:** When a patient's answer reveals a high-yield clue, ask immediate follow-up questions.
- **Exhaustive Inquiry:** Be thorough. Use your full allowance of questions.
- **Fact-Finding:** Focus exclusively on gathering specific, objective information.
- **Progress Forward:** After each answer, always advance to a NEW topic or aspect. Never loop back to what was already covered.

### Interview Topic Progression ###
Cover these areas in order, one question at a time:
1. Onset and duration of main symptom
2. Character/quality of the symptom
3. Severity (scale 1-10)
4. Location and radiation
5. Aggravating factors
6. Relieving factors
7. Associated symptoms
8. Timing patterns
9. Prior episodes
10. Medical history
11. Current medications
12. Allergies
13. Family history
14. Social history (smoking, alcohol)
15. Recent travel or exposures
16. Impact on daily activities
17-20. Any remaining clinically relevant details not yet covered

### Procedure ###
1. **Start Interview:** Wait for the patient to speak first. Do NOT introduce yourself. Your FIRST response only: briefly acknowledge their concern (one short phrase), then immediately ask your first question. For ALL responses after the first: output ONLY the question — no greeting, no acknowledgment, no preamble of any kind.
2. **Conduct Interview:** Proceed with your questioning, following all rules and strategies above. Always match the patient's language.
3. **End Interview:** You MUST continue until you have asked 20 questions OR the patient cannot provide more information. Then conclude with (in the patient's language): "Thank you for answering my questions. I have everything needed to prepare a report for your visit. End interview."
"""


def report_writer_instructions() -> str:
    """System prompt for report writing. No EHR — built from conversation only."""
    return """<role>
You are a highly skilled medical assistant with expertise in clinical documentation.
</role>

<task>
Your task is to generate a concise yet clinically comprehensive medical intake report
for a Primary Care Physician (PCP). This report is based SOLELY on the patient interview.
</task>

<guiding_principles>
1. **Principle of Brevity**:
   - Use professional medical terminology.
   - Omit conversational filler, pleasantries, or repeated phrases.

2. **Principle of Clinical Relevance**:
   - Prioritize the HPI (onset, duration, quality, severity, timing, modifying factors).
   - Include pertinent negatives the patient explicitly denies.
   - Include any self-reported medical history or medications the patient mentions.
</guiding_principles>

<instructions>
1. Synthesize the interview into a clear, organized report.
2. Content Focus:
   - **Primary Concern**: Chief complaint.
   - **HPI**: Detailed history of present illness with pertinent negatives.
   - **Self-reported Medical History**: Only what the patient reports.
   - **Medications**: Only what the patient reports.
3. Constraints: Factual information only. No diagnosis or assessment.
</instructions>

<output_format>
Output ONLY the full Markdown medical report. No introductions or explanations.
</output_format>"""

REPORT_TEMPLATE = """### Primary concern:

### History of Present Illness (HPI):

### Self-reported Medical History:

### Medications:
"""


def write_report(patient_name: str, interview_text: str, existing_report: str = None) -> str:
    """Build / update the medical report from interview Q&A only (no EHR)."""
    instructions = report_writer_instructions()

    if not existing_report:
        existing_report = REPORT_TEMPLATE

    user_prompt = f"""Patient name: {patient_name}

<interview_start>
{interview_text}
<interview_end>

<previous_report>
{existing_report}
</previous_report>

<task_instructions>
Update the report using the new information from the interview.
1. Integrate new symptoms or details into the appropriate sections.
2. Replace outdated details with more current information.
3. Remove information that is no longer relevant.
4. Do not change the Markdown section titles.
</task_instructions>

Generate the complete and updated medical report. Output only the Markdown text."""

    messages = [
        {"role": "system", "content": [{"type": "text", "text": instructions}]},
        {"role": "user",   "content": [{"type": "text", "text": user_prompt}]}
    ]

    report = medgemma_get_text_response(messages)
    cleaned = re.sub(r'<unused94>.*?</unused95>', '', report, flags=re.DOTALL).strip()
    match = re.match(r'^\s*```(?:markdown)?\s*(.*?)\s*```\s*$', cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        cleaned = match.group(1)
    return cleaned.strip()


def _strip_greeting(text: str, is_first_response: bool) -> str:
    """Remove greeting phrases from model responses after the first turn."""
    if is_first_response:
        return text  # allow greeting only on first response

    # Common Arabic and English greeting patterns to strip
    greeting_patterns = [
        r'^أهلاً بك[،,.]?\s*',
        r'^أهلاً وسهلاً[،,.]?\s*',
        r'^مرحباً[،,.]?\s*',
        r'^مرحبا[،,.]?\s*',
        r'^أهلا[،,.]?\s*',
        r'^حياك الله[،,.]?\s*',
        r'^Hello[,.]?\s*',
        r'^Hi[,.]?\s*',
        r'^Welcome[,.]?\s*',
        r'^Good\s+\w+[,.]?\s*',
        r'^Greetings[,.]?\s*',
    ]
    for pattern in greeting_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

    return text


def _is_system_nudge(msg: dict) -> bool:
    """Check if a dialog message is a temporary system nudge (should be cleaned up)."""
    try:
        content = msg.get("content", [])
        if isinstance(content, list):
            return any(
                "__SYSTEM_NUDGE__" in (c.get("text", "") if isinstance(c, dict) else "")
                for c in content
            )
        if isinstance(content, str):
            return "__SYSTEM_NUDGE__" in content
    except Exception:
        pass
    return False


def _clean_nudges(dialog: list) -> list:
    """Remove all temporary system nudge messages from dialog."""
    return [msg for msg in dialog if not _is_system_nudge(msg)]


def start_interview(patient_name: str) -> tuple:
    """
    Begin a new interview session.
    Returns (session_id, None) because patient speaks first.
    """
    session_id = str(uuid.uuid4())

    instructions = interviewer_roleplay_instructions(patient_name, "English")

    dialog = [
        {"role": "system", "content": [{"type": "text", "text": instructions}]}
    ]

    sessions[session_id] = {
        "patient_name": patient_name,
        "dialog": dialog,
        "report": "",
        "full_qa": "",
        "question_count": 0,
        "ended": False,
        "last_question": None,
        "patient_language": None,
        "asked_questions": [],          # ← NEW: tracks all asked questions
    }

    return session_id, None


def process_patient_message(session_id: str, patient_text: str) -> tuple:
    """
    Process a patient reply and return (next_question, updated_report, is_ended).
    Includes loop detection to prevent the model from repeating questions.
    """
    session = sessions.get(session_id)
    if session is None or session["ended"]:
        return None, session.get("report", "") if session else "", True

    patient_text = _normalize_response(patient_text)
    patient_name = session["patient_name"]

    # ── Detect patient language on first message ──────────────────────────
    if session["patient_language"] is None:
        detected_lang = detect_patient_language(patient_text)
        session["patient_language"] = detected_lang
        new_instructions = interviewer_roleplay_instructions(patient_name, detected_lang)
        session["dialog"][0]["content"][0]["text"] = new_instructions

    # ── Add patient turn to dialog ────────────────────────────────────────
    session["dialog"].append(
        {"role": "user", "content": [{"type": "text", "text": patient_text}]}
    )

    # ── Build Q&A for the report writer ──────────────────────────────────
    if session["last_question"]:
        qa_pair = f"Q: {session['last_question']}\nA: {patient_text}\n"
    else:
        qa_pair = f"Patient initial concern: {patient_text}\n"

    combined_qa = (
        "PREVIOUS Q&A:\n" + session["full_qa"] +
        "\nNEW Q&A:\n" + qa_pair
    )

    # ── Update report ─────────────────────────────────────────────────────
    session["report"] = write_report(patient_name, combined_qa, session["report"])
    session["full_qa"] += qa_pair

    if session["last_question"]:
        session["question_count"] += 1

    # ── Check question limit ──────────────────────────────────────────────
    if session["question_count"] > 20:
        session["ended"] = True
        end_messages = {
            'Arabic':  "شكرًا لإجابتك على أسئلتي. لدي الآن كل المعلومات اللازمة لإعداد تقرير لزيارتك. إنهاء المقابلة.",
            'English': "Thank you for answering my questions. I have everything needed to prepare a report for your visit. End interview.",
            'French':  "Merci d'avoir répondu à mes questions. J'ai tout ce qu'il faut pour préparer un rapport pour votre visite. Fin de l'entretien.",
            'Spanish': "Gracias por responder a mis preguntas. Tengo todo lo necesario para preparar un informe para su visita. Fin de la entrevista.",
        }
        end_msg = end_messages.get(session["patient_language"], end_messages['English'])
        return end_msg, session["report"], True

    # ── Build a summary of already-asked questions for the nudge ─────────
    asked_summary = ""
    if session["asked_questions"]:
        asked_summary = "\n".join(
            f"- {q}" for q in session["asked_questions"]
        )

    # ── Try to get a NEW, non-repeated question (up to 3 attempts) ────────
    MAX_ATTEMPTS = 3
    clean_question = None
    raw_question   = None

    for attempt in range(MAX_ATTEMPTS):
        # On retry, inject a nudge so the model knows to change course
        if attempt > 0:
            nudge_text = (
                f"__SYSTEM_NUDGE__ You just repeated a question that was already asked. "
                f"You MUST ask a completely different question now. "
                f"Questions already asked:\n{asked_summary}\n"
                f"Pick a NEW topic that has NOT been covered yet."
            )
            session["dialog"].append({
                "role": "user",
                "content": [{"type": "text", "text": nudge_text}]
            })

        raw = medgemma_get_text_response(
            messages=session["dialog"],
            temperature=0.1 + (attempt * 0.15),   # raise temp on retry
            max_tokens=2048,
        )
        raw = re.sub(r'<unused\d+>.*?</unused\d+>', '', raw, flags=re.DOTALL)
        candidate = _normalize_response(raw)
        # Strip greetings for every response after the very first
        is_first = (session["question_count"] == 0 and attempt == 0)
        candidate = _strip_greeting(candidate, is_first_response=is_first)
        clean_candidate = candidate.replace("End interview.", "").strip()

        # Accept the candidate if it differs from ALL previously asked questions
        is_repeated = any(
            clean_candidate.strip() == q.strip()
            for q in session["asked_questions"]
        )

        if not is_repeated:
            clean_question = clean_candidate
            raw_question   = candidate
            break

    # ── Clean all nudge messages from dialog before storing assistant turn ─
    session["dialog"] = _clean_nudges(session["dialog"])

    # ── Fallback if model kept repeating after all attempts ──────────────
    if clean_question is None:
        fallback_questions = {
            'Arabic':  "هل هناك أي شيء آخر تريد إضافته؟",
            'English': "Is there anything else you'd like to add?",
            'French':  "Y a-t-il autre chose que vous souhaitez ajouter?",
            'Spanish': "¿Hay algo más que le gustaría agregar?",
        }
        clean_question = fallback_questions.get(
            session["patient_language"], fallback_questions['English']
        )
        raw_question = clean_question

    # ── Store assistant turn in dialog ────────────────────────────────────
    session["dialog"].append(
        {"role": "assistant", "content": [{"type": "text", "text": raw_question}]}
    )

    # ── Track the new question ────────────────────────────────────────────
    session["last_question"] = clean_question
    session["asked_questions"].append(clean_question)

    if session["question_count"] == 0:
        session["question_count"] = 1

    # ── Check for natural end-of-interview signal from model ──────────────
    if "End interview" in raw_question:
        session["ended"] = True
        return clean_question, session["report"], True

    return clean_question, session["report"], False


def start_interview_with_patient_first(patient_name: str, patient_first_message: str) -> tuple:
    """
    بدء مقابلة مع أول رسالة من المريض مباشرة
    """
    session_id, _ = start_interview(patient_name)
    return process_patient_message(session_id, patient_first_message)