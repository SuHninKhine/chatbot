import streamlit as st
from openai import OpenAI
from datetime import date

# =========================================================
# ✅ API Setup
# =========================================================
API_KEY = st.secrets.get("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❗️ OpenRouter API key not found. Please add it in your Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")

# =========================================================
# ✅ Page Config
# =========================================================
st.set_page_config(page_title="💬 AI Therapist", page_icon="🧠")
st.title("🧠 AI Therapist")
st.markdown("> A safe, non-judgmental space to listen, support, guide, and help you understand therapy approaches.")

# =========================================================
# ✅ Session State Initialization
# =========================================================
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": None,
        "gender": None,
        "birthday": None,
        "goal": None,
        "personality_profile": None,  # New field for quiz answers
    }

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =========================================================
# ✅ Personality Quiz Questions (0-100% scale)
# =========================================================
personality_questions = [
    {"key": "energy", "question": "When meeting new people, how energized do you feel?"},
    {"key": "decision_style", "question": "When making decisions, how much do you rely on logic (vs feelings)?"},
    {"key": "focus", "question": "How much do you prefer practical details (vs big-picture ideas)?"},
    {"key": "structure", "question": "How much do you prefer plans and structure (vs spontaneity)?"},
    {"key": "stress_response", "question": "When stressed, how much do you seek social support (vs dealing with it alone)?"}
]
percentage_options = ["0%", "20%", "40%", "60%", "80%", "100%"]

# =========================================================
# ✅ Build System Prompt (Personality Included)
# =========================================================
def build_system_prompt(profile):
    base_prompt = (
        "You are a warm, empathetic, and supportive AI therapist. "
        "You start with supportive listening, then provide gentle, educational guidance. "
        "You are skilled in explaining and applying counselling approaches with examples — CBT, Person-Centered, Psychodynamic, Solution-Focused, Gestalt, Narrative, and Integrative.\n\n"
        "User details:\n"
        f"- Name: {profile.get('name', 'N/A')}\n"
        f"- Gender: {profile.get('gender', 'N/A')}\n"
        f"- Date of Birth: {profile.get('birthday', 'N/A')}\n"
        f"- Therapy Goal: {profile.get('goal', 'N/A')}\n"
    )
    if profile.get("personality_profile"):
        base_prompt += "Personality profile (0–100% scale answers):\n"
        for q in personality_questions:
            ans = profile["personality_profile"].get(q["key"], "N/A")
            base_prompt += f"- {q['question']} → {ans}\n"

    base_prompt += (
        "\nConversation rules:\n"
        "- Always validate the user's feelings first.\n"
        "- If asked about therapy methods, give clear examples and benefits.\n"
        "- If asked 'which therapy fits me', explain how counsellors decide in real-world practice.\n"
        "- If user types 'summary' or 'end session', summarise the session with actionable steps.\n"
        "- If signs of crisis appear, urge contacting a crisis hotline immediately.\n"
    )
    return base_prompt

# =========================================================
# ✅ Onboarding Flow
# =========================================================
onboarding_questions = [
    ("name", "Hi! What’s your name?", None),
    ("gender", "How do you identify?", ["Male", "Female", "Non-binary", "Prefer not to say"]),
    ("birthday", "When is your birthday?", None),
    ("goal", "What’s your main goal with therapy right now?",
        ["Reduce stress", "Manage anxiety", "Improve self-confidence", "Better self-awareness", "Other"]),
]

def onboarding_incomplete(profile):
    for field, _, _ in onboarding_questions:
        if profile.get(field) is None:
            return field
    if profile.get("personality_profile") is None:
        return "personality_profile"
    return None

def ask_onboarding_question(field, question, options=None):
    if field == "birthday":
        dob = st.date_input(question, key=field, min_value=date(1900,1,1), max_value=date.today())
        if st.button("Submit", key=f"submit_{field}"):
            st.session_state.user_profile[field] = dob.strftime("%Y-%m-%d")
            st.rerun()
    elif options:
        choice = st.radio(question, options, key=field, horizontal=True)
        if st.button("Submit", key=f"submit_{field}"):
            st.session_state.user_profile[field] = choice
            st.rerun()
    else:
        answer = st.text_input(question, key=field)
        if answer:
            st.session_state.user_profile[field] = answer.strip()
            st.rerun()

def ask_personality_profile():
    st.write("### Quick personality check (slider 0% - 100%)")
    answers = {}
    for q in personality_questions:
        ans = st.select_slider(q["question"], options=percentage_options, key=q["key"])
        answers[q["key"]] = ans
    if st.button("Submit Personality Profile"):
        st.session_state.user_profile["personality_profile"] = answers
        st.rerun()

next_field = onboarding_incomplete(st.session_state.user_profile)
if next_field:
    if next_field == "personality_profile":
        ask_personality_profile()
    else:
        for field, question, options in onboarding_questions:
            if field == next_field:
                ask_onboarding_question(field, question, options)
    st.stop()

# =========================================================
# ✅ Intro After Onboarding
# =========================================================
if not st.session_state.get("intro_message_shown"):
    name = st.session_state.user_profile["name"]
    goal = st.session_state.user_profile["goal"]
    intro_message = (
        f"{name}, I’m glad you’re here. Your main goal is **{goal.lower()}**.\n\n"
        "I've also noted your personality preferences to help tailor our conversation.\n"
        "Let's begin — could you share what’s been on your mind lately?"
    )
    st.session_state.chat_history.append({"role": "assistant", "content": intro_message})
    st.session_state.intro_message_shown = True
    st.rerun()

# =========================================================
# ✅ Chat History Setup
# =========================================================
if not st.session_state.chat_history:
    system_prompt = build_system_prompt(st.session_state.user_profile)
    greeting = f"Hello, {st.session_state.user_profile['name']}! How are you feeling today?"
    st.session_state.chat_history = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": greeting}
    ]
else:
    st.session_state.chat_history[0]["content"] = build_system_prompt(st.session_state.user_profile)

# =========================================================
# ✅ Display Messages
# =========================================================
for message in st.session_state.chat_history[1:]:
    st.chat_message(message["role"]).write(message["content"])

# =========================================================
# ✅ AI Call (with summary command)
# =========================================================
def ask_ai(user_message, history):
    try:
        if user_message.strip().lower() in ["summary", "end session"]:
            summary_prompt = history + [
                {"role": "user", "content": "Please give a session summary with key points discussed and recommended next steps."}
            ]
            response = client.chat.completions.create(
                model="meta-llama/llama-3-70b-instruct",
                messages=summary_prompt,
                max_tokens=500,
                temperature=0.4,
            )
        else:
            response = client.chat.completions.create(
                model="meta-llama/llama-3-70b-instruct",
                messages=history,
                max_tokens=800,
                temperature=0.4,
            )
        ai_reply = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": ai_reply})
        return ai_reply, history
    except Exception as e:
        error_msg = f"⚠️ Error: {str(e)}"
        history.append({"role": "assistant", "content": error_msg})
        return error_msg, history

# =========================================================
# ✅ Pending Input Handling
# =========================================================
if "pending_user_input" in st.session_state:
    user_msg = st.session_state.pending_user_input
    st.chat_message("user").write(user_msg)
    st.session_state.chat_history.append({"role": "user", "content": user_msg})
    with st.spinner("Thinking..."):
        reply, st.session_state.chat_history = ask_ai(user_msg, st.session_state.chat_history)
    del st.session_state["pending_user_input"]
    st.rerun()

# =========================================================
# ✅ User Input Box
# =========================================================
user_input = st.chat_input("Type your message here...")
if user_input:
    st.session_state.pending_user_input = user_input
    st.rerun()
