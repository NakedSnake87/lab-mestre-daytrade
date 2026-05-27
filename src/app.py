import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
from PIL import Image
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ── CONFIG ──────────────────────────────────────────────────────────────────
GEMINI_KEY = "AIzaSyCWQuirMzM1BqMT-8N71-Yz5lxEbNzzP0o"  # substitua pela sua chave real
NEWS_KEY   = "5124f5a861fa416db858736df592d6a1"           # substitua pela sua chave real

st.set_page_config(page_title="MestreDoDayTrade Pro", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"]{display:none!important}
[data-testid="collapsedControl"]{display:none!important}
.stApp{background:#0F1217!important;color:#E2E8F0!important}
.stTabs [data-baseweb="tab-list"]{background:#161A22;border-radius:8px;padding:4px;gap:4px}
.stTabs [data-baseweb="tab"]{background:transparent;color:#848E9C;border-radius:6px;font-weight:600;padding:8px 20px}
.stTabs [aria-selected="true"]{background:#2979FF!important;color:#fff!important}
.card{background:#161A22;border:1px solid #232936;border-radius:8px;padding:16px;margin-bottom:12px}
.metric-row{display:flex;gap:12px;margin-bottom:20px}
.metric-box{background:#161A22;border:1px solid #232936;border-radius:8px;padding:14px;flex:1;text-align:center}
.metric-label{color:#848E9C;font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:6px}
.metric-value{font-size:22px;font-weight:700}
.alert-red{background:#2D1418;border:1px solid #D50000;color:#FF8A80;padding:12px;border-radius:6px;text-align:center;font-weight:700;margin-bottom:16px}
.alert-green{background:#0D2318;border:1px solid #00C853;color:#69F0AE;padding:12px;border-radius:6px;text-align:center;font-weight:700;margin-bottom:16px}
.news-card{background:#161A22;border-left:4px solid #2979FF;border-radius:6px;padding:14px;margin-bottom:10px}
.news-title{color:#FFFFFF;font-weight:600;font-size:14px;margin-bottom:4px}
.news-meta{color:#848E9C;font-size:11px}
.roll-card{background:#161A22;border:1px solid #232936;border-radius:8px;padding:16px;margin-bottom:10px}
.stChatMessage{background:#161A22!important;border-radius:6px!important;margin-bottom:10px!important}
.stChatMessage p,.stChatMessage li{color:#FFFFFF!important;font-size:14px!important}
.stChatMessage strong{color:#00E676!important}
h1,h2,h3{color:#FFFFFF!important}
</style>
""", unsafe_allow_html=True)

# ── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("## 📈 MestreDoDayTrade Pro — Assistente Operacional WIN/WDO")

# ── DADOS DO TRADER ──────────────────────────────────────────────────────────
perfil = {"nome": "Trader Scalper Pro", "stop_diario": 200.0, "meta_diaria": 300.0, "max_win": 2, "max_wdo": 1}
trades = pd.DataFrame({
    "Horario": ["09:15", "10:30", "11:00"],
    "Ativo":   ["WING26", "WDOH26", "WING26"],
    "Resultado_RS": [80.0, -120.0, -170.0],
    "Setup": ["Retracao VWAP", "Rompimento Pivo", "Rompimento Pivo"]
})
saldo = trades["Resultado_RS"].sum()
wr    = len(trades[trades["Resultado_RS"] > 0]) / len(trades) * 100
bloqueado = saldo <= -perfil["stop_diario"]

# ── PAINEL TOPO ──────────────────────────────────────────────────────────────
cor_saldo = "#FF5252" if saldo < 0 else "#00E676"
st.markdown(f"""
<div class="metric-row">
  <div class="metric-box"><div class="metric-label">TRADER</div>
    <div class="metric-value" style="color:#fff;font-size:16px">{perfil['nome']}</div></div>
  <div class="metric-box"><div class="metric-label">SALDO DO DIA</div>
    <div class="metric-value" style="color:{cor_saldo}">R$ {saldo:.2f}</div></div>
  <div class="metric-box"><div class="metric-label">WIN RATE</div>
    <div class="metric-value" style="color:#00E676">{wr:.1f}%</div></div>
  <div class="metric-box"><div class="metric-label">OPERAÇÕES</div>
    <div class="metric-value" style="color:#fff">{len(trades)}</div></div>
  <div class="metric-box"><div class="metric-label">STATUS</div>
    <div class="metric-value" style="color:{'#FF5252' if bloqueado else '#00E676'};font-size:13px">
      {'🔴 BLOQUEADO' if bloqueado else '🟢 LIBERADO'}</div></div>
</div>
""", unsafe_allow_html=True)

if bloqueado:
    st.markdown('<div class="alert-red">🚨 STOP DIÁRIO ATINGIDO — PLATAFORMA BLOQUEADA. FECHE O PROFIT.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-green">✅ OPERAÇÕES LIBERADAS — Dentro do gerenciamento.</div>', unsafe_allow_html=True)

# ── ABAS ─────────────────────────────────────────────────────────────────────
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📊 Análise Técnica",
    "🛡️ Gerenciamento de Risco",
    "📰 Notícias do Mercado",
    "🔄 Rolagem de Contratos",
    "🤖 Chat Operacional"
])

# ════════════════════════════════════════════════════════════════════════════
# ABA 1 — ANÁLISE TÉCNICA
# ════════════════════════════════════════════════════════════════════════════
with aba1:
    st.markdown("### 📊 Análise Técnica de Gráficos")
    st.markdown('<div class="card">Envie um <b>print do seu gráfico</b> do ProfitPro. A IA vai identificar padrões gráficos, suportes, resistências, VWAP e dar uma análise técnica completa.</div>', unsafe_allow_html=True)

    grafico = st.file_uploader("📷 Carregar gráfico (WIN ou WDO):", type=["png", "jpg", "jpeg"], key="grafico")
    timeframe = st.selectbox("Timeframe do gráfico:", ["1 minuto", "5 minutos", "15 minutos", "60 minutos", "Diário"])
    ativo_analise = st.selectbox("Ativo:", ["Mini-Índice (WIN)", "Mini-Dólar (WDO)"])

    if grafico:
        st.image(grafico, caption="Gráfico carregado", use_column_width=True)
        if st.button("🔍 Analisar Gráfico", type="primary"):
            with st.spinner("Analisando padrões gráficos..."):
                bytes_img = grafico.getvalue()
                b64 = base64.b64encode(bytes_img).decode()
                llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key=GEMINI_KEY)
                prompt = f"""Você é um analista técnico sênior especialista em mercado futuro brasileiro (B3), 
                especificamente em {ativo_analise} no timeframe de {timeframe}.
                
                Analise este gráfico e forneça:
                1. PADRÕES GRÁFICOS identificados (OCO, Topo/Fundo Duplo, Triângulo, Bandeira, Cunha, etc.)
                2. SUPORTES E RESISTÊNCIAS principais visíveis
                3. INDICADORES (se visíveis): VWAP, Médias Móveis, Volume
                4. TENDÊNCIA atual (Alta, Baixa ou Lateral)
                5. CONTEXTO OPERACIONAL: o que o gráfico sugere para o trader
                6. PONTOS DE ATENÇÃO: riscos e armadilhas visíveis
                
                Use linguagem técnica de trader profissional. Seja direto e objetivo."""
                
                msg = HumanMessage(content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ])
                resp = llm.invoke([msg])
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown(resp.content)
                st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# ABA 2 — GERENCIAMENTO DE RISCO
# ════════════════════════════════════════════════════════════════════════════
with aba2:
    st.markdown("### 🛡️ Gerenciamento de Risco")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Plano de Trade")
        capital = st.number_input("Capital na corretora (R$):", value=10000.0, step=500.0)
        stop_op = st.number_input("Stop por operação (R$):", value=50.0, step=10.0)
        meta_op = st.number_input("Meta por operação (R$):", value=100.0, step=10.0)
        contratos = st.number_input("Contratos por operação:", value=1, step=1, min_value=1, max_value=10)

        rr = meta_op / stop_op if stop_op > 0 else 0
        risco_pct = (stop_op * contratos / capital * 100) if capital > 0 else 0

        st.markdown(f"""
        <div class="card">
        <div class="metric-label">RISCO/RETORNO</div>
        <div class="metric-value" style="color:{'#00E676' if rr >= 2 else '#FF5252'}">{rr:.1f}x</div>
        <br>
        <div class="metric-label">RISCO DO CAPITAL (%)</div>
        <div class="metric-value" style="color:{'#00E676' if risco_pct <= 2 else '#FF5252'}">{risco_pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

        if rr < 2:
            st.warning("⚠️ Risco/Retorno abaixo de 2:1. Revise sua meta ou stop.")
        if risco_pct > 2:
            st.error("🚨 Risco por operação acima de 2% do capital. Reduza os contratos.")

    with col2:
        st.markdown("#### Performance do Dia")
        st.dataframe(trades.style.applymap(
            lambda v: "color: #00C853" if isinstance(v, float) and v > 0 else ("color: #FF5252" if isinstance(v, float) and v < 0 else ""),
            subset=["Resultado_RS"]
        ), use_container_width=True)

        lucro = trades[trades["Resultado_RS"] > 0]["Resultado_RS"].sum()
        prejuizo = abs(trades[trades["Resultado_RS"] < 0]["Resultado_RS"].sum())
        fator_lucro = lucro / prejuizo if prejuizo > 0 else 0

        st.markdown(f"""
        <div class="card">
        <div class="metric-label">FATOR DE LUCRO</div>
        <div class="metric-value" style="color:{'#00E676' if fator_lucro >= 1.5 else '#FF5252'}">{fator_lucro:.2f}</div>
        <br>
        <div class="metric-label">PROGRESSO DA META</div>
        <div class="metric-value" style="color:#fff">{max(0,saldo):.0f} / {perfil['meta_diaria']:.0f}</div>
        </div>
        """, unsafe_allow_html=True)

        progresso = min(100, max(0, saldo / perfil["meta_diaria"] * 100))
        st.progress(progresso / 100)

# ════════════════════════════════════════════════════════════════════════════
# ABA 3 — NOTÍCIAS
# ════════════════════════════════════════════════════════════════════════════
with aba3:
    st.markdown("### 📰 Notícias Relevantes para WIN/WDO")

    col_busca, col_btn = st.columns([4, 1])
    with col_busca:
        termo = st.text_input("Buscar:", value="Ibovespa B3 mercado futuro", label_visibility="collapsed")
    with col_btn:
        buscar = st.button("🔍 Buscar", type="primary", use_container_width=True)

    temas = st.multiselect("Temas rápidos:", ["Ibovespa", "Dólar", "Juros COPOM", "Fed EUA", "PIB Brasil", "Petróleo", "China"], default=["Ibovespa", "Dólar"])

    if buscar or temas:
        query = termo + " " + " ".join(temas)
        with st.spinner("Buscando notícias..."):
            try:
                url = f"https://newsapi.org/v2/everything?q={query}&language=pt&sortBy=publishedAt&pageSize=10&apiKey={NEWS_KEY}"
                r = requests.get(url, timeout=10)
                data = r.json()
                arts = data.get("articles", [])

                if arts:
                    for a in arts[:8]:
                        titulo = a.get("title", "")
                        fonte  = a.get("source", {}).get("name", "")
                        data_p = a.get("publishedAt", "")[:10]
                        link   = a.get("url", "#")
                        desc   = a.get("description", "") or ""
                        st.markdown(f"""
                        <div class="news-card">
                          <div class="news-title">{titulo}</div>
                          <div class="news-meta">{fonte} • {data_p}</div>
                          <div style="color:#B0BEC5;font-size:13px;margin-top:6px">{desc[:150]}...</div>
                          <a href="{link}" target="_blank" style="color:#2979FF;font-size:12px">Ler mais →</a>
                        </div>
                        """, unsafe_allow_html=True)

                    # Resumo pela IA
                    if st.button("🤖 Resumir impacto no WIN/WDO", type="primary"):
                        with st.spinner("Analisando impacto no mercado..."):
                            headlines = "\n".join([a.get("title","") for a in arts[:5]])
                            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2, google_api_key=GEMINI_KEY)
                            prompt = f"""Você é um analista de mercado especialista em Mini-Índice (WIN) e Mini-Dólar (WDO) na B3.
                            
Com base nestas manchetes de hoje:
{headlines}

Analise:
1. Impacto esperado no Mini-Índice (alta/baixa/neutro e por quê)
2. Impacto esperado no Mini-Dólar (alta/baixa/neutro e por quê)
3. Principais riscos do dia para o trader de futuros
4. Horários críticos de volatilidade esperada

Seja direto e use linguagem de trader profissional."""
                            resp = llm.invoke([HumanMessage(content=prompt)])
                            st.markdown('<div class="card">', unsafe_allow_html=True)
                            st.markdown(resp.content)
                            st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("Nenhuma notícia encontrada. Tente outros termos.")
            except Exception as e:
                st.error(f"Erro ao buscar notícias: {e}")

# ════════════════════════════════════════════════════════════════════════════
# ABA 4 — ROLAGEM DE CONTRATOS
# ════════════════════════════════════════════════════════════════════════════
with aba4:
    st.markdown("### 🔄 Rolagem de Contratos WIN/WDO")

    st.markdown("""
    <div class="card">
    <b>📅 Calendário de Vencimentos 2025/2026</b><br><br>
    Os contratos futuros vencem na <b>quarta-feira mais próxima do dia 15</b> nos meses de vencimento.
    </div>
    """, unsafe_allow_html=True)

    vencimentos = [
        {"Contrato": "WINM25", "Ativo": "Mini-Índice", "Vencimento": "16/Jun/2025", "Status": "✅ Vencido"},
        {"Contrato": "WINQ25", "Ativo": "Mini-Índice", "Vencimento": "18/Ago/2025", "Status": "✅ Vencido"},
        {"Contrato": "WINV25", "Ativo": "Mini-Índice", "Vencimento": "15/Out/2025", "Status": "✅ Vencido"},
        {"Contrato": "WINZ25", "Ativo": "Mini-Índice", "Vencimento": "17/Dez/2025", "Status": "✅ Vencido"},
        {"Contrato": "WING26", "Ativo": "Mini-Índice", "Vencimento": "18/Fev/2026", "Status": "🔵 Ativo"},
        {"Contrato": "WINJ26", "Ativo": "Mini-Índice", "Vencimento": "15/Abr/2026", "Status": "🟡 Próximo"},
        {"Contrato": "WINM26", "Ativo": "Mini-Índice", "Vencimento": "17/Jun/2026", "Status": "⚪ Futuro"},
        {"Contrato": "WDOH26", "Ativo": "Mini-Dólar",  "Vencimento": "02/Mar/2026", "Status": "🔵 Ativo"},
        {"Contrato": "WDOJ26", "Ativo": "Mini-Dólar",  "Vencimento": "01/Abr/2026", "Status": "🟡 Próximo"},
        {"Contrato": "WDOK26", "Ativo": "Mini-Dólar",  "Vencimento": "04/Mai/2026", "Status": "⚪ Futuro"},
    ]

    df_venc = pd.DataFrame(vencimentos)
    st.dataframe(df_venc, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 📖 Como Fazer a Rolagem")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="roll-card">
        <b style="color:#00E676">📌 Quando rolar?</b><br><br>
        • <b>WIN:</b> Rolar na semana anterior ao vencimento<br>
        • <b>WDO:</b> Rolar 2-3 dias antes do vencimento<br>
        • Observe o <b>volume financeiro</b> — quando o contrato atual perder liquidez para o próximo, é hora de rolar<br>
        • Geralmente o volume migra <b>5-7 dias antes</b> do vencimento
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="roll-card">
        <b style="color:#2979FF">⚙️ Como rolar no Profit?</b><br><br>
        1. Monitore o <b>Open Interest</b> dos dois contratos<br>
        2. Quando o próximo superar o atual em volume, role<br>
        3. No Profit: altere o código do ativo no Book/Gráfico<br>
        4. <b>Atenção ao spread</b> na rolagem — evite rolar em horários de baixa liquidez<br>
        5. Melhor horário: <b>10h-11h30 e 14h-16h</b>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🤖 Perguntar ao Mestre sobre Rolagem", type="primary"):
        pergunta_roll = st.text_input("Sua dúvida sobre rolagem:")
        if pergunta_roll:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key=GEMINI_KEY)
            resp = llm.invoke([HumanMessage(content=f"Responda como especialista em mercado futuro brasileiro (B3): {pergunta_roll}")])
            st.markdown(resp.content)

# ════════════════════════════════════════════════════════════════════════════
# ABA 5 — CHAT OPERACIONAL
# ════════════════════════════════════════════════════════════════════════════
with aba5:
    st.markdown("### 🤖 Chat com o MestreDoDayTrade")

    PROMPT_MESTRE = f"""Você é o MestreDoDayTrade, uma IA especialista sênior em:
- Mercado futuro brasileiro: Mini-Índice (WIN) e Mini-Dólar (WDO) na B3
- Plataforma ProfitPro da Nelogica (ferramentas, indicadores, configurações)
- Análise técnica: Price Action, VWAP, Médias Móveis, Fibonacci, Tape Reading, Book de Ofertas
- Padrões gráficos: OCO, Topo/Fundo Duplo, Triângulos, Bandeiras, Cunhas, Candles japoneses
- Gerenciamento de risco e psicologia do trader

Contexto do trader hoje:
- Saldo: R$ {saldo:.2f} | Status: {'BLOQUEADO' if bloqueado else 'LIBERADO'}
- Win Rate: {wr:.1f}% | Operações: {len(trades)}

Instruções:
1. Use linguagem técnica de trader profissional da B3
2. Seja direto, objetivo e use jargões do mercado quando adequado
3. NUNCA dê calls de compra/venda em tempo real
4. Se o trader estiver BLOQUEADO, reforce que o dia operacional encerrou
5. Explique ferramentas do Profit com detalhes práticos quando perguntado
6. Para padrões gráficos, explique como identificar E como operar cada um"""

    if "chat_op" not in st.session_state:
        st.session_state.chat_op = []
        msg_inicial = "⚡ **MestreDoDayTrade ativo!** Estou pronto para te ajudar com análise técnica, ferramentas do Profit, padrões gráficos, gerenciamento de risco e dúvidas operacionais. O que você quer aprender ou discutir hoje?"
        if bloqueado:
            msg_inicial = "🚨 **ALERTA:** Você atingiu o stop diário. Dia operacional encerrado. Mas o módulo de estudo está ativo — podemos analisar seus erros de hoje e preparar a estratégia para amanhã. O que quer discutir?"
        st.session_state.chat_op.append(AIMessage(content=msg_inicial))

    for msg in st.session_state.chat_op:
        with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
            st.write(msg.content)

    # Upload de imagem no chat
    img_chat = st.file_uploader("📷 Anexar gráfico para análise no chat:", type=["png","jpg","jpeg"], key="img_chat")
    if img_chat:
        st.image(img_chat, width=300)

    if user_input := st.chat_input("Pergunte sobre WIN, WDO, Profit, padrões gráficos..."):
        with st.chat_message("user"):
            st.write(user_input)

        conteudo = [{"type": "text", "text": user_input}]
        if img_chat:
            b64 = base64.b64encode(img_chat.getvalue()).decode()
            conteudo.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        st.session_state.chat_op.append(HumanMessage(content=conteudo if img_chat else user_input))
        fluxo = [SystemMessage(content=PROMPT_MESTRE)] + st.session_state.chat_op

        with st.spinner("Analisando..."):
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key=GEMINI_KEY)
            resp = llm.invoke(fluxo)

        with st.chat_message("assistant"):
            st.write(resp.content)
        st.session_state.chat_op.append(AIMessage(content=resp.content))
