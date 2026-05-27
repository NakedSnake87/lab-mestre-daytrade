# 02 — Base de Conhecimento

## Estratégia de Dados

O MestreDoDayTrade utiliza **dados mockados locais** que simulam o ambiente real de um trader de Mini-Índice e Mini-Dólar. Todos os arquivos estão na pasta `data/`.

---

## Arquivos Utilizados

| Arquivo | Formato | Descrição |
|---|---|---|
| `perfil_investidor.json` | JSON | Plano de trade: stop máximo diário, meta de ganho |
| `transacoes.csv` | CSV | Histórico de ordens executadas no pregão do dia |

---

## Estrutura dos Dados

### perfil_investidor.json
```json
{
  "nome_trader": "Trader Scalper Pro",
  "stop_maximo_diario_rs": 200.00,
  "meta_ganho_diaria_rs": 300.00
}
```

**Como é usado:** O campo `stop_maximo_diario_rs` é comparado com o saldo do pregão calculado pelo Python. Se o saldo for menor ou igual ao negativo desse valor, o agente aciona a trava de risco automaticamente.

---

### transacoes.csv
```
Horario,Ativo,Resultado_RS,Setup
09:15,WING26,80.00,Retracao na VWAP
10:30,WDOH26,-120.00,Rompimento de Pivo
11:00,WING26,-170.00,Rompimento de Pivo
```

**Como é usado:** O histórico completo de ordens é injetado no System Prompt para que a IA identifique padrões de erro (ex: dois stops consecutivos no mesmo setup) e gere análises comportamentais personalizadas.

---

## Como Adaptar para Uso Real

Para usar com dados reais do seu pregão:

1. Exporte o relatório de ordens do dia pelo ProfitPro (Relatório de Performance)
2. Formate as colunas no padrão: `Horario, Ativo, Resultado_RS, Setup`
3. Substitua o arquivo `data/transacoes.csv` com os dados do dia
4. Ajuste os limites em `data/perfil_investidor.json` conforme seu gerenciamento real

---

## Expansões Possíveis

- `historico_atendimento.csv` — Histórico de dias anteriores para análise de tendência
- `setups_autorizados.json` — Catálogo de setups homologados pelo trader
- `diario_trade.md` — Anotações comportamentais do operador
