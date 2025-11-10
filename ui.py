import os
import json
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from tools import recommend_apps  # uses your existing tool

# Load API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY is not set in .env")
    st.stop()

client = OpenAI(api_key=api_key)

# ---- System prompt (same vibe as chat.py) ----
SYSTEM_PROMPT = """
You are Femtech Concierge, a warm, evidence-informed, feminist companion
for people navigating cycles, perimenopause, and menopause.

You:
- Give education, tracking ideas, and visit prep help.
- Do NOT diagnose or prescribe or give medication instructions.
- Are weight-neutral and body-respectful.
- Suggest apps and tools when helpful.
- Encourage users to discuss any decisions with a clinician.

When recommending apps:
- Consider user preferences (platform, budget, no diet/weight-loss focus).
- Explain why each app might fit them.
- Use a friendly, validating tone.
Always remind: "I'm not a clinician; this is informational support only."
""".strip()

# ---- Tool schema (same as chat.py) ----
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "recommend_apps",
            "description": "Recommend femtech apps based on a goal and user preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "What the user wants, e.g. 'menopause_symptom_tracking' or 'cycle_tracking'."
                    },
                    "platform": {
                        "type": ["string", "null"],
                        "description": "Preferred platform, e.g. 'iOS' or 'Android'."
                    },
                    "max_price": {
                        "type": ["number", "null"],
                        "description": "Maximum monthly price in USD the user is willing to pay."
                    }
                },
                "required": ["goal"]
            }
        }
    }
]

# ---- Streamlit page setup ----
st.set_page_config(page_title="Femtech Concierge", page_icon="✨")
st.title("✨ Femtech Concierge")
st.caption("Prototype femtech agent – informational only, not medical advice.")

# Initialize chat history in session_state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []  # just user/assistant text for UI


def run_model(user_input: str) -> str:
    """
    Sends the conversation to the model, handles tool calls,
    and returns the assistant's reply text.
    """
    messages = st.session_state.messages + [{"role": "user", "content": user_input}]

    # First call: let the model decide if it wants to call a tool
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )

    msg = response.choices[0].message

    # If tool(s) called
    if getattr(msg, "tool_calls", None):
        tool_messages = []
        for tool_call in msg.tool_calls:
            if tool_call.function.name == "recommend_apps":
                args = json.loads(tool_call.function.arguments)
                apps = recommend_apps(
                    goal=args.get("goal"),
                    platform=args.get("platform"),
                    max_price=args.get("max_price"),
                )
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": "recommend_apps",
                    "content": json.dumps(apps)
                })

        # Second call: pass tool output back to model
        followup = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages + [msg] + tool_messages
        )
        final_msg = followup.choices[0].message
        return final_msg.content

    # No tool used, simple answer
    return msg.content


# ---- Chat UI ----

# Show chat history
for m in st.session_state.chat_display:
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
    elif m["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(m["content"])

# Input box at the bottom
user_input = st.chat_input("Ask about symptoms, apps, or visit prep...")

if user_input:
    # Add user message to UI history
    st.session_state.chat_display.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                reply = run_model(user_input)
            except Exception as e:
                reply = (
                    "Hmm, I ran into an error talking to the model. "
                    "Please try again or check your API key / quota."
                )
                st.error(str(e))

            st.markdown(reply)

    # Save assistant reply
    st.session_state.chat_display.append({"role": "assistant", "content": reply})
    st.session_state.messages.append({"role": "assistant", "content": reply})
    
