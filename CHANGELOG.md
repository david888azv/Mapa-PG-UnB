# Changelog — MAPA-PG-UnB

## v3.0.0 — Estratos CAPES 2025–2028 (2026-06-20)

**Novidade principal:** estratificação da produção de artigos em **A1–A8 + C** segundo a
**Ficha de Avaliação CAPES 2025–2028** (Avaliação de Permanência / Quadrienal 2029), por
**percentil do fator de impacto do periódico dentro da área** (classes de 12,5%):
A1 = 87,5–100% … A8 = 0–12,5%; **C = sem indicador de IF**.

### Adicionado
- **Filtro por estrato CAPES** (A1…A8, C) substituindo as 3 faixas de IF (Baixo/Médio/Alto).
  Cada estrato exibe o **percentil** e o **corte de fator de impacto da área** (ex.: `A1 · percentil 87,5–100% · IF ≥ 4,84`).
  O usuário marca um ou mais estratos, ou usa **Todos / Nenhum** e o checkbox-mestre **Todos os estratos**.
  No app multi-área os cortes de IF se atualizam conforme a área carregada.
- Métricas `ma_all/ma_perm/ma_colab/ma_visit` passam a reponderar pelos estratos marcados.
- Relatório detalhado de fator de impacto (HTML/TXT/CSV/gráficos) reescrito para os 9 estratos.
- Dados: novos campos por programa×quadriênio `estr_perm`, `estr_colab`, `estr_visit`, `estr_all`
  (vetores A1..A8,C) e bloco `metadata.estratos` (cortes de IF + percentis) por área.
  Gerados por `build/gerar_estratos_app.py` (paridade exata Σ A1–A8 == faixas de IF; C aditivo).

### Preservado
- A versão anterior (filtro por **faixas de fator de impacto**) continua acessível em
  **`faixas-if.html`**, intacta, lendo os mesmos dados (campos antigos não foram alterados).

### Notas
- Apenas adições aos JSON de dados; nenhum valor pré-existente foi modificado.
- O total “com IF” usando todos os estratos inclui **C** (periódicos sem indicador), por isso pode
  exceder a soma das antigas faixas de IF.
- Service worker e `shell_version` atualizados para forçar o novo conteúdo em visitantes recorrentes.

## v2.0 e anteriores
Comparador multi-área (42 áreas CAPES, 92 programas UnB, 2013–2024) com 3 faixas de fator de impacto.
