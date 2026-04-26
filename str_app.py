"""
AppointReady — Live Chat Medical Interview (Streamlit UI)

Run with:
    streamlit run streamlit_app.py
"""
import io
import re

from edge_ai_tts import synthesize_tts
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import streamlit as st
from interview_simulator import start_interview, process_patient_message
from stt_service import transcribe_audio


def _get_tts_audio(text: str | None):
    """Generate TTS audio bytes, auto-selecting Arabic or English voice."""
    if not text:
        return None
    has_arabic = bool(re.search('[\u0600-\u06FF]', text))
    voice = "ar-EG-SalmaNeural" if has_arabic else "en-US-AriaNeural"
    audio_bytes, _ = synthesize_tts(text, voice)
    return audio_bytes


def _report_to_pdf_bytes(report_markdown: str, patient_name: str) -> bytes:
    """Convert markdown report text to a styled PDF and return raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=50, leftMargin=50,
        topMargin=60, bottomMargin=50,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ReportTitle', parent=styles['Title'],
        fontSize=16, textColor=colors.HexColor('#0f172a'),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        'ReportSub', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#64748b'),
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        'ReportHeading', parent=styles['Heading3'],
        fontSize=11, textColor=colors.HexColor('#0369a1'),
        spaceBefore=14, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'ReportBody', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#1e293b'),
        leading=16, spaceAfter=4,
    )

    story = [
        Paragraph("AppointReady — Medical Intake Report", title_style),
        Paragraph(f"Patient: {patient_name}", subtitle_style),
    ]

    for line in report_markdown.splitlines():
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], heading_style))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], heading_style))
        elif line.startswith('**') and line.endswith('**'):
            story.append(Paragraph(f"<b>{line[2:-2]}</b>", body_style))
        else:
            # Escape any stray XML characters that would break ReportLab
            safe = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe, body_style))

    doc.build(story)
    return buffer.getvalue()


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AppointReady",
    page_icon="🏥",
    layout="wide",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #0f172a;
    }

    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }

    [data-testid="stSidebar"] .stInfo {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        color: #94a3b8 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #334155 !important;
    }

    /* ── Report card inside sidebar ── */
    .report-card {
        background: #1e293b;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-top: 0.5rem;
        border: 1px solid #334155;
        font-size: 0.88rem;
        line-height: 1.7;
        color: #e2e8f0 !important;
    }

    /* Section headers inside the report */
    .report-card h3 {
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: #38bdf8 !important;
        margin-top: 1.1rem !important;
        margin-bottom: 0.3rem !important;
        padding-bottom: 0.25rem !important;
        border-bottom: 1px solid #334155 !important;
    }

    .report-card p, .report-card li {
        color: #cbd5e1 !important;
        margin: 0.2rem 0 !important;
    }

    /* ── Status badge ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .badge-active {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-ended {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }

    /* ── Main chat header ── */
    .app-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.25rem;
    }
    .app-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
    }
    .app-subtitle {
        color: #64748b;
        font-size: 0.9rem;
        margin-top: 0.1rem;
    }

    /* ── Start screen card ── */
    .start-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 2.5rem 2rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }

    .start-card h3 {
        font-size: 1.3rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.5rem;
    }

    .start-card p {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* ── Chat bubbles tweak ── */
    [data-testid="stChatMessage"] {
        border-radius: 12px !important;
    }

    /* ── Sidebar title ── */
    .sidebar-title {
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #94a3b8;
        margin-bottom: 0.8rem;
    }

    /* ── Reset button ── */
    [data-testid="stSidebar"] .stButton button {
        background: #1e3a5f !important;
        color: #93c5fd !important;
        border: 1px solid #2563eb !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: #1d4ed8 !important;
        color: #fff !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ───────────────────────────────────────────────────
_defaults = {
    "interview_started": False,
    "interview_ended": False,
    "session_id": None,
    "messages": [],
    "report": "",
    "patient_name": "",
    "tts_audio": None,
    "last_audio_id": None,
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Sidebar: Report ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="sidebar-title">📄 Medical Report</p>', unsafe_allow_html=True)

    if st.session_state.interview_started:
        if st.session_state.interview_ended:
            st.markdown(
                '<span class="status-badge badge-ended">🔴 Interview Complete</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="status-badge badge-active">🟢 In Progress</span>',
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.report:
        # Render report markdown inside a styled card
        st.markdown(
            f'<div class="report-card">'
            + st.session_state.report.replace("\n", "<br>")
            + "</div>",
            unsafe_allow_html=True,
        )

        # ── Download PDF button ───────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        pdf_bytes = _report_to_pdf_bytes(
            st.session_state.report,
            st.session_state.patient_name,
        )
        st.download_button(
            label="⬇️ Download Report (PDF)",
            data=pdf_bytes,
            file_name=f"report_{st.session_state.patient_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("The medical report will appear here as the interview progresses.")

    if st.session_state.interview_started:
        st.divider()
        if st.button("🔄 Start New Interview", use_container_width=True):
            for key, val in _defaults.items():
                st.session_state[key] = val
            st.rerun()


# ── Main area ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-header">'
    '<span style="font-size:2rem">🏥</span>'
    '<div><p class="app-title">AppointReady</p>'
    '<p class="app-subtitle">Pre-visit Medical Interview — powered by MedGemma</p></div>'
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Start screen ─────────────────────────────────────────────────────────────
if not st.session_state.interview_started:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            '<div class="start-card">'
            "<h3>Welcome 👋</h3>"
            "<p>This assistant will ask you a few medical questions to prepare "
            "a report for your doctor before your visit.<br>"
            "You can respond in <strong>English</strong> or <strong>Arabic</strong> — "
            "the assistant will match your language.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        name = st.text_input(
            "Enter your name to begin:",
            placeholder="e.g. Ahmed / أحمد",
        )
        start_btn = st.button(
            "🚀 Start Interview",
            use_container_width=True,
            type="primary",
            disabled=not name,
        )

        if start_btn and name:
            with st.spinner("Starting interview..."):
                session_id, greeting = start_interview(name.strip())

            st.session_state.session_id = session_id
            st.session_state.interview_started = True
            st.session_state.patient_name = name.strip()
            st.session_state.messages.append(
                {"role": "assistant", "content": greeting}
            )
            st.session_state.tts_audio = _get_tts_audio(greeting)
            st.rerun()

# ── Chat screen ──────────────────────────────────────────────────────────────
else:
    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Auto-play TTS for the latest assistant message
    if st.session_state.tts_audio:
        st.audio(st.session_state.tts_audio, format="audio/mpeg", autoplay=True)
        st.session_state.tts_audio = None

    # Interview ended banner
    if st.session_state.interview_ended:
        st.success(
            "✅ Interview complete! Check the sidebar for your full medical report."
        )
    else:
        # ── Helper: process a prompt and update state ────────────────────
        def _handle_prompt(prompt: str):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    next_question, report, ended = process_patient_message(
                        st.session_state.session_id, prompt
                    )

            st.session_state.report = report
            st.session_state.interview_ended = ended
            if next_question:
                st.session_state.messages.append(
                    {"role": "assistant", "content": next_question}
                )
                st.session_state.tts_audio = _get_tts_audio(next_question)
            st.rerun()

        # ── Voice input ──────────────────────────────────────────────────
        audio = st.audio_input("🎙️ Record your response / سجّل ردك")
        if audio:
            audio_id = audio.file_id if hasattr(audio, "file_id") else id(audio)
            if audio_id != st.session_state.last_audio_id:
                st.session_state.last_audio_id = audio_id
                with st.spinner("Transcribing… / جارٍ التحويل…"):
                    prompt = transcribe_audio(
                        audio.read(),
                        language=None,
                    )
                if prompt:
                    _handle_prompt(prompt)

        # ── Text input ───────────────────────────────────────────────────
        if prompt := st.chat_input("Type your response here… / اكتب ردك هنا…"):
            _handle_prompt(prompt)