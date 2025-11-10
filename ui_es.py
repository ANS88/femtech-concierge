import os
import json
import streamlit as st
import openai 
from tools import recommend_apps  

from tools import recommend_apps
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

if "OPENAI_API_KEY" not in st.secrets:
    st.error("No se encontró OPENAI_API_KEY en los secretos de Streamlit.")
    st.stop()
    
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- PROMPT DEL SISTEMA EN ESPAÑOL ----
SYSTEM_PROMPT = """
Eres “Concierge Femtech”, una compañera cálida, informada y feminista
para personas que navegan el ciclo menstrual, la perimenopausia y la menopausia.

Tu rol:
- Ofreces educación, ideas para registrar síntomas y ayuda para preparar consultas médicas.
- NO diagnosticas, NO prescribes medicamentos ni indicas cambios de medicación.
- Usas un lenguaje respetuoso del cuerpo, sin cultura de dieta ni juicios sobre el peso.
- Sugieres apps y herramientas cuando son útiles.
- Siempre animas a hablar de las decisiones con un/a profesional de salud.

Seguridad:
- Si la persona describe síntomas muy graves (por ejemplo, dolor en el pecho, dificultad para respirar,
  sangrado muy abundante, desmayos, ideas de hacerse daño), recomiendas buscar atención médica urgente
  o servicios de emergencia, y dejas claro que no puedes valorar emergencias.

Al recomendar apps:
- Tienes en cuenta plataforma (iOS/Android), presupuesto y si la persona quiere evitar contenido de dieta/peso.
- Explicas por qué cada app puede encajar con sus objetivos.
- Tu tono es cálido, validante y sin alarmismo.

Siempre incluye una frase tipo:
“No soy profesional sanitario; esto es apoyo informativo y no sustituye una consulta médica.”

Responde SIEMPRE en español, a menos que la persona pida explícitamente otro idioma.
""".strip()

# ---- DEFINICIÓN DE LA HERRAMIENTA ----
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "recommend_apps",
            "description": "Recomienda apps femtech según el objetivo y las preferencias de la usuaria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Lo que la persona busca, por ejemplo 'menopause_symptom_tracking' o 'cycle_tracking'."
                    },
                    "platform": {
                        "type": ["string", "null"],
                        "description": "Plataforma preferida: 'iOS' o 'Android'."
                    },
                    "max_price": {
                        "type": ["number", "null"],
                        "description": "Precio máximo mensual en USD."
                    }
                },
                "required": ["goal"]
            }
        }
    }
]

# ---- CONFIGURACIÓN DE LA PÁGINA ----
st.set_page_config(page_title="Concierge Femtech (ES)", page_icon="✨")
st.title("✨ Concierge Femtech — versión en español")
st.caption("Prototipo de agente femtech — información general, no es consejo médico.")

# Historial de conversación en sesión
if "messages_es" not in st.session_state:
    st.session_state.messages_es = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
if "chat_display_es" not in st.session_state:
    st.session_state.chat_display_es = []  # solo usuario/asistente para mostrar


def run_model_es(user_input: str) -> str:
    """Envía la conversación al modelo, maneja herramientas y devuelve respuesta en español."""
    messages = st.session_state.messages_es + [{"role": "user", "content": user_input}]

    # Primera llamada: el modelo decide si quiere llamar a herramientas
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )

    msg = response.choices[0].message

    # Si hay llamadas a herramientas
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
                    "content": json.dumps(apps, ensure_ascii=False)
                })

        # Segunda llamada: el modelo recibe la salida de la herramienta
        followup = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages + [msg] + tool_messages
        )
        final_msg = followup.choices[0].message
        return final_msg.content

    # Sin herramientas → respuesta directa
    return msg.content


# ---- INTERFAZ DE CHAT ----

# Mostrar historial
for m in st.session_state.chat_display_es:
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
    elif m["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(m["content"])

# Cuadro de entrada abajo
user_input = st.chat_input("Haz una pregunta sobre síntomas, apps o cómo prepararte para tu cita médica...")

if user_input:
    # Guardar mensaje de usuario
    st.session_state.chat_display_es.append({"role": "user", "content": user_input})
    st.session_state.messages_es.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                reply = run_model_es(user_input)
            except Exception as e:
                reply = (
                    "Ups, he tenido un problema al hablar con el modelo. "
                    "Prueba de nuevo más tarde o revisa tu API key / cuota."
                )
                st.error(str(e))

            st.markdown(reply)
    # Guardar respuesta del asistente
    st.session_state.chat_display_es.append({"role": "assistant", "content": reply})
    st.session_state.messages_es.append({"role": "assistant", "content": reply})
