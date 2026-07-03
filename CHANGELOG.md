# Changelog — MAPA-PG-UnB

## v4.0.0 — Três bases de impacto para a estratificação (2026-07-03)

**Novidade principal:** a estratificação **A1–A8/C** passa a poder ser calculada sob **três
bases de indicador de impacto**, selecionáveis no grupo **"Relatório Detalhado IF"**:
- **CiteScore (Scopus)** — indicador **oficial** prescrito pela Ficha de Avaliação CAPES
  2025–2028; é o **padrão** (pré-marcado);
- **OpenAlex** — IF de 2 anos (base aberta, cobertura máxima; comportamento das versões ≤ 3.2);
- **Híbrido** — CiteScore onde há; onde falta, o percentil do OpenAlex (recupera a cobertura
  das áreas pouco indexadas no Scopus, sobretudo Humanas/Sociais/Linguística).

A base escolhida recalcula os percentis de **todos** os estratos no app (filtro por estrato,
métricas `ma_*`, rótulos A1–A8 e o Relatório Detalhado IF). Como a comparação é sempre
intra-área, as leituras se mantêm robustas; muda a fração que cai em **C** por ausência de
indicador (alta no CiteScore nas Humanas, baixa no Híbrido).

### Adicionado
- Três rádios de base (`name="ifBase"`, CiteScore/OpenAlex/Híbrido) sob "Relatório Detalhado IF"
  em `index.html`; `setIFBase()` troca a base e re-renderiza.
- Vetores de estrato por base nos `docs/dados/area-*.json`: `estr_{perm,colab,visit,all}_{cs,oa,hb}`
  e `metadata.estratos_{cs,oa,hb}` (com `fonte` e `frac_c`). Campos sem sufixo = CiteScore (padrão).
- Indicador da base ativa no cabeçalho do Relatório Detalhado IF e nos exports TXT/CSV.

### Interno
- `build/gerar_estratos_app.py` computa as 3 bases (CiteScore via crosswalk ISSN→ISSN-L +
  `citescore_2025_TODAS_AREAS.csv`; híbrido em cascata). Invariante validado: Σ dos 9 estratos
  é igual entre as bases; paridade legada com `if_*` mantida na base OpenAlex.
- `aplicarBaseEstrato()` remapeia os campos sem sufixo a partir da base ativa, ao carregar a
  área e ao trocar a base (mínimo churn nas ~16 leituras de estrato).
- Versão do app **v4.0.0** (`VERSION` + `#headerVersion`); cache do Service Worker `mapa-pg-v4.0.0`.

## v3.2.0 — Filtros de nota 3 e 4 (2026-06-30)

**Novidade principal:** o filtro **Nota CAPES** passa a expor as notas **3** e **4**, antes
ausentes da interface (só 5, 6 e 7 eram selecionáveis), embora os dados já as contivessem
(≈3.900 registros nota 3 e ≈4.291 nota 4 no conjunto nacional).

### Adicionado
- Checkboxes **Nota 3** e **Nota 4** no grupo "Nota CAPES", em `index.html` e `faixas-if.html`.
  Desmarcados por padrão, preservando a visão inicial (apenas Nota 5 marcada); como os demais
  checkboxes de nota, são aplicados ao clicar em **Analisar**.
- Cores próprias por nota em `NOTA_COLORS` para legendas/gráficos: nota 3 (roxo `#9C27B0`) e
  nota 4 (ciano `#00BCD4`).

### Interno
- `getFilters()` inclui as notas 3 e 4 na lista de notas selecionadas (ambas as páginas).
- Versão do app exibida no cabeçalho atualizada para **v3.2-multi** (`VERSION` + `#headerVersion`).
- Bump do cache do Service Worker (`mapa-pg-v3.3.0`) para refletir o novo shell em visitantes recorrentes.

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
