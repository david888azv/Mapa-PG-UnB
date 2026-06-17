# PIP — Plano de Incremento de Produtividade (UnB)

Estudos derivados da base já preparada pelo app **mapa-pg-multi**
(`../docs/dados/area-*.json`), para estimar quanto cada programa de
pós-graduação **acadêmico** da UnB hoje **nota 3** ou **nota 4** precisa
aumentar sua **produção de artigos por pesquisador** para alcançar a média
nacional dos programas da nota imediatamente superior (3→4, 4→5), **dentro da
mesma área de avaliação CAPES** — única comparação válida pela metodologia da
CAPES.

## Decisões metodológicas (2026-06-17)

1. **Nota vigente + produção do último quadriênio completo.** A nota de cada
   programa é a do registro **2021-2024** (nota atual). A **produção**, porém, é
   medida em **2017-2020**, porque a coleta 2021-2024 ainda está incompleta
   (muitos programas com produção zerada). As médias de referência usam o mesmo
   par (nota vigente × produção 2017-2020).
2. **Apenas docentes permanentes.** A produtividade por pesquisador usa
   `n_perm` / `ma_perm`. `ma_perm` = artigos em periódico por docente permanente
   **por ano** (média do quadriênio).
3. **Apenas programas acadêmicos.** Profissionais ficam fora da análise e das
   médias de referência.

## Métrica de incremento (dois alvos, sempre art/pesquisador/ano)

Toda a produtividade é expressa em **artigos por pesquisador permanente por
ano** (`ma_perm`), para comparação igualitária entre programas. Para cada
programa UnB nota 3/4, na área *A*, calculam-se **dois alvos nacionais**:

```
alvo_nota4 = MÍNIMO de ma_perm (2017-2020) entre os programas acadêmicos
             nota 4 da área A      → piso de produtividade para ser nota 4
alvo_nota5 = MÉDIA  de ma_perm (2017-2020) entre os programas acadêmicos
             nota 5 da área A      → alvo de produtividade para ser nota 5

incremento_p/nota4 = max(0, alvo_nota4 - ma_perm_do_programa)   (art/pesq/ano)
incremento_p/nota5 = max(0, alvo_nota5 - ma_perm_do_programa)   (art/pesq/ano)
```

Um programa que já atinge um alvo recebe **SIM** naquela coluna (em vez do
número), indicando que já alcançou a referência nacional correspondente.

A aba **Artigos por faixa de impacto** distribui o incremento até a *próxima*
nota (3→4 pelo mínimo; 4→5 pela média) entre as faixas de impacto OpenAlex,
também em art/pesquisador/ano.

## Arquivos

- `build_pip.py` — gera `saida/relatorio_pip_unb.xlsx` com 5 abas:
  **Quantitativos UnB**, **Incremento de produção**, **Projeção por nota**,
  **Artigos por faixa de impacto** e **Referências por área**.
  A aba **Projeção por nota** (2026-06-17) agrega a produção art/permanente/ano
  (2017-2020) por NOTA atravessando TODAS as áreas: produção PONDERADA pelos
  permanentes de cada programa (Σ artigos/ano ÷ Σ permanentes), além de média e
  mediana nacionais, para Brasil e UnB; e projeta o incremento da produção
  ponderada da UnB de cada nota até a média/mediana nacional da nota seguinte
  (3→4, 4→5, 5→6, 6→7). Ressalva embutida: a produção por pesquisador SATURA a
  partir da nota 4 (Brasil ~10,9 na 4 e ~11–12 nas 5/6/7) — acima da nota 4 o que
  distingue é o IMPACTO, não o volume; logo o incremento de quantidade é condição
  necessária, não suficiente.
- `investiga_quedas.py` — investigação de quedas de produção da UnB ano a ano
  (ver seção abaixo). Gera `relatorio_quedas_unb.xlsx`, `quedas_criticas.png` e
  `lista_vermelha.md`.
- `estatisticas_por_nota.py` — gera `saida/estatisticas_unb_por_nota.xlsx` (os
  92 programas EM FUNCIONAMENTO por nota CAPES vigente + resumo por nota com
  fórmulas vivas). Lê só `../docs/registry.json` e `../docs/dados/area-*.json`
  (nota vigente = `conceito[-1]`; docentes/permanentes = roster do quad. 2021-2024).
- `cache_unb/` — caches do recálculo bruto (gerados; não versionar):
  `art_total_ano.json` (artigos distintos/programa/ano, prod_intel),
  `roster_ano.json` (n_doc/n_perm/n_pq/nota por ano, docentes),
  `prod_artpe_unb.json` (permanentes 2021-24), `prod_autor_unb.json`
  (permanentes 2013-20, por interseção com IDs artpe).
- `saida/` — saídas geradas (não versionar dados pesados).

## Investigação de quedas (`investiga_quedas.py`, 2026-06-17)

Recálculo a partir dos **dados brutos** da CAPES porque a camada
pré-processada (`docs/dados/area-*.json`, campo `prod_ano`) **subnotifica
2021-2024**: ela só credita um artigo ao programa se o docente-autor estiver no
**roster de 2021** (único ano de docentes coletado no quadriênio). Verificado:
ANTROPOLOGIA/UnB tem 128 artigos em 2021 mas só **34** mapeiam ao roster → o
build mostra "queda de 92%" que é **falsa** (produção real estável:
128/122/104/95).

**Sinal limpo:** nº de artigos distintos (`ID_ADD_PRODUCAO_INTELECTUAL`) por
programa por ano, direto de `prod_intel_*_artpe` (cobre 2013-2024, sem depender
de roster nem de vínculo autor). Vínculo por categoria (permanente) vem de
`prod_autor_*` (2013-20, subtipo artigo-em-periódico via interseção de IDs com
o conjunto artpe) e `prod_artpe_*` (2021-24, já só subtipo 25).

**Classificação** pela retenção limpa `ret = média(artigos 2021-24) /
média(artigos 2017-20)`:
- 🟢 **Verde** ret ≥ 0,85 (manteve/cresceu) · 🟡 **Amarelo** 0,50–0,85 ·
  🔴 **Vermelho** ret < 0,50 · ⬛ **Estrutural** (desativado/sucessor/rede
  encerrada — não é alerta).

**Achado central:** no agregado a produção da UnB **não caiu** em 2021-2024
(retenção mediana ≈ **1,11** em artigos brutos). A "queda" da camada
pré-processada e da mediana nacional (que cai de ~8 para ~3 art/doc/ano em 3.378
programas) é **artefato de coleta** (Sucupira em andamento + atribuição ao
roster de 2021), não perda real de produtividade.

**Resultado (84 acadêmicos):** 68 verde, 11 amarelo, **2 vermelho**, 3
estrutural. Vermelhos = Eng. de Sistemas Eletrônicos e Automação (subnotificação
Sucupira) e Biotecnologia–Rede Pró-Centro-Oeste (rede; checar IES parceiras).
Estruturais = Botânica (desativado, sucessor `…112P6`), Tecnologias Química e
Biológica (desativado), Contabilidade UnB-UFPB-UFRN (rede zerada em 2019).

Para rodar é preciso reconstruir os caches uma vez (`build_cache_unb.py`, lê os
CSV/XLSX brutos de `../../dados_capes/`); depois `investiga_quedas.py` roda em
segundos.

**Modalidade (acadêmico × profissional):** os scripts aceitam o argumento `prof`
para analisar os programas **profissionais** em arquivos separados (sufixo
`_profissional`); sem argumento = acadêmicos (padrão).
```bash
python3 investiga_quedas.py            # UnB acadêmicos  → relatorio_quedas_unb.xlsx …
python3 investiga_quedas.py prof       # UnB profissionais → relatorio_quedas_unb_profissional.xlsx …
python3 investiga_nacional.py prof     # nacional profissionais → nacional_quedas_profissional.xlsx
python3 grafico_nacional.py prof       # gráfico nacional profissionais
```
UnB profissionais (13): 🟢9 🟡0 🔴1 (Ensino de Ciências) ⬛3. Nacional profissionais
(909, 341 IES): 🟢642 🟡150 🔴41 ⬛76. **Cautela:** a avaliação de programas
profissionais valoriza muito a **produção técnica/aplicada** (produtos, software,
patentes), não só artigos — o sinal de artigos subnotifica essas modalidades mais
que as acadêmicas; trate os alertas como indicativos.

**Regra de caso estrutural (refinada 2026-06-17):** um programa é ESTRUTURAL
(não-alerta) quando está em desativação, é sucessor de código desativado, OU
**não tem produção em 2020 nem em 2021-24** (última atividade ≤2019 → encerrado/
recodificado antes do período). Isso evita falsos vermelhos de programas que
encerraram em 2019 e cuja atividade migrou para um código-irmão na mesma IES.

## Versão NACIONAL (todas as IES)

- `build_cache_nacional.py` → `cache_nac/` (art_total + roster de todos os
  programas; ~30s).
- `investiga_nacional.py` → `saida/nacional_quedas.xlsx` (+ PDF). Abas:
  **Distribuição**, **Programas** (todos), **Resumo por IES**, **Lista vermelha
  nacional**. Metadados (IES/área/modalidade/situação) vêm de `programas_*.csv`.
- Resultado: **3.866 programas acad. · 377 IES** — 🟢2.966 🟡615 🔴110 ⬛175.
  Mediana nacional da retenção limpa ≈ **1,10** (igual à UnB): no agregado a
  produção nacional **não caiu**; a "queda" é o mesmo artefato de atribuição.
- **Nota:** a contagem nacional é por CD completo (redes/multi-IES somam todos os
  parceiros, deduplicado por ID de artigo), enquanto o relatório UnB fatia por
  `SG_ENTIDADE_ENSINO=='UNB'`. Por isso uma rede pode mudar de classe entre os
  dois (ex.: Biotecnologia-Rede: 🔴 na fatia UnB, 🟡 no total da rede).
- **Cluster Zootecnia investigado (2026-06-17):** NÃO é lacuna de coleta da área.
  Dos 67 programas, só 10 zeraram em 2021-24; ~8 são fusões/encerramentos
  (atividade migrou p/ código-irmão na mesma IES, confirmado no bruto: 0 linhas
  em prod_intel_2021a2024) — agora ESTRUTURAL pela regra refinada. Restam 4
  vermelhos reais (ex.: UTFPR Zootecnia, forte até 2020 e silêncio depois).

## Relatório de incremento (PDF)

`gerar_relatorio_incremento.py` → `saida/relatorio_incremento_pip.pdf` (6 pág.):
fecha a análise das transições **3→4 e 4→5** — metodologia, produção ponderada
por nota (Brasil × UnB), as **4 definições de alvo** (piso e média ponderada da
própria área; mediana e média nacionais), detalhe por programa e conclusões.
Importa o `build_pip` para recalcular os números ao vivo; HTML → PDF via
LibreOffice. Conclusão central: pelo **piso da área**, a produção da UnB já basta
(3→4: incremento 0; 4→5: +102 art/ano) — o salto de nota depende de
qualidade/impacto, não de volume.

## Documento final (PDF)

`gerar_documento.py` → `saida/relatorio_mapa_pg_metodologia.pdf` (9 pág.):
metodologia + resultados + conclusões + as 4 figuras (UnB e Brasil, acad. e
prof.), com as notas de rodapé do período mantidas. Inclui a **ressalva**:
o número de docentes só existe até 2021 nos datasets da CAPES — verificação
universal (4.698 programas com docentes em 2021; **0 em 2022/2023/2024**), e o
roster de 2021 é repetido para estimar a produção por pesquisador nesses anos.
(HTML → PDF via LibreOffice; figuras têm o DPI recarimbado p/ caber na página.)

## Qualis — não usado (decisão 2026-06-17)

**O Qualis foi abandonado.** Não trabalhamos mais com estratos Qualis: a análise
de impacto fica **apenas no fator de impacto OpenAlex**, como já está implementado
(faixas baixo IF<2,2 / médio 2,2–8,0 / alto >8,0, campo `if_perm` em
`build/gerar_dados_completos.py`).

Contexto da decisão: o `SG_ESTRATO` (Qualis) só existe na coleta CAPES até 2016
(de 2017 em diante vem vazio), então um corte "artigos por Qualis" não seria
extraível para 2017-2020 sem recurso a tabelas externas — e o Qualis deixou de
ser o instrumento vigente. Logo, mantemos a métrica de impacto unificada no IF.

## Como rodar

```bash
cd mapa-pg-multi/pip
python3 build_pip.py
```
