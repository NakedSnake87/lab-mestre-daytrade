import streamlit as st
import requests
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz

# ── CONFIG ────────────────────────────────────────────────────────────────────
GROQ_KEY = st.secrets["GROQ_KEY"]
NEWS_KEY  = st.secrets["NEWS_KEY"]
BR_TZ     = pytz.timezone("America/Sao_Paulo")

def agora_br():
    return datetime.now(BR_TZ).strftime("%d/%m/%Y %H:%M")

# ── IA ────────────────────────────────────────────────────────────────────────
def ia(prompt, system="", historico=None, imagem_b64=None):
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    if historico:
        for h in historico[-10:]:
            msgs.append({"role": h["role"], "content": h["content"]})
    if imagem_b64:
        msgs.append({"role": "user", "content": [
            {"type": "text",      "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagem_b64}"}}
        ]})
    else:
        msgs.append({"role": "user", "content": prompt})

    model = "meta-llama/llama-4-scout-17b-16e-instruct" if imagem_b64 else "llama-3.3-70b-versatile"
    resp  = client.chat.completions.create(model=model, messages=msgs, max_tokens=1500, temperature=0.15)
    return resp.choices[0].message.content

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é o MestreDoDayTrade Pro — especialista sênior em contratos futuros WIN (Mini-Índice) e WDO (Mini-Dólar) na B3.

REGRAS OBRIGATÓRIAS:
1. Responda APENAS o que foi perguntado. Direto ao ponto, sem introdução.
2. NUNCA mencione Topo Duplo, OCO ou padrões gráficos a menos que o usuário pergunte diretamente.
3. NUNCA faça desenhos ASCII. Proibido. Use apenas texto descritivo objetivo.
4. Máximo 4-6 linhas em perguntas simples. Nunca enrole.
5. Não emita calls de compra ou venda — apenas educação e gerenciamento de risco.
6. Linguagem de trader veterano — direto, sem academicismo.
7. Sobre tendência hoje: use os dados fornecidos no contexto. Se não tiver dados suficientes, oriente o trader sobre o que observar no gráfico.

AO ANALISAR GRÁFICOS (imagem enviada):
- Descreva a TENDÊNCIA DOMINANTE (alta, baixa, lateral) com base nas médias visíveis
- Analise o COMPORTAMENTO DAS MÉDIAS: direção, cruzamentos recentes, afastamento entre elas
- Comente o VOLUME: está crescendo, secando, divergindo com o preço?
- Identifique SUPORTES e RESISTÊNCIAS claros visíveis no gráfico
- Se houver indicadores visíveis (IFR, MACD, Bandas, VWAP), comente o que mostram
- Se houver padrões CLARAMENTE visíveis, mencione — mas não invente
- Finalize com o CONTEXTO GERAL: gráfico favorece continuidade ou alerta para reversão?
- Seja específico com os valores/preços que enxerga"""

# ── MULTIPLICADORES B3 CORRETOS ────────────────────────────────────────────────
# WIN: tick mínimo = 5 pontos = R$ 1,00 → logo R$ 0,20 por ponto por contrato
# WDO: tick mínimo = 0,5 ponto = R$ 5,00 → logo R$ 10,00 por ponto por contrato
MULT = {"WIN": 0.20, "WDO": 10.0}

# ── COTAÇÕES — múltiplas fontes com fallback ──────────────────────────────────
ATIVOS_YAHOO = {
    "IBOVESPA":        "^BVSP",
    "WIN (Mini-Índ.)": "WINM25.SA",
    "WDO (Mini-Dól.)": "WDOM25.SA",
    "S&P 500":         "^GSPC",
    "Nasdaq":          "^IXIC",
    "DAX":             "^GDAXI",
    "FTSE 100":        "^FTSE",
    "Nikkei":          "^N225",
    "Shanghai":        "000001.SS",
    "Petróleo WTI":    "CL=F",
    "Ouro":            "GC=F",
    "Dólar/BRL":       "BRL=X",
    "EUR/USD":         "EURUSD=X",
    "GBP/USD":         "GBPUSD=X",
    "USD/JPY":         "JPY=X",
    "AUD/USD":         "AUDUSD=X",
    "USD/CNY":         "CNY=X",
    "Bitcoin":         "BTC-USD",
    "Ethereum":        "ETH-USD",
    "Solana":          "SOL-USD",
    "BNB":             "BNB-USD",
}

# Mapeamento para Coinbase (cripto) e Frankfurter (forex)
CRIPTO_IDS = {
    "Bitcoin":  "bitcoin",
    "Ethereum": "ethereum",
    "Solana":   "solana",
    "BNB":      "binancecoin",
}

@st.cache_data(ttl=60)
def buscar_cotacoes():
    resultado = {}
    nome_por_simbolo = {v: k for k, v in ATIVOS_YAHOO.items()}

    # ── Fonte 1: Yahoo Finance com session + crumb ────────────────────────────
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://finance.yahoo.com",
            "Referer": "https://finance.yahoo.com/",
        })
        session.get("https://finance.yahoo.com", timeout=5)
        crumb = ""
        rc = session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=5)
        if rc.status_code == 200:
            crumb = rc.text.strip()

        tickers_str = "%2C".join(ATIVOS_YAHOO.values())
        url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={tickers_str}"
        if crumb:
            url += f"&crumb={crumb}"
        r = session.get(url, timeout=12)
        if r.status_code == 200:
            for q in r.json().get("quoteResponse", {}).get("result", []):
                sym   = q.get("symbol", "")
                nome  = nome_por_simbolo.get(sym, sym)
                preco = q.get("regularMarketPrice") or q.get("ask") or 0
                var   = q.get("regularMarketChangePercent", 0)
                if preco:
                    resultado[nome] = {"preco": preco, "var": var}
    except:
        pass

    # ── Fonte 2: CoinGecko (cripto) — fallback se Yahoo falhou ───────────────
    cripto_faltando = [n for n in CRIPTO_IDS if n not in resultado]
    if cripto_faltando:
        try:
            ids = ",".join(CRIPTO_IDS[n] for n in cripto_faltando)
            cg = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true",
                timeout=8, headers={"User-Agent": "Mozilla/5.0"}
            )
            if cg.status_code == 200:
                data = cg.json()
                for nome, cid in CRIPTO_IDS.items():
                    if cid in data:
                        resultado[nome] = {
                            "preco": data[cid].get("usd", 0),
                            "var":   data[cid].get("usd_24h_change", 0),
                        }
        except:
            pass

    # ── Fonte 3: Frankfurter (forex) — fallback ───────────────────────────────
    forex_map = {
        "Dólar/BRL": ("USD","BRL"),
        "EUR/USD":   ("EUR","USD"),
        "GBP/USD":   ("GBP","USD"),
        "USD/JPY":   ("USD","JPY"),
        "AUD/USD":   ("AUD","USD"),
        "USD/CNY":   ("USD","CNY"),
    }
    forex_faltando = [n for n in forex_map if n not in resultado]
    if forex_faltando:
        try:
            ff = requests.get(
                "https://api.frankfurter.app/latest?from=USD&to=BRL,EUR,GBP,JPY,CNY,AUD",
                timeout=6, headers={"User-Agent": "Mozilla/5.0"}
            )
            if ff.status_code == 200:
                rates = ff.json().get("rates", {})
                if "BRL" in rates and "Dólar/BRL" not in resultado:
                    resultado["Dólar/BRL"] = {"preco": rates["BRL"], "var": 0}
                if "EUR" in rates and "EUR/USD" not in resultado:
                    resultado["EUR/USD"] = {"preco": round(1/rates["EUR"], 5), "var": 0}
                if "GBP" in rates and "GBP/USD" not in resultado:
                    resultado["GBP/USD"] = {"preco": round(1/rates["GBP"], 5), "var": 0}
                if "JPY" in rates and "USD/JPY" not in resultado:
                    resultado["USD/JPY"] = {"preco": rates["JPY"], "var": 0}
                if "AUD" in rates and "AUD/USD" not in resultado:
                    resultado["AUD/USD"] = {"preco": round(1/rates["AUD"], 5), "var": 0}
                if "CNY" in rates and "USD/CNY" not in resultado:
                    resultado["USD/CNY"] = {"preco": rates["CNY"], "var": 0}
        except:
            pass

    return resultado

# ── NOTÍCIAS — RSS ao vivo (sem chave de API) ─────────────────────────────────
FEEDS_RSS = [
    ("InfoMoney",    "https://www.infomoney.com.br/feed/"),
    ("Valor Econômico", "https://valor.globo.com/rss/home"),
    ("Reuters BR",   "https://feeds.reuters.com/reuters/BRbusinessNews"),
    ("Exame",        "https://exame.com/feed/"),
    ("Money Times",  "https://www.moneytimes.com.br/feed/"),
]

@st.cache_data(ttl=120)
def buscar_noticias_rss(query=""):
    artigos = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; newsbot/1.0)"}
    query_lower = query.lower() if query else ""

    for fonte, feed_url in FEEDS_RSS:
        try:
            r = requests.get(feed_url, timeout=8, headers=headers)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            channel = root.find("channel")
            if channel is None:
                channel = root

            items = channel.findall("item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:6]:
                titulo = (item.findtext("title") or "").strip()
                desc   = (item.findtext("description") or item.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip()
                link   = (item.findtext("link") or item.findtext("{http://www.w3.org/2005/Atom}id") or "#").strip()
                pub    = (item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}updated") or "").strip()

                # Remove tags HTML da descrição
                import re
                desc = re.sub(r"<[^>]+>", "", desc)[:200]

                # Filtro por query se fornecida
                if query_lower:
                    termos = query_lower.split()
                    texto_busca = (titulo + " " + desc).lower()
                    if not any(t in texto_busca for t in termos):
                        continue

                if titulo:
                    artigos.append({
                        "title":  titulo,
                        "desc":   desc,
                        "url":    link,
                        "fonte":  fonte,
                        "pub":    pub[:16] if pub else "",
                    })
        except:
            continue

    # Fallback: NewsAPI se RSS não trouxer nada
    if not artigos:
        try:
            q = query or "Ibovespa B3 dólar mercado futuro"
            url = f"https://newsapi.org/v2/everything?q={q}&language=pt&sortBy=publishedAt&pageSize=10&apiKey={NEWS_KEY}"
            r = requests.get(url, timeout=8)
            for n in r.json().get("articles", []):
                artigos.append({
                    "title": n.get("title",""),
                    "desc":  (n.get("description") or "")[:200],
                    "url":   n.get("url","#"),
                    "fonte": n.get("source",{}).get("name",""),
                    "pub":   n.get("publishedAt","")[:16],
                })
        except:
            pass

    return artigos[:8]

# ── % RISCO SUGERIDO ──────────────────────────────────────────────────────────
def risco_sugerido(capital: float) -> float:
    if capital <= 2000:   return 5.0
    if capital <= 10000:  return 7.0
    if capital <= 50000:  return 8.0
    if capital <= 100000: return 9.0
    return 10.0

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
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
[data-testid="stSidebar"]  { display: none !important; }
[data-testid="stHeader"]   { display: none !important; }
.block-container { padding: 1.5rem 2rem !important; max-width: 1400px !important; }

.header-box {
    background: linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
    border: 1px solid #1e3a5f; border-radius: 16px;
    padding: 1.2rem 2rem;
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 24px rgba(0,102,255,.10);
}
.logo-icon {
    width:52px;height:52px;
    background:linear-gradient(135deg,#0066ff,#00c6ff);
    border-radius:14px; display:flex; align-items:center; justify-content:center;
    font-size:1.6rem; box-shadow:0 0 20px rgba(0,102,255,.4);
}
.header-title { font-size:1.5rem; font-weight:700; color:#fff; line-height:1; }
.header-sub   { font-size:.8rem; color:#64748b; margin-top:3px; }
.header-badge {
    background:rgba(0,102,255,.15); border:1px solid rgba(0,102,255,.3);
    border-radius:8px; padding:.4rem .9rem;
    font-size:.75rem; color:#60a5fa;
    font-family:'JetBrains Mono',monospace; font-weight:600;
}

.stTabs [data-baseweb="tab-list"] {
    background:#0f172a !important; border-radius:12px !important;
    padding:4px !important; gap:4px !important;
    border:1px solid #1e293b !important; margin-bottom:1.5rem;
}
.stTabs [data-baseweb="tab"] {
    background:transparent !important; color:#64748b !important;
    border-radius:8px !important; font-weight:500 !important;
    padding:.5rem 1.2rem !important; font-size:.88rem !important; border:none !important;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#0066ff,#0052cc) !important;
    color:#fff !important; box-shadow:0 2px 12px rgba(0,102,255,.35) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display:none !important; }

.ativo-card {
    background:#0f172a; border:1px solid #1e293b; border-radius:12px;
    padding:.9rem 1rem; text-align:center; transition:all .2s ease;
    min-width:135px; flex:0 0 auto;
}
.ativo-card:hover { border-color:#0066ff; transform:translateY(-2px); box-shadow:0 4px 16px rgba(0,102,255,.15); }
.ativo-nome   { font-size:.7rem; color:#64748b; font-weight:500; text-transform:uppercase; letter-spacing:.05em; margin-bottom:.4rem; }
.ativo-preco  { font-size:1.05rem; font-weight:700; color:#f1f5f9; font-family:'JetBrains Mono',monospace; }
.ativo-var-up { font-size:.78rem; color:#22c55e; font-weight:600; margin-top:.25rem; }
.ativo-var-dn { font-size:.78rem; color:#ef4444; font-weight:600; margin-top:.25rem; }
.ativo-var-nt { font-size:.78rem; color:#94a3b8; font-weight:600; margin-top:.25rem; }

.sec-title    { font-size:1.15rem; font-weight:700; color:#f1f5f9; margin:1.5rem 0 .8rem 0; display:flex; align-items:center; gap:.5rem; }
.sec-divider  { height:1px; background:#1e293b; margin:1rem 0; }

.scroll-wrapper { overflow-x:auto; padding-bottom:.5rem; scrollbar-width:thin; scrollbar-color:#1e293b transparent; }
.scroll-wrapper::-webkit-scrollbar { height:4px; }
.scroll-wrapper::-webkit-scrollbar-thumb { background:#1e293b; border-radius:4px; }
.scroll-track { display:flex; gap:.75rem; padding:.5rem 0; width:max-content; }

.noticia-card {
    background:#0f172a; border:1px solid #1e293b; border-radius:12px;
    padding:1rem 1.2rem; margin-bottom:.75rem; transition:all .2s;
}
.noticia-card:hover { border-color:#334155; }
.noticia-fonte  { display:inline-block; background:rgba(0,102,255,.15); border:1px solid rgba(0,102,255,.2); border-radius:5px; padding:.15rem .5rem; font-size:.65rem; color:#60a5fa; font-weight:700; text-transform:uppercase; letter-spacing:.05em; margin-bottom:.4rem; }
.noticia-titulo { font-size:.9rem; font-weight:600; color:#f1f5f9; margin-bottom:.4rem; line-height:1.4; }
.noticia-desc   { font-size:.82rem; color:#94a3b8; margin-top:.3rem; line-height:1.5; }
.noticia-meta   { font-size:.72rem; color:#475569; }
.noticia-link a { color:#60a5fa; font-size:.75rem; text-decoration:none; }

.risco-sugerido {
    background:rgba(0,102,255,.08); border:1px solid rgba(0,102,255,.25);
    border-radius:10px; padding:.7rem 1rem; margin-top:.5rem;
    font-size:.82rem; color:#93c5fd;
}
.calc-result {
    background:linear-gradient(135deg,#0f2a1f,#0a1f14);
    border:1px solid #166534; border-radius:12px; padding:1.2rem 1.5rem; margin-top:1rem;
}
.calc-result-titulo { font-size:.78rem; color:#4ade80; font-weight:700; text-transform:uppercase; letter-spacing:.08em; margin-bottom:.8rem; }
.calc-linha  { display:flex; justify-content:space-between; align-items:center; padding:.3rem 0; border-bottom:1px solid rgba(255,255,255,.05); }
.calc-label  { font-size:.82rem; color:#94a3b8; }
.calc-valor  { font-size:.9rem; font-weight:700; color:#f1f5f9; font-family:'JetBrains Mono',monospace; }
.calc-alerta { background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.3); border-radius:8px; padding:.6rem .9rem; margin-top:.75rem; font-size:.8rem; color:#fca5a5; }

.chat-msg-user {
    background:linear-gradient(135deg,#0066ff,#0052cc);
    border-radius:16px 16px 4px 16px; padding:.8rem 1.1rem;
    margin:.5rem 0 .5rem auto; max-width:75%;
    font-size:.88rem; color:#fff; width:fit-content;
}
.chat-msg-bot {
    background:#0f172a; border:1px solid #1e293b;
    border-radius:16px 16px 16px 4px; padding:.8rem 1.1rem;
    margin:.5rem auto .5rem 0; max-width:85%;
    font-size:.88rem; color:#e2e8f0; line-height:1.6; width:fit-content;
}
.chat-container { max-height:440px; overflow-y:auto; padding:.5rem; scrollbar-width:thin; scrollbar-color:#1e293b transparent; }

.stButton > button {
    background:linear-gradient(135deg,#0066ff,#0052cc) !important;
    color:#fff !important; border:none !important; border-radius:10px !important;
    font-weight:600 !important; font-family:'Space Grotesk',sans-serif !important;
    padding:.5rem 1.2rem !important; transition:all .2s !important;
    box-shadow:0 2px 12px rgba(0,102,255,.25) !important;
}
.stButton > button:hover { transform:translateY(-1px) !important; box-shadow:0 4px 20px rgba(0,102,255,.4) !important; }

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    background:#0f172a !important; border:1px solid #1e293b !important;
    border-radius:10px !important; color:#f1f5f9 !important;
    font-family:'Space Grotesk',sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color:#0066ff !important; box-shadow:0 0 0 2px rgba(0,102,255,.2) !important;
}
[data-baseweb="select"] { background:#0f172a !important; }
[data-baseweb="menu"]   { background:#1e293b !important; }
[data-testid="metric-container"] { background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:.8rem 1rem; }
[data-testid="stMetricLabel"] { color:#64748b !important; font-size:.75rem !important; }
[data-testid="stMetricValue"] { color:#f1f5f9 !important; font-family:'JetBrains Mono',monospace !important; }
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-thumb { background:#1e293b; border-radius:4px; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "historico"      not in st.session_state: st.session_state.historico      = []
if "enviar_flag"    not in st.session_state: st.session_state.enviar_flag    = False
if "pergunta_envio" not in st.session_state: st.session_state.pergunta_envio = ""
if "img_b64_envio"  not in st.session_state: st.session_state.img_b64_envio  = None

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="header-box">
  <div style="display:flex;align-items:center;gap:1rem;">
    <div class="logo-icon">📈</div>
    <div>
      <div class="header-title">MestreDoDayTrade Pro</div>
      <div class="header-sub">Assistente Inteligente para WIN &amp; WDO · B3</div>
    </div>
  </div>
  <div style="display:flex;gap:.75rem;align-items:center;">
    <div class="header-badge">🤖 Groq AI</div>
    <div class="header-badge">🕐 {agora_br()}</div>
  </div>
</div>
""", unsafe_allow_html=True)

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
        st.markdown("<div style='color:#475569;font-size:.78rem;padding-top:.6rem'>Atualização automática · Yahoo Finance + CoinGecko + Frankfurter</div>", unsafe_allow_html=True)

    cotacoes = buscar_cotacoes()

    def fmt_preco(preco):
        if preco > 10000:  return f"{preco:,.0f}".replace(",",".")
        if preco > 100:    return f"{preco:,.2f}".replace(",","X").replace(".","," ).replace("X",".")
        if preco > 1:      return f"{preco:.4f}"
        return f"{preco:.6f}"

    def card_html(nome, dados):
        preco = dados.get("preco", 0) if dados else 0
        var   = dados.get("var",   0) if dados else 0
        if not preco:
            return f'<div class="ativo-card"><div class="ativo-nome">{nome}</div><div class="ativo-preco" style="color:#334155;font-size:.8rem">carregando…</div><div class="ativo-var-nt">—</div></div>'
        ps = fmt_preco(preco)
        if   var > 0: vh = f'<div class="ativo-var-up">▲ {var:.2f}%</div>'
        elif var < 0: vh = f'<div class="ativo-var-dn">▼ {abs(var):.2f}%</div>'
        else:         vh = f'<div class="ativo-var-nt">— 0.00%</div>'
        return f'<div class="ativo-card"><div class="ativo-nome">{nome}</div><div class="ativo-preco">{ps}</div>{vh}</div>'

    grupos = [
        ("🇧🇷 Brasil",        ["IBOVESPA","WIN (Mini-Índ.)","WDO (Mini-Dól.)"]),
        ("🌎 Bolsas Globais",  ["S&P 500","Nasdaq","DAX","FTSE 100","Nikkei","Shanghai"]),
        ("🛢️ Commodities",    ["Petróleo WTI","Ouro"]),
        ("💱 Câmbio",          ["Dólar/BRL","EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CNY"]),
        ("₿ Cripto",           ["Bitcoin","Ethereum","Solana","BNB"]),
    ]
    for gnome, ativos_g in grupos:
        st.markdown(f'<div class="sec-title">{gnome}</div>', unsafe_allow_html=True)
        cards = "".join(card_html(a, cotacoes.get(a)) for a in ativos_g)
        st.markdown(f'<div class="scroll-wrapper"><div class="scroll-track">{cards}</div></div>', unsafe_allow_html=True)

    # ── NOTÍCIAS RSS ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div><div class="sec-title">📰 Notícias ao Vivo</div>', unsafe_allow_html=True)
    col_busca, col_btn2 = st.columns([4,1])
    with col_busca:
        query_noticias = st.text_input("", placeholder="Ibovespa, dólar, WIN, WDO…", value="", label_visibility="collapsed")
    with col_btn2:
        st.button("🔍  Buscar")

    with st.spinner("Buscando notícias…"):
        noticias = buscar_noticias_rss(query_noticias)

    if not noticias:
        st.markdown('<div style="color:#475569;font-size:.85rem;padding:1rem 0">Nenhuma notícia encontrada no momento.</div>', unsafe_allow_html=True)
    else:
        for n in noticias:
            titulo = n.get("title","")
            desc   = n.get("desc","")
            url    = n.get("url","#")
            fonte  = n.get("fonte","")
            pub    = n.get("pub","")
            st.markdown(f"""
            <div class="noticia-card">
              <span class="noticia-fonte">{fonte}</span>
              <div class="noticia-titulo">{titulo}</div>
              {'<div class="noticia-desc">'+desc+'</div>' if desc else ''}
              <div style="display:flex;justify-content:space-between;margin-top:.5rem;align-items:center;">
                <div class="noticia-meta">{pub}</div>
                <div class="noticia-link"><a href="{url}" target="_blank">Ler completo →</a></div>
              </div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — GERENCIAMENTO DE RISCO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec-title">🛡️ Calculadora de Risco</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        ativo_sel  = st.selectbox("Ativo", ["WIN (Mini-Índice)", "WDO (Mini-Dólar)"])
        capital    = st.number_input("Capital disponível (R$)", min_value=500.0, max_value=1000000.0, value=5000.0, step=500.0)
        pct_max    = risco_sugerido(capital)
        pct_padrao = min(pct_max, 2.0)
        st.markdown(f'<div class="risco-sugerido">💡 Para R$ {capital:,.0f} o risco sugerido é até <b>{pct_max:.0f}%</b> por operação (máx 10%).</div>', unsafe_allow_html=True)
        risco_pct  = st.number_input("% do capital a arriscar", min_value=0.5, max_value=10.0, value=pct_padrao, step=0.5)
        if risco_pct > pct_max:
            st.markdown(f'<div class="calc-alerta">⚠️ Acima do limite sugerido de {pct_max:.0f}% para este capital.</div>', unsafe_allow_html=True)

    with col2:
        stop        = st.number_input("Stop (pontos)", min_value=1, max_value=500, value=50, step=5)
        meta        = st.number_input("Meta (pontos)", min_value=1, max_value=2000, value=100, step=5)
        n_contratos = st.number_input("Nº de contratos", min_value=1, max_value=20, value=1, step=1)

    # Multiplicador correto B3
    tipo_ativo = "WDO" if "WDO" in ativo_sel else "WIN"
    val_ponto  = MULT[tipo_ativo]   # WIN=0.20, WDO=10.0

    if st.button("📊  Calcular Risco"):
        perda_pts       = stop  * n_contratos * val_ponto
        ganho_pts       = meta  * n_contratos * val_ponto
        rr              = meta  / stop if stop > 0 else 0
        risco_real      = (risco_pct / 100) * capital
        stops_ate_zerar = int(capital / perda_pts) if perda_pts > 0 else 0

        rr_cor    = "#22c55e" if rr >= 2 else "#f59e0b" if rr >= 1.5 else "#ef4444"
        risco_cor = "#22c55e" if perda_pts <= risco_real else "#ef4444"

        # Descrição do tick para orientação
        if tipo_ativo == "WIN":
            tick_info = "tick mínimo = 5 pts = R$ 1,00 → R$ 0,20/pt"
        else:
            tick_info = "tick mínimo = 0,5 pt = R$ 5,00 → R$ 10,00/pt"

        st.markdown(f"""
        <div class="calc-result">
          <div class="calc-result-titulo">📊 Resultado da Análise</div>
          <div class="calc-linha"><span class="calc-label">Ativo</span><span class="calc-valor">{ativo_sel}</span></div>
          <div class="calc-linha"><span class="calc-label">Valor por ponto (B3)</span><span class="calc-valor">R$ {val_ponto:.2f}/pt · {tick_info}</span></div>
          <div class="calc-linha"><span class="calc-label">Perda máxima (stop {stop} pts)</span><span class="calc-valor" style="color:{risco_cor}">R$ {perda_pts:,.2f}</span></div>
          <div class="calc-linha"><span class="calc-label">Ganho potencial (meta {meta} pts)</span><span class="calc-valor" style="color:#22c55e">R$ {ganho_pts:,.2f}</span></div>
          <div class="calc-linha"><span class="calc-label">Risco/Retorno</span><span class="calc-valor" style="color:{rr_cor}">1:{rr:.1f}</span></div>
          <div class="calc-linha"><span class="calc-label">% do capital arriscado</span><span class="calc-valor">{(perda_pts/capital*100):.2f}%</span></div>
          <div class="calc-linha"><span class="calc-label">Limite permitido ({risco_pct:.1f}%)</span><span class="calc-valor">R$ {risco_real:,.2f}</span></div>
          <div class="calc-linha"><span class="calc-label">Stops até zerar a conta</span><span class="calc-valor">{stops_ate_zerar} stops consecutivos</span></div>
        </div>
        """, unsafe_allow_html=True)

        if perda_pts > risco_real:
            st.markdown(f'<div class="calc-alerta">⚠️ Perda de R$ {perda_pts:,.2f} ultrapassa seu limite de R$ {risco_real:,.2f}. Reduza contratos ou o stop.</div>', unsafe_allow_html=True)
        if rr < 1.5:
            st.markdown('<div class="calc-alerta">⚠️ RR abaixo de 1:1.5 — setup desfavorável. Aumente a meta ou reduza o stop.</div>', unsafe_allow_html=True)
        if stops_ate_zerar <= 5:
            st.markdown(f'<div class="calc-alerta">🚨 Apenas {stops_ate_zerar} stops seguidos zeram sua conta. Reduza o tamanho da posição.</div>', unsafe_allow_html=True)

        with st.spinner("IA analisando setup…"):
            analise = ia(
                f"Setup: {ativo_sel} | Capital R${capital:,.0f} | Stop {stop}pts = R${perda_pts:,.2f} | Meta {meta}pts = R${ganho_pts:,.2f} | {n_contratos} contrato(s) | RR 1:{rr:.1f} | Risco do capital: {perda_pts/capital*100:.2f}%. Avalie em 3-4 linhas diretas.",
                system=SYSTEM_PROMPT
            )
        st.markdown(f'<div class="chat-msg-bot" style="max-width:100%;margin-top:1rem">🤖 {analise}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-divider"></div><div class="sec-title">📅 Aviso de Rolagem</div>', unsafe_allow_html=True)
    mes = datetime.now(BR_TZ).month
    meses_venc = {2:"FEV",4:"ABR",6:"JUN",8:"AGO",10:"OUT",12:"DEZ"}
    if mes in meses_venc:
        st.markdown(f'<div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:10px;padding:.9rem 1.2rem;color:#fbbf24;font-size:.85rem">⚠️ <b>Mês de rolagem!</b> Contratos vencem em {meses_venc[mes]}. Verifique o contrato mais líquido antes de operar.</div>', unsafe_allow_html=True)
    else:
        prox     = [m for m in meses_venc if m > mes]
        prox_mes = meses_venc[prox[0]] if prox else "FEV"
        st.markdown(f'<div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.2);border-radius:10px;padding:.9rem 1.2rem;color:#4ade80;font-size:.85rem">✅ Sem rolagem este mês. Próximo vencimento: <b>{prox_mes}</b></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    col_chat, col_lateral = st.columns([3, 1])

    with col_lateral:
        st.markdown('<div style="font-size:.78rem;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.75rem">Análise de Gráfico</div>', unsafe_allow_html=True)
        img_upload = st.file_uploader("Envie print do ProfitPro", type=["jpg","jpeg","png"], label_visibility="collapsed")
        if img_upload:
            st.image(img_upload, use_container_width=True)

        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:.78rem;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.75rem">Atalhos rápidos</div>', unsafe_allow_html=True)

        atalhos = [
            "Como usar VWAP no Profit?",
            "O que é IFR e como interpretar?",
            "Diferença entre candle de reversão e continuação",
            "Como definir suporte e resistência no WIN?",
            "O que olhar antes de abrir operação?",
        ]
        for a in atalhos:
            if st.button(a, key=f"atl_{a}"):
                st.session_state.pergunta_envio = a
                st.session_state.img_b64_envio  = None
                st.session_state.enviar_flag    = True

    with col_chat:
        # ── Processar envio (flag evita loop) ─────────────────────────────────
        if st.session_state.enviar_flag:
            st.session_state.enviar_flag = False
            txt = st.session_state.pergunta_envio
            b64 = st.session_state.img_b64_envio
            st.session_state.pergunta_envio = ""
            st.session_state.img_b64_envio  = None
            if txt.strip():
                st.session_state.historico.append({"role":"user","content":txt.strip()})
                with st.spinner("Analisando…"):
                    resp = ia(txt.strip(), system=SYSTEM_PROMPT, historico=st.session_state.historico, imagem_b64=b64)
                st.session_state.historico.append({"role":"assistant","content":resp})

        # ── Histórico ─────────────────────────────────────────────────────────
        import html as html_mod
        chat_html = '<div class="chat-container">'
        if not st.session_state.historico:
            chat_html += '<div style="color:#475569;font-size:.85rem;padding:1rem 0;text-align:center">👋 Pode perguntar sobre WIN, WDO, indicadores ou mandar um print do gráfico.</div>'
        else:
            for msg in st.session_state.historico[-20:]:
                c = html_mod.escape(msg["content"])
                if msg["role"] == "user":
                    chat_html += f'<div class="chat-msg-user">{c}</div>'
                else:
                    chat_html += f'<div class="chat-msg-bot">{c}</div>'
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)

        # ── Input ─────────────────────────────────────────────────────────────
        col_inp, col_send = st.columns([5,1])
        with col_inp:
            pergunta = st.text_input("", placeholder="Pergunte sobre WIN, WDO, indicadores ou mande um gráfico…", key="pergunta_input", label_visibility="collapsed")
        with col_send:
            enviar = st.button("Enviar")

        if enviar and pergunta.strip():
            imagem_b64 = None
            if img_upload:
                img_upload.seek(0)
                imagem_b64 = base64.b64encode(img_upload.read()).decode("utf-8")
            st.session_state.pergunta_envio = pergunta.strip()
            st.session_state.img_b64_envio  = imagem_b64
            st.session_state.enviar_flag    = True
            st.rerun()

        col_l, col_r = st.columns(2)
        with col_l:
            if st.button("🗑️  Limpar conversa"):
                st.session_state.historico = []
                st.rerun()
        with col_r:
            if st.session_state.historico:
                qtd = len(st.session_state.historico)//2
                st.markdown(f'<div style="font-size:.72rem;color:#475569;padding-top:.6rem;text-align:right">{qtd} mensagem(s)</div>', unsafe_allow_html=True)
