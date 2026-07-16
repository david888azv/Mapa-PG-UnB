# MAPA-PG — Monitoramento e Análise da Produção Acadêmica da Pós-Graduação

Sistema interativo e gratuito para comparar a produção e os indicadores de **4.776
programas de pós-graduação** do Brasil (**500 instituições**) em todas as **49 Áreas de
Avaliação da CAPES**, ao longo de três quadriênios (2013–2024). Cada programa é comparado
sempre **dentro da própria Área CAPES** — a única comparação válida segundo a metodologia
da CAPES.

### 🔗 Abrir o aplicativo: **https://david888azv.github.io/Mapa-PG-UnB/**

Escolha uma das **27 universidades federais** como referência e compare-a com seus pares
nacionais. Uma página por instituição, por exemplo:

| | |
|---|---|
| 🏛️ **UnB** | https://david888azv.github.io/Mapa-PG-UnB/ies/unb/ |
| 🏛️ **UFRN** | https://david888azv.github.io/Mapa-PG-UnB/ies/ufrn/ |
| 🏛️ **UFPE** | https://david888azv.github.io/Mapa-PG-UnB/ies/ufpe/ |
| 🏛️ **UFBA** | https://david888azv.github.io/Mapa-PG-UnB/ies/ufba/ |

Parte do projeto de divulgação científica **DA ciência** — https://daciencia.org

> **Cobertura (16/07/2026):** as **49** Áreas de Avaliação da CAPES. Até esta data eram 42 —
> o catálogo de áreas era derivado da pegada da UnB (`gerar_registry.py` montava `areas_capes`
> iterando sobre os programas dela), então as 7 áreas em que a UnB não atua sumiam do app
> inteiro: CIÊNCIAS BIOLÓGICAS II, ENGENHARIAS II, ZOOTECNIA/RECURSOS PESQUEIROS, CIÊNCIA DE
> ALIMENTOS, MEDICINA III, PLANEJAMENTO URBANO E REGIONAL/DEMOGRAFIA e CIÊNCIAS DA RELIGIÃO E
> TEOLOGIA (442 programas). O catálogo agora é nacional; áreas sem UnB entram com `n_unb=0`.

## Projeto irmão (graduação): MAPA-GR

Os mesmos princípios, aplicados à graduação sob o INEP/SINAES (CPC, ENADE, IDD, IGC),
em 47.091 cursos:

- Aplicativo: https://david888azv.github.io/Mapa-GR/
- Repositório: https://github.com/david888azv/Mapa-GR

| | MAPA-PG | MAPA-GR |
|---|---|---|
| Nível | Pós-graduação | Graduação |
| Órgão | CAPES | INEP/SINAES |
| Escala | 1–7 | 1–5 |
| Unidade | Programa | Curso |

## Programas da UnB

O aplicativo nasceu do acompanhamento dos **92 programas de pós-graduação da UnB** em
funcionamento (82 acadêmicos e 10 profissionais), que seguem sendo o recorte de referência
do projeto, e se generalizou para as demais instituições.

## Identificação dos programas

Cada programa UnB recebe um identificador `MAPA-PG-XXXXXX`, com sufixo
de até 6 letras maiúsculas. Programas profissionais que coexistem com
acadêmicos do mesmo nome recebem sufixo terminado em `P`
(ex.: `ADMIN`/`ADMINP`, `ECONOM`/`ECONOP`, `ENGELE`/`ENGELP`).

Mapeamento canônico em [`docs/registry.json`](docs/registry.json).

Acesso direto via deeplink: `index.html?curso=FISICA`.

## Arquitetura (Opção D — híbrida)

- **Shell único** `docs/index.html` (~104 KB) reaproveita 100% do
  layout, gráficos, filtros e relatórios do `MAPA-PG-FISICA`
  (1.4-mapa-pg.html).
- **Dados particionados por Área CAPES** (`docs/dados/area-<slug>.json`)
  carregados sob demanda — 100–400 KB por área.
- **Pastas por curso** `docs/cursos/<SUFIXO>/` com `meta.json` e `README.md`
  (conteúdo editorial isolado, opcional).
- **PWA**: `app.webmanifest` + `sw.js` com cache versionado para uso
  offline depois da 1ª visita.

## Custo de banda

| Cenário                                     | Banda           |
|---------------------------------------------|-----------------|
| 1ª visita (área de Física)                  | ~365 KB         |
| 2ª visita (qualquer área já carregada)      | 0 KB (cache SW) |
| Trocar de curso na **mesma** área           | 0 KB            |
| Trocar para outra área                      | 100–400 KB      |
| Repositório completo (tudo cacheado)        | 5,3 MB          |

## Camadas de dados

1. **Camada mínima** (já gerada — 49 áreas): metadados de programas,
   conceito CAPES por quadriênio, modalidade, situação. Total ≈ 4 MB.
2. **Camada com métricas completas** (já gerada para **todas as 49 áreas** —
   `docs/dados/area-*.json`, ~11,8 MB no total; `manifest.json` marca
   `tem_metricas: true` nas 42): n_doc, médias por categoria, fator de
   impacto OpenAlex, produção por subtipo bibliográfico. A migração inicial
   da Física (`MAPA-PG-FISICA`) é preservada como referência.

A camada completa é gerada por `build/gerar_dados_completos.py`
(pipeline batch offline a partir dos CSVs CAPES + `openalex_journals.csv`).

## Pipeline batch — estratégia de paralelismo

A leitura ingênua "8 áreas em paralelo, cada uma lendo todo o
`dados_capes/` (7,5 GB)" gera 60 GB de I/O concorrente. Estratégia
adotada:

1. **Fase 1 — Pré-filtro single-pass (sequencial, I/O-bound)**: lê cada
   CSV de `dados_capes/` uma única vez e despacha cada linha para o
   cache da área CAPES correspondente — `build/cache/<slug>/`.
2. **Fase 2 — Cálculo de métricas (paralelo, Pool=8, CPU-bound)**: cada
   worker pega uma área pré-filtrada (já pequena) e gera o
   `area-<slug>.json`. Escala bem porque cada área é independente.

Total: ~16 min na 1ª execução; subsequentes ~3,5 min se reaproveitar
o cache. Comandos:

```bash
# Listar as 49 áreas, slugs e estado de métricas
python3 build/gerar_dados_completos.py --list

# Tudo do zero (Fase 1 + Fase 2) — ~16 min
python3 build/gerar_dados_completos.py --workers 8

# Só Fase 2, todas as áreas (cache existente) — ~3,5 min
python3 build/gerar_dados_completos.py --skip-fase1

# Uma única área (cache existente) — 3 a 150 s
python3 build/gerar_dados_completos.py --only quimica --skip-fase1
```

Slug inválido sai com exit 2 e instrução para usar `--list`.

## Estrutura

```
mapa-pg-multi/
├── README.md
├── build/
│   ├── gerar_registry.py         — 92 sufixos UnB
│   ├── gerar_dados_minimos.py    — 42 JSONs de área (camada mínima)
│   ├── migrar_fisica.py          — slot área-astronomia-fisica.json com métricas
│   └── gerar_cursos_meta.py      — 92 pastas docs/cursos/<SUFIXO>/
└── docs/                         ← raiz do GitHub Pages
    ├── index.html                — shell multi-área
    ├── chart.umd.min.js
    ├── help-doc.html
    ├── manifest.json             — catálogo de áreas
    ├── registry.json             — registro dos 92 programas UnB
    ├── app.webmanifest           — PWA
    ├── sw.js                     — Service Worker (cache offline)
    ├── logos/                    — UnB / CAPES / CNPq / FAPDF
    ├── dados/
    │   ├── area-astronomia-fisica.json    (com métricas)
    │   ├── area-quimica.json              (mínimo)
    │   ├── area-engenharias-i.json        (mínimo)
    │   └── ... (42 arquivos)
    └── cursos/
        ├── FISICA/  ← MAPA-PG-FISICA (referência)
        ├── QUIMIC/  ← MAPA-PG-QUIMIC
        ├── PSCDES/  ← MAPA-PG-PSCDES
        └── ... (92 pastas)
```

## Como visualizar localmente

```bash
cd mapa-pg-multi/docs
python3 -m http.server 8000
# Abrir http://localhost:8000/?curso=FISICA
```

## Como publicar no GitHub Pages

Apontar Pages para `docs/` no branch principal. Nenhum build adicional
necessário — todo o conteúdo é estático.

## Autor

**Prof. Titular David Lima Azevedo**
Grupo de Dinâmica e Ab Initio (GDAI) · Núcleo de Estrutura da Matéria
Instituto de Física — Universidade de Brasília (UnB)

- ORCID: https://orcid.org/0000-0002-3456-554X
- Google Scholar: https://scholar.google.com.br/citations?hl=en&user=o-qWsUAAAAAJ&view_op=list_works&sortby=pubdate
- Lattes: http://lattes.cnpq.br/3892893860696339
- E-mail: david888azv@unb.br

## Como citar

AZEVEDO, D. L. **MAPA-PG — um sistema interativo para monitoramento e análise de
produção acadêmica: aplicação à área de Astronomia e Física**. *Physicae Organum*,
Brasília, v. 11, n. 1, 2026. DOI:
[10.26512/2446-564X2026e62064](https://doi.org/10.26512/2446-564X2026e62064).

Veja também `CITATION.cff` (formato legível por máquina).
