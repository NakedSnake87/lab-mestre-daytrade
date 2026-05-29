import streamlit as st
import requests
import base64
import xml.etree.ElementTree as ET
import re
import html as html_mod
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
7. Sobre tendência hoje: use os dados fornecidos no contexto. Se não tiver dados, oriente o trader sobre o que observar.

AO ANALISAR GRÁFICOS (imagem enviada):
- Tendência dominante (alta, baixa, lateral) com base nas médias visíveis
- Comportamento das médias: direção, cruzamentos recentes, afastamento
- Volume: crescendo, secando, divergindo com o preço?
- Suportes e resistências claros visíveis
- Indicadores visíveis (IFR, MACD, Bandas, VWAP) — comente o que mostram
- Padrões CLARAMENTE visíveis — não invente
- Contexto geral: favorece continuidade ou alerta reversão?
- Seja específico com valores/preços visíveis"""

# ── MULTIPLICADORES B3 ────────────────────────────────────────────────────────
# WIN: tick=5pts=R$1,00 → R$0,20/pt   |   WDO: tick=0,5pt=R$5,00 → R$10,00/pt
MULT = {"WIN": 0.20, "WDO": 10.0}

# ── COTAÇÕES — Stooq (índices/commodities) + CoinGecko (cripto) + Frankfurter (forex)
STOOQ_MAP = {
    "IBOVESPA":       "^bvsp",
    "S&P 500":        "^spx",
    "Nasdaq":         "^ndx",
    "DAX":            "^dax",
    "FTSE 100":       "^ftse",
    "Nikkei":         "^nkx",
    "Petróleo WTI":   "cl.f",
    "Ouro":           "gc.f",
}
CRIPTO_IDS = {
    "Bitcoin":  "bitcoin",
    "Ethereum": "ethereum",
    "Solana":   "solana",
    "BNB":      "binancecoin",
}

@st.cache_data(ttl=90)
def buscar_cotacoes():
    resultado = {}
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # ── Stooq — índices e commodities ────────────────────────────────────────
    for nome, sym in STOOQ_MAP.items():
        try:
            url = f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcvn&h&e=csv"
            r = requests.get(url, headers=hdrs, timeout=8)
            lines = r.text.strip().split("\n")
            if len(lines) >= 2:
                cols = lines[1].split(",")
                # cols: Symbol,Date,Time,Open,High,Low,Close,Volume,Name
                if len(cols) >= 7:
                    close = float(cols[6]) if cols[6] not in ("N/D","") else 0
                    open_ = float(cols[3]) if cols[3] not in ("N/D","") else 0
                    var   = ((close - open_) / open_ * 100) if open_ else 0
                    if close:
                        resultado[nome] = {"preco": close, "var": round(var, 2)}
        except:
            pass

    # ── WIN e WDO via Stooq ───────────────────────────────────────────────────
    for nome, sym in [("WIN (Mini-Índ.)", "winm25.sa"), ("WDO (Mini-Dól.)", "wdom25.sa")]:
        try:
            url = f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcvn&h&e=csv"
            r = requests.get(url, headers=hdrs, timeout=8)
            lines = r.text.strip().split("\n")
            if len(lines) >= 2:
                cols = lines[1].split(",")
                if len(cols) >= 7:
                    close = float(cols[6]) if cols[6] not in ("N/D","") else 0
                    open_ = float(cols[3]) if cols[3] not in ("N/D","") else 0
                    var   = ((close - open_) / open_ * 100) if open_ else 0
                    if close:
                        resultado[nome] = {"preco": close, "var": round(var, 2)}
        except:
            pass

    # ── Frankfurter — forex ───────────────────────────────────────────────────
    try:
        r = requests.get(
            "https://api.frankfurter.app/latest?from=USD&to=BRL,EUR,GBP,JPY,CNY,AUD",
            timeout=8, headers=hdrs
        )
        if r.status_code == 200:
            rates = r.json().get("rates", {})
            pares = {
                "Dólar/BRL": rates.get("BRL", 0),
                "EUR/USD":   round(1/rates["EUR"], 5) if rates.get("EUR") else 0,
                "GBP/USD":   round(1/rates["GBP"], 5) if rates.get("GBP") else 0,
                "USD/JPY":   rates.get("JPY", 0),
                "AUD/USD":   round(1/rates["AUD"], 5) if rates.get("AUD") else 0,
                "USD/CNY":   rates.get("CNY", 0),
            }
            for nome, preco in pares.items():
                if preco:
                    resultado[nome] = {"preco": preco, "var": 0}
    except:
        pass

    # ── CoinGecko — cripto ────────────────────────────────────────────────────
    try:
        ids = ",".join(CRIPTO_IDS.values())
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true",
            timeout=10, headers=hdrs
        )
        if r.status_code == 200:
            data = r.json()
            for nome, cid in CRIPTO_IDS.items():
                if cid in data:
                    resultado[nome] = {
                        "preco": data[cid].get("usd", 0),
                        "var":   round(data[cid].get("usd_24h_change", 0), 2),
                    }
    except:
        pass

    return resultado

# ── NOTÍCIAS — RSS com filtro de qualidade ────────────────────────────────────
DOMINIOS_OK = {"infomoney.com.br","valor.globo.com","reuters.com","exame.com",
               "moneytimes.com.br","investing.com","b3.com.br","cnnbrasil.com.br",
               "globo.com","estadao.com.br","folha.uol.com.br"}

FEEDS_RSS = [
    ("InfoMoney",    "https://www.infomoney.com.br/feed/"),
    ("Reuters BR",   "https://feeds.reuters.com/reuters/BRbusinessNews"),
    ("Exame",        "https://exame.com/feed/"),
    ("Money Times",  "https://www.moneytimes.com.br/feed/"),
    ("CNN Brasil",   "https://www.cnnbrasil.com.br/economy/feed/"),
]

QUERY_PADRAO = "Ibovespa dólar B3 mercado futuro WIN WDO"

@st.cache_data(ttl=120)
def buscar_noticias_rss(query=""):
    artigos = []
    hdrs = {"User-Agent": "Mozilla/5.0 (compatible; newsbot/1.0)"}
    q_lower = (query or QUERY_PADRAO).lower()
    termos  = [t for t in q_lower.split() if len(t) > 2]

    for fonte, feed_url in FEEDS_RSS:
        try:
            r = requests.get(feed_url, timeout=8, headers=hdrs)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            ch   = root.find("channel") or root
            for item in (ch.findall("item") or [])[:8]:
                titulo = (item.findtext("title") or "").strip()
                desc   = re.sub(r"<[^>]+>", "", item.findtext("description") or "").strip()[:220]
                link   = (item.findtext("link") or "#").strip()
                pub    = (item.findtext("pubDate") or "")[:22].strip()

                if not titulo or len(titulo) < 10:
                    continue

                # Filtra domínio — rejeita lixo
                dominio = re.search(r"https?://([^/]+)", link)
                if dominio:
                    dom = dominio.group(1).replace("www.","")
                    dom_ok = any(ok in dom for ok in DOMINIOS_OK)
                else:
                    dom_ok = True  # sem link, aceita pelo nome da fonte

                if not dom_ok:
                    continue

                # Filtra por relevância financeira
                txt_busca = (titulo + " " + desc).lower()
                tem_termo = any(t in txt_busca for t in termos)
                if not tem_termo and query:
                    continue

                artigos.append({
                    "title": titulo,
                    "desc":  desc,
                    "url":   link,
                    "fonte": fonte,
                    "pub":   pub,
                })
        except:
            continue

    # Fallback NewsAPI se não veio nada dos RSS
    if not artigos:
        try:
            q = query or "Ibovespa B3 dólar futuro"
            url = f"https://newsapi.org/v2/everything?q={q}&language=pt&sortBy=publishedAt&pageSize=10&apiKey={NEWS_KEY}"
            r = requests.get(url, timeout=8)
            for n in r.json().get("articles", []):
                artigos.append({
                    "title": n.get("title",""),
                    "desc":  (n.get("description") or "")[:220],
                    "url":   n.get("url","#"),
                    "fonte": n.get("source",{}).get("name",""),
                    "pub":   n.get("publishedAt","")[:16],
                })
        except:
            pass

    return artigos[:8]

# ── % RISCO SUGERIDO ──────────────────────────────────────────────────────────
def risco_sugerido(capital):
    if capital <= 2000:   return 5.0
    if capital <= 10000:  return 7.0
    if capital <= 50000:  return 8.0
    if capital <= 100000: return 9.0
    return 10.0

# ── FORMATAR PREÇO ────────────────────────────────────────────────────────────
def fmt_preco(p):
    if p > 10000: return f"{p:,.0f}".replace(",",".")
    if p > 100:   return f"{p:,.2f}".replace(",","X").replace(".","," ).replace("X",".")
    if p > 1:     return f"{p:.4f}"
    return f"{p:.6f}"

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG + CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="MestreDoDayTrade Pro", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,[data-testid="stAppViewContainer"]{background:#0a0e1a!important;color:#e2e8f0!important;font-family:'Space Grotesk',sans-serif!important}
[data-testid="stSidebar"],[data-testid="stHeader"]{display:none!important}
.block-container{padding:0!important;max-width:100%!important}

/* ── TICKER TAPE ── */
.ticker-wrap{
    width:100%;background:#0b1120;border-bottom:1px solid #1e293b;
    overflow:hidden;padding:0;height:32px;display:flex;align-items:center;
    position:sticky;top:0;z-index:999;
}
.ticker-label{
    flex-shrink:0;background:#0066ff;color:#fff;font-size:.7rem;font-weight:700;
    padding:0 .8rem;height:100%;display:flex;align-items:center;letter-spacing:.05em;
    white-space:nowrap;font-family:'JetBrains Mono',monospace;
}
.ticker-track{
    display:flex;gap:0;white-space:nowrap;
    animation:ticker-scroll 60s linear infinite;
    padding-left:2rem;
}
.ticker-wrap:hover .ticker-track{animation-play-state:paused}
@keyframes ticker-scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.ticker-item{
    display:inline-flex;align-items:center;gap:.4rem;
    padding:0 1.2rem;font-size:.72rem;font-family:'JetBrains Mono',monospace;
    border-right:1px solid #1e293b;height:32px;
}
.ti-nome{color:#94a3b8;font-weight:500}
.ti-preco{color:#f1f5f9;font-weight:700}
.ti-up{color:#22c55e;font-weight:600}
.ti-dn{color:#ef4444;font-weight:600}
.ti-nt{color:#64748b}

/* ── MAIN WRAP ── */
.main-wrap{padding:1.2rem 2rem;max-width:1400px;margin:0 auto}

/* ── HEADER ── */
.header-box{
    background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
    border:1px solid #1e3a5f;border-radius:16px;padding:1rem 1.8rem;
    display:flex;align-items:center;justify-content:space-between;
    margin-bottom:1.2rem;box-shadow:0 4px 24px rgba(0,102,255,.10);
}
.logo-icon{width:46px;height:46px;background:linear-gradient(135deg,#0066ff,#00c6ff);
    border-radius:12px;display:flex;align-items:center;justify-content:center;
    font-size:1.4rem;box-shadow:0 0 16px rgba(0,102,255,.4)}
.header-title{font-size:1.3rem;font-weight:700;color:#fff;line-height:1}
.header-sub{font-size:.75rem;color:#64748b;margin-top:2px}
.header-badge{background:rgba(0,102,255,.15);border:1px solid rgba(0,102,255,.3);
    border-radius:7px;padding:.3rem .8rem;font-size:.72rem;color:#60a5fa;
    font-family:'JetBrains Mono',monospace;font-weight:600}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{background:#0f172a!important;border-radius:12px!important;
    padding:4px!important;gap:4px!important;border:1px solid #1e293b!important;margin-bottom:1.2rem}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#64748b!important;
    border-radius:8px!important;font-weight:500!important;padding:.45rem 1.1rem!important;
    font-size:.86rem!important;border:none!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#0066ff,#0052cc)!important;
    color:#fff!important;box-shadow:0 2px 12px rgba(0,102,255,.35)!important}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none!important}

/* ── ATIVO CARD (painel detalhado) ── */
.ativo-card{background:#0f172a;border:1px solid #1e293b;border-radius:12px;
    padding:.8rem .9rem;text-align:center;transition:all .2s ease;min-width:130px;flex:0 0 auto}
.ativo-card:hover{border-color:#0066ff;transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,102,255,.15)}
.ativo-nome{font-size:.65rem;color:#64748b;font-weight:500;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.35rem}
.ativo-preco{font-size:1rem;font-weight:700;color:#f1f5f9;font-family:'JetBrains Mono',monospace}
.ativo-var-up{font-size:.74rem;color:#22c55e;font-weight:600;margin-top:.2rem}
.ativo-var-dn{font-size:.74rem;color:#ef4444;font-weight:600;margin-top:.2rem}
.ativo-var-nt{font-size:.74rem;color:#94a3b8;margin-top:.2rem}

/* ── UTILITÁRIOS ── */
.sec-title{font-size:1.05rem;font-weight:700;color:#f1f5f9;margin:1.2rem 0 .7rem;display:flex;align-items:center;gap:.5rem}
.sec-divider{height:1px;background:#1e293b;margin:.8rem 0}
.scroll-wrapper{overflow-x:auto;padding-bottom:.4rem;scrollbar-width:thin;scrollbar-color:#1e293b transparent}
.scroll-wrapper::-webkit-scrollbar{height:4px}
.scroll-wrapper::-webkit-scrollbar-thumb{background:#1e293b;border-radius:4px}
.scroll-track{display:flex;gap:.6rem;padding:.4rem 0;width:max-content}

/* ── NOTÍCIAS ── */
.noticia-card{background:#0f172a;border:1px solid #1e293b;border-radius:12px;
    padding:.9rem 1.1rem;margin-bottom:.65rem;transition:all .2s}
.noticia-card:hover{border-color:#334155}
.noticia-fonte{display:inline-block;background:rgba(0,102,255,.15);border:1px solid rgba(0,102,255,.2);
    border-radius:4px;padding:.12rem .45rem;font-size:.62rem;color:#60a5fa;font-weight:700;
    text-transform:uppercase;letter-spacing:.05em;margin-bottom:.35rem}
.noticia-titulo{font-size:.88rem;font-weight:600;color:#f1f5f9;margin-bottom:.35rem;line-height:1.4}
.noticia-desc{font-size:.8rem;color:#94a3b8;line-height:1.5}
.noticia-meta{font-size:.7rem;color:#475569}
.noticia-link a{color:#60a5fa;font-size:.72rem;text-decoration:none}

/* ── CALCULADORA ── */
.risco-sugerido{background:rgba(0,102,255,.08);border:1px solid rgba(0,102,255,.25);
    border-radius:10px;padding:.65rem .9rem;margin-top:.4rem;font-size:.8rem;color:#93c5fd}
.calc-result{background:linear-gradient(135deg,#0f2a1f,#0a1f14);border:1px solid #166534;
    border-radius:12px;padding:1.1rem 1.4rem;margin-top:.9rem}
.calc-result-titulo{font-size:.74rem;color:#4ade80;font-weight:700;text-transform:uppercase;
    letter-spacing:.08em;margin-bottom:.7rem}
.calc-linha{display:flex;justify-content:space-between;align-items:center;
    padding:.28rem 0;border-bottom:1px solid rgba(255,255,255,.05)}
.calc-label{font-size:.8rem;color:#94a3b8}
.calc-valor{font-size:.88rem;font-weight:700;color:#f1f5f9;font-family:'JetBrains Mono',monospace}
.calc-alerta{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);
    border-radius:8px;padding:.55rem .85rem;margin-top:.65rem;font-size:.78rem;color:#fca5a5}

/* ── CHAT ── */
.chat-msg-user{background:linear-gradient(135deg,#0066ff,#0052cc);
    border-radius:16px 16px 4px 16px;padding:.75rem 1rem;
    margin:.45rem 0 .45rem auto;max-width:75%;font-size:.86rem;color:#fff;width:fit-content}
.chat-msg-bot{background:#0f172a;border:1px solid #1e293b;
    border-radius:16px 16px 16px 4px;padding:.75rem 1rem;
    margin:.45rem auto .45rem 0;max-width:85%;font-size:.86rem;
    color:#e2e8f0;line-height:1.6;width:fit-content}
.chat-container{max-height:430px;overflow-y:auto;padding:.4rem;
    scrollbar-width:thin;scrollbar-color:#1e293b transparent}

/* ── BOTÕES ── */
.stButton>button{background:linear-gradient(135deg,#0066ff,#0052cc)!important;
    color:#fff!important;border:none!important;border-radius:10px!important;
    font-weight:600!important;font-family:'Space Grotesk',sans-serif!important;
    padding:.45rem 1.1rem!important;transition:all .2s!important;
    box-shadow:0 2px 12px rgba(0,102,255,.25)!important}
.stButton>button:hover{transform:translateY(-1px)!important;
    box-shadow:0 4px 20px rgba(0,102,255,.4)!important}

/* ── INPUTS ── */
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stTextArea>div>div>textarea{
    background:#0f172a!important;border:1px solid #1e293b!important;
    border-radius:10px!important;color:#f1f5f9!important;
    font-family:'Space Grotesk',sans-serif!important}
[data-baseweb="select"]{background:#0f172a!important}
[data-baseweb="menu"]{background:#1e293b!important}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-thumb{background:#1e293b;border-radius:4px}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "historico"      not in st.session_state: st.session_state.historico      = []
if "enviar_flag"    not in st.session_state: st.session_state.enviar_flag    = False
if "pergunta_envio" not in st.session_state: st.session_state.pergunta_envio = ""
if "img_b64_envio"  not in st.session_state: st.session_state.img_b64_envio  = None

# ── BUSCAR COTAÇÕES ────────────────────────────────────────────────────────────
cotacoes = buscar_cotacoes()

# ── TICKER TAPE ───────────────────────────────────────────────────────────────
TICKER_ATIVOS = [
    "IBOVESPA","WIN (Mini-Índ.)","WDO (Mini-Dól.)",
    "S&P 500","Nasdaq","DAX","FTSE 100","Nikkei",
    "Petróleo WTI","Ouro",
    "Dólar/BRL","EUR/USD","GBP/USD","USD/JPY",
    "Bitcoin","Ethereum","Solana","BNB",
]

def ticker_item(nome, dados):
    if not dados or not dados.get("preco"):
        return f'<span class="ticker-item"><span class="ti-nome">{nome}</span><span class="ti-preco">—</span></span>'
    p   = dados["preco"]
    var = dados.get("var", 0)
    ps  = fmt_preco(p)
    if   var > 0:  vc = f'<span class="ti-up">▲{var:.2f}%</span>'
    elif var < 0:  vc = f'<span class="ti-dn">▼{abs(var):.2f}%</span>'
    else:          vc = f'<span class="ti-nt">—</span>'
    return f'<span class="ticker-item"><span class="ti-nome">{nome}</span><span class="ti-preco">{ps}</span>{vc}</span>'

items_html = "".join(ticker_item(n, cotacoes.get(n)) for n in TICKER_ATIVOS)
# Duplica para loop contínuo
tape_html = f"""
<div class="ticker-wrap">
  <div class="ticker-label">📈 LIVE</div>
  <div class="ticker-track">{items_html}{items_html}</div>
</div>
"""
st.markdown(tape_html, unsafe_allow_html=True)

# ── MAIN WRAP ─────────────────────────────────────────────────────────────────
st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="header-box">
  <div style="display:flex;align-items:center;gap:.9rem">
    <div class="logo-icon">📈</div>
    <div>
      <div class="header-title">MestreDoDayTrade Pro</div>
      <div class="header-sub">Assistente Inteligente para WIN &amp; WDO · B3</div>
    </div>
  </div>
  <div style="display:flex;gap:.6rem;align-items:center">
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
    col_btn, col_info = st.columns([1,4])
    with col_btn:
        if st.button("⟳  Atualizar"):
            st.cache_data.clear(); st.rerun()
    with col_info:
        st.markdown("<div style='color:#475569;font-size:.75rem;padding-top:.55rem'>Stooq · CoinGecko · Frankfurter · atualiza a cada 90s</div>", unsafe_allow_html=True)

    def card_html(nome, dados):
        p = dados.get("preco",0) if dados else 0
        v = dados.get("var",  0) if dados else 0
        if not p:
            return f'<div class="ativo-card"><div class="ativo-nome">{nome}</div><div class="ativo-preco" style="color:#334155;font-size:.78rem">—</div><div class="ativo-var-nt">sem dado</div></div>'
        ps = fmt_preco(p)
        if   v > 0: vh = f'<div class="ativo-var-up">▲ {v:.2f}%</div>'
        elif v < 0: vh = f'<div class="ativo-var-dn">▼ {abs(v):.2f}%</div>'
        else:       vh = '<div class="ativo-var-nt">— 0.00%</div>'
        return f'<div class="ativo-card"><div class="ativo-nome">{nome}</div><div class="ativo-preco">{ps}</div>{vh}</div>'

    grupos = [
        ("🇧🇷 Brasil",       ["IBOVESPA","WIN (Mini-Índ.)","WDO (Mini-Dól.)"]),
        ("🌎 Bolsas Globais", ["S&P 500","Nasdaq","DAX","FTSE 100","Nikkei"]),
        ("🛢️ Commodities",   ["Petróleo WTI","Ouro"]),
        ("💱 Câmbio",         ["Dólar/BRL","EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CNY"]),
        ("₿ Cripto",          ["Bitcoin","Ethereum","Solana","BNB"]),
    ]
    for gnome, ativos_g in grupos:
        st.markdown(f'<div class="sec-title">{gnome}</div>', unsafe_allow_html=True)
        cards = "".join(card_html(a, cotacoes.get(a)) for a in ativos_g)
        st.markdown(f'<div class="scroll-wrapper"><div class="scroll-track">{cards}</div></div>', unsafe_allow_html=True)

    # ── NOTÍCIAS ──────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div><div class="sec-title">📰 Notícias ao Vivo</div>', unsafe_allow_html=True)
    col_busca, col_btn2 = st.columns([5,1])
    with col_busca:
        query_n = st.text_input("", placeholder="Buscar: Ibovespa, dólar, WIN, juros…", label_visibility="collapsed")
    with col_btn2:
        st.button("🔍 Buscar")

    with st.spinner("Buscando notícias…"):
        noticias = buscar_noticias_rss(query_n)

    if not noticias:
        st.markdown('<div style="color:#475569;font-size:.83rem;padding:.8rem 0">Nenhuma notícia encontrada. Tente outro termo.</div>', unsafe_allow_html=True)
    else:
        for n in noticias:
            t = html_mod.escape(n.get("title",""))
            d = html_mod.escape(n.get("desc",""))
            u = n.get("url","#")
            f = n.get("fonte","")
            p = n.get("pub","")
            st.markdown(f"""
            <div class="noticia-card">
              <span class="noticia-fonte">{f}</span>
              <div class="noticia-titulo">{t}</div>
              {'<div class="noticia-desc">'+d+'</div>' if d else ''}
              <div style="display:flex;justify-content:space-between;margin-top:.45rem;align-items:center">
                <div class="noticia-meta">{p}</div>
                <div class="noticia-link"><a href="{u}" target="_blank">Ler completo →</a></div>
              </div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — GERENCIAMENTO DE RISCO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec-title">🛡️ Calculadora de Risco</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        ativo_sel  = st.selectbox("Ativo", ["WIN (Mini-Índice)","WDO (Mini-Dólar)"])
        capital    = st.number_input("Capital disponível (R$)", min_value=500.0, max_value=1000000.0, value=5000.0, step=500.0)
        pct_max    = risco_sugerido(capital)
        pct_padrao = min(pct_max, 2.0)
        st.markdown(f'<div class="risco-sugerido">💡 Para R$ {capital:,.0f} → risco sugerido até <b>{pct_max:.0f}%</b>/operação (máx 10%)</div>', unsafe_allow_html=True)
        risco_pct  = st.number_input("% do capital a arriscar", min_value=0.5, max_value=10.0, value=pct_padrao, step=0.5)
        if risco_pct > pct_max:
            st.markdown(f'<div class="calc-alerta">⚠️ Acima do sugerido de {pct_max:.0f}% para este capital.</div>', unsafe_allow_html=True)
    with col2:
        stop        = st.number_input("Stop (pontos)", min_value=1, max_value=500, value=50, step=5)
        meta        = st.number_input("Meta (pontos)", min_value=1, max_value=2000, value=100, step=5)
        n_contratos = st.number_input("Nº de contratos", min_value=1, max_value=20, value=1, step=1)

    tipo_ativo = "WDO" if "WDO" in ativo_sel else "WIN"
    val_ponto  = MULT[tipo_ativo]  # WIN=0.20, WDO=10.0

    if st.button("📊  Calcular Risco"):
        perda_pts       = stop  * n_contratos * val_ponto
        ganho_pts       = meta  * n_contratos * val_ponto
        rr              = meta  / stop if stop > 0 else 0
        risco_real      = (risco_pct/100) * capital
        stops_ate_zerar = int(capital/perda_pts) if perda_pts > 0 else 0
        rr_cor    = "#22c55e" if rr>=2 else "#f59e0b" if rr>=1.5 else "#ef4444"
        risco_cor = "#22c55e" if perda_pts<=risco_real else "#ef4444"
        tick_info = "tick 5pts=R$1,00 → R$0,20/pt" if tipo_ativo=="WIN" else "tick 0,5pt=R$5,00 → R$10,00/pt"

        st.markdown(f"""
        <div class="calc-result">
          <div class="calc-result-titulo">📊 Resultado da Análise</div>
          <div class="calc-linha"><span class="calc-label">Ativo</span><span class="calc-valor">{ativo_sel}</span></div>
          <div class="calc-linha"><span class="calc-label">Valor por ponto (B3)</span><span class="calc-valor">R$ {val_ponto:.2f}/pt · {tick_info}</span></div>
          <div class="calc-linha"><span class="calc-label">Perda máxima (stop {stop}pts)</span><span class="calc-valor" style="color:{risco_cor}">R$ {perda_pts:,.2f}</span></div>
          <div class="calc-linha"><span class="calc-label">Ganho potencial (meta {meta}pts)</span><span class="calc-valor" style="color:#22c55e">R$ {ganho_pts:,.2f}</span></div>
          <div class="calc-linha"><span class="calc-label">Risco/Retorno</span><span class="calc-valor" style="color:{rr_cor}">1:{rr:.1f}</span></div>
          <div class="calc-linha"><span class="calc-label">% do capital arriscado</span><span class="calc-valor">{perda_pts/capital*100:.2f}%</span></div>
          <div class="calc-linha"><span class="calc-label">Limite ({risco_pct:.1f}%)</span><span class="calc-valor">R$ {risco_real:,.2f}</span></div>
          <div class="calc-linha"><span class="calc-label">Stops até zerar</span><span class="calc-valor">{stops_ate_zerar} stops consecutivos</span></div>
        </div>""", unsafe_allow_html=True)

        if perda_pts > risco_real:
            st.markdown(f'<div class="calc-alerta">⚠️ Perda R${perda_pts:,.2f} passa seu limite de R${risco_real:,.2f}. Reduza contratos ou stop.</div>', unsafe_allow_html=True)
        if rr < 1.5:
            st.markdown('<div class="calc-alerta">⚠️ RR abaixo de 1:1.5 — setup desfavorável. Amplie meta ou reduza stop.</div>', unsafe_allow_html=True)
        if stops_ate_zerar <= 5:
            st.markdown(f'<div class="calc-alerta">🚨 {stops_ate_zerar} stops seguidos zeram a conta. Reduza o tamanho.</div>', unsafe_allow_html=True)

        with st.spinner("IA analisando setup…"):
            analise = ia(
                f"Setup: {ativo_sel} | Capital R${capital:,.0f} | Stop {stop}pts=R${perda_pts:,.2f} | Meta {meta}pts=R${ganho_pts:,.2f} | {n_contratos}x | RR 1:{rr:.1f} | Risco capital: {perda_pts/capital*100:.2f}%. Avalie em 3-4 linhas diretas.",
                system=SYSTEM_PROMPT)
        st.markdown(f'<div class="chat-msg-bot" style="max-width:100%;margin-top:.9rem">🤖 {html_mod.escape(analise)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-divider"></div><div class="sec-title">📅 Aviso de Rolagem</div>', unsafe_allow_html=True)
    mes = datetime.now(BR_TZ).month
    meses_venc = {2:"FEV",4:"ABR",6:"JUN",8:"AGO",10:"OUT",12:"DEZ"}
    if mes in meses_venc:
        st.markdown(f'<div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:10px;padding:.8rem 1.1rem;color:#fbbf24;font-size:.83rem">⚠️ <b>Mês de rolagem!</b> Contratos vencem em {meses_venc[mes]}. Verifique o mais líquido antes de operar.</div>', unsafe_allow_html=True)
    else:
        prox=[m for m in meses_venc if m>mes]; pm=meses_venc[prox[0]] if prox else "FEV"
        st.markdown(f'<div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.2);border-radius:10px;padding:.8rem 1.1rem;color:#4ade80;font-size:.83rem">✅ Sem rolagem este mês. Próximo: <b>{pm}</b></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    col_chat, col_lateral = st.columns([3,1])

    with col_lateral:
        st.markdown('<div style="font-size:.74rem;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.6rem">Análise de Gráfico</div>', unsafe_allow_html=True)
        img_upload = st.file_uploader("Print do ProfitPro", type=["jpg","jpeg","png"], label_visibility="collapsed")
        if img_upload:
            st.image(img_upload, use_container_width=True)
        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:.74rem;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.6rem">Atalhos</div>', unsafe_allow_html=True)
        atalhos = [
            "Como usar VWAP no Profit?",
            "O que é IFR e como interpretar?",
            "Diferença candle reversão e continuação",
            "Como definir suporte e resistência no WIN?",
            "O que olhar antes de abrir operação?",
        ]
        for a in atalhos:
            if st.button(a, key=f"atl_{a}"):
                st.session_state.pergunta_envio = a
                st.session_state.img_b64_envio  = None
                st.session_state.enviar_flag    = True

    with col_chat:
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

        chat_html = '<div class="chat-container">'
        if not st.session_state.historico:
            chat_html += '<div style="color:#475569;font-size:.83rem;padding:1rem 0;text-align:center">👋 Pergunte sobre WIN, WDO, indicadores ou mande um print do gráfico.</div>'
        else:
            for msg in st.session_state.historico[-20:]:
                c = html_mod.escape(msg["content"])
                cls = "chat-msg-user" if msg["role"]=="user" else "chat-msg-bot"
                chat_html += f'<div class="{cls}">{c}</div>'
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)

        col_inp, col_send = st.columns([5,1])
        with col_inp:
            pergunta = st.text_input("", placeholder="Pergunte sobre WIN, WDO, indicadores ou mande gráfico…", key="pergunta_input", label_visibility="collapsed")
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
            if st.button("🗑️  Limpar"):
                st.session_state.historico = []; st.rerun()
        with col_r:
            if st.session_state.historico:
                qtd = len(st.session_state.historico)//2
                st.markdown(f'<div style="font-size:.7rem;color:#475569;padding-top:.55rem;text-align:right">{qtd} mensagem(s)</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
