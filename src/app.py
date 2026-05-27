import streamlit as st
import pandas as pd
import json
import base64
from io import BytesIO
from PIL import Image
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Configuração da Página Sem a Barra Lateral
st.set_page_config(page_title="MestreDoDayTrade Pro", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# 🖥️ INJEÇÃO DE CSS CORRIGIDO (Garante contraste máximo e leitura brilhante)
st.markdown("""
    <style>
    /* Ocultar barra lateral */
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    
    /* Fundo Escuro Oficial ProfitPro */
    .stApp {
        background-color: #0F1217 !important;
        color: #FFFFFF !important;
    }
    
    /* Container dos Cards do Topo */
    .profit-grid {
        display: flex;
        gap: 15px;
        margin-bottom: 25px;
    }
    .profit-card {
        background-color: #161A22 !important;
        border: 1px solid #232936 !important;
        border-radius: 6px;
        padding: 15px;
        flex: 1;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* 🚨 BLINDAGEM DO TEXTO DO CHAT: Força a cor branca pura em TODOS os elementos de texto */
    .stChatMessage {
        background-color: #161A22 !important;
        border-radius: 6px !important;
        margin-bottom: 12px !important;
        padding: 15px !important;
    }
    
    /* Força texto branco brilhante para parágrafos, listas e textos gerais dentro do chat */
    .stChatMessage *, 
    .stChatMessage p, 
    .stChatMessage li, 
    .stChatMessage span,
    [data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
        font-weight: 400 !important;
    }
    
    /* Destaca títulos dentro da resposta da IA */
    .stChatMessage h1, .stChatMessage h2, .stChatMessage h3, .stChatMessage strong {
        color: #00E676 !important; /* Verde neon para títulos internos */
        font-weight: bold !important;
    }
    
    /* Mensagem do Usuário (Borda Verde Compra) */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        border-left: 5px solid #00C853 !important;
    }
    /* Mensagem da IA (Borda Vermelha Venda) */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        border-left: 5px solid #D50000 !important;
    }
    
    /* Alerta de Risco */
    .alert-profit {
        background-color: #2D1418 !important;
        border: 1px solid #D50000 !important;
        color: #FF8A80 !important;
        padding: 15px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-weight: bold;
        text-align: center;
    }
    
    /* Garante que os títulos principais fora do chat fiquem visíveis */
    h1, h2, h3 { color: #FFFFFF !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 MestreDoDayTrade v4.0 - Monitor de Tela ProfitPro")

# Base de Dados Injetada
perfil = {"nome_trader": "Trader Scalper Pro", "stop_maximo_diario_rs": 200.00, "meta_ganho_diaria_rs": 300.00}
dados_csv = {
    "Horario": ["09:15", "10:30", "11:00"], "Ativo": ["WING26", "WDOH26", "WING26"],
    "Resultado_RS": [80.00, -120.00, -170.00], "Setup": ["Retracao na VWAP", "Rompimento de Pivo", "Rompimento de Pivo"]
}
historico_trades = pd.DataFrame(dados_csv)
resultado_atual = historico_trades["Resultado_RS"].sum()
total_trades = len(historico_trades)
trades_ganhos = len(historico_trades[historico_trades["Resultado_RS"] > 0])
win_rate = (trades_ganhos / total_trades) * 100 if total_trades > 0 else 0

# WIDGETS DO TOPO
st.markdown(f"""
    <div class="profit-grid">
        <div class="profit-card">
            <span style="color: #848E9C !important; font-size: 12px; font-weight: bold;">CONTA CORRENTE / TRADER</span><br>
            <span style="color: #FFFFFF !important; font-size: 20px; font-weight: bold;">{perfil['nome_trader']}</span>
        </div>
        <div class="profit-card">
            <span style="color: #848E9C !important; font-size: 12px; font-weight: bold;">SALDO DO PREGÃO (LUCRO/PREJUÍZO)</span><br>
            <span style="color: #FF5252 !important; font-size: 24px; font-weight: bold;">R$ {resultado_atual:.2f}</span>
        </div>
        <div class="profit-card">
            <span style="color: #848E9C !important; font-size: 12px; font-weight: bold;">TAXA DE ACERTO (WIN RATE)</span><br>
            <span style="color: #00E676 !important; font-size: 24px; font-weight: bold;">{win_rate:.1f}%</span>
        </div>
    </div>
""", unsafe_allow_html=True)

if resultado_atual <= -perfil["stop_maximo_diario_rs"]:
    st.markdown('<div class="alert-profit">🚨 TRAVA DE SEGURANÇA ACIONADA: LIMITE DE STOP LOSS DIÁRIO VIOLADO NA CORRETORA. PLATAFORMA BLOQUEADA.</div>', unsafe_allow_html=True)
    status_risco = "BLOQUEADO - O trader quebrou os limites operacionais no mini-índice/mini-dólar."
else:
    status_risco = "LIBERADO - Operando dentro das regras matemáticas."

PROMPT_SISTEMA = f"""
Você é o MestreDoDayTrade, uma IA multimodal especialista sênior em mercado futuro de Mini-Índice (WIN) e Mini-Dólar (WDO) na B3. Você analisa tanto dados numéricos quanto capturas de tela do ProfitPro (gráficos, indicadores, VWAP, fluxo).

Dados de Hoje:
- Resultados: R$ {resultado_atual:.2f} (Stop Diário ultrapassado)
- Status: {status_risco}
- Histórico do Profit: {historico_trades.to_json(orient='records')}

Instruções Operacionais:
1. Responda usando jargões reais e sérios de traders de tela da B3 (como "preço de ajuste", "bater lote", "clicar errado", "fúria", "proteger no zero a zero").
2. Como o usuário estourou o risco, mande ele largar o mouse e fechar o Profit. Se ele enviar uma imagem de gráfico, faça uma análise fria e técnica explicando onde estavam os suportes, resistências ou indicadores visuais relevantes, mas lembre-o de que o dia operacional já encerrou.
3. Jamais dê dicas de compra/venda para entradas agora.
"""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    analise_inicial = "⚡ [MestreDoDayTrade] AMBIENTE PROFITPRO ATIVO: Identifiquei que você estourou o limite diário de perdas (R$ -210.00). O painel operacional está bloqueado para novas ordens. No entanto, o módulo de análise está ativo: você pode interagir via chat ou carregar um print do seu gráfico do Profit no botão abaixo para analisarmos tecnicamente o seu contexto operacional. O que deseja avaliar?"
    st.session_state.chat_history.append(AIMessage(content=analise_inicial))

for msg in st.session_state.chat_history:
    with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
        st.write(msg.content)

# Botão de Upload de Imagem
print_profit = st.file_uploader("📷 Carregar print de tela ou gráfico do ProfitPro para análise técnica:", type=["png", "jpg", "jpeg"])

if print_profit is not None:
    st.image(print_profit, caption="Print do Profit Carregado com Sucesso", width=450)

# Campo do Chat
if user_input := st.chat_input("Insira o comando ou dúvida técnica para o Mestre..."):
    with st.chat_message("user"):
        st.write(user_input)
    
    conteudo_human = [{"type": "text", "text": user_input}]
    
    if print_profit is not None:
        bytes_data = print_profit.getvalue()
        base64_image = base64.b64encode(bytes_data).decode("utf-8")
        conteudo_human.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
        
    st.session_state.chat_history.append(HumanMessage(content=conteudo_human))
    fluxo = [SystemMessage(content=PROMPT_SISTEMA)] + st.session_state.chat_history
    
    with st.spinner("Analisando fluxo, imagem e métricas de ordens..."):
        # ⚠️ LEMBRE-SE DE MANTER OPERACIONAL A SUA CHAVE DO GEMINI ABAIXO:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key="AIzaSyCWQuirMzM1BqMT-8N71-Yz5lxEbNzzP0o")
        response = llm.invoke(fluxo)
    
    with st.chat_message("assistant"):
        st.write(response.content)
    st.session_state.chat_history.append(AIMessage(content=response.content))
