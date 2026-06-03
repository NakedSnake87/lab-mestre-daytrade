import streamlit as st
import requests
import base64
import xml.etree.ElementTree as ET
import re
import html as html_mod
import sqlite3
import os
from datetime import datetime, timedelta, date
import pytz

# ── CONFIG ────────────────────────────────────────────────────────────────────
GROQ_KEY = st.secrets["GROQ_KEY"]
NEWS_KEY  = st.secrets["NEWS_KEY"]
BR_TZ     = pytz.timezone("America/Sao_Paulo")
DB_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diario_trades.db")

def agora_br():
    return datetime.now(BR_TZ).strftime("%d/%m/%Y %H:%M")

# ══════════════════════════════════════════════════════════════════════════════
# CALENDÁRIO ECONÔMICO — eventos macro que afetam WIN/WDO
# ══════════════════════════════════════════════════════════════════════════════
# Eventos pontuais com data específica (atualizar anualmente conforme calendário oficial)
EVENTOS_FIXOS = [
    # COPOM 2026 (datas oficiais BCB) — decisão de juros, sempre quarta
    {"data":"2026-01-28","hora":"18:30","pais":"🇧🇷","evento":"Decisão COPOM (Selic)","impacto":"alto","win":"Selic alta pressiona Bolsa","wdo":"Selic alta tende a valorizar Real"},
    {"data":"2026-03-18","hora":"18:30","pais":"🇧🇷","evento":"Decisão COPOM (Selic)","impacto":"alto","win":"Selic alta pressiona Bolsa","wdo":"Selic alta tende a valorizar Real"},
    {"data":"2026-05-06","hora":"18:30","pais":"🇧🇷","evento":"Decisão COPOM (Selic)","impacto":"alto","win":"Selic alta pressiona Bolsa","wdo":"Selic alta tende a valorizar Real"},
    {"data":"2026-06-17","hora":"18:30","pais":"🇧🇷","evento":"Decisão COPOM (Selic)","impacto":"alto","win":"Selic alta pressiona Bolsa","wdo":"Selic alta tende a valorizar Real"},
    {"data":"2026-07-29","hora":"18:30","pais":"🇧🇷","evento":"Decisão COPOM (Selic)","impacto":"alto","win":"Selic alta pressiona Bolsa","wdo":"Selic alta tende a valorizar Real"},
    {"data":"2026-09-16","hora":"18:30","pais":"🇧🇷","evento":"Decisão COPOM (Selic)","impacto":"alto","win":"Selic alta pressiona Bolsa","wdo":"Selic alta tende a valorizar Real"},
    {"data":"2026-11-04","hora":"18:30","pais":"🇧🇷","evento":"Decisão COPOM (Selic)","impacto":"alto","win":"Selic alta pressiona Bolsa","wdo":"Selic alta tende a valorizar Real"},
    {"data":"2026-12-09","hora":"18:30","pais":"🇧🇷","evento":"Decisão COPOM (Selic)","impacto":"alto","win":"Selic alta pressiona Bolsa","wdo":"Selic alta tende a valorizar Real"},
    # FOMC 2026 (Fed) — decisão de juros EUA
    {"data":"2026-01-28","hora":"16:00","pais":"🇺🇸","evento":"Decisão FOMC (Fed)","impacto":"alto","win":"Juros EUA altos pressionam emergentes","wdo":"Fed hawkish fortalece Dólar"},
    {"data":"2026-03-18","hora":"15:00","pais":"🇺🇸","evento":"Decisão FOMC (Fed)","impacto":"alto","win":"Juros EUA altos pressionam emergentes","wdo":"Fed hawkish fortalece Dólar"},
    {"data":"2026-04-29","hora":"15:00","pais":"🇺🇸","evento":"Decisão FOMC (Fed)","impacto":"alto","win":"Juros EUA altos pressionam emergentes","wdo":"Fed hawkish fortalece Dólar"},
    {"data":"2026-06-17","hora":"15:00","pais":"🇺🇸","evento":"Decisão FOMC (Fed)","impacto":"alto","win":"Juros EUA altos pressionam emergentes","wdo":"Fed hawkish fortalece Dólar"},
    {"data":"2026-07-29","hora":"15:00","pais":"🇺🇸","evento":"Decisão FOMC (Fed)","impacto":"alto","win":"Juros EUA altos pressionam emergentes","wdo":"Fed hawkish fortalece Dólar"},
    {"data":"2026-09-16","hora":"15:00","pais":"🇺🇸","evento":"Decisão FOMC (Fed)","impacto":"alto","win":"Juros EUA altos pressionam emergentes","wdo":"Fed hawkish fortalece Dólar"},
    {"data":"2026-10-28","hora":"15:00","pais":"🇺🇸","evento":"Decisão FOMC (Fed)","impacto":"alto","win":"Juros EUA altos pressionam emergentes","wdo":"Fed hawkish fortalece Dólar"},
    {"data":"2026-12-09","hora":"15:00","pais":"🇺🇸","evento":"Decisão FOMC (Fed)","impacto":"alto","win":"Juros EUA altos pressionam emergentes","wdo":"Fed hawkish fortalece Dólar"},
]

def _primeira_sexta(ano, mes):
    """Retorna a primeira sexta-feira do mês (Payroll dos EUA)."""
    d = date(ano, mes, 1)
    while d.weekday() != 4:  # 4 = sexta
        d += timedelta(days=1)
    return d

def gerar_eventos_recorrentes(ano, mes):
    """Gera eventos recorrentes do mês: Payroll, CPI, IPCA."""
    eventos = []
    # Payroll — 1ª sexta do mês, 9h30 (Brasília)
    payroll = _primeira_sexta(ano, mes)
    eventos.append({
        "data": payroll.strftime("%Y-%m-%d"), "hora":"09:30", "pais":"🇺🇸",
        "evento":"Payroll (Folha de Pagamento EUA)", "impacto":"alto",
        "win":"Dado forte = Fed mais duro, pressiona Bolsa",
        "wdo":"Payroll forte fortalece Dólar",
    })
    # CPI EUA — geralmente meados do mês (~dia 12), 9h30
    eventos.append({
        "data": date(ano, mes, 12).strftime("%Y-%m-%d"), "hora":"09:30", "pais":"🇺🇸",
        "evento":"CPI (Inflação EUA)", "impacto":"alto",
        "win":"Inflação alta = juros altos = pressão na Bolsa",
        "wdo":"CPI alto fortalece Dólar",
    })
    # IPCA Brasil — geralmente ~dia 10, 9h
    eventos.append({
        "data": date(ano, mes, 10).strftime("%Y-%m-%d"), "hora":"09:00", "pais":"🇧🇷",
        "evento":"IPCA (Inflação Brasil)", "impacto":"medio",
        "win":"IPCA alto = expectativa de Selic maior",
        "wdo":"IPCA afeta trajetória da Selic e o Real",
    })
    return eventos

def calendario_proximos(dias=14):
    """Retorna eventos dos próximos N dias, ordenados por data."""
    hoje = datetime.now(BR_TZ).date()
    limite = hoje + timedelta(days=dias)
    todos = list(EVENTOS_FIXOS)
    # adiciona recorrentes do mês atual e do próximo
    for delta_mes in (0, 1):
        ref = (hoje.replace(day=1) + timedelta(days=32*delta_mes)).replace(day=1)
        todos += gerar_eventos_recorrentes(ref.year, ref.month)
    # filtra janela e ordena
    out = []
    for e in todos:
        try:
            d = datetime.strptime(e["data"], "%Y-%m-%d").date()
            if hoje <= d <= limite:
                out.append(e)
        except:
            continue
    out.sort(key=lambda x: (x["data"], x["hora"]))
    return out



# ══════════════════════════════════════════════════════════════════════════════
# CAMADA DE DADOS — Diário de Operações (SQLite)
# ══════════════════════════════════════════════════════════════════════════════
def db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def db_init():
    conn = db_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            data        TEXT NOT NULL,
            ativo       TEXT NOT NULL,
            direcao     TEXT NOT NULL,
            contratos   INTEGER DEFAULT 1,
            pontos      REAL DEFAULT 0,
            resultado   REAL DEFAULT 0,
            seguiu_setup INTEGER DEFAULT 1,
            esticou_stop INTEGER DEFAULT 0,
            hora        TEXT DEFAULT '',
            obs         TEXT DEFAULT '',
            criado_em   TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS acessos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            data      TEXT NOT NULL,
            momento   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def db_registrar_acesso():
    conn = db_conn()
    hoje = datetime.now(BR_TZ)
    conn.execute("INSERT INTO acessos (data, momento) VALUES (?,?)",
                 (hoje.strftime("%Y-%m-%d"), hoje.isoformat()))
    conn.commit()
    conn.close()

def db_stats_acessos():
    conn = db_conn()
    total = conn.execute("SELECT COUNT(*) FROM acessos").fetchone()[0]
    hoje = datetime.now(BR_TZ).strftime("%Y-%m-%d")
    hoje_n = conn.execute("SELECT COUNT(*) FROM acessos WHERE data = ?", (hoje,)).fetchone()[0]
    conn.close()
    return {"total": total, "hoje": hoje_n}

def db_add_trade(d):
    conn = db_conn()
    conn.execute("""
        INSERT INTO trades (data, ativo, direcao, contratos, pontos, resultado,
                            seguiu_setup, esticou_stop, hora, obs, criado_em)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (d["data"], d["ativo"], d["direcao"], d["contratos"], d["pontos"],
          d["resultado"], d["seguiu_setup"], d["esticou_stop"], d["hora"],
          d["obs"], datetime.now(BR_TZ).isoformat()))
    conn.commit()
    conn.close()

def db_listar_trades(limite=500):
    conn = db_conn()
    rows = conn.execute("SELECT * FROM trades ORDER BY data DESC, id DESC LIMIT ?", (limite,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_deletar_trade(trade_id):
    conn = db_conn()
    conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    conn.commit()
    conn.close()

def db_trades_periodo(dias=30):
    conn = db_conn()
    limite = (datetime.now(BR_TZ) - timedelta(days=dias)).strftime("%Y-%m-%d")
    rows = conn.execute("SELECT * FROM trades WHERE data >= ? ORDER BY data", (limite,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── ESTATÍSTICAS ──────────────────────────────────────────────────────────────
def calcular_estatisticas(trades):
    if not trades:
        return None
    n = len(trades)
    resultados = [t["resultado"] for t in trades]
    lucro_total = sum(resultados)
    ganhos  = [r for r in resultados if r > 0]
    perdas  = [r for r in resultados if r < 0]
    n_ganhos = len(ganhos)
    n_perdas = len(perdas)
    assertividade = (n_ganhos / n * 100) if n else 0
    soma_ganhos = sum(ganhos)
    soma_perdas = abs(sum(perdas))
    profit_factor = (soma_ganhos / soma_perdas) if soma_perdas else (soma_ganhos if soma_ganhos else 0)
    media_ganho = (soma_ganhos / n_ganhos) if n_ganhos else 0
    media_perda = (soma_perdas / n_perdas) if n_perdas else 0
    rr_medio = (media_ganho / media_perda) if media_perda else (media_ganho if media_ganho else 0)

    # Por dia
    por_dia = {}
    for t in trades:
        por_dia.setdefault(t["data"], 0)
        por_dia[t["data"]] += t["resultado"]
    melhor_dia = max(por_dia.values()) if por_dia else 0
    pior_dia   = min(por_dia.values()) if por_dia else 0

    # Erros comportamentais
    esticou_stop = sum(1 for t in trades if t.get("esticou_stop"))
    fora_setup   = sum(1 for t in trades if not t.get("seguiu_setup"))
    perda_por_esticar = abs(sum(t["resultado"] for t in trades if t.get("esticou_stop") and t["resultado"] < 0))

    # Overtrade: dias com mais de 4 trades
    trades_por_dia = {}
    for t in trades:
        trades_por_dia.setdefault(t["data"], 0)
        trades_por_dia[t["data"]] += 1
    dias_overtrade = sum(1 for c in trades_por_dia.values() if c > 4)

    return {
        "n": n, "lucro_total": lucro_total, "assertividade": assertividade,
        "profit_factor": profit_factor, "rr_medio": rr_medio,
        "melhor_dia": melhor_dia, "pior_dia": pior_dia,
        "n_ganhos": n_ganhos, "n_perdas": n_perdas,
        "media_ganho": media_ganho, "media_perda": media_perda,
        "esticou_stop": esticou_stop, "fora_setup": fora_setup,
        "perda_por_esticar": perda_por_esticar, "dias_overtrade": dias_overtrade,
        "por_dia": por_dia,
    }

# ── SCORE DE TRADER ───────────────────────────────────────────────────────────
def calcular_score(stats):
    if not stats or stats["n"] < 3:
        return None
    n = stats["n"]

    # Gestão de risco (0-100): penaliza esticar stop e profit factor baixo
    pct_esticou = stats["esticou_stop"] / n
    pf = stats["profit_factor"]
    gestao = 100
    gestao -= pct_esticou * 60          # esticar stop pesa muito
    gestao += min((pf - 1) * 20, 20) if pf > 1 else max((pf - 1) * 30, -40)
    gestao = max(0, min(100, gestao))

    # Disciplina (0-100): seguir setup + não fazer overtrade
    pct_setup = (n - stats["fora_setup"]) / n
    n_dias = len(stats["por_dia"]) or 1
    pct_overtrade = stats["dias_overtrade"] / n_dias
    disciplina = pct_setup * 100 - pct_overtrade * 40
    disciplina = max(0, min(100, disciplina))

    # Assertividade (0-100): direto, com teto realista
    assert_score = min(stats["assertividade"] * 1.25, 100)

    # Risco/retorno (0-100)
    rr = stats["rr_medio"]
    rr_score = min(rr / 2 * 100, 100) if rr > 0 else 0

    geral = round(gestao * 0.30 + disciplina * 0.30 + assert_score * 0.20 + rr_score * 0.20)
    return {
        "geral": geral,
        "gestao": round(gestao),
        "disciplina": round(disciplina),
        "assertividade": round(assert_score),
        "risco_retorno": round(rr_score),
    }

# ── ESCALONAMENTO DE CONTRATOS (por pontos acumulados) ────────────────────────
ESCALA_PADRAO = {
    "WIN": [(5000,1),(7500,2),(10000,3),(12500,4),(15000,5)],
    "WDO": [(200,1),(300,2),(400,3),(500,4),(600,5)],
}

def calcular_escalonamento(trades, escala=None):
    """Soma pontos acumulados por ativo e determina contratos liberados.
    'escala' é um dict {ativo: [(pontos, contratos), ...]}; usa o padrão se None."""
    if escala is None:
        escala = ESCALA_PADRAO
    acum = {"WIN": 0.0, "WDO": 0.0}
    for t in trades:
        a = t.get("ativo")
        if a in acum:
            acum[a] += t.get("pontos", 0)
    res = {}
    for ativo, faixas in escala.items():
        faixas = sorted(faixas, key=lambda x: x[0])  # ordena por pontos
        pts = acum.get(ativo, 0)
        contratos = 0
        proxima = None
        for limiar, c in faixas:
            if pts >= limiar:
                contratos = c
            else:
                proxima = (limiar, c)
                break
        res[ativo] = {
            "pontos": pts,
            "contratos": contratos,
            "proxima": proxima,  # (pontos_necessarios, contratos) ou None
        }
    return res

# ── DIAGNÓSTICO AUTOMÁTICO ────────────────────────────────────────────────────
def gerar_diagnostico(stats, score):
    """Classifica os indicadores em Ponto Forte / Atenção / Erro Crítico / Próxima Ação."""
    fortes, atencao, criticos, acoes = [], [], [], []

    # Gestão de risco
    if score["gestao"] >= 80:
        fortes.append(f"Gestão de risco {score['gestao']}/100 — você protege bem o capital")
    elif score["gestao"] >= 60:
        atencao.append(f"Gestão de risco {score['gestao']}/100 — dá pra melhorar")
    else:
        criticos.append(f"Gestão de risco {score['gestao']}/100 — frágil")

    # Profit Factor
    pf = stats["profit_factor"]
    if pf >= 1.5:
        fortes.append(f"Profit Factor {pf:.2f} — seus ganhos superam bem as perdas")
    elif pf >= 1.0:
        atencao.append(f"Profit Factor {pf:.2f} — positivo, mas com pouca margem (meta: 1,5)")
    else:
        criticos.append(f"Profit Factor {pf:.2f} — você perde mais do que ganha")
        acoes.append("Elevar o Profit Factor acima de 1,2 — corte perdas mais cedo e deixe ganhos correrem")

    # Assertividade
    ass = stats["assertividade"]
    if ass >= 60:
        fortes.append(f"Assertividade {ass:.0f}% — boa taxa de acerto")
    elif ass >= 45:
        atencao.append(f"Assertividade {ass:.0f}% — na média, refine os pontos de entrada")
    else:
        criticos.append(f"Assertividade {ass:.0f}% — taxa de acerto baixa")

    # Risco/Retorno
    rr = stats["rr_medio"]
    if rr >= 1.5:
        fortes.append(f"Risco/Retorno 1:{rr:.1f} — excelente relação")
    elif rr >= 1.0:
        atencao.append(f"Risco/Retorno 1:{rr:.1f} — aceitável, busque 1:2")
    else:
        criticos.append(f"Risco/Retorno 1:{rr:.1f} — seus alvos são menores que seus stops")
        acoes.append("Buscar relação risco/retorno de no mínimo 1:1,5 por operação")

    # Overtrade
    if stats["dias_overtrade"] > 0:
        criticos.append(f"Overtrade em {stats['dias_overtrade']} dia(s) — excesso de operações")
        acoes.append("Limitar a no máximo 3-4 operações por pregão")

    # Esticar stop
    if stats["esticou_stop"] > 0:
        atencao.append(f"Stop esticado {stats['esticou_stop']}x — custou R$ {stats['perda_por_esticar']:.2f}")
        acoes.append("Respeitar o stop inicial — nunca aumentar a perda planejada")

    if not acoes:
        acoes.append("Manter a consistência e registrar todas as operações")

    return {"fortes": fortes, "atencao": atencao, "criticos": criticos, "acoes": acoes}

# ── RANKING DE VAZAMENTOS (maiores fontes de perda) ───────────────────────────
def ranking_vazamentos(trades):
    vaz = {}
    # Por esticar stop
    perda_stop = abs(sum(t["resultado"] for t in trades if t.get("esticou_stop") and t["resultado"] < 0))
    if perda_stop > 0:
        vaz["Stop alongado"] = perda_stop
    # Por operar fora do setup
    perda_setup = abs(sum(t["resultado"] for t in trades if not t.get("seguiu_setup") and t["resultado"] < 0))
    if perda_setup > 0:
        vaz["Operar fora do setup"] = perda_setup
    # Por overtrade: perdas em dias com mais de 4 trades
    cont_dia = {}
    for t in trades:
        cont_dia.setdefault(t["data"], []).append(t)
    perda_over = 0
    for dia, ts in cont_dia.items():
        if len(ts) > 4:
            perda_over += abs(sum(t["resultado"] for t in ts if t["resultado"] < 0))
    if perda_over > 0:
        vaz["Overtrade"] = perda_over
    return sorted(vaz.items(), key=lambda x: x[1], reverse=True)


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
    "FTSE 100":       "^ftx",
    "Nikkei":         "^nkx",
    "Petróleo WTI":   "cl.f",
    "Ouro":           "gc.f",
}

# Símbolos alternativos para fallback (Yahoo Finance via yfinance-like URL)
STOOQ_ALT = {
    "IBOVESPA":       "bvsp.b",
    "FTSE 100":       "^ftse",
    "Nikkei":         "^n225",
}
CRIPTO_IDS = {
    "Bitcoin":  "bitcoin",
    "Ethereum": "ethereum",
    "Solana":   "solana",
    "BNB":      "binancecoin",
}

def _stooq_csv(sym, timeout=3):
    """Busca CSV do Stooq e retorna dict OHLCV ou None."""
    hdrs = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcvn&h&e=csv"
        r = requests.get(url, headers=hdrs, timeout=timeout)
        lines = r.text.strip().split("\n")
        if len(lines) >= 2:
            cols = lines[1].split(",")
            if len(cols) >= 7:
                def safe(v): return float(v) if v not in ("N/D","","0","N/A") else 0
                open_  = safe(cols[3])
                high   = safe(cols[4])
                low    = safe(cols[5])
                close  = safe(cols[6])
                volume = safe(cols[7]) if len(cols) > 7 else 0
                var    = round(((close - open_) / open_ * 100), 2) if open_ and close else 0
                if close and close > 0:
                    return {"preco": close, "var": var, "open": open_,
                            "high": high, "low": low, "volume": volume}
    except:
        pass
    return None

def _fetch_stooq(nome_sym):
    """Busca UM ativo no Stooq com fallback de símbolo."""
    nome, sym = nome_sym
    # Tenta símbolo principal
    dados = _stooq_csv(sym)
    # Tenta alternativo se falhou
    if not dados and nome in STOOQ_ALT:
        dados = _stooq_csv(STOOQ_ALT[nome])
    return nome, dados

def _fetch_forex():
    """Frankfurter — fallback de câmbio (yfinance é a fonte primária com variações)."""
    hdrs = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(
            "https://api.frankfurter.app/latest?from=USD&to=BRL,EUR,GBP,JPY,CNY,AUD",
            timeout=3, headers=hdrs)
        if r.status_code == 200:
            rates = r.json().get("rates", {})
            return {
                "_Dólar/BRL_fb": {"preco": rates.get("BRL",0), "var": 0},
                "_EUR/USD_fb":   {"preco": round(1/rates["EUR"],5) if rates.get("EUR") else 0, "var": 0},
                "_GBP/USD_fb":   {"preco": round(1/rates["GBP"],5) if rates.get("GBP") else 0, "var": 0},
                "_USD/JPY_fb":   {"preco": rates.get("JPY",0), "var": 0},
                "_AUD/USD_fb":   {"preco": round(1/rates["AUD"],5) if rates.get("AUD") else 0, "var": 0},
                "_USD/CNY_fb":   {"preco": rates.get("CNY",0), "var": 0},
            }
    except:
        pass
    return {}

def _fetch_cripto():
    hdrs = {"User-Agent": "Mozilla/5.0"}
    res = {}
    try:
        ids = ",".join(CRIPTO_IDS.values())
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true",
            timeout=4, headers=hdrs)
        if r.status_code == 200:
            data = r.json()
            for nome, cid in CRIPTO_IDS.items():
                if cid in data:
                    res[nome] = {
                        "preco": data[cid].get("usd",0),
                        "var":   round(data[cid].get("usd_24h_change",0),2),
                        "var_dia": round(data[cid].get("usd_24h_change",0),2),
                    }
    except:
        pass

    # Histórico 1 ano para variações de período (só BTC e ETH p/ não estourar rate-limit)
    for nome in ("Bitcoin", "Ethereum"):
        if nome not in res:
            continue
        try:
            cid = CRIPTO_IDS[nome]
            rh = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=usd&days=365&interval=daily",
                timeout=6, headers=hdrs)
            if rh.status_code == 200:
                precos = [p[1] for p in rh.json().get("prices", [])]
                if precos:
                    vp = _variacoes_periodo(precos)
                    for k in ("var_semana","var_mes","var_ano","max_semana","min_semana",
                              "max_mes","min_mes","max_ano","min_ano"):
                        if vp.get(k) is not None:
                            res[nome][k] = vp[k]
        except:
            pass

    return res

# ── yfinance — fonte robusta com variações por período ────────────────────────
YF_MAP = {
    "IBOVESPA":      "^BVSP",
    "Dólar/BRL":     "BRL=X",
    "EUR/USD":       "EURUSD=X",
    "GBP/USD":       "GBPUSD=X",
    "USD/JPY":       "JPY=X",
    "AUD/USD":       "AUDUSD=X",
    "USD/CNY":       "CNY=X",
    "S&P 500":       "^GSPC",
    "Nasdaq":        "^IXIC",
    "DAX":           "^GDAXI",
    "FTSE 100":      "^FTSE",
    "Nikkei":        "^N225",
    "Petróleo WTI":  "CL=F",
    "Ouro":          "GC=F",
}

def _variacoes_periodo(serie_close, serie_high=None, serie_low=None):
    """Calcula variação %, máxima e mínima por período (dia/semana/mês/ano)."""
    import math
    if serie_close is None or len(serie_close) < 1:
        return {}
    closes = [float(c) for c in serie_close if c is not None and not math.isnan(c)]
    if len(closes) < 1:
        return {}
    highs = [float(h) for h in (serie_high or serie_close) if h is not None and not math.isnan(h)]
    lows  = [float(l) for l in (serie_low  or serie_close) if l is not None and not math.isnan(l)]
    atual = closes[-1]

    def var_n(n):
        if len(closes) > n:
            ref = closes[-(n+1)]
        elif len(closes) >= 2:
            ref = closes[0]
        else:
            return None
        return round((atual - ref) / ref * 100, 2) if ref else None

    def maxmin_n(n):
        jan_h = highs[-(n+1):] if len(highs) > n else highs
        jan_l = lows[-(n+1):]  if len(lows)  > n else lows
        mx = max(jan_h) if jan_h else None
        mn = min(jan_l) if jan_l else None
        return mx, mn

    out = {
        "var_dia":    var_n(1),
        "var_semana": var_n(5),
        "var_mes":    var_n(22),
        "var_ano":    var_n(252),
    }
    for nome, n in [("semana",5), ("mes",22), ("ano",252)]:
        mx, mn = maxmin_n(n)
        out[f"max_{nome}"] = mx
        out[f"min_{nome}"] = mn
    return out

def _fetch_yfinance():
    """Busca índices via yfinance com histórico de 1 ano (p/ variações de período)."""
    out = {}
    try:
        import yfinance as yf
        simbolos = list(YF_MAP.values())
        # 1 ano de histórico para calcular variações de período
        data = yf.download(simbolos, period="1y", interval="1d",
                           progress=False, group_by="ticker", threads=True)
        for nome, sym in YF_MAP.items():
            try:
                df = data[sym] if len(simbolos) > 1 else data
                df = df.dropna()
                if len(df) >= 1:
                    close = float(df["Close"].iloc[-1])
                    open_ = float(df["Open"].iloc[-1])
                    high  = float(df["High"].iloc[-1])
                    low   = float(df["Low"].iloc[-1])
                    vol   = float(df["Volume"].iloc[-1]) if "Volume" in df else 0
                    vars_ = _variacoes_periodo(df["Close"].tolist(),
                                               df["High"].tolist(),
                                               df["Low"].tolist())
                    var = vars_.get("var_dia") or 0
                    if close:
                        d = {"preco": close, "var": var, "open": open_,
                             "high": high, "low": low, "volume": vol}
                        d.update(vars_)
                        out[nome] = d
            except:
                continue
    except:
        pass
    return out

@st.cache_data(ttl=90)
def buscar_cotacoes():
    from concurrent.futures import ThreadPoolExecutor, wait
    resultado = {}

    ex = ThreadPoolExecutor(max_workers=6)
    fut_yf     = ex.submit(_fetch_yfinance)
    fut_forex  = ex.submit(_fetch_forex)
    fut_cripto = ex.submit(_fetch_cripto)

    todas = [fut_yf, fut_forex, fut_cripto]
    done, _ = wait(todas, timeout=14)

    for fut in done:
        try:
            res = fut.result(timeout=0.1)
            if isinstance(res, dict):
                resultado.update({k: v for k, v in res.items() if v and v.get("preco")})
        except:
            pass

    ex.shutdown(wait=False)

    # Câmbio: usa fallback do Frankfurter só para pares que o yfinance não trouxe
    for par in ("Dólar/BRL","EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CNY"):
        fb_key = f"_{par}_fb"
        if par not in resultado and fb_key in resultado:
            resultado[par] = resultado[fb_key]
    # Remove as chaves de fallback
    for k in list(resultado.keys()):
        if k.startswith("_") and k.endswith("_fb"):
            resultado.pop(k, None)

    # WINFUT — espelha IBOV (índice à vista; futuro anda colado)
    if "IBOVESPA" in resultado:
        ibov = resultado["IBOVESPA"]
        resultado["WINFUT"] = dict(ibov)
        resultado["WINFUT"]["aprox"] = True

    # WDOFUT — Dólar × 1000 (mini-dólar)
    if "Dólar/BRL" in resultado:
        dol = resultado["Dólar/BRL"]
        wdo = {
            "preco": round(dol["preco"] * 1000, 1),
            "var":   dol.get("var", 0),
            "open": round(dol.get("open",0)*1000,1) if dol.get("open") else 0,
            "high": round(dol.get("high",0)*1000,1) if dol.get("high") else 0,
            "low":  round(dol.get("low",0)*1000,1) if dol.get("low") else 0,
            "volume": 0, "aprox": True,
        }
        # herda variações % (mesmas do dólar)
        for k in ("var_dia","var_semana","var_mes","var_ano"):
            if k in dol:
                wdo[k] = dol[k]
        # herda max/min de período com escala ×1000
        for k in ("max_semana","min_semana","max_mes","min_mes","max_ano","min_ano"):
            if dol.get(k):
                wdo[k] = round(dol[k]*1000, 1)
        resultado["WDOFUT"] = wdo

    return resultado

# ── NOTÍCIAS — RSS de mercado/economia, busca paralela ───────────────────────
# Feeds ESPECÍFICOS de economia/mercado (não o feed geral que traz política/esporte)
FEEDS_RSS = [
    ("InfoMoney",   "https://www.infomoney.com.br/mercados/feed/"),
    ("InfoMoney",   "https://www.infomoney.com.br/economia/feed/"),
    ("Exame Invest","https://exame.com/invest/feed/"),
    ("Exame Econ.", "https://exame.com/economia/feed/"),
    ("MoneyTimes",  "https://www.moneytimes.com.br/feed/"),
    ("Valor Inv.",  "https://valorinveste.globo.com/rss/valorinveste/"),
    ("InvestingBR", "https://br.investing.com/rss/news_25.rss"),
    ("Suno",        "https://www.suno.com.br/noticias/feed/"),
]

# Categorização por palavras-chave
CATEGORIAS = [
    ("💱 Câmbio",      {"dólar","dollar","câmbio","real","euro","moeda","brl","cambial"}),
    ("📊 Bolsa",       {"ibovespa","ibov","bolsa","ações","ação","pregão","b3","índice"}),
    ("🏦 Economia",    {"selic","copom","juros","ipca","inflação","pib","fiscal","bc","banco central","fed","fomc"}),
    ("🛢️ Commodities",{"petróleo","ouro","minério","commodity","commodities","soja","milho"}),
    ("₿ Cripto",       {"bitcoin","btc","ethereum","cripto","crypto","blockchain"}),
]
# Notícias com esses termos ganham destaque (borda laranja)
TERMOS_QUENTES = {"selic","copom","fed","fomc","ipca","ibge","pib","payroll",
                  "decisão de juros","ata do copom","intervenção","circuit breaker"}

TERMOS_FIN = {
    "ibovespa","ibov","bovespa","b3","bolsa","ações","mercado","índice",
    "dólar","dollar","câmbio","real","brl","cotação","euro","moeda",
    "win","wdo","futuro","futuros","mini-índice","mini-dólar",
    "juros","selic","ipca","inflação","pib","economia","fiscal","copom",
    "fed","fomc","banco central","bcb","taxa básica","payroll",
    "petróleo","ouro","commodity","commodities","minério","soja",
    "bitcoin","btc","ethereum","cripto","blockchain",
    "s&p","nasdaq","dow jones","nikkei","dax","ftse","wall street",
    "alta","baixa","queda","valoriza","desvalori","recua","sobe","cai","dispara",
    "pregão","abertura","fechamento","resultado","lucro","balanço","dividendo",
    "ação","ativo","investimento","investidor","trader","operação","tesouro",
}
TERMOS_REJEITAR = {
    "futebol","gol ","copa","campeonato","jogador","clube","esporte",
    "tênis","roland garros","wimbledon","fórmula 1","motogp","ciclismo","olimp",
    "cantor","música","show","cinema","série","novela","ator","atriz","celebridade",
    "culinária","viagem","turismo","moda","beleza",
    "crime","polícia","acidente","violência","avião","caverna","resgate","morto",
    "djokovic","fonseca","neymar","messi","ronaldo","lebron","caiado","zema","kassab",
}

def _categorizar(texto):
    tl = texto.lower()
    for cat, kws in CATEGORIAS:
        if any(k in tl for k in kws):
            return cat
    return "📰 Mercado"

def _eh_quente(texto):
    tl = texto.lower()
    return any(k in tl for k in TERMOS_QUENTES)

def _parse_data(pub):
    """Converte data RSS em datetime; retorna None se falhar."""
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(pub)
        if dt.tzinfo is None:
            dt = BR_TZ.localize(dt)
        return dt.astimezone(BR_TZ)
    except:
        return None

def _tempo_relativo(dt):
    if not dt:
        return ""
    agora = datetime.now(BR_TZ)
    delta = agora - dt
    seg = delta.total_seconds()
    if seg < 60:     return "agora mesmo"
    if seg < 3600:   return f"há {int(seg//60)} min"
    if seg < 86400:  return f"há {int(seg//3600)} h"
    return dt.strftime("%d/%m %H:%M")

def _limpar_html(texto):
    """Limpa HTML do RSS: desescapa entidades, remove tags, remove rodapé 'The post...'."""
    if not texto:
        return ""
    # Desescapa entidades (&lt; vira <, &amp; vira &, etc) — 2x por segurança
    texto = html_mod.unescape(html_mod.unescape(texto))
    # Remove blocos CDATA
    texto = re.sub(r"<!\[CDATA\[|\]\]>", "", texto)
    # Remove todas as tags HTML
    texto = re.sub(r"<[^>]+>", " ", texto)
    # Remove rodapé padrão do WordPress "The post ... appeared first on ..."
    texto = re.sub(r"The post .*?appeared first on.*", "", texto, flags=re.IGNORECASE|re.DOTALL)
    texto = re.sub(r"The post .*", "", texto, flags=re.IGNORECASE)
    # Normaliza espaços
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def _fetch_feed(fonte_url):
    fonte, feed_url = fonte_url
    out  = []
    hdrs = {"User-Agent": "Mozilla/5.0 (compatible; newsbot/1.0)"}
    try:
        r = requests.get(feed_url, timeout=4, headers=hdrs)
        if r.status_code != 200:
            return out
        root = ET.fromstring(r.content)
        ch   = root.find("channel") or root
        for item in (ch.findall("item") or [])[:12]:
            titulo = _limpar_html(item.findtext("title") or "")
            desc   = _limpar_html(item.findtext("description") or "")[:200]
            link   = (item.findtext("link") or "#").strip()
            pub    = (item.findtext("pubDate") or "").strip()
            if titulo and len(titulo) >= 10:
                out.append({"title": titulo, "desc": desc, "url": link,
                            "fonte": fonte, "pub_raw": pub})
    except:
        pass
    return out

@st.cache_data(ttl=120)
def buscar_noticias_rss(query=""):
    from concurrent.futures import ThreadPoolExecutor, wait
    q_lower = query.strip().lower()
    termos_busca = [t for t in q_lower.split() if len(t) > 2] if q_lower else []

    # Busca todos os feeds EM PARALELO (rápido)
    brutos = []
    ex = ThreadPoolExecutor(max_workers=len(FEEDS_RSS))
    futs = [ex.submit(_fetch_feed, fu) for fu in FEEDS_RSS]
    done, _ = wait(futs, timeout=5)
    for f in done:
        try:
            brutos.extend(f.result(timeout=0.1))
        except:
            pass
    ex.shutdown(wait=False)

    # Filtra, categoriza, deduplica
    vistos = set()
    artigos = []
    for a in brutos:
        titulo = a["title"]
        tit_low = titulo.lower()
        txt_low = tit_low + " " + a["desc"].lower()

        # Dedup por título
        chave = tit_low[:60]
        if chave in vistos:
            continue

        # Rejeita lixo
        if any(t in tit_low for t in TERMOS_REJEITAR):
            continue

        # Filtro de relevância
        if termos_busca:
            if not any(t in txt_low for t in termos_busca):
                continue
        else:
            if not any(t in txt_low for t in TERMOS_FIN):
                continue

        vistos.add(chave)
        dt = _parse_data(a["pub_raw"])
        artigos.append({
            "title":    titulo,
            "desc":     a["desc"],
            "url":      a["url"],
            "fonte":    a["fonte"],
            "cat":      _categorizar(txt_low),
            "quente":   _eh_quente(txt_low),
            "dt":       dt,
            "tempo":    _tempo_relativo(dt),
        })

    # Ordena por data (mais recente primeiro)
    artigos.sort(key=lambda x: x["dt"] or datetime.min.replace(tzinfo=BR_TZ), reverse=True)

    # Fallback NewsAPI
    if not artigos:
        try:
            q = query or "Ibovespa B3 dólar mercado futuro"
            url = f"https://newsapi.org/v2/everything?q={q}&language=pt&sortBy=publishedAt&pageSize=12&apiKey={NEWS_KEY}"
            r = requests.get(url, timeout=6)
            for n in r.json().get("articles", []):
                t = n.get("title","")
                if t and not any(x in t.lower() for x in TERMOS_REJEITAR):
                    artigos.append({
                        "title": t, "desc": (n.get("description") or "")[:200],
                        "url": n.get("url","#"), "fonte": n.get("source",{}).get("name",""),
                        "cat": "📰 Mercado", "quente": False, "dt": None,
                        "tempo": n.get("publishedAt","")[:16],
                    })
        except:
            pass

    return artigos[:15]

# ══════════════════════════════════════════════════════════════════════════════
# CALENDÁRIO ECONÔMICO — eventos macro que afetam WIN/WDO
# ══════════════════════════════════════════════════════════════════════════════
# Datas oficiais de 2026 (COPOM e FOMC são divulgadas com antecedência)
COPOM_2026 = ["2026-01-28","2026-03-18","2026-05-06","2026-06-17",
              "2026-07-29","2026-09-16","2026-11-04","2026-12-09"]
FOMC_2026  = ["2026-01-28","2026-03-18","2026-04-29","2026-06-17",
              "2026-07-29","2026-09-16","2026-11-04","2026-12-16"]

def _primeira_sexta(ano, mes):
    d = date(ano, mes, 1)
    while d.weekday() != 4:  # 4 = sexta
        d += timedelta(days=1)
    return d

def gerar_calendario(dias_a_frente=14):
    """Gera eventos macro dos próximos N dias com impacto classificado."""
    hoje = datetime.now(BR_TZ).date()
    fim  = hoje + timedelta(days=dias_a_frente)
    eventos = []

    def add(d, hora, pais, nome, impacto, win, wdo):
        if hoje <= d <= fim:
            eventos.append({"data": d, "hora": hora, "pais": pais, "nome": nome,
                            "impacto": impacto, "win": win, "wdo": wdo})

    # Varre cada mês no intervalo
    meses = set()
    d = hoje
    while d <= fim:
        meses.add((d.year, d.month))
        d += timedelta(days=1)

    for ano, mes in meses:
        # Payroll EUA — 1ª sexta, 9h30 (Brasília)
        pf = _primeira_sexta(ano, mes)
        add(pf, "09:30", "🇺🇸", "Payroll (Nonfarm Payrolls)", "alto",
            "Volatilidade forte, define humor do dia", "Forte impacto no dólar")
        # CPI EUA — ~dia 12
        add(date(ano, mes, 12), "09:30", "🇺🇸", "CPI — Inflação EUA", "alto",
            "Afeta via expectativa de juros do Fed", "Dólar reage forte")
        # IPCA Brasil — ~dia 10
        add(date(ano, mes, 10), "09:00", "🇧🇷", "IPCA — Inflação Brasil", "alto",
            "Define expectativa da Selic", "Impacta o real")
        # IPCA-15 — ~dia 25
        add(date(ano, mes, 25), "09:00", "🇧🇷", "IPCA-15 (prévia)", "medio",
            "Prévia da inflação", "Impacto moderado no real")

    # COPOM e FOMC (decisão de juros — sempre alto impacto)
    for ds in COPOM_2026:
        d = datetime.strptime(ds, "%Y-%m-%d").date()
        add(d, "18:30", "🇧🇷", "Decisão COPOM (Selic)", "alto",
            "Define direção da bolsa", "Forte impacto no real")
    for ds in FOMC_2026:
        d = datetime.strptime(ds, "%Y-%m-%d").date()
        add(d, "15:00", "🇺🇸", "Decisão FOMC (Fed)", "alto",
            "Move bolsas globais", "Dólar reage forte")

    eventos.sort(key=lambda e: (e["data"], e["hora"]))
    return eventos

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

# ── GOOGLE ANALYTICS (rastreamento de acessos) ───────────────────────────────
def injetar_analytics():
    try:
        ga_id = st.secrets.get("GA_ID", "")
    except Exception:
        ga_id = ""
    if not ga_id:
        return
    ga_code = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{ga_id}');
    </script>
    """
    st.components.v1.html(ga_code, height=0)

injetar_analytics()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,[data-testid="stAppViewContainer"]{background:#0a0e1a!important;color:#e2e8f0!important;font-family:'Space Grotesk',sans-serif!important}
[data-testid="stSidebar"],[data-testid="stHeader"]{display:none!important}
.block-container{padding:0!important;max-width:100%!important}
/* Compacta o espaço vertical entre blocos do Streamlit */
[data-testid="stVerticalBlock"]{gap:.5rem!important}
[data-testid="stElementContainer"]{margin:0!important}
.main-wrap [data-testid="stMarkdownContainer"] p{margin:0!important}
/* Limita a largura útil do app (evita campos esticados em tela larga) */
[data-testid="stMainBlockContainer"],[data-testid="stAppViewBlockContainer"],
section.main > div.block-container,.main .block-container,
[data-testid="block-container"]{max-width:1100px!important;margin:0 auto!important;padding:.6rem 1.2rem!important}
/* Compacta inputs, selects e textareas */
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stDateInput"] input,
[data-baseweb="select"]{min-height:34px!important;font-size:.85rem!important}
[data-testid="stTextInput"],[data-testid="stNumberInput"],[data-testid="stSelectbox"],[data-testid="stDateInput"]{margin-bottom:.2rem!important}
/* Labels menores e mais justos */
[data-testid="stWidgetLabel"] p{font-size:.78rem!important;margin-bottom:.1rem!important}
/* Botões mais compactos */
[data-testid="stButton"] button{padding:.35rem .9rem!important;font-size:.85rem!important}

/* ── COMPACTAÇÃO AGRESSIVA DAS GRADES ── */
/* Grade de cotações mais densa */
.grade-row{gap:.35rem!important;margin-bottom:.2rem!important}
.grade-cel{padding:.4rem .6rem!important}
.grade-grupo-label{margin:.45rem 0 .25rem!important}
/* Cards de scroll/notícias mais justos */
.noticia-card{padding:.6rem .8rem!important;margin-bottom:.4rem!important}
/* Reduz respiro das colunas */
[data-testid="stHorizontalBlock"]{gap:.6rem!important}
/* Espaço entre seções markdown ainda menor */
.sec-title{margin:.6rem 0 .35rem!important}
.sec-divider{margin:.45rem 0!important}
/* Checkbox e radio mais compactos */
[data-testid="stCheckbox"],[data-testid="stRadio"]{margin-bottom:.1rem!important}
[data-testid="stRadio"] label{font-size:.82rem!important}

/* ── TICKER TAPE ── */
.ticker-wrap{
    width:100%;background:#0b1120;border-bottom:1px solid #1e293b;
    overflow:hidden;padding:0;height:32px;display:flex;align-items:center;
    position:sticky;top:0;z-index:999;
}
.ticker-label{
    flex-shrink:0;background:#0066ff;color:#fff;font-size:.7rem;font-weight:700;
    padding:0 .9rem;height:100%;display:flex;align-items:center;gap:.3rem;letter-spacing:.05em;
    white-space:nowrap;font-family:'JetBrains Mono',monospace;
    position:relative;z-index:2;
    box-shadow:6px 0 12px rgba(11,17,32,.95);
}
.ticker-live-dot{width:7px;height:7px;border-radius:50%;background:#fff;
    animation:live-pulse 1.4s ease-in-out infinite}
@keyframes live-pulse{0%,100%{opacity:1}50%{opacity:.3}}
.ticker-viewport{flex:1;overflow:hidden;position:relative;z-index:1}
.ticker-track{
    display:flex;gap:0;white-space:nowrap;
    animation:ticker-scroll 60s linear infinite;
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
.main-wrap{padding:.8rem 1.2rem;max-width:1500px;margin:0 auto}

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

/* ── GRADE DE COTAÇÕES (estilo Profit) ── */
.grade-wrap{margin-bottom:.5rem}
.grade-grupo-label{font-size:.68rem;font-weight:700;color:#64748b;text-transform:uppercase;
    letter-spacing:.08em;margin:.7rem 0 .35rem}
.grade-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.4rem;margin-bottom:.3rem}
.grade-cel{border-radius:8px;padding:.5rem .7rem;border:1px solid transparent;
    display:flex;flex-direction:column;gap:.1rem;transition:all .15s}
.grade-cel:hover{transform:translateY(-1px);filter:brightness(1.15)}
.grade-up{background:rgba(34,197,94,.12);border-color:rgba(34,197,94,.35)}
.grade-dn{background:rgba(239,68,68,.12);border-color:rgba(239,68,68,.35)}
.grade-nt{background:#0f172a;border-color:#1e293b}
.grade-nome{font-size:.64rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.03em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.grade-preco{font-size:1.05rem;font-weight:700;color:#f1f5f9;font-family:'JetBrains Mono',monospace;line-height:1.1}
.grade-up .grade-var{font-size:.72rem;font-weight:700;color:#22c55e;font-family:'JetBrains Mono',monospace}
.grade-dn .grade-var{font-size:.72rem;font-weight:700;color:#ef4444;font-family:'JetBrains Mono',monospace}
.grade-nt .grade-var{font-size:.72rem;font-weight:600;color:#64748b}

/* ── TABELA DE PERÍODO ── */
.tab-periodo{width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace}
.tab-periodo th{font-size:.62rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;
    font-weight:600;padding:.35rem .5rem;text-align:center;border-bottom:1px solid #1e293b}
.tab-periodo th:first-child{text-align:left}
.tab-periodo td{font-size:.82rem;font-weight:700;padding:.4rem .5rem;text-align:center;border-bottom:1px solid rgba(255,255,255,.04)}
.tab-periodo .tp-lbl{font-size:.66rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.04em;text-align:left;font-family:'Space Grotesk',sans-serif}
.tab-periodo tr:last-child td{border-bottom:none}

/* ── UTILITÁRIOS ── */
.sec-title{font-size:1rem;font-weight:700;color:#f1f5f9;margin:.8rem 0 .5rem;display:flex;align-items:center;gap:.5rem}
.sec-divider{height:1px;background:#1e293b;margin:.6rem 0}
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
    "IBOVESPA", "WINFUT", "WDOFUT",
    "S&P 500", "Nasdaq", "DAX", "Nikkei",
    "Petróleo WTI", "Ouro",
    "Dólar/BRL", "EUR/USD", "GBP/USD", "USD/JPY",
    "Bitcoin", "Ethereum",
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
  <div class="ticker-label"><span class="ticker-live-dot"></span>LIVE</div>
  <div class="ticker-viewport"><div class="ticker-track">{items_html}{items_html}</div></div>
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

db_init()

# Conta 1 acesso por sessão (visita única)
if "acesso_contado" not in st.session_state:
    try:
        db_registrar_acesso()
    except Exception:
        pass
    st.session_state.acesso_contado = True

tab1, tab2, tab3, tab4 = st.tabs([
    "🌍  Mercados & Notícias",
    "🛡️  Gerenciamento de Risco",
    "🤖  Chat com o Mestre",
    "📒  Diário & Score",
])

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

    # ── GRADE DE COTAÇÕES estilo Profit (mapa de mercado) ────────────────────
    st.markdown('<div class="sec-title">📊 Cotações</div>', unsafe_allow_html=True)

    GRUPOS_GRADE = [
        ("🇧🇷 Brasil",     ["WINFUT", "WDOFUT"]),
        ("🌎 Global",      ["S&P 500", "Nasdaq", "DAX", "Nikkei"]),
        ("🛢️ Commodities",["Petróleo WTI", "Ouro"]),
        ("💱 Forex",       ["Dólar/BRL", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CNY"]),
        ("₿ Cripto",       ["Bitcoin", "Ethereum", "Solana", "BNB"]),
    ]

    def celula_grade(nome, dados):
        p = dados.get("preco", 0) if dados else 0
        v = dados.get("var",   0) if dados else 0
        if not p:
            return f'''<div class="grade-cel grade-nt">
                <div class="grade-nome">{nome}</div>
                <div class="grade-preco">—</div>
                <div class="grade-var">s/ dado</div></div>'''
        cls = "grade-up" if v > 0 else "grade-dn" if v < 0 else "grade-nt"
        seta = "▲" if v > 0 else "▼" if v < 0 else "—"
        return f'''<div class="grade-cel {cls}">
            <div class="grade-nome">{nome}</div>
            <div class="grade-preco">{fmt_preco(p)}</div>
            <div class="grade-var">{seta} {abs(v):.2f}%</div></div>'''

    grade_html = '<div class="grade-wrap">'
    for gnome, ativos_g in GRUPOS_GRADE:
        grade_html += f'<div class="grade-grupo-label">{gnome}</div><div class="grade-row">'
        grade_html += "".join(celula_grade(a, cotacoes.get(a)) for a in ativos_g)
        grade_html += '</div>'
    grade_html += '</div>'
    st.markdown(grade_html, unsafe_allow_html=True)

    # ── DETALHE expandido (abertura/máxima/mínima/volume) ────────────────────
    st.markdown('<div class="sec-title" style="font-size:.95rem;margin-top:1rem">🔍 Detalhe do Ativo</div>', unsafe_allow_html=True)
    TODOS_ATIVOS_LISTA = [
        "WINFUT", "WDOFUT", "IBOVESPA",
        "S&P 500", "Nasdaq", "DAX", "FTSE 100", "Nikkei",
        "Petróleo WTI", "Ouro",
        "Dólar/BRL", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CNY",
        "Bitcoin", "Ethereum", "Solana", "BNB",
    ]
    col_sel, _ = st.columns([2, 3])
    with col_sel:
        ativo_detalhe = st.selectbox("Escolha o ativo", TODOS_ATIVOS_LISTA, label_visibility="collapsed")

    dados_d = cotacoes.get(ativo_detalhe, {})
    preco_d = dados_d.get("preco", 0)
    var_d   = dados_d.get("var",   0)
    open_d  = dados_d.get("open",  0)
    high_d  = dados_d.get("high",  0)
    low_d   = dados_d.get("low",   0)
    vol_d   = dados_d.get("volume",0)

    if preco_d:
        cor_var = "#22c55e" if var_d > 0 else "#ef4444" if var_d < 0 else "#94a3b8"
        seta    = "▲" if var_d > 0 else "▼" if var_d < 0 else "—"
        vol_fmt = f"{vol_d:,.0f}".replace(",",".") if vol_d else "—"

        def cel_var(v):
            if v is None:
                return '<span style="color:#475569">—</span>'
            cor = "#22c55e" if v > 0 else "#ef4444" if v < 0 else "#94a3b8"
            s = "▲" if v > 0 else "▼" if v < 0 else "—"
            return f'<span style="color:{cor}">{s} {abs(v):.2f}%</span>'

        def cel_val(v, cor="#f1f5f9"):
            return f'<span style="color:{cor}">{fmt_preco(v)}</span>' if v else '<span style="color:#475569">—</span>'

        # Tabela: linhas = Variação / Máxima / Mínima | colunas = Dia/Semana/Mês/Ano
        tabela = f"""
        <table class="tab-periodo">
          <thead><tr><th></th><th>Dia</th><th>Semana</th><th>Mês</th><th>Ano</th></tr></thead>
          <tbody>
            <tr>
              <td class="tp-lbl">Variação</td>
              <td>{cel_var(dados_d.get("var_dia"))}</td>
              <td>{cel_var(dados_d.get("var_semana"))}</td>
              <td>{cel_var(dados_d.get("var_mes"))}</td>
              <td>{cel_var(dados_d.get("var_ano"))}</td>
            </tr>
            <tr>
              <td class="tp-lbl">Máxima</td>
              <td>{cel_val(high_d, "#22c55e")}</td>
              <td>{cel_val(dados_d.get("max_semana"), "#22c55e")}</td>
              <td>{cel_val(dados_d.get("max_mes"), "#22c55e")}</td>
              <td>{cel_val(dados_d.get("max_ano"), "#22c55e")}</td>
            </tr>
            <tr>
              <td class="tp-lbl">Mínima</td>
              <td>{cel_val(low_d, "#ef4444")}</td>
              <td>{cel_val(dados_d.get("min_semana"), "#ef4444")}</td>
              <td>{cel_val(dados_d.get("min_mes"), "#ef4444")}</td>
              <td>{cel_val(dados_d.get("min_ano"), "#ef4444")}</td>
            </tr>
          </tbody>
        </table>
        """

        st.markdown(f"""
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:1rem 1.3rem;margin-bottom:1rem">
          <div style="display:flex;align-items:baseline;gap:1rem;flex-wrap:wrap;margin-bottom:.9rem">
            <div style="font-size:1.6rem;font-weight:700;color:#f1f5f9;font-family:'JetBrains Mono',monospace">{fmt_preco(preco_d)}</div>
            <div style="font-size:.95rem;font-weight:700;color:{cor_var}">{seta} {abs(var_d):.2f}%</div>
            <div style="font-size:.78rem;color:#475569;margin-left:auto">{ativo_detalhe}</div>
          </div>
          {tabela}
          <div style="display:flex;gap:1.5rem;margin-top:.8rem;font-size:.78rem;color:#94a3b8">
            <div>Abertura: <b style="color:#f1f5f9;font-family:'JetBrains Mono',monospace">{fmt_preco(open_d) if open_d else '—'}</b></div>
            <div>Volume: <b style="color:#f1f5f9;font-family:'JetBrains Mono',monospace">{vol_fmt}</b></div>
          </div>
          {'<div style="font-size:.66rem;color:#475569;margin-top:.6rem">≈ valor de referência (WINFUT ~ IBOV à vista · WDOFUT ~ Dólar×1000). Máx/Mín do dia atualizam no pregão.</div>' if dados_d.get("aprox") else ''}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:1rem 1.3rem;color:#475569;font-size:.83rem;margin-bottom:1rem">⏳ Aguardando dados de <b>{ativo_detalhe}</b>… Clique em Atualizar.</div>', unsafe_allow_html=True)

    # ── NOTÍCIAS ──────────────────────────────────────────────────────────────
    # ── CALENDÁRIO ECONÔMICO ──────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div><div class="sec-title">📅 Calendário Econômico — Próximos 14 dias</div>', unsafe_allow_html=True)
    eventos = gerar_calendario(14)
    if not eventos:
        st.markdown('<div style="color:#475569;font-size:.83rem;padding:.5rem 0">Sem eventos macro relevantes nos próximos dias.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="display:flex;gap:1rem;font-size:.7rem;color:#64748b;margin-bottom:.6rem">🔴 Alto impacto &nbsp; 🟡 Médio &nbsp; 🟢 Baixo</div>', unsafe_allow_html=True)
        hoje_d = datetime.now(BR_TZ).date()
        cal_html = ""
        for e in eventos:
            cor_imp = {"alto":"#ef4444","medio":"#f59e0b","baixo":"#22c55e"}[e["impacto"]]
            bola = {"alto":"🔴","medio":"🟡","baixo":"🟢"}[e["impacto"]]
            dia_lbl = "HOJE" if e["data"] == hoje_d else ("AMANHÃ" if e["data"] == hoje_d + timedelta(days=1) else e["data"].strftime("%d/%m"))
            destaque = "background:rgba(239,68,68,.07);" if (e["data"] == hoje_d and e["impacto"]=="alto") else ""
            cal_html += (
                f'<div style="background:#0f172a;{destaque}border:1px solid #1e293b;border-left:3px solid {cor_imp};border-radius:8px;padding:.6rem .9rem;margin-bottom:.4rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem">'
                f'<div style="font-size:.84rem;color:#f1f5f9;font-weight:600">{bola} {e["pais"]} {e["nome"]}</div>'
                f'<div style="font-size:.75rem;color:#94a3b8;font-family:\'JetBrains Mono\',monospace">{dia_lbl} · {e["hora"]}</div>'
                f'</div>'
                f'<div style="display:flex;gap:1.2rem;margin-top:.35rem;font-size:.7rem;color:#64748b;flex-wrap:wrap">'
                f'<span>📊 WIN: {e["win"]}</span><span>💵 WDO: {e["wdo"]}</span>'
                f'</div></div>'
            )
        st.markdown(cal_html, unsafe_allow_html=True)

    # ── CALENDÁRIO ECONÔMICO ──────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div><div class="sec-title">📅 Calendário Econômico — Próximos Eventos</div>', unsafe_allow_html=True)
    eventos = calendario_proximos(14)
    if not eventos:
        st.markdown('<div style="color:#475569;font-size:.83rem;padding:.5rem 0">Sem eventos relevantes nos próximos 14 dias.</div>', unsafe_allow_html=True)
    else:
        hoje_str = datetime.now(BR_TZ).strftime("%Y-%m-%d")
        cor_imp = {"alto":"#ef4444","medio":"#f59e0b","baixo":"#22c55e"}
        lbl_imp = {"alto":"🔴 ALTO","medio":"🟡 MÉDIO","baixo":"🟢 BAIXO"}
        for e in eventos:
            imp = e.get("impacto","medio")
            c = cor_imp.get(imp, "#f59e0b")
            d_obj = datetime.strptime(e["data"], "%Y-%m-%d")
            data_fmt = d_obj.strftime("%d/%m")
            dia_semana = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"][d_obj.weekday()]
            eh_hoje = e["data"] == hoje_str
            badge_hoje = '<span style="background:#0066ff;color:#fff;border-radius:4px;padding:.1rem .4rem;font-size:.6rem;font-weight:700;margin-left:.4rem">HOJE</span>' if eh_hoje else ''
            ev = html_mod.escape(e["evento"])
            win = html_mod.escape(e.get("win",""))
            wdo = html_mod.escape(e.get("wdo",""))
            card_cal = (
                f'<div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid {c};border-radius:8px;padding:.6rem .9rem;margin-bottom:.4rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.4rem">'
                f'<div style="font-size:.85rem;color:#f1f5f9;font-weight:600">{e["pais"]} {ev}{badge_hoje}</div>'
                f'<div style="display:flex;gap:.6rem;align-items:center">'
                f'<span style="font-size:.7rem;color:#94a3b8;font-family:\'JetBrains Mono\',monospace">{dia_semana} {data_fmt} · {e["hora"]}</span>'
                f'<span style="font-size:.6rem;font-weight:700;color:{c}">{lbl_imp.get(imp,"")}</span>'
                f'</div></div>'
                f'<div style="display:flex;gap:1.2rem;margin-top:.4rem;font-size:.7rem;color:#64748b;flex-wrap:wrap">'
                f'<span>📊 <b style="color:#94a3b8">WIN:</b> {win}</span>'
                f'<span>💱 <b style="color:#94a3b8">WDO:</b> {wdo}</span>'
                f'</div></div>'
            )
            st.markdown(card_cal, unsafe_allow_html=True)
        st.markdown('<div style="font-size:.66rem;color:#475569;margin-top:.3rem">Datas COPOM/FOMC oficiais. Payroll, CPI e IPCA são estimativas recorrentes — confirme o horário exato no dia.</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-divider"></div><div class="sec-title">📺 Central de Notícias — Mercado ao Vivo</div>', unsafe_allow_html=True)
    col_busca, col_btn2 = st.columns([5,1])
    with col_busca:
        query_n = st.text_input("", placeholder="Filtrar: Ibovespa, dólar, WIN, juros, selic…", label_visibility="collapsed")
    with col_btn2:
        st.button("🔍 Buscar")

    with st.spinner("Carregando notícias…"):
        noticias = buscar_noticias_rss(query_n)

    if not noticias:
        st.markdown('<div style="color:#475569;font-size:.83rem;padding:.8rem 0">Nenhuma notícia encontrada. Tente outro termo.</div>', unsafe_allow_html=True)
    else:
        # ── DESTAQUES DO DIA (manchetes quentes) ──────────────────────────────
        if not query_n:
            destaques = [n for n in noticias if n.get("quente")][:3]
            if destaques:
                cards_dest = ""
                for n in destaques:
                    t = html_mod.escape(n.get("title",""))
                    u = n.get("url","#")
                    f = n.get("fonte","")
                    cat = n.get("cat","📰")
                    cards_dest += f"""<a href="{u}" target="_blank" style="text-decoration:none;flex:1;min-width:220px">
                        <div style="background:linear-gradient(135deg,#1a1408,#0f0c04);border:1px solid rgba(245,158,11,.35);border-left:3px solid #f59e0b;border-radius:10px;padding:.7rem .9rem;height:100%;transition:all .2s">
                          <div style="font-size:.6rem;color:#fbbf24;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.35rem">🔥 {f} · {cat}</div>
                          <div style="font-size:.82rem;font-weight:600;color:#f1f5f9;line-height:1.35">{t}</div>
                        </div></a>"""
                st.markdown('<div class="sec-title" style="font-size:.95rem;margin-top:.3rem">🔥 Destaques do Dia</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:1rem">{cards_dest}</div>', unsafe_allow_html=True)
                st.markdown('<div class="sec-title" style="font-size:.95rem">📰 Todas as Notícias</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="font-size:.72rem;color:#475569;margin-bottom:.6rem">🔴 {len(noticias)} notícias · atualiza a cada 2 min</div>', unsafe_allow_html=True)
        for n in noticias:
            t = html_mod.escape(n.get("title",""))
            d = html_mod.escape(n.get("desc",""))
            u = n.get("url","#")
            f = n.get("fonte","")
            cat = n.get("cat","📰 Mercado")
            tempo = n.get("tempo","")
            quente = n.get("quente", False)

            borda = "border-left:3px solid #f59e0b" if quente else ""
            badge_quente = '<span style="background:rgba(245,158,11,.18);border:1px solid rgba(245,158,11,.4);border-radius:4px;padding:.12rem .45rem;font-size:.62rem;color:#fbbf24;font-weight:700;margin-left:.4rem">🔥 QUENTE</span>' if quente else ''

            st.markdown(f"""
            <div class="noticia-card" style="{borda}">
              <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.35rem;flex-wrap:wrap">
                <span class="noticia-fonte">{f}</span>
                <span style="font-size:.65rem;color:#64748b;font-weight:600">{cat}</span>
                {badge_quente}
              </div>
              <div class="noticia-titulo">{t}</div>
              {'<div class="noticia-desc">'+d+'</div>' if d else ''}
              <div style="display:flex;justify-content:space-between;margin-top:.45rem;align-items:center">
                <div class="noticia-meta">🕐 {tempo}</div>
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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DIÁRIO & SCORE
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    # ── CADEADO: diário privado até implementarmos login por usuário ──────────
    if "diario_liberado" not in st.session_state:
        st.session_state.diario_liberado = False

    if not st.session_state.diario_liberado:
        st.markdown('<div class="sec-title" style="margin-top:.3rem">🔒 Área Privada — Diário & Score</div>', unsafe_allow_html=True)
        st.markdown('<div style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:1rem;color:#94a3b8;font-size:.88rem;line-height:1.6">'
                    '📒 O Diário de Operações e o Score de Trader são pessoais.<br>'
                    '<b style="color:#60a5fa">Em breve liberado para todos os usuários</b>, cada um com seu diário privado e login individual.<br>'
                    'Por enquanto, esta área é restrita.</div>', unsafe_allow_html=True)
        senha = st.text_input("Senha de acesso", type="password", key="senha_diario")
        if st.button("🔓  Entrar"):
            try:
                senha_correta = st.secrets["DIARIO_SENHA"]
            except Exception:
                senha_correta = "mestre2026"  # fallback se não configurar nos secrets
            if senha == senha_correta:
                st.session_state.diario_liberado = True
                st.rerun()
            else:
                st.error("Senha incorreta.")

if st.session_state.get("diario_liberado"):
  with tab4:
    # ── CONTADOR DE ACESSOS (visível só na área restrita) ─────────────────────
    try:
        ac = db_stats_acessos()
        st.markdown(
            f'<div style="display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:.3rem">'
            f'<div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:1px solid #1e3a8a;border-radius:10px;padding:.55rem .9rem;min-width:130px">'
            f'<div style="font-size:.58rem;color:#60a5fa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.1rem">👥 Acessos totais</div>'
            f'<div style="font-size:1.3rem;font-weight:700;color:#f1f5f9;font-family:\'JetBrains Mono\',monospace">{ac["total"]:,}</div></div>'
            f'<div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:1px solid #1e3a8a;border-radius:10px;padding:.55rem .9rem;min-width:130px">'
            f'<div style="font-size:.58rem;color:#60a5fa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.1rem">📅 Acessos hoje</div>'
            f'<div style="font-size:1.3rem;font-weight:700;color:#f1f5f9;font-family:\'JetBrains Mono\',monospace">{ac["hoje"]:,}</div></div>'
            f'</div>',
            unsafe_allow_html=True)
        st.markdown('<div style="font-size:.6rem;color:#475569;margin:.1rem 0 .6rem">Contagem por sessão. Permanente com o login (em breve).</div>', unsafe_allow_html=True)
    except Exception:
        pass

    sub_reg, sub_stats = st.columns([1, 1])

    # ── REGISTRAR OPERAÇÃO ────────────────────────────────────────────────────
    with sub_reg:
        st.markdown('<div class="sec-title" style="margin-top:.3rem">✍️ Registrar Operação</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            r_data    = st.date_input("Data", value=datetime.now(BR_TZ).date(), format="DD/MM/YYYY")
            r_ativo   = st.selectbox("Ativo", ["WIN", "WDO"])
            r_direcao = st.selectbox("Direção", ["Compra", "Venda"])
            r_hora    = st.selectbox("Horário", ["9h-10h","10h-11h","11h-12h","12h-14h","14h-16h","16h-18h"])
        with c2:
            r_contratos = st.number_input("Contratos", min_value=1, max_value=50, value=1, step=1)
            r_tipo      = st.radio("Resultado", ["🟢 Gain", "🔴 Loss"], horizontal=True)
            r_pontos_abs = st.number_input("Pontos", min_value=0.0, value=0.0, step=5.0, format="%.1f")
            r_seguiu    = st.checkbox("Segui meu setup", value=True)
            r_esticou   = st.checkbox("Estiquei o stop", value=False)

        r_obs = st.text_input("Observação (opcional)", placeholder="Ex: entrei no rompimento da máxima…")

        # Aplica sinal conforme Gain/Loss
        r_pontos = r_pontos_abs if r_tipo == "🟢 Gain" else -r_pontos_abs

        # Calcula resultado em R$ pelo multiplicador B3
        val_pt = MULT["WDO" if r_ativo == "WDO" else "WIN"]
        r_resultado = r_pontos * r_contratos * val_pt
        cor_prev = "#22c55e" if r_resultado > 0 else "#ef4444" if r_resultado < 0 else "#94a3b8"
        st.markdown(f'<div style="font-size:.85rem;color:#94a3b8;margin:.3rem 0">Resultado calculado: <b style="color:{cor_prev};font-family:\'JetBrains Mono\',monospace">R$ {r_resultado:,.2f}</b></div>', unsafe_allow_html=True)

        if st.button("💾  Salvar Operação"):
            db_add_trade({
                "data": r_data.strftime("%Y-%m-%d"),
                "ativo": r_ativo, "direcao": r_direcao,
                "contratos": int(r_contratos), "pontos": float(r_pontos),
                "resultado": float(r_resultado),
                "seguiu_setup": 1 if r_seguiu else 0,
                "esticou_stop": 1 if r_esticou else 0,
                "hora": r_hora, "obs": r_obs,
            })
            st.success("Operação registrada!")
            st.rerun()

    # ── SCORE ─────────────────────────────────────────────────────────────────
    with sub_stats:
        periodo = st.selectbox("Período de análise", ["Últimos 30 dias","Últimos 7 dias","Últimos 90 dias","Tudo"], key="periodo_stats")
        dias_map = {"Últimos 7 dias":7,"Últimos 30 dias":30,"Últimos 90 dias":90,"Tudo":3650}
        trades = db_trades_periodo(dias_map[periodo])
        stats  = calcular_estatisticas(trades)
        score  = calcular_score(stats) if stats else None

        st.markdown('<div class="sec-title" style="margin-top:.3rem">🏆 Score de Trader</div>', unsafe_allow_html=True)
        if score:
            cor_geral = "#22c55e" if score["geral"] >= 75 else "#f59e0b" if score["geral"] >= 50 else "#ef4444"
            def barra(lbl, val):
                cor = "#22c55e" if val >= 75 else "#f59e0b" if val >= 50 else "#ef4444"
                return f'''<div style="margin-bottom:.5rem">
                    <div style="display:flex;justify-content:space-between;font-size:.78rem;margin-bottom:.2rem">
                        <span style="color:#94a3b8">{lbl}</span><span style="color:{cor};font-weight:700;font-family:'JetBrains Mono',monospace">{val}</span>
                    </div>
                    <div style="background:#0a0e1a;border-radius:6px;height:7px;overflow:hidden">
                        <div style="width:{val}%;height:100%;background:{cor};border-radius:6px"></div>
                    </div></div>'''
            st.markdown(f"""
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:1.2rem 1.4rem">
              <div style="text-align:center;margin-bottom:1rem">
                <div style="font-size:2.6rem;font-weight:700;color:{cor_geral};font-family:'JetBrains Mono',monospace;line-height:1">{score['geral']}<span style="font-size:1rem;color:#475569">/100</span></div>
                <div style="font-size:.7rem;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-top:.3rem">Score Geral</div>
              </div>
              {barra("Gestão de risco", score["gestao"])}
              {barra("Disciplina", score["disciplina"])}
              {barra("Assertividade", score["assertividade"])}
              {barra("Risco/Retorno", score["risco_retorno"])}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:1.2rem;color:#475569;font-size:.85rem">Registre pelo menos 3 operações para gerar seu Score.</div>', unsafe_allow_html=True)

    # ── PAINEL DE ESTATÍSTICAS ────────────────────────────────────────────────
    if stats:
        st.markdown('<div class="sec-divider"></div><div class="sec-title">📊 Estatísticas — ' + periodo + '</div>', unsafe_allow_html=True)
        cor_lucro = "#22c55e" if stats["lucro_total"] >= 0 else "#ef4444"
        cols = st.columns(4)
        metricas = [
            ("Resultado", f"R$ {stats['lucro_total']:,.2f}", cor_lucro),
            ("Assertividade", f"{stats['assertividade']:.1f}%", "#f1f5f9"),
            ("Profit Factor", f"{stats['profit_factor']:.2f}", "#22c55e" if stats['profit_factor']>=1.5 else "#f59e0b"),
            ("Operações", f"{stats['n']}", "#f1f5f9"),
        ]
        for col, (lbl, val, cor) in zip(cols, metricas):
            col.markdown(f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:.8rem 1rem"><div style="font-size:.62rem;color:#475569;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.25rem">{lbl}</div><div style="font-size:1.15rem;font-weight:700;color:{cor};font-family:\'JetBrains Mono\',monospace">{val}</div></div>', unsafe_allow_html=True)

        cols2 = st.columns(4)
        metricas2 = [
            ("Melhor dia", f"R$ {stats['melhor_dia']:,.2f}", "#22c55e"),
            ("Pior dia", f"R$ {stats['pior_dia']:,.2f}", "#ef4444"),
            ("Ganhos / Perdas", f"{stats['n_ganhos']} / {stats['n_perdas']}", "#f1f5f9"),
            ("R/R médio", f"1:{stats['rr_medio']:.1f}", "#f1f5f9"),
        ]
        for col, (lbl, val, cor) in zip(cols2, metricas2):
            col.markdown(f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:.8rem 1rem;margin-top:.5rem"><div style="font-size:.62rem;color:#475569;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.25rem">{lbl}</div><div style="font-size:1.15rem;font-weight:700;color:{cor};font-family:\'JetBrains Mono\',monospace">{val}</div></div>', unsafe_allow_html=True)

        # ── DIAGNÓSTICO AUTOMÁTICO ────────────────────────────────────────────
        if score:
            diag = gerar_diagnostico(stats, score)
            st.markdown('<div class="sec-title" style="font-size:.95rem;margin-top:1rem">🩺 Diagnóstico do Trader</div>', unsafe_allow_html=True)

            def bloco_diag(titulo, itens, cor, bg):
                if not itens:
                    return ""
                linhas = "".join(f'<div style="font-size:.8rem;color:#cbd5e1;margin:.2rem 0">• {i}</div>' for i in itens)
                return (f'<div style="background:{bg};border:1px solid {cor}40;border-left:3px solid {cor};border-radius:8px;padding:.7rem .9rem;margin-bottom:.5rem">'
                        f'<div style="font-size:.72rem;font-weight:700;color:{cor};text-transform:uppercase;letter-spacing:.05em;margin-bottom:.3rem">{titulo}</div>{linhas}</div>')

            html_diag = (
                bloco_diag("🟢 Pontos Fortes", diag["fortes"], "#22c55e", "rgba(34,197,94,.06)") +
                bloco_diag("🟡 Pontos de Atenção", diag["atencao"], "#f59e0b", "rgba(245,158,11,.06)") +
                bloco_diag("🔴 Erros Críticos", diag["criticos"], "#ef4444", "rgba(239,68,68,.06)") +
                bloco_diag("🎯 Próximas Ações", diag["acoes"], "#0066ff", "rgba(0,102,255,.06)")
            )
            st.markdown(html_diag, unsafe_allow_html=True)

        # ── ESCALONAMENTO DE CONTRATOS (acumulado total) ──────────────────────
        st.markdown('<div class="sec-title" style="font-size:.95rem;margin-top:1rem">📈 Escalonamento de Contratos</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:.72rem;color:#64748b;margin-bottom:.5rem">Baseado nos pontos acumulados (total). Cada trader configura a própria escada.</div>', unsafe_allow_html=True)

        # Escada personalizada (guardada na sessão)
        if "escala_win" not in st.session_state:
            st.session_state.escala_win = [5000, 7500, 10000, 12500, 15000]
        if "escala_wdo" not in st.session_state:
            st.session_state.escala_wdo = [200, 300, 400, 500, 600]

        with st.expander("⚙️ Configurar minha escada de contratos"):
            st.markdown('<div style="font-size:.78rem;color:#94a3b8;margin-bottom:.5rem">Defina quantos pontos acumulados liberam cada quantidade de contratos. Cada um faz a sua.</div>', unsafe_allow_html=True)
            cfg1, cfg2 = st.columns(2)
            nova_win, nova_wdo = [], []
            with cfg1:
                st.markdown("**WINFUT**")
                for i in range(5):
                    nova_win.append(st.number_input(f"{i+1} contrato(s) a partir de (pts)", min_value=0,
                                                     value=int(st.session_state.escala_win[i]),
                                                     step=500, key=f"cfg_win_{i}"))
            with cfg2:
                st.markdown("**WDOFUT**")
                for i in range(5):
                    nova_wdo.append(st.number_input(f"{i+1} contrato(s) a partir de (pts)", min_value=0,
                                                    value=int(st.session_state.escala_wdo[i]),
                                                    step=50, key=f"cfg_wdo_{i}"))
            if st.button("💾 Salvar minha escada"):
                st.session_state.escala_win = nova_win
                st.session_state.escala_wdo = nova_wdo
                st.success("Escada atualizada!")
                st.rerun()
            st.markdown('<div style="font-size:.66rem;color:#475569;margin-top:.4rem">⚠️ Por enquanto a configuração vale só nesta sessão. Com o login (em breve) ela ficará salva na sua conta.</div>', unsafe_allow_html=True)

        # Monta a escala a partir da config da sessão
        escala_user = {
            "WIN": [(st.session_state.escala_win[i], i+1) for i in range(5)],
            "WDO": [(st.session_state.escala_wdo[i], i+1) for i in range(5)],
        }
        trades_tudo = db_listar_trades(5000)
        esc = calcular_escalonamento(trades_tudo, escala_user)
        col_e1, col_e2 = st.columns(2)
        for col, ativo in zip([col_e1, col_e2], ["WIN", "WDO"]):
            e = esc[ativo]
            pts = e["pontos"]
            cont = e["contratos"]
            prox = e["proxima"]
            if cont == 0:
                falta = prox[0] - pts if prox else 0
                msg = f'<div style="font-size:.74rem;color:#f59e0b;margin-top:.3rem">Faltam <b>{falta:,.0f} pts</b> para liberar 1 contrato</div>'
                cor_c = "#f59e0b"
            elif prox:
                falta = prox[0] - pts
                msg = f'<div style="font-size:.74rem;color:#94a3b8;margin-top:.3rem">Faltam <b>{falta:,.0f} pts</b> para {prox[1]} contratos</div>'
                cor_c = "#22c55e"
            else:
                msg = '<div style="font-size:.74rem;color:#22c55e;margin-top:.3rem">Faixa máxima atingida! 🏆</div>'
                cor_c = "#22c55e"
            col.markdown(
                f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:.9rem 1.1rem">'
                f'<div style="font-size:.7rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em">{ativo}FUT</div>'
                f'<div style="display:flex;align-items:baseline;gap:.5rem;margin:.2rem 0">'
                f'<span style="font-size:1.8rem;font-weight:700;color:{cor_c};font-family:\'JetBrains Mono\',monospace">{cont}</span>'
                f'<span style="font-size:.8rem;color:#94a3b8">contrato(s) liberado(s)</span></div>'
                f'<div style="font-size:.72rem;color:#64748b">Acumulado: <b style="color:#cbd5e1;font-family:\'JetBrains Mono\',monospace">{pts:,.0f} pts</b></div>'
                f'{msg}</div>', unsafe_allow_html=True)

        # ── RANKING DE VAZAMENTOS ─────────────────────────────────────────────
        vaz = ranking_vazamentos(trades)
        if vaz:
            st.markdown('<div class="sec-title" style="font-size:.95rem;margin-top:1rem">💸 Seus Maiores Vazamentos</div>', unsafe_allow_html=True)
            medalhas = ["🥇","🥈","🥉","4️⃣","5️⃣"]
            for i, (nome, valor) in enumerate(vaz[:5]):
                st.markdown(
                    f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:.55rem .9rem;margin-bottom:.4rem;display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="font-size:.84rem;color:#e2e8f0">{medalhas[i]} {nome}</span>'
                    f'<span style="font-size:.9rem;font-weight:700;color:#ef4444;font-family:\'JetBrains Mono\',monospace">−R$ {valor:,.2f}</span>'
                    f'</div>', unsafe_allow_html=True)

        # ── COACH + ANÁLISE COMPORTAMENTAL VIA IA ─────────────────────────────
        if st.button("🧠  Coach de Performance — análise completa com IA"):
            esc_txt = (f"Escalonamento: WIN {esc['WIN']['pontos']:.0f}pts acumulados ({esc['WIN']['contratos']} contratos liberados), "
                       f"WDO {esc['WDO']['pontos']:.0f}pts ({esc['WDO']['contratos']} contratos).")
            resumo = (f"Trader com {stats['n']} operações no período. "
                      f"Resultado: R${stats['lucro_total']:.2f}. Assertividade: {stats['assertividade']:.1f}%. "
                      f"Profit factor: {stats['profit_factor']:.2f}. RR médio: 1:{stats['rr_medio']:.1f}. "
                      f"Score geral: {score['geral'] if score else 'N/A'}/100. "
                      f"Esticou stop {stats['esticou_stop']}x (perda R${stats['perda_por_esticar']:.2f}). "
                      f"Overtrade em {stats['dias_overtrade']} dias. Fora do setup {stats['fora_setup']}x. "
                      f"Melhor dia R${stats['melhor_dia']:.2f}, pior dia R${stats['pior_dia']:.2f}. {esc_txt}")
            with st.spinner("Coach analisando sua performance…"):
                analise = ia(
                    "Você é um coach de performance de day trade. Com base nos dados, NÃO repita só os números — "
                    "transforme em DECISÕES e METAS práticas. Dê: 1 ponto forte para manter, o erro mais caro para "
                    "corrigir já, e 2 metas concretas para a próxima semana (com números). Seja direto, fale como mentor. "
                    f"Dados: {resumo}",
                    system=SYSTEM_PROMPT)
            st.markdown(f'<div class="chat-msg-bot" style="max-width:100%">🎯 {html_mod.escape(analise)}</div>', unsafe_allow_html=True)

    # ── HISTÓRICO DE OPERAÇÕES ────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div><div class="sec-title">📋 Histórico de Operações</div>', unsafe_allow_html=True)
    todos = db_listar_trades(100)
    if not todos:
        st.markdown('<div style="color:#475569;font-size:.85rem;padding:.5rem 0">Nenhuma operação registrada ainda. Comece pelo formulário acima.</div>', unsafe_allow_html=True)
    else:
        for t in todos[:30]:
            cor = "#22c55e" if t["resultado"] > 0 else "#ef4444" if t["resultado"] < 0 else "#94a3b8"
            dir_emoji = "🟢" if t["direcao"] == "Compra" else "🔴"
            data_fmt = datetime.strptime(t["data"], "%Y-%m-%d").strftime("%d/%m")
            flags = []
            if t.get("esticou_stop"): flags.append("⚠️ stop esticado")
            if not t.get("seguiu_setup"): flags.append("fora do setup")
            flags_txt = " · ".join(flags)
            cc1, cc2 = st.columns([6,1])
            with cc1:
                obs_html = f'<div style="font-size:.7rem;color:#64748b;margin-top:.2rem">{html_mod.escape(t["obs"])}</div>' if t.get("obs") else ''
                flags_html = f'<div style="font-size:.68rem;color:#f59e0b;margin-top:.2rem">{flags_txt}</div>' if flags_txt else ''
                card_html_hist = (
                    f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:.5rem .8rem;margin-bottom:.35rem">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div style="font-size:.82rem;color:#e2e8f0">{dir_emoji} <b>{t["ativo"]}</b> · {data_fmt} · {t["hora"]} · {t["contratos"]}c · {t["pontos"]:+.0f}pts</div>'
                    f'<div style="font-size:.9rem;font-weight:700;color:{cor};font-family:\'JetBrains Mono\',monospace">R$ {t["resultado"]:,.2f}</div>'
                    f'</div>{flags_html}{obs_html}</div>'
                )
                st.markdown(card_html_hist, unsafe_allow_html=True)
            with cc2:
                if st.button("🗑️", key=f"del_{t['id']}"):
                    db_deletar_trade(t["id"])
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# RODAPÉ — Divulgação do curso (todas as abas)
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# RODAPÉ — Divulgação do curso (card compacto em destaque)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@keyframes seta-sobe{0%{stroke-dashoffset:120}100%{stroke-dashoffset:0}}
@keyframes pulso-curso{0%,100%{box-shadow:0 0 0 0 rgba(0,102,255,.35)}50%{box-shadow:0 0 0 6px rgba(0,102,255,0)}}
.card-curso{background:linear-gradient(135deg,#0a1628,#0f172a);border:1px solid #1e3a8a;border-radius:14px;
   padding:1rem 1.2rem;margin-top:1rem;display:flex;align-items:center;gap:1rem;max-width:520px;
   transition:all .2s;animation:pulso-curso 2.8s infinite}
.card-curso:hover{border-color:#3b82f6;transform:translateY(-2px)}
.card-curso svg path{stroke-dasharray:120;animation:seta-sobe 2s ease-out infinite}
</style>
<a href="https://go.hotmart.com/K105904656Q?dp=1" target="_blank" style="text-decoration:none">
  <div class="card-curso">
    <svg width="46" height="46" viewBox="0 0 46 46" fill="none">
      <rect width="46" height="46" rx="10" fill="#0066ff" opacity="0.12"/>
      <path d="M10 32 L20 24 L27 28 L36 14" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      <path d="M30 14 L36 14 L36 20" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>
    <div style="flex:1">
      <div style="font-size:.9rem;font-weight:700;color:#f1f5f9;margin-bottom:.15rem">🎓 Guia Mestre de Day Trade</div>
      <div style="font-size:.72rem;color:#94a3b8;line-height:1.35">Aprenda o método WIN &amp; WDO por trás desta ferramenta</div>
    </div>
    <div style="background:#0066ff;color:#fff;border-radius:8px;padding:.5rem .9rem;font-size:.8rem;font-weight:700;white-space:nowrap">Ver curso →</div>
  </div>
</a>
<div style="font-size:.6rem;color:#475569;margin-top:.4rem;max-width:520px;line-height:1.4">
  ⚠️ Operar day trade envolve risco de perda. A maioria dos traders perde dinheiro. Conteúdo educacional, não é recomendação de investimento.
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
