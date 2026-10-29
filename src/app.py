"""Web demo. Run from the project root:  streamlit run src/app.py"""
import streamlit as st
from agent import Session
from tools import load

st.set_page_config(page_title="Career Skills Assistant", page_icon="🎯", layout="wide")

EXAMPLES = ["What should I learn next?",
            "Enroll me in Intro to Machine Learning",
            "What skills does Jordan have?"]

employees = {e["employee_id"]: e for e in load("employees.json")}

# --- Sidebar: simulated sign-in. The employee id comes from here, never from the AI.
with st.sidebar:
    st.header("Signed in as")
    emp_id = st.selectbox("Employee", list(employees),
                          format_func=lambda i: f"{employees[i]['name']} ({i})")
    me = employees[emp_id]
    st.markdown(f"**{me['current_role']}**  \nGoal: {me['career_interest']}")
    st.caption("Current skills: " + ", ".join(me["skills"]))
    st.divider()
    show_details = st.toggle("Show behind the scenes", value=True)
    if st.button("Start over"):
        st.session_state.pop("session", None)

# --- One conversation per signed-in employee. Switching employees starts fresh.
if st.session_state.get("employee") != emp_id or "session" not in st.session_state:
    st.session_state.employee = emp_id
    st.session_state.session = Session(emp_id)
    st.session_state.chat = []
session = st.session_state.session


def show_recommendations(recs):
    """Skills, courses and roles as three columns of cards."""
    sections = [("Skills to build", recs["skills"], "skill"),
                ("Courses to take", recs["courses"], "title"),
                ("Roles to grow into", recs["roles"], "title")]
    for col, (heading, items, name_key) in zip(st.columns(3), sections):
        with col:
            st.markdown(f"#### {heading}")
            for item in items:
                with st.container(border=True):
                    st.markdown(f"**{item[name_key]}**")
                    st.caption(item["reason"])


def show_details_line(d):
    """What happened behind the scenes for one answer."""
    tools = ", ".join(d["tools"]) or "none"
    valid = "valid JSON ✓" if d["valid"] else "invalid JSON ✗"
    st.caption(f"Tools: {tools} · {valid} · {d['calls']} AI calls · "
               f"{d['ms']} ms · {d['tokens']} tokens")


def show_turn(turn):
    with st.chat_message(turn["role"]):
        if turn.get("error"):
            st.error(turn["text"])
            return
        st.markdown(turn["text"])
        if turn.get("recs"):
            show_recommendations(turn["recs"])
        if turn.get("details") and show_details:
            show_details_line(turn["details"])


# --- Page
st.title("Career Skills Assistant")
st.caption("Tells you what to learn next, based on your skills and career goal.")

for turn in st.session_state.chat:
    show_turn(turn)

question = st.chat_input("Ask the assistant…")
if not st.session_state.chat:              # quick-start buttons on an empty chat
    for col, example in zip(st.columns(len(EXAMPLES)), EXAMPLES):
        if col.button(example, use_container_width=True):
            question = example

if question and question.strip():
    question = question.strip()
    st.session_state.chat.append({"role": "user", "text": question})
    show_turn(st.session_state.chat[-1])

    calls_before = len(session.log)
    with st.chat_message("assistant"), st.spinner("Thinking…"):
        try:
            result = session.ask(question)
            calls = session.log[calls_before:]
            turn = {"role": "assistant", "text": result["message"],
                    "recs": result["recommendations"],
                    "details": {"tools": [t["tool"] for t in session.trace],
                                "valid": result["valid"],
                                "calls": len(calls),
                                "ms": sum(c["ms"] for c in calls),
                                "tokens": sum(c["tokens"] or 0 for c in calls)}}
        except Exception as e:             # API down, bad key, rate limit, etc.
            turn = {"role": "assistant", "error": True,
                    "text": f"Couldn't reach the AI model ({type(e).__name__}). "
                            "Check your .env settings and internet, then try again."}
    st.session_state.chat.append(turn)
    st.rerun()
