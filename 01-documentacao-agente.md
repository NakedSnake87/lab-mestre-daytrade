# 01 — Documentação do Agente: MestreDoDayTrade

## 1. Caso de Uso

O **MestreDoDayTrade** resolve o problema do **descontrole emocional** em operações de Day Trade no mercado futuro brasileiro (B3).

**Problema financeiro que ele resolve:**
- Traders que insistem em operar após atingir o stop diário ("fúria de mercado")
- Repetição compulsiva de setups que não estão funcionando no dia
- Falta de análise técnica fria e objetiva sobre os erros operacionais

**Público-alvo:** Traders de varejo que operam Mini-Índice (WIN) e Mini-Dólar (WDO) na B3 via plataforma ProfitPro.

---

## 2. Persona e Tom de Voz

- **Nome:** MestreDoDayTrade
- **Perfil:** Mentor sênior de mesa proprietária / Gerente de Risco Quantitativo
- **Tom de Voz:** Direto, assertivo, analítico e sem rodeios. Usa jargões reais do mercado futuro brasileiro: "preço de ajuste", "bater lote", "fúria", "proteger no zero a zero", "largar o mouse"
- **Comportamento:** Proativo — não espera o trader perguntar. Inicia a conversa com análise baseada nos dados do pregão atual

---

## 3. Arquitetura

```
[Trader] → [Interface Streamlit]
                    ↓
         [Carregamento de Dados Locais]
         perfil_investidor.json + transacoes.csv
                    ↓
         [Cálculos Python: saldo, win rate, status de risco]
                    ↓
         [System Prompt + RAG: injeção de contexto]
                    ↓
         [Google Gemini 2.5 Flash — LLM Multimodal]
                    ↓
         [Resposta proativa e personalizada ao Trader]
```

**Fluxo de imagem (análise de gráfico):**
O trader pode enviar um print da tela do ProfitPro. A imagem é convertida para base64 e enviada junto ao texto para o modelo multimodal, que analisa os indicadores visuais (VWAP, médias móveis, volume) e retorna uma análise técnica.

---

## 4. Segurança e Anti-Alucinação

- **RAG Local:** Todos os dados injetados vêm exclusivamente dos arquivos locais do trader — a IA não busca dados externos
- **Bloqueio matemático:** O cálculo do saldo e do win rate é feito em Python puro antes de chegar na IA, eliminando qualquer possibilidade de erro numérico
- **Restrição de calls:** O System Prompt proíbe explicitamente qualquer recomendação de compra ou venda em tempo real
- **Conformidade CVM:** O agente atua como educador e gerente de risco, não como analista de valores mobiliários
