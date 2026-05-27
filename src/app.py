import streamlit as st
import requests
import base64
import anthropic
from datetime import datetime

# ── CONFIG ───────────────────────────────────────────────────────────────────
CLAUDE_KEY = "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"
NEWS_KEY   = "5124f5a861fa416db858736df592d6a1"

def claude(prompt, system="", historico=None, imagem_b64=None):
    client = anthropic.Anthropic(api_key=CLAUDE_KEY)
    msgs = []
    if historico:
        for h in historico:
            msgs.append({"role": h["role"], "content": h["content"]})
    if imagem_b64:
        msgs.append({"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": imagem_b64}},
            {"type": "text", "text": prompt}
        ]})
    else:
        msgs.append({"role": "user", "content": prompt})
    kwargs = {"model": "claude-sonnet-4-5", "max_tokens": 2048, "messages": msgs}
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return resp.content[0].text

st.set_page_config(page_title="MestreDoDayTrade Pro", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# ── CSS PROFISSIONAL ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
.stApp { background: #080B10 !important; }
p, li, span, div, label { color: #F0F4F8 !important; }
h1 { color: #FFFFFF !important; font-weight: 700 !important; font-size: 26px !important; }
h2 { color: #FFFFFF !important; font-weight: 600 !important; font-size: 20px !important; }
h3 { color: #E2E8F0 !important; font-weight: 600 !important; font-size: 16px !important; }
strong, b { color: #FFFFFF !important; font-weight: 700 !important; }
.stTabs [data-baseweb="tab-list"] { background: #0F1520; border-radius: 10px; padding: 5px; gap: 4px; border: 1px solid #1E2D40; }
.stTabs [data-baseweb="tab"] { background: transparent; color: #94A3B8 !important; border-radius: 8px; font-weight: 600; font-size: 13px; padding: 8px 18px; border: none; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #1D4ED8, #2563EB) !important; color: #FFFFFF !important; }
.card { background: #0F1520; border: 1px solid #1E2D40; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
.card p, .card li, .card span { color: #E2E8F0 !important; }
.market-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 24px; }
.market-card { background: #0F1520; border: 1px solid #1E2D40; border-radius: 10px; padding: 14px 18px; flex: 1; min-width: 140px; text-align: center; }
.market-name { color: #94A3B8 !important; font-size: 11px; font-weight: 600; letter-spacing: 1px; margin-bottom: 6px; }
.market-value { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.market-change { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; display: inline-block; }
.news-card { background: #0F1520; border-left: 3px solid #2563EB; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.news-title { color: #F0F4F8 !important; font-weight: 600; font-size: 14px; line-height: 1.5; margin-bottom: 6px; }
.news-meta { color: #64748B !important; font-size: 11px; margin-bottom: 8px; }
.news-desc { color: #94A3B8 !important; font-size: 13px; line-height: 1.6; }
.stChatMessage { background: #0F1520 !important; border: 1px solid #1E2D40 !important; border-radius: 12px !important; padding: 16px !important; margin-bottom: 12px !important; }
.stChatMessage p { color: #F0F4F8 !important; font-size: 15px !important; line-height: 1.7 !important; font-weight: 400 !important; }
.stChatMessage li { color: #E2E8F0 !important; font-size: 14px !important; line-height: 1.8 !important; }
.stChatMessage strong, .stChatMessage b { color: #60A5FA !important; font-weight: 700 !important; }
.stChatMessage h1, .stChatMessage h2, .stChatMessage h3 { color: #60A5FA !important; font-weight: 700 !important; }
.stChatMessage code { background: #1E2D40 !important; color: #10B981 !important; padding: 2px 6px; border-radius: 4px; font-size: 13px !important; }
.stChatInput textarea { background: #0F1520 !important; border: 1px solid #2563EB !important; border-radius: 10px !important; color: #F0F4F8 !important; font-size: 15px !important; }
.stButton button { background: linear-gradient(135deg, #1D4ED8, #2563EB) !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; }
.risco-card { background: #0F1520; border: 1px solid #1E2D40; border-radius: 12px; padding: 20px; margin-bottom: 12px; }
.risco-label { color: #64748B !important; font-size: 11px; font-weight: 700; letter-spacing: 1px; margin-bottom: 8px; }
.risco-value { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.risco-sub { color: #94A3B8 !important; font-size: 12px; }
.stNumberInput input, .stTextInput input { background: #0F1520 !important; border: 1px solid #1E2D40 !important; color: #F0F4F8 !important; border-radius: 8px !important; }
[data-testid="stNumberInput"] label, [data-testid="stTextInput"] label, [data-testid="stSelectbox"] label { color: #94A3B8 !important; font-size: 13px !important; }
hr { border-color: #1E2D40 !important; }
.roll-notice { background: rgba(37,99,235,0.1); border: 1px solid #2563EB; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; color: #93C5FD !important; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:16px;padding:20px 0 8px 0;border-bottom:1px solid #1E2D40;margin-bottom:24px">
    <div style="background:linear-gradient(135deg,#1D4ED8,#2563EB);border-radius:12px;padding:10px 14px;font-size:24px">📈</div>
    <div>
        <div style="color:#FFFFFF;font-size:22px;font-weight:700;line-height:1.2">MestreDoDayTrade Pro</div>
        <div style="color:#64748B;font-size:13px">Assistente Inteligente para WIN & WDO · B3</div>
    </div>
    <div style="margin-left:auto;text-align:right">
        <div style="color:#64748B;font-size:11px">POWERED BY</div>
        <div style="color:#60A5FA;font-size:13px;font-weight:600">Claude AI</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── AVISO ROLAGEM ─────────────────────────────────────────────────────────────
hoje = datetime.now()
if hoje.month in [2, 4, 6, 8, 10, 12]:
    st.markdown(f"""
    <div class="roll-notice">
        🔄 <b>Atenção Rolagem:</b> Estamos em {hoje.strftime('%B/%Y')} — verifique a liquidez do contrato ativo.
        WIN vence na quarta mais próxima do dia 15. WDO vence mensalmente no 1º dia útil.
    </div>
    """, unsafe_allow_html=True)

# ── ABAS ──────────────────────────────────────────────────────────────────────
aba1, aba2, aba3 = st.tabs(["🌍 Mercados & Notícias", "🛡️ Gerenciamento de Risco", "🤖 Chat com o Mestre"])

# ════════════════════════════════════════════════════════════════════════════
# ABA 1 — MERCADOS GLOBAIS + NOTÍCIAS
# ════════════════════════════════════════════════════════════════════════════
with aba1:
    st.markdown("### 🌍 Mercados Globais em Tempo Real")
    st.markdown('<div style="color:#64748B;font-size:13px;margin-bottom:16px">Principais índices e ativos que impactam diretamente o WIN e o WDO</div>', unsafe_allow_html=True)

    tickers = {
        "S&P 500": "^GSPC", "Nasdaq": "^IXIC", "DAX": "^GDAXI",
        "Nikkei": "^N225", "Petróleo": "CL=F", "Ouro": "GC=F",
        "Dólar/BRL": "BRL=X", "Bitcoin": "BTC-USD"
    }

    if st.button("🔄 Atualizar Mercados", type="primary"):
        st.session_state.pop("mercados_data", None)

    if "mercados_data" not in st.session_state:
        mercados_html = '<div class="market-grid">'
        for nome, ticker in tickers.items():
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d"
                r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                data = r.json()
                closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                closes = [c for c in closes if c is not None]
                if len(closes) >= 2:
                    atual, ant = closes[-1], closes[-2]
                    var = ((atual - ant) / ant) * 100
                    cor_val = "#10B981" if var >= 0 else "#EF4444"
                    cor_bg  = "rgba(16,185,129,0.15)" if var >= 0 else "rgba(239,68,68,0.15)"
                    cor_txt = "#10B981" if var >= 0 else "#EF4444"
                    sinal   = "▲" if var >= 0 else "▼"
                    fmt = f"R$ {atual:.4f}" if ticker == "BRL=X" else (f"{atual:,.0f}" if atual > 10000 else f"{atual:,.2f}")
                    mercados_html += f"""
                    <div class="market-card">
                        <div class="market-name">{nome}</div>
                        <div class="market-value" style="color:{cor_val}">{fmt}</div>
                        <span class="market-change" style="background:{cor_bg};color:{cor_txt}">{sinal} {abs(var):.2f}%</span>
                    </div>"""
                else:
                    mercados_html += f'<div class="market-card"><div class="market-name">{nome}</div><div style="color:#64748B;font-size:13px">—</div></div>'
            except:
                mercados_html += f'<div class="market-card"><div class="market-name">{nome}</div><div style="color:#64748B;font-size:13px">—</div></div>'
        mercados_html += "</div>"
        st.session_state["mercados_data"] = mercados_html

    st.markdown(st.session_state.get("mercados_data", ""), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📰 Notícias do Mercado")

    col_q, col_btn = st.columns([5, 1])
    with col_q:
        query = st.text_input("", value="Ibovespa B3 dólar mercado futuro", placeholder="Buscar notícias...", label_visibility="collapsed")
    with col_btn:
        buscar = st.button("Buscar", type="primary", use_container_width=True)

    temas = st.multiselect("Filtros:", ["Ibovespa", "Mini-Índice", "Dólar", "Fed EUA", "COPOM Juros", "Petróleo", "China", "PIB Brasil"], default=["Ibovespa", "Dólar"])

    if buscar or "noticias_cache" not in st.session_state:
        q = query + " " + " ".join(temas)
        with st.spinner("Buscando notícias..."):
            try:
                url = f"https://newsapi.org/v2/everything?q={q}&language=pt&sortBy=publishedAt&pageSize=12&apiKey={NEWS_KEY}"
                r = requests.get(url, timeout=10)
                arts = r.json().get("articles", [])
                st.session_state["noticias_cache"] = arts
            except:
                arts = []
    else:
        arts = st.session_state.get("noticias_cache", [])

    if arts:
        for a in arts[:8]:
            titulo = a.get("title", "") or ""
            fonte  = a.get("source", {}).get("name", "")
            data_p = (a.get("publishedAt", "") or "")[:10]
            link   = a.get("url", "#")
            desc   = (a.get("description", "") or "")[:180]
            if titulo and "[Removed]" not in titulo:
                st.markdown(f"""
                <div class="news-card">
                    <div class="news-title">{titulo}</div>
                    <div class="news-meta">📡 {fonte} &nbsp;·&nbsp; 📅 {data_p}</div>
                    <div class="news-desc">{desc}...</div>
                    <a href="{link}" target="_blank" style="color:#3B82F6;font-size:12px;font-weight:600;text-decoration:none">Ler matéria completa →</a>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🤖 Analisar impacto no WIN e WDO", type="primary"):
            with st.spinner("Claude analisando..."):
                headlines = "\n".join([a.get("title","") for a in arts[:6] if a.get("title") and "[Removed]" not in a.get("title","")])
                system = "Você é um analista sênior de mercado futuro brasileiro especializado em Mini-Índice (WIN) e Mini-Dólar (WDO) na B3."
                prompt = f"""Manchetes de hoje:\n{headlines}\n\nAnalise:\n1. **Impacto no WIN:** tendência e por quê\n2. **Impacto no WDO:** tendência e por quê\n3. **Riscos do dia** para o trader\n4. **Horários críticos** de volatilidade\n5. **Correlações importantes**\n\nSeja direto e use linguagem de trader profissional."""
                resp = claude(prompt, system=system)
                st.markdown(f'<div class="card">{resp}</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# ABA 2 — GERENCIAMENTO DE RISCO
# ════════════════════════════════════════════════════════════════════════════
with aba2:
    st.markdown("### 🛡️ Calculadora de Gerenciamento de Risco")
    st.markdown('<div style="color:#94A3B8;font-size:13px;margin-bottom:20px">Preencha os dados para calcular o risco real da operação</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Parâmetros")
        ativo     = st.selectbox("Ativo:", ["Mini-Índice (WIN)", "Mini-Dólar (WDO)"])
        capital   = st.number_input("Capital (R$):", value=10000.0, step=1000.0, min_value=1000.0)
        contratos = st.number_input("Contratos:", value=1, min_value=1, max_value=20, step=1)
        stop_pts  = st.number_input("Stop Loss (pontos):", value=15, min_value=1, step=1)
        meta_pts  = st.number_input("Take Profit (pontos):", value=20, min_value=1, step=1)

        val_ponto  = 0.20 if "WIN" in ativo else 10.0
        nome_ativo = "WIN" if "WIN" in ativo else "WDO"
        stop_rs    = stop_pts * val_ponto * contratos
        meta_rs    = meta_pts * val_ponto * contratos
        rr         = meta_rs / stop_rs if stop_rs > 0 else 0
        risco_pct  = (stop_rs / capital) * 100 if capital > 0 else 0

    with col2:
        st.markdown("#### Resultado")
        cor_rr    = "#10B981" if rr >= 1.5 else "#F59E0B" if rr >= 1.0 else "#EF4444"
        cor_risco = "#10B981" if risco_pct <= 1 else "#F59E0B" if risco_pct <= 2 else "#EF4444"
        st_rr     = "✅ Ótimo" if rr >= 2.0 else "⚠️ Aceitável" if rr >= 1.5 else "⚠️ Marginal" if rr >= 1.0 else "❌ Não compensa"
        st_risco  = "✅ Conservador" if risco_pct <= 1 else "⚠️ Moderado" if risco_pct <= 2 else "❌ Alto"
        ops_perder = int(capital / stop_rs) if stop_rs > 0 else 0

        st.markdown(f"""
        <div class="risco-card">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                <div>
                    <div class="risco-label">STOP LOSS</div>
                    <div class="risco-value" style="color:#EF4444">-R$ {stop_rs:.2f}</div>
                    <div class="risco-sub">{stop_pts} pts × R${val_ponto} × {contratos}x</div>
                </div>
                <div>
                    <div class="risco-label">TAKE PROFIT</div>
                    <div class="risco-value" style="color:#10B981">+R$ {meta_rs:.2f}</div>
                    <div class="risco-sub">{meta_pts} pts × R${val_ponto} × {contratos}x</div>
                </div>
                <div>
                    <div class="risco-label">RISCO/RETORNO</div>
                    <div class="risco-value" style="color:{cor_rr}">{rr:.2f}x</div>
                    <div class="risco-sub">{st_rr}</div>
                </div>
                <div>
                    <div class="risco-label">RISCO DO CAPITAL</div>
                    <div class="risco-value" style="color:{cor_risco}">{risco_pct:.2f}%</div>
                    <div class="risco-sub">{st_risco}</div>
                </div>
            </div>
            <hr style="margin:16px 0;border-color:#1E2D40">
            <div style="color:#94A3B8;font-size:13px">
                Você aguenta <b style="color:#60A5FA">{ops_perder} stops consecutivos</b> antes de zerar o capital.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🤖 Mestre, avalia meu setup", type="primary"):
        with st.spinner("Claude avaliando..."):
            system = f"Você é um gerente de risco sênior de mesa proprietária especializado em {nome_ativo} na B3."
            prompt = f"""Setup do trader:
- Capital: R$ {capital:.2f} | Contratos: {contratos}
- Stop: {stop_pts} pts (R$ {stop_rs:.2f}) | Meta: {meta_pts} pts (R$ {meta_rs:.2f})
- RR: {rr:.2f}x | Risco do capital: {risco_pct:.2f}%

Avalie diretamente:
1. Este setup é viável?
2. O que ajustar?
3. Win rate mínimo para ser lucrativo?
4. Recomendação final em 1 linha"""
            resp = claude(prompt, system=system)
            st.markdown(f'<div class="card">{resp}</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# ABA 3 — CHAT COM O MESTRE
# ════════════════════════════════════════════════════════════════════════════
with aba3:
    st.markdown("### 🤖 Chat com o MestreDoDayTrade")
    st.markdown('<div style="color:#94A3B8;font-size:13px;margin-bottom:20px">Pergunte sobre padrões gráficos, análise técnica, ferramentas do Profit e estratégias</div>', unsafe_allow_html=True)

    SYSTEM_MESTRE = """Você é o MestreDoDayTrade, especialista sênior em:
- Mercado futuro brasileiro: Mini-Índice (WIN) e Mini-Dólar (WDO) na B3
- Plataforma ProfitPro: Book, Tape Reading, indicadores, configurações
- Análise técnica: Price Action, VWAP, Médias Móveis, Fibonacci, Bollinger
- Padrões gráficos: OCO, Topo/Fundo Duplo, Triângulos, Bandeiras, Cunhas
- Candles japoneses: Doji, Martelo, Estrela Cadente, Engolfo, Harami, Marubozu
- Ondas de Elliott, Volume Profile, Teoria de Dow
- Gerenciamento de risco e psicologia do trader

REGRA IMPORTANTE SOBRE PADRÕES GRÁFICOS:
Sempre que explicar um padrão, inclua representação visual em ASCII mostrando como ele aparece no gráfico. Exemplo para Topo Duplo:
```
    /\    /\
   /  \  /  \  ← Dois topos na mesma região
  /    \/    \
              \  ← Rompimento da neckline = entrada
```

Para cada padrão explique: como identificar, o que significa, como operar (entrada, stop, alvo) e exemplo no WIN/WDO.
NUNCA dê calls em tempo real. Use linguagem de trader profissional."""

    if "chat_mestre" not in st.session_state:
        st.session_state.chat_mestre = []
        st.session_state.chat_mestre_hist = []

    if not st.session_state.chat_mestre:
        boas_vindas = """👋 **Olá! Sou o MestreDoDayTrade, powered by Claude AI.**

Estou aqui para te ajudar a evoluir no mercado futuro. Posso te explicar:

📊 **Padrões Gráficos** — OCO, Topo Duplo, Triângulos, Candles (com visual ASCII)
📐 **Indicadores** — VWAP, Fibonacci, Médias Móveis, Bollinger
🖥️ **Plataforma Profit** — Book, Tape Reading, configurações
🧠 **Estratégia e Psicologia** — Disciplina, gerenciamento, setups

**O que você quer aprender hoje?**"""
        st.session_state.chat_mestre.append({"role": "assistant", "content": boas_vindas})

    for msg in st.session_state.chat_mestre:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    img_chat = st.file_uploader("📷 Anexar print de gráfico (opcional):", type=["png","jpg","jpeg"], key="img_chat")
    if img_chat:
        st.image(img_chat, width=350, caption="Gráfico anexado")

    if user_input := st.chat_input("Pergunte sobre WIN, WDO, padrões gráficos, Profit..."):
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.chat_mestre.append({"role": "user", "content": user_input})

        hist = [m for m in st.session_state.chat_mestre[:-1] if m["role"] in ["user", "assistant"]]

        with st.spinner("Claude analisando..."):
            b64 = base64.b64encode(img_chat.getvalue()).decode() if img_chat else None
            resp = claude(user_input, system=SYSTEM_MESTRE, historico=hist, imagem_b64=b64)

        with st.chat_message("assistant"):
            st.write(resp)
        st.session_state.chat_mestre.append({"role": "assistant", "content": resp})

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:24px 0 8px;border-top:1px solid #1E2D40;margin-top:32px">
    <span style="color:#1E2D40;font-size:12px">MestreDoDayTrade Pro · Projeto DIO × Bradesco · Powered by Claude AI</span>
</div>
""", unsafe_allow_html=True)
