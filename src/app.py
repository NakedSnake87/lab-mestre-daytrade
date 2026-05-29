import streamlit as st
import requests
import base64
import time
import random
from datetime import datetime
from groq import Groq

# ── CONFIG ────────────────────────────────────────────────────────────────────
GROQ_KEY = st.secrets["GROQ_KEY"]
NEWS_KEY  = st.secrets["NEWS_KEY"]

# ── IA ────────────────────────────────────────────────────────────────────────
def ia(prompt, system="", historico=None, imagem_b64=None):
    client = Groq(api_key=GROQ_KEY)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    if historico:
        for h in historico[-10:]:  # últimas 10 mensagens pra não estourar contexto
            msgs.append({"role": h["role"], "content": h["content"]})
    if imagem_b64:
        msgs.append({"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagem_b64}"}}
        ]})
    else:
        msgs.append({"role": "user", "content": prompt})

    model = "meta-llama/llama-4-scout-17b-16e-instruct" if imagem_b64 else "llama-3.3-70b-versatile"
    resp = client.chat.completions.create(model=model, messages=msgs, max_tokens=1500, temperature=0.15)
    return resp.choices[0].message.content

# System prompt corrigido — sem topo duplo automático, sem ASCII
SYSTEM_PROMPT = """Você é o MestreDoDayTrade Pro — especialista em contratos futuros WIN (Mini-Índice) e WDO (Mini-Dólar) na B3.

REGRAS OBRIGATÓRIAS:
1. Responda APENAS o que foi perguntado. Sem enrolação, sem introdução longa.
2. NUNCA mencione Topo Duplo, OCO ou qualquer padrão gráfico a menos que o usuário pergunte especificamente sobre eles.
3. NUNCA faça desenhos ASCII. Jamais. Se precisar explicar visualmente, use texto descritivo curto.
4. Seja direto: máximo 4-6 linhas por resposta em perguntas simples.
5. Não emita calls de compra ou venda — apenas educação e gerenciamento de risco.
6. Se o usuário mandar um gráfico, analise o que vê: tendência, suportes/resistências, indicadores visíveis. Sem criar padrões que não estão claros.
7. Use linguagem direta de trader — não de professor universitário.
8. Foco total em WIN e WDO quando contextualizado em futuros B3."""

# ── COTAÇÕES — Yahoo Finance ──────────────────────────────────────────────────
ATIVOS = {
    # Índices Brasil
    "IBOVESPA": "^BVSP",
    "WIN (Mini-Índ.)": "WINM25.SA",
    "WDO (Mini-Dól.)": "WDOM25.SA",
    # Índices globais
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "DAX": "^GDAXI",
    "FTSE 100": "^FTSE",
    "Nikkei": "^N225",
    "Shanghai": "000001.SS",
    # Commodities
    "Petróleo WTI": "CL=F",
    "Ouro": "GC=F",
    # Forex
    "Dólar/BRL": "BRL=X",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CNY": "CNY=X",
    # Cripto
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD",
    "BNB": "BNB-USD",
}

@st.cache_data(ttl=60)
def buscar_cotacoes():
    simbolos = list(ATIVOS.values())
    tickers = "%2C".join(simbolos)
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={tickers}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        resultados = {}
        quotes = data.get("quoteResponse", {}).get("result", [])
        nome_por_simbolo = {v: k for k, v in ATIVOS.items()}
        for q in quotes:
            sym = q.get("symbol", "")
            nome = nome_por_simbolo.get(sym, sym)
            preco = q.get("regularMarketPrice", 0)
            var = q.get("regularMarketChangePercent", 0)
            resultados[nome] = {"preco": preco, "var": var}
        return resultados
    except:
        return {}

# ── NOTÍCIAS ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def buscar_noticias(query="Ibovespa B3 dólar mercado futuro"):
    url = f"https://newsapi.org/v2/everything?q={query}&language=pt&sortBy=publishedAt&pageSize=8&apiKey={NEWS_KEY}"
    try:
        r = requests.get(url, timeout=8)
        return r.json().get("articles", [])
    except:
        return []

# ── LAYOUT ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MestreDoDayTrade Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [data-testid="stAppViewContainer"] {
    background: #0a0e1a !important;
    color: #e2e8f0 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stHeader"] { display: none !important; }
.block-container { padding: 1.5rem 2rem !important; max-width: 1400px !important; }

/* HEADER */
.header-box {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 1.2rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 24px rgba(0,102,255,0.1);
}
.header-logo {
    display: flex; align-items: center; gap: 1rem;
}
.logo-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #0066ff, #00c6ff);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.6rem;
    box-shadow: 0 0 20px rgba(0,102,255,0.4);
}
.header-title { font-size: 1.5rem; font-weight: 700; color: #fff; line-height: 1; }
.header-sub { font-size: 0.8rem; color: #64748b; margin-top: 3px; }
.header-badge {
    background: rgba(0,102,255,0.15);
    border: 1px solid rgba(0,102,255,0.3);
    border-radius: 8px;
    padding: 0.4rem 0.9rem;
    font-size: 0.75rem;
    color: #60a5fa;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    background: #0f172a !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid #1e293b !important;
    margin-bottom: 1.5rem;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748b !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.2rem !important;
    font-size: 0.88rem !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #0066ff, #0052cc) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(0,102,255,0.35) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* CARDS DE ATIVOS */
.ativo-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    text-align: center;
    transition: all 0.2s ease;
    min-width: 130px;
    flex: 0 0 auto;
}
.ativo-card:hover { border-color: #0066ff; transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,102,255,0.15); }
.ativo-nome { font-size: 0.7rem; color: #64748b; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem; }
.ativo-preco { font-size: 1.05rem; font-weight: 700; color: #f1f5f9; font-family: 'JetBrains Mono', monospace; }
.ativo-var-up { font-size: 0.78rem; color: #22c55e; font-weight: 600; margin-top: 0.25rem; }
.ativo-var-dn { font-size: 0.78rem; color: #ef4444; font-weight: 600; margin-top: 0.25rem; }
.ativo-var-nt { font-size: 0.78rem; color: #94a3b8; font-weight: 600; margin-top: 0.25rem; }

/* SEÇÃO TÍTULO */
.sec-title {
    font-size: 1.15rem; font-weight: 700; color: #f1f5f9;
    margin: 1.5rem 0 0.8rem 0;
    display: flex; align-items: center; gap: 0.5rem;
}
.sec-divider { height: 1px; background: #1e293b; margin: 1rem 0; }

/* PAINEL ROLAGEM */
.scroll-wrapper {
    overflow-x: auto;
    padding-bottom: 0.5rem;
    scrollbar-width: thin;
    scrollbar-color: #1e293b transparent;
}
.scroll-wrapper::-webkit-scrollbar { height: 4px; }
.scroll-wrapper::-webkit-scrollbar-track { background: transparent; }
.scroll-wrapper::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
.scroll-track {
    display: flex;
    gap: 0.75rem;
    padding: 0.5rem 0;
    width: max-content;
}

/* GRUPO DE ATIVOS */
.grupo-label {
    font-size: 0.65rem; font-weight: 700; color: #475569;
    text-transform: uppercase; letter-spacing: 0.1em;
    padding: 0.2rem 0.6rem;
    background: #1e293b;
    border-radius: 4px;
    white-space: nowrap;
    align-self: center;
}

/* NOTÍCIAS */
.noticia-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    transition: all 0.2s;
}
.noticia-card:hover { border-color: #334155; }
.noticia-titulo { font-size: 0.9rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.4rem; line-height: 1.4; }
.noticia-meta { font-size: 0.72rem; color: #475569; }
.noticia-desc { font-size: 0.82rem; color: #94a3b8; margin-top: 0.4rem; line-height: 1.5; }
.noticia-link a { color: #60a5fa; font-size: 0.75rem; text-decoration: none; }

/* CALCULADORA */
.calc-result {
    background: linear-gradient(135deg, #0f2a1f, #0a1f14);
    border: 1px solid #166534;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-top: 1rem;
}
.calc-result-titulo { font-size: 0.78rem; color: #4ade80; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.8rem; }
.calc-linha { display: flex; justify-content: space-between; align-items: center; padding: 0.3rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
.calc-label { font-size: 0.82rem; color: #94a3b8; }
.calc-valor { font-size: 0.9rem; font-weight: 700; color: #f1f5f9; font-family: 'JetBrains Mono', monospace; }
.calc-alerta { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 0.6rem 0.9rem; margin-top: 0.75rem; font-size: 0.8rem; color: #fca5a5; }

/* CHAT */
.chat-msg-user {
    background: linear-gradient(135deg, #0066ff, #0052cc);
    border-radius: 16px 16px 4px 16px;
    padding: 0.8rem 1.1rem;
    margin: 0.5rem 0 0.5rem auto;
    max-width: 75%;
    font-size: 0.88rem;
    color: #fff;
    width: fit-content;
}
.chat-msg-bot {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px 16px 16px 4px;
    padding: 0.8rem 1.1rem;
    margin: 0.5rem auto 0.5rem 0;
    max-width: 85%;
    font-size: 0.88rem;
    color: #e2e8f0;
    line-height: 1.6;
    width: fit-content;
}
.chat-container { max-height: 420px; overflow-y: auto; padding: 0.5rem; scrollbar-width: thin; scrollbar-color: #1e293b transparent; }

/* BOTÕES */
.stButton > button {
    background: linear-gradient(135deg, #0066ff, #0052cc) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.2s !important;
    box-shadow: 0 2px 12px rgba(0,102,255,0.25) !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 4px 20px rgba(0,102,255,0.4) !important; }

/* INPUTS */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stTextArea > div > div > textarea {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #0066ff !important;
    box-shadow: 0 0 0 2px rgba(0,102,255,0.2) !important;
}

/* SLIDER */
.stSlider [data-baseweb="slider"] { margin: 0.5rem 0; }

/* UPLOADER */
.stFileUploader { background: #0f172a !important; border: 1px dashed #1e293b !important; border-radius: 12px !important; }

/* MÉTRICAS */
[data-testid="metric-container"] {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 0.8rem 1rem;
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.75rem !important; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-family: 'JetBrains Mono', monospace !important; }

/* SELECT */
[data-baseweb="select"] { background: #0f172a !important; }
[data-baseweb="menu"] { background: #1e293b !important; }

/* SCROLLBAR GLOBAL */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ── SESSÃO ────────────────────────────────────────────────────────────────────
if "historico" not in st.session_state:
    st.session_state.historico = []
if "cotacoes" not in st.session_state:
    st.session_state.cotacoes = {}

# ── HEADER ────────────────────────────────────────────────────────────────────
agora = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"""
<div class="header-box">
    <div class="header-logo">
        <div class="logo-icon">📈</div>
        <div>
            <div class="header-title">MestreDoDayTrade Pro</div>
            <div class="header-sub">Assistente Inteligente para WIN &amp; WDO · B3</div>
        </div>
    </div>
    <div style="display:flex;gap:0.75rem;align-items:center;">
        <div class="header-badge">🤖 Groq AI</div>
        <div class="header-badge">🕐 {agora}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🌍  Mercados & Notícias", "🛡️  Gerenciamento de Risco", "🤖  Chat com o Mestre"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MERCADOS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("⟳  Atualizar Mercados"):
            st.cache_data.clear()
            st.rerun()
    with col_info:
        st.markdown("<div style='color:#475569;font-size:0.78rem;padding-top:0.6rem'>Atualização automática a cada 60s · Dados: Yahoo Finance</div>", unsafe_allow_html=True)

    cotacoes = buscar_cotacoes()

    def card_html(nome, dados):
        preco = dados.get("preco", 0)
        var = dados.get("var", 0)
        # Formata preço
        if preco > 1000:
            preco_str = f"{preco:,.0f}".replace(",", ".")
        elif preco > 10:
            preco_str = f"{preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            preco_str = f"{preco:.4f}"

        if var > 0:
            var_html = f'<div class="ativo-var-up">▲ {var:.2f}%</div>'
        elif var < 0:
            var_html = f'<div class="ativo-var-dn">▼ {abs(var):.2f}%</div>'
        else:
            var_html = f'<div class="ativo-var-nt">— 0.00%</div>'

        return f"""<div class="ativo-card">
            <div class="ativo-nome">{nome}</div>
            <div class="ativo-preco">{preco_str}</div>
            {var_html}
        </div>"""

    grupos = [
        ("🇧🇷 Brasil", ["IBOVESPA", "WIN (Mini-Índ.)", "WDO (Mini-Dól.)"]),
        ("🌎 Bolsas", ["S&P 500", "Nasdaq", "DAX", "FTSE 100", "Nikkei", "Shanghai"]),
        ("🛢️ Commodities", ["Petróleo WTI", "Ouro"]),
        ("💱 Câmbio", ["Dólar/BRL", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CNY"]),
        ("₿ Cripto", ["Bitcoin", "Ethereum", "Solana", "BNB"]),
    ]

    for grupo_nome, ativos_grupo in grupos:
        st.markdown(f'<div class="sec-title">{grupo_nome}</div>', unsafe_allow_html=True)
        cards_html = "".join([
            card_html(a, cotacoes.get(a, {"preco": 0, "var": 0}))
            for a in ativos_grupo
        ])
        st.markdown(f'<div class="scroll-wrapper"><div class="scroll-track">{cards_html}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)

    # NOTÍCIAS
    st.markdown('<div class="sec-title">📰 Notícias do Mercado</div>', unsafe_allow_html=True)

    col_busca, col_btn2 = st.columns([4, 1])
    with col_busca:
        query_noticias = st.text_input("", value="Ibovespa B3 dólar mercado futuro", label_visibility="collapsed")
    with col_btn2:
        buscar_btn = st.button("🔍  Buscar")

    filtro = st.radio("Filtros:", ["Todos", "Alta", "Baixa", "Neutro"], horizontal=True, label_visibility="collapsed")

    noticias = buscar_noticias(query_noticias)

    if not noticias:
        st.markdown('<div style="color:#475569;font-size:0.85rem;padding:1rem 0">Nenhuma notícia encontrada. Tente outro termo.</div>', unsafe_allow_html=True)
    else:
        for n in noticias[:6]:
            titulo = n.get("title", "")
            desc = n.get("description", "")
            url = n.get("url", "#")
            fonte = n.get("source", {}).get("name", "")
            pub = n.get("publishedAt", "")[:10]
            st.markdown(f"""
            <div class="noticia-card">
                <div class="noticia-titulo">{titulo}</div>
                <div class="noticia-desc">{desc[:180] + '...' if desc and len(desc) > 180 else desc or ''}</div>
                <div style="display:flex;justify-content:space-between;margin-top:0.5rem;align-items:center;">
                    <div class="noticia-meta">{fonte} · {pub}</div>
                    <div class="noticia-link"><a href="{url}" target="_blank">Ler completo →</a></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — GERENCIAMENTO DE RISCO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:

    st.markdown('<div class="sec-title">🛡️ Calculadora de Risco</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        ativo_sel = st.selectbox("Ativo", ["WIN (Mini-Índice)", "WDO (Mini-Dólar)"])
        capital = st.number_input("Capital disponível (R$)", min_value=500.0, max_value=500000.0, value=5000.0, step=500.0)
        risco_pct = st.slider("% do capital para arriscar por operação", 0.5, 5.0, 1.0, 0.5)
    with col2:
        stop = st.number_input("Stop (pontos)", min_value=1, max_value=500, value=50, step=5)
        meta = st.number_input("Meta (pontos)", min_value=1, max_value=1000, value=100, step=5)
        n_contratos = st.number_input("Nº de contratos", min_value=1, max_value=20, value=1, step=1)

    if st.button("📊  Calcular Risco"):
        # Valores por ponto
        val_ponto = 0.20 if "WDO" in ativo_sel else 0.20  # WIN e WDO: R$0.20/ponto por contrato
        multiplicador = 10 if "WDO" in ativo_sel else 20   # WIN: 20x, WDO: 10x

        perda_pts = stop * n_contratos * multiplicador
        ganho_pts = meta * n_contratos * multiplicador
        rr = meta / stop if stop > 0 else 0
        risco_real = (risco_pct / 100) * capital
        stops_ate_zerar = int(capital / perda_pts) if perda_pts > 0 else 0

        # Cor do RR
        rr_cor = "#22c55e" if rr >= 2 else "#f59e0b" if rr >= 1.5 else "#ef4444"
        risco_cor = "#22c55e" if perda_pts <= risco_real else "#ef4444"

        st.markdown(f"""
        <div class="calc-result">
            <div class="calc-result-titulo">📊 Resultado da Análise</div>
            <div class="calc-linha"><span class="calc-label">Ativo</span><span class="calc-valor">{ativo_sel}</span></div>
            <div class="calc-linha"><span class="calc-label">Perda máxima</span><span class="calc-valor" style="color:{risco_cor}">R$ {perda_pts:,.2f}</span></div>
            <div class="calc-linha"><span class="calc-label">Ganho potencial</span><span class="calc-valor" style="color:#22c55e">R$ {ganho_pts:,.2f}</span></div>
            <div class="calc-linha"><span class="calc-label">Risco/Retorno</span><span class="calc-valor" style="color:{rr_cor}">1:{rr:.1f}</span></div>
            <div class="calc-linha"><span class="calc-label">% do capital arriscado</span><span class="calc-valor">{(perda_pts/capital*100):.1f}%</span></div>
            <div class="calc-linha"><span class="calc-label">Stops até zerar a conta</span><span class="calc-valor">{stops_ate_zerar} stops</span></div>
        </div>
        """, unsafe_allow_html=True)

        if perda_pts > risco_real:
            st.markdown(f'<div class="calc-alerta">⚠️ Você está arriscando R$ {perda_pts:,.2f} mas seu limite é R$ {risco_real:,.2f} ({risco_pct}% do capital). Reduza contratos ou aumente o capital.</div>', unsafe_allow_html=True)
        if rr < 1.5:
            st.markdown('<div class="calc-alerta">⚠️ RR abaixo de 1:1.5 — setup desfavorável. Considere ampliar a meta ou reduzir o stop.</div>', unsafe_allow_html=True)
        if stops_ate_zerar <= 5:
            st.markdown(f'<div class="calc-alerta">🚨 Com apenas {stops_ate_zerar} stops você zera a conta. Operação de alto risco.</div>', unsafe_allow_html=True)

        # Análise via IA
        with st.spinner("Analisando setup com IA..."):
            analise = ia(
                f"Analise este setup: {ativo_sel}, capital R${capital}, stop {stop}pts, meta {meta}pts, {n_contratos} contrato(s), RR 1:{rr:.1f}, perda máx R${perda_pts:.2f}. Dê uma opinião direta em 3-4 linhas.",
                system=SYSTEM_PROMPT
            )
        st.markdown(f'<div class="chat-msg-bot" style="max-width:100%;margin-top:1rem">🤖 {analise}</div>', unsafe_allow_html=True)

    # INFO ROLAGEM
    st.markdown('<div class="sec-divider"></div><div class="sec-title">📅 Aviso de Rolagem</div>', unsafe_allow_html=True)
    mes = datetime.now().month
    meses_venc = {2: "FEV", 4: "ABR", 6: "JUN", 8: "AGO", 10: "OUT", 12: "DEZ"}
    if mes in meses_venc:
        st.markdown(f'<div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:10px;padding:0.9rem 1.2rem;color:#fbbf24;font-size:0.85rem">⚠️ <b>Mês de rolagem!</b> Contratos vencem em {meses_venc[mes]}. Verifique o contrato mais líquido antes de operar.</div>', unsafe_allow_html=True)
    else:
        prox = [m for m in meses_venc if m > mes]
        prox_mes = meses_venc[prox[0]] if prox else "FEV"
        st.markdown(f'<div style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.2);border-radius:10px;padding:0.9rem 1.2rem;color:#4ade80;font-size:0.85rem">✅ Sem rolagem este mês. Próximo vencimento: <b>{prox_mes}</b></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab3:

    col_chat, col_lateral = st.columns([3, 1])

    with col_lateral:
        st.markdown('<div style="font-size:0.78rem;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem">Análise de Gráfico</div>', unsafe_allow_html=True)
        img_upload = st.file_uploader("Envie print do ProfitPro", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        if img_upload:
            st.image(img_upload, use_container_width=True)

        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.78rem;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem">Atalhos rápidos</div>', unsafe_allow_html=True)

        atalhos = ["Como usar VWAP no Profit?", "O que é IFR e como interpretar?", "Diferença entre candle de reversão e continuação", "Como definir suporte e resistência no WIN?", "O que olhar antes de abrir operação?"]
        for a in atalhos:
            if st.button(a, key=f"atalho_{a}"):
                st.session_state.historico.append({"role": "user", "content": a})
                with st.spinner(""):
                    resp = ia(a, system=SYSTEM_PROMPT, historico=st.session_state.historico)
                st.session_state.historico.append({"role": "assistant", "content": resp})
                st.rerun()

    with col_chat:
        # Histórico
        chat_html = '<div class="chat-container">'
        if not st.session_state.historico:
            chat_html += '<div style="color:#475569;font-size:0.85rem;padding:1rem 0;text-align:center">👋 Olá! Pode perguntar sobre WIN, WDO, análise técnica, indicadores ou mandar um print do gráfico.</div>'
        else:
            for msg in st.session_state.historico[-20:]:
                if msg["role"] == "user":
                    chat_html += f'<div class="chat-msg-user">{msg["content"]}</div>'
                else:
                    chat_html += f'<div class="chat-msg-bot">{msg["content"]}</div>'
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)

        # Input
        col_inp, col_send = st.columns([5, 1])
        with col_inp:
            pergunta = st.text_input("", placeholder="Pergunte sobre WIN, WDO, indicadores...", key="pergunta_input", label_visibility="collapsed")
        with col_send:
            enviar = st.button("Enviar")

        if (enviar or pergunta) and pergunta.strip():
            imagem_b64 = None
            if img_upload:
                imagem_b64 = base64.b64encode(img_upload.read()).decode("utf-8")

            st.session_state.historico.append({"role": "user", "content": pergunta.strip()})
            with st.spinner("Analisando..."):
                resp = ia(pergunta.strip(), system=SYSTEM_PROMPT, historico=st.session_state.historico, imagem_b64=imagem_b64)
            st.session_state.historico.append({"role": "assistant", "content": resp})
            st.rerun()

        col_l, col_r = st.columns(2)
        with col_l:
            if st.button("🗑️  Limpar conversa"):
                st.session_state.historico = []
                st.rerun()
        with col_r:
            if st.session_state.historico:
                st.markdown(f'<div style="font-size:0.72rem;color:#475569;padding-top:0.6rem;text-align:right">{len(st.session_state.historico)//2} mensagens</div>', unsafe_allow_html=True)
