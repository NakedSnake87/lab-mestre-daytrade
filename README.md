# 📈 MestreDoDayTrade Pro — Agente Financeiro Inteligente com IA Generativa

> Projeto desenvolvido para o desafio **"Agente Financeiro Inteligente com IA Generativa"** da [DIO](https://www.dio.me) em parceria com o **Bradesco**.

🔗 **[Acesse o app ao vivo](https://lab-mestre-daytrade-putevtf7ehtwizjdswgfsp.streamlit.app)**

---

## 🤖 Sobre o Agente

O **MestreDoDayTrade Pro** é um assistente inteligente especializado em contratos futuros de **Mini-Índice (WIN)** e **Mini-Dólar (WDO)** na B3. Combina IA Generativa com dados de mercado em tempo real para oferecer análise técnica, controle de risco e educação operacional para traders de varejo.

---

## 🎯 Problema que Resolve

95% dos day traders perdem dinheiro — não por falta de técnica, mas por **descontrole emocional**: fúria de mercado, overtrading e quebra do gerenciamento de risco.

O MestreDoDayTrade atua como um **gerente de risco e mentor comportamental** que:

- Monitora mercados globais em tempo real (S&P 500, Nasdaq, DAX, Nikkei, Petróleo, Ouro, Dólar, Bitcoin)
- Busca e analisa notícias relevantes com impacto direto no WIN e WDO
- Calcula risco real de cada operação (stop, meta, RR, risco do capital)
- Explica padrões gráficos com representação visual (OCO, Topo Duplo, Fibonacci, Candles japoneses)
- Analisa prints de gráficos do ProfitPro via IA multimodal
- **Nunca emite "calls"** de compra/venda (conformidade regulatória CVM)

---

## 🚀 Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| 🌍 Mercados Globais | 8 índices e ativos em tempo real via Yahoo Finance |
| 📰 Notícias ao Vivo | Busca notícias financeiras com análise de impacto no WIN/WDO |
| 🛡️ Calculadora de Risco | Stop, meta, RR, risco do capital e análise de sobrevivência |
| 🤖 Chat Especialista | Explica padrões gráficos, indicadores e ferramentas do Profit |
| 📷 Análise Multimodal | Lê prints de gráficos do ProfitPro e identifica padrões |
| 🔄 Aviso de Rolagem | Alerta automático nos meses de vencimento de contratos |

---

## 🛠️ Tecnologias

- **Python 3.14**
- **Streamlit** — Interface web interativa
- **Groq AI (Llama 3.3 70B)** — Modelo LLM ultra-rápido e gratuito
- **NewsAPI** — Notícias financeiras em tempo real
- **Yahoo Finance API** — Cotações de mercados globais
- **Pillow** — Processamento de imagens dos gráficos

---

## 📁 Estrutura do Repositório

```
lab-mestre-daytrade/
│
├── README.md
│
├── data/
│   ├── perfil_investidor.json       # Plano de trade mockado
│   └── transacoes.csv               # Histórico de operações mockado
│
├── docs/
│   ├── 01-documentacao-agente.md    # Caso de uso e arquitetura
│   ├── 02-base-conhecimento.md      # Estratégia de dados
│   ├── 03-prompts.md                # Engenharia de prompts
│   ├── 04-metricas.md               # Avaliação e métricas
│   └── 05-pitch.md                  # Roteiro do pitch
│
├── src/
│   └── app.py                       # Código-fonte da aplicação
│
└── requirements.txt                 # Dependências do projeto
```

---

## ▶️ Como Executar Localmente

```bash
# 1. Instalar dependências
pip install streamlit requests groq Pillow

# 2. Configurar secrets (criar arquivo .streamlit/secrets.toml)
# GROQ_KEY = "sua_chave_groq"
# NEWS_KEY = "sua_chave_newsapi"

# 3. Rodar
streamlit run src/app.py
```

---

## 🧠 Arquitetura

```
[Usuário] → [Interface Streamlit]
                    ↓
     [Yahoo Finance API] → Cotações em tempo real
     [NewsAPI]           → Notícias do mercado
                    ↓
     [System Prompt + Contexto de mercado]
                    ↓
     [Groq AI - Llama 3.3 70B]
                    ↓
     [Resposta proativa e personalizada]
```

---

## 📢 Pitch

**O problema:** 95% dos day traders perdem dinheiro por descontrole emocional e quebra do gerenciamento de risco — não por falta de técnica.

**A solução:** O MestreDoDayTrade combina dados de mercado em tempo real com IA Generativa para ser o copiloto que todo trader de varejo precisava — monitorando riscos, analisando gráficos e educando sobre padrões técnicos.

**O diferencial:** IA multimodal que lê gráficos reais do ProfitPro + notícias em tempo real + conformidade regulatória total (zero calls).

---

*Desenvolvido por [NakedSnake87](https://github.com/NakedSnake87) para o bootcamp de IA Generativa da DIO × Bradesco.*
