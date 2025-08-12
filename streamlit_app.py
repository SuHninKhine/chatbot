import streamlit as st
from openai import OpenAI
from datetime import date

# =========================================================
# ✅ API Setup (same as before)
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
st.markdown("> A safe, non-judgmental space to listen, support, and guide you gently.")

# =========================================================
# ✅ Session State Initialization
# =========================================================
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": None,
        "gender": None,
        "birthday": None,
        "goal": None
    }

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =========================================================
# ✅ Build System Prompt
# =========================================================
def build_system_prompt(profile):
    base_prompt = (
        "You are a warm, empathetic, and supportive AI therapist, skilled in active listening, "
        "reflective questioning, and goal-oriented encouragement. "
        "You use supportive listening first before offering strategies, "
        "and you never provide a diagnosis. Always consider the user's name, gender, "
        "date of birth, and personal goal for therapy when crafting responses.\n\n"

        "Conversation rules:\n"
        "- Always validate the user's feelings first.\n"
        "- Offer gentle, non-judgmental reflection.\n"
        "- Provide practical coping steps only when appropriate.\n"
        "- If the user expresses severe distress or suicidal thoughts, advise them to "
        "contact an appropriate crisis hotline immediately.\n"
        "- At the end of the session or on request, provide a session review with actionable steps.\n"
    )

    additions = []
    if profile.get("name"):
        additions.append(f"The user's name is {profile['name']}.")
    if profile.get("gender"):
        additions.append(f"The user identifies as {profile['gender']}.")
    if profile.get("birthday"):
        additions.append(f"The user was born on {profile['birthday']}.")
    if profile.get("goal"):
        additions.append(f"Their main goal for therapy is: {profile['goal']}.")

    return base_prompt + " " + " ".join(additions)


# =========================================================
# ✅ Onboarding Questions
# =========================================================
onboarding_questions = [
    ("name", "Hi! What’s your name?", None),
    ("gender", "How do you identify?", ["Male", "Female", "Non-binary", "Prefer not to say"]),
    ("birthday", "When is your birthday?", None),
    ("goal", "What’s your main goal with therapy right now?",
        ["Reduce stress", "Manage anxiety", "Improve self-confidence", "Better self-awareness", "Other"])
]

def onboarding_incomplete(profile):
    for field, _, _ in onboarding_questions:
        if profile.get(field) is None:
            return field
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

next_field = onboarding_incomplete(st.session_state.user_profile)
if next_field:
    for field, question, options in onboarding_questions:
        if field == next_field:
            ask_onboarding_question(field, question, options)
    st.stop()

# =========================================================
# ✅ Show Intro After Onboarding
# =========================================================
if not st.session_state.get("intro_message_shown"):
    name = st.session_state.user_profile["name"]
    goal = st.session_state.user_profile["goal"]

    intro_message = (
        f"{name}, I’m glad you’re here. I understand your main goal is **{goal.lower()}**.\n\n"
        "Let’s take things step-by-step. There's no rush — I’m here to listen first.\n\n"
        "To begin, could you share what’s been on your mind lately?"
    )

    st.session_state.chat_history.append({"role": "assistant", "content": intro_message})
    st.session_state.intro_message_shown = True
    st.rerun()

# =========================================================
# ✅ Initialize Chat History
# =========================================================
if not st.session_state.chat_history:
    system_prompt = build_system_prompt(st.session_state.user_profile)
    greeting = f"Hello, {st.session_state.user_profile['name']}! How are you feeling today?"
    st.session_state.chat_history = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": greeting}
    ]
else:
    system_prompt = build_system_prompt(st.session_state.user_profile)
    st.session_state.chat_history[0]["content"] = system_prompt

# =========================================================
# ✅ Display Messages
# =========================================================
for message in st.session_state.chat_history[1:]:
    if message["role"] == "assistant":
        st.chat_message("assistant").write(message["content"])
    elif message["role"] == "user":
        st.chat_message("user").write(message["content"])

# =========================================================
# ✅ AI Call
# =========================================================
def ask_ai(user_message, history):
    try:
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
