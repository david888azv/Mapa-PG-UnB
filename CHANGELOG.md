# Changelog — MAPA-PG-UnB

## v5.0.0 — Revisão de medida: a produtividade agora é calculada de forma correta e honesta (2026-07-17)

**Versão maior — os números mudaram e o ranking também.** Esta revisão corrige três
defeitos na forma de medir a produção acadêmica e incorpora dados de docentes que a CAPES
publicou e que o aplicativo ainda não usava. As três correções são da mesma família: um
fator que **varia de programa para programa** estava embutido numa taxa e, por isso,
**não se cancelava na comparação** — inflava uns programas e penalizava outros. Como isso
altera a posição relativa dos programas dentro de cada área, a versão sobe de 4.x para
5.0. Um documento dedicado explica cada mudança, seus efeitos e sua justificativa:
**"O que mudou na v5.0"** (botão no painel; `mudancas-v5.0.0.html` / `.pdf`).

**As três correções de medida:**

1. **Artigos distintos, não eventos artigo×autor.** A base da CAPES traz uma linha por
   (artigo, autor); o app contava essas linhas, então um artigo com 3 permanentes contava
   3 vezes. O fator de inflação variava de 1,00 (autoria única) a 7,52 entre os programas.
   *(já entregue na v4.2.0, consolidada aqui.)*

2. **Denominador em anos-docente, não docentes × 4.** O app dividia por `n_perm × 4`,
   tratando quem entrou no último ano como presente nos quatro. Programas que existiram em
   um único ano do quadriênio — tipicamente **novos** — apareciam com **um quarto** da
   produtividade real. O fator `(n_perm×4 ÷ anos-docente)` tinha mediana ~1,17, chegava a
   2,0 no p90 e a 4,0 no extremo. Agora o denominador é a soma, ano a ano, dos docentes
   daquele ano. Novo campo `ad_*` no JSON; `n_perm` continua na tela como headcount.

3. **Recorte de topo A1–A4 (percentil ≥ 50), não A1–A3.** Alinha ao corte dominante nas
   fichas de área da CAPES (A1–A3 aparecia em uma única área). Não altera a predição — é
   fidelidade à norma. O grupo "elite" (A1–A2, ≥ 75%) foi mantido.

**Dados novos — os docentes de 2022 a 2024.** A CAPES publicou 2022/2023 em 25/03/2025 e
2024 em 01/12/2025; o quadriênio 2021-2024 usava só o roster de 2021. Proveniência
confirmada (o arquivo de 2021 baixado é byte-idêntico ao já usado). **82%** dos programas
do país tiveram o nº de permanentes alterado.

**Efeitos medidos:** a taxa exibida sobe em ~96% dos programas em 2013-2016 e 2017-2020
(razão mediana ~1,17); **83 programas da UnB** mudaram de posição dentro da própria área só
em 2017-2020 (um subiu 80 posições; outro caiu 32). Sobe **e** desce — a assinatura de um
viés que não se cancelava. O que **não** mudou: fonte (CAPES/Sucupira), recorte por área,
estratificação A1–A8/C e o princípio de comparar só dentro da mesma área.

**Nota sobre as fichas por área (no documento):** a auditoria das 48 fichas de avaliação
disponíveis mostra que a CAPES **não padroniza** o quesito de produção — 31 áreas usam taxa
por docente, 17 usam percentual de docentes, ~10 usam cota fixa (onde publicar mais não
pontua), e os denominadores e réguas de estrato divergem. Seguir a ficha de cada área é
inviável para ~86% delas (o bloqueio é o denominador, que depende de declaração do próprio
programa e não existe em base pública). Por isso o app mantém uma **régua única, explícita
e uniforme**, e o documento é transparente sobre o que ela **não** faz.

## v4.2.0 — A produção passa a ser contada em artigos distintos (2026-07-17)

**Correção de medida. Os números exibidos mudam.** Até aqui o app contava *eventos
artigo×autor*: um artigo assinado por três docentes permanentes do programa entrava três vezes
na contagem daquele programa. Como todas as métricas são taxas (por docente, por ano), isso
embutia a coautoria interna no indicador — e o fator de inflação **não é constante**: varia de
1,00 (Filosofia, Artes, onde a autoria única é a norma) a 7,52 entre os 4.375 programas, com
mediana 1,18. Por não ser uniforme, ele não se cancelava na comparação entre programas:
quem tinha muita coautoria interna aparecia inflado, quem tinha pouca aparecia penalizado.

Agora cada artigo é contado **uma vez** por categoria de docente, se tiver ao menos um autor
naquela categoria. O efeito é maior nas áreas de coautoria intensa (Odontologia: 4,75 → 2,42
artigos por permanente/ano) e quase nulo nas de autoria única (Filosofia: 7,89 → 7,61).

Atinge `ma_pq`/`ma_spq`/`ma_all`/`ma_perm`/`ma_colab`/`ma_visit`, `prod_sub`, `prod_ano`, as
faixas de IF (`if_perm`/`if_colab`/`if_visit`/`if_all`) e os vetores de estrato A1–A8/C
(`estr_*`) nas três bases (CiteScore, OpenAlex, híbrida). `avg_if`/`med_if`/`max_if`/`n_if` já
eram sobre artigos distintos e ficaram **inalterados** — serviram de controle da migração.

Os dois caminhos do app (filtro de tipo via `prod_sub` e filtro de estrato via `estr_*`)
continuam na mesma unidade, e a invariante de paridade `sum(if_perm) == sum(estr_perm_oa[:8])`
fecha nas 49 áreas, sem erros.

## v4.1.0 — Universidade de referência configurável: 26 IFES + UnB (2026-07-05)

**Nova funcionalidade.** O usuário passa a escolher **qual universidade federal** usar como
referência (destaque em vermelho), em vez de a UnB ser fixa. Após o consentimento, uma tela
apresenta **27 opções** (as 26 federais "capitais", uma por UF, + a UnB); escolha única, clica
em **OK** e todos os painéis abrem padronizados, com a IFES selecionada destacada em vermelho —
exatamente como era feito para a UnB — na comparação com todos os pares nacionais de cada área.

Arquitetura: **app único** (uma fonte de verdade, um deploy). Os dados de área já são nacionais;
o destaque sempre foi um conceito de runtime — a generalização apenas passou a derivar os códigos
de referência da IFES escolhida (por variante de sigla CAPES) em vez de `metadata.unb_cds`.

### Adicionado
- **Tela de escolha da IFES de referência** pós-licença (`showIesPicker`), escolha única entre
  27 universidades federais; botão **"↺ Trocar universidade de referência"** na barra lateral.
- `build/gerar_registry_ies.py` → **`docs/registry_ies.json`**: catálogo das 27 IFES (grande área →
  área CAPES → programas EM FUNCIONAMENTO), derivado dos próprios `docs/dados/area-*.json`. Trata
  variantes de sigla por campus/fundação: **Piauí = FUFPI, Sergipe = FUFSE/FUFSE-ITAB, UFPB em 4
  campi, UFSC + Blumenau**.
- **Deep-link `?ies=SIGLA`** (persistido em `localStorage`) e **27 stubs** `docs/ies/<sigla>/` →
  `/?ies=SIGLA` (`build/gerar_stubs_ies.py`), com URL limpa/indexável por universidade; 27 URLs
  novas no `sitemap.xml`.

### Alterado
- `index.html`: `REGISTRY` agora é montado para a IFES de referência (mesmo shape do antigo
  `registry.json`); rótulos, títulos, notas de gráfico, cabeçalhos de CSV e relatórios passam a
  refletir a sigla escolhida (`refSigla()`). Deep-links `?curso=SUFIXO` da UnB seguem válidos.
- Service worker → `mapa-pg-v4.1.0`; precache passa a incluir `registry_ies.json`.

### Notas
- Validação headless (Playwright) end-to-end: consentimento → seletor → destaque correto por
  variante de sigla (UnB, UFMG, UFPB/campi, UFPI=FUFPI, UFS=FUFSE), stub `?ies=` sem reabrir o
  seletor, e troca de referência ao vivo (UFMG→UFRGS).

## v4.0.1 — Atribuição Scopus/Elsevier do CiteScore (2026-07-03)

**Manutenção — conformidade e atribuição.** Adiciona a atribuição e a nota de conformidade
exigidas pela Elsevier para o uso do **CiteScore** (base padrão, extraída da base **Scopus**
via API gratuita), sem alterar dados nem cálculos.

### Adicionado
- `help-doc.html`: nova **FONTE 10 — CiteScore 2025 (Scopus / Elsevier)** com métrica,
  endpoints (`api.elsevier.com` / `www.scopus.com`), **data de coleta (3 jul 2026)**, uso
  acadêmico não-comercial e nota de conformidade; linha correspondente no Resumo Consolidado.
- `index.html`: parágrafo de acknowledgement Scopus/Elsevier no **modal de licença** (exibido
  a cada abertura) e reforço da nota de fonte inline dos estratos (base CiteScore).

### Notas
- Apenas texto/atribuição; nenhum valor de dado foi modificado. Confirmado que os JSON
  publicados contêm **apenas agregados** (contagens por estrato e limiares de faixa por área),
  sem registros brutos por periódico. O CSV bruto do CiteScore não é versionado nem publicado.
- Service worker atualizado para `mapa-pg-v4.0.1` (cache-first) para propagar a nova ajuda.

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
