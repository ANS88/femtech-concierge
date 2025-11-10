# chat.py
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from tools import recommend_apps

# Load environment variables from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set in .env")

client = OpenAI(api_key=api_key)

# ---- System prompt for your Femtech Concierge ----
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

# ---- Tool schema we expose to the model ----
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


def chat_loop() -> None:
    """Simple terminal chat loop with the Femtech Concierge agent."""
    print("Femtech Concierge ✨ (type 'quit' to exit)\n")

    # Start conversation with system prompt
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit"}:
            print("Bye! 💛")
            break

        messages.append({"role": "user", "content": user_input})

        # First call: let the model decide if it wants to call a tool
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # you can change this to another chat model if needed
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        # If the model decided to call a tool:
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

                    # Add the tool result as a message
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": "recommend_apps",
                        "content": json.dumps(apps)
                    })

            # Second call: give the model the tool output so it can craft a good answer
            followup = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages + [msg] + tool_messages
            )
            final_msg = followup.choices[0].message
            assistant_text = final_msg.content
            print(f"\nConcierge: {assistant_text}\n")
            messages.append({"role": "assistant", "content": assistant_text})

        else:
            # No tool used, just answer directly
            assistant_text = msg.content
            print(f"\nConcierge: {assistant_text}\n")
            messages.append({"role": "assistant", "content": assistant_text})


if __name__ == "__main__":
    chat_loop()
