# 📈 MestreDoDayTrade v4.0 — Agente Financeiro Inteligente com IA Generativa

> Projeto desenvolvido para o desafio **"Agente Financeiro Inteligente com IA Generativa"** da [DIO](https://www.dio.me).

---

## 🤖 Sobre o Agente

O **MestreDoDayTrade** é um copiloto de alta performance especializado em contratos futuros de **Mini-Índice (WIN)** e **Mini-Dólar (WDO)** na B3. Ele atua como um mentor sênior de mesa proprietária, combinando IA Generativa com dados reais do trader para oferecer análises proativas, controle de risco e feedbacks comportamentais.

---

## 🎯 Caso de Uso

Traders de varejo que operam WIN e WDO frequentemente perdem dinheiro não por falta de técnica, mas por **descontrole emocional** — fúria de mercado, overtrading e insistência em setups que não estão funcionando no dia.

O MestreDoDayTrade resolve isso sendo um **gerente de risco automatizado e mentor comportamental**, que:

- Monitora o saldo do pregão em tempo real
- Aciona trava de segurança quando o stop diário é violado
- Identifica padrões de erro (ex: dois stops seguidos no mesmo setup)
- Analisa prints de gráficos do ProfitPro via IA multimodal
- Nunca emite "calls" de compra/venda (conformidade regulatória CVM)

---

## 🚀 Funcionalidades Principais

| Funcionalidade | Descrição |
|---|---|
| 🔴 Trava de Risco | Bloqueia o trader quando o stop diário é atingido |
| 📊 Painel de Métricas | Exibe saldo do pregão e win rate em tempo real |
| 🧠 IA Proativa | Inicia a conversa com análise baseada nos dados do dia |
| 📷 Análise Multimodal | Lê prints de gráficos do ProfitPro (VWAP, médias, volume) |
| 🛡️ Anti-Alucinação | Nunca inventa dados — usa apenas a base de conhecimento local |

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.14**
- **Streamlit** — Interface web interativa
- **LangChain** — Orquestração de prompts e histórico de conversa
- **Google Gemini 2.5 Flash** — Modelo LLM multimodal (texto + imagem)
- **Pandas** — Processamento de dados do histórico de trades
- **Pillow** — Processamento de imagens dos gráficos

---

## 📁 Estrutura do Repositório

```
lab-mestre-daytrade/
│
├── README.md
│
├── data/
│   ├── perfil_investidor.json       # Plano de trade: stop diário, meta, contratos
│   └── transacoes.csv               # Histórico de ordens executadas no pregão
│
├── docs/
│   ├── 01-documentacao-agente.md    # Caso de uso e arquitetura
│   ├── 02-base-conhecimento.md      # Estratégia de dados
│   ├── 03-prompts.md                # Engenharia de prompts
│   ├── 04-metricas.md               # Avaliação e métricas
│   └── 05-pitch.md                  # Roteiro do pitch
│
└── src/
    └── app.py                       # Código-fonte da aplicação Streamlit
```

---

## ▶️ Como Executar Localmente

```bash
# 1. Instalar dependências
pip install streamlit pandas langchain langchain-google-genai pillow

# 2. Rodar a aplicação
streamlit run src/app.py
```

> ⚠️ Necessário ter uma chave de API do [Google AI Studio](https://aistudio.google.com) configurada no arquivo `src/app.py`.

---

## 🛡️ Mecanismo Anti-Alucinação

O agente utiliza a técnica **RAG (Retrieval-Augmented Generation)**: os dados do trader (`perfil_investidor.json` e `transacoes.csv`) são injetados diretamente no System Prompt antes de cada resposta. A IA nunca busca dados externos — responde exclusivamente com base na realidade operacional do usuário.

---

## 📢 Pitch

**O problema:** 95% dos day traders perdem dinheiro — não por falta de técnica, mas por descontrole emocional e quebra do gerenciamento de risco.

**A solução:** O MestreDoDayTrade monitora o pregão em tempo real, aciona travas automáticas e age como um mentor que manda você largar o mouse antes que o prejuízo vire catástrofe.

**O diferencial:** IA multimodal que lê gráficos do ProfitPro + conformidade regulatória total (zero calls).

---

*Desenvolvido por [NakedSnake87](https://github.com/NakedSnake87) para o bootcamp de IA Generativa da DIO.*
