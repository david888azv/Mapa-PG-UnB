# Changelog — MAPA-PG-UnB

## v3.1.0 — TOP / Ranking de programas (2026-06-25)

**Novidade principal:** painel **TOP / Ranking de programas**, portando para a pós-graduação
o recurso "TOP de cursos" do MAPA-GR.

### Adicionado
- Botão **🏆 TOP / Ranking de programas** no sidebar. Ranqueia os programas da área pela
  **métrica selecionada** (art/ano PQ/sem PQ/geral/por categoria docente, ou IF médio),
  respeitando os filtros ativos (nota, quadriênio, região, IES, estratos CAPES, tipo de produção).
- Quatro modos: **TOP melhores** e **TOP mais baixos** (nacional), **Melhor por UF** e
  **Pior por UF** (um programa por estado). Seletor de N (10/20/50/Todos) no modo nacional.
- Quando "Todos os quadriênios" está selecionado, usa o **quadriênio mais recente** de cada
  programa. Programas da UnB destacados (★) e tabela com posição/IES/UF/nota/quadriênio/docentes/valor.
- Gráfico de barras horizontais do recorte e **exportação CSV** do ranking.
- O filtro Pública/Privada do MAPA-GR **não** foi portado: os dados de pós-graduação não têm
  categoria administrativa e a pós stricto sensu é majoritariamente pública.

### Interno
- `METRICA_LABEL` / `WEIGHT_FIELD` extraídos para constantes compartilhadas por `analisar()` e
  `renderRanking()`. Bump de cache do Service Worker (`mapa-pg-v3.2.0`).

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
