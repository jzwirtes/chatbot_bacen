import os
import streamlit as st
from google import genai
import json
from content import limpar_texto_html, fetch_normativo
from datetime import datetime

# Configurações
KEY = ""
client = genai.Client(api_key=KEY)

SYSTEM_PROMPT = (
    "Atue como um analista regulatório. "
    "Seu papel é ler e interpretar o texto das normas que o usuário envia "
    "e responder às questões do usuário baseando-se, se possível, estritamente no texto das normas."
)

reg_types = [
    "Resolução CMN",
    "Resolução BCB",
    "Instrução Normativa BCB",
    "Circular",
    "Carta Circular",
    "Resolução Conjunta"
]

LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)

def escreve_log(log_path: str, role: str, content: str):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    ts = datetime.now().isoformat(sep=" ", timespec="seconds")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {role}: {content}\n\n")

# Inicialização de session_state
if "chat" not in st.session_state:
    st.session_state.chat = None
    st.session_state.log_path = None
    st.session_state.norma_loaded = False
    st.session_state.normas = []      # lista de tuples (tipo, numero, payload_json)
    st.session_state.history = []     # lista de {"role", "content"}

st.title("BCBot — Assistente de Normas do BCB")

# Sidebar: formulário para adicionar uma norma
with st.sidebar.expander("📄 Adicionar norma"):
    with st.form("add_norma"):
        tipo_reg = st.selectbox("Tipo da norma", reg_types)
        numero = st.text_input("Número da norma", help="Somente dígitos")
        btn = st.form_submit_button("Adicionar")
    if btn:
        if not numero.isdigit():
            st.sidebar.error("O número deve conter apenas dígitos.")
        else:
            # Busca e limpa
            raw = fetch_normativo(tipo_reg, numero)
            norma = raw["conteudo"][0]
            norma["Texto"] = limpar_texto_html(norma["Texto"])
            payload = json.dumps(norma, ensure_ascii=False, indent=2)

            # Se for a primeira norma, inicializa chat e log
            if not st.session_state.norma_loaded:
                safe_tipo = tipo_reg.replace(" ", "_").replace("º", "")
                log_path = os.path.join(LOG_DIR, f"chat_{safe_tipo}_{numero}.log")
                st.session_state.log_path = log_path
                # inicia chat
                chat = client.chats.create(model="gemini-2.5-flash-lite-preview-06-17")
                # envia sistema
                chat.send_message(SYSTEM_PROMPT)
                escreve_log(log_path, "system", SYSTEM_PROMPT)
                st.session_state.chat = chat
                st.session_state.norma_loaded = True

            # registra esta norma no histórico e no chat
            st.session_state.normas.append((tipo_reg, numero, payload))
            st.session_state.chat.send_message(f"Informações da norma:\n{payload}")
            escreve_log(st.session_state.log_path, "user", f"Informações da norma:\n{payload}")
            st.session_state.history.append({"role": "assistant", 
                                             "content": f"Norma adicionada: {tipo_reg} nº {numero}"})
            st.success(f"{tipo_reg} nº {numero} adicionada ao contexto.")

# Área principal: chat
if st.session_state.norma_loaded:
    # Pergunta
    pergunta = st.chat_input("Faça sua pergunta sobre as normas:")
    if pergunta:
        # log e histórico
        escreve_log(st.session_state.log_path, "user", pergunta)
        st.session_state.history.append({"role": "user", "content": pergunta})
        # envia ao Gemini
        try:
            resp = st.session_state.chat.send_message(pergunta)
            answer = resp.text
        except Exception as e:
            answer = f"Erro ao chamar Gemini: {e}"
            escreve_log(st.session_state.log_path, "error", answer)
        # log e histórico da resposta
        escreve_log(st.session_state.log_path, "assistant", answer)
        st.session_state.history.append({"role": "assistant", "content": answer})

    # Exibe todo o histórico (omitindo system e payload internos)
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
