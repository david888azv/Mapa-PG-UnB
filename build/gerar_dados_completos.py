#!/usr/bin/env python3
"""
Pipeline batch: gera docs/dados/area-<slug>.json com métricas completas
para as 41 áreas CAPES restantes (Física já vem do migrar_fisica.py).

Estrutura:
  Fase 1 — Pré-filtrar (sequencial, single-pass dos CSVs):
    cache/<slug>/programas.csv, docentes.csv, prod.csv, issn_impacto.csv
  Fase 2 — Calcular métricas (paralela, Pool=8):
    docs/dados/area-<slug>.json (sobrescreve a versão mínima)

Uso:
    python3 gerar_dados_completos.py [--area "QUÍMICA"|--all]
    python3 gerar_dados_completos.py --skip-fase1   # se cache já existe
    python3 gerar_dados_completos.py --workers 8
"""
import os, glob, json, time, argparse, warnings, sys, re, unicodedata
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd

warnings.filterwarnings('ignore')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
CACHE_DIR = os.path.join(REPO, 'build', 'cache')
DOCS_DIR = os.path.join(REPO, 'docs', 'dados')
REGISTRY = os.path.join(REPO, 'docs', 'registry.json')
MANIFEST = os.path.join(REPO, 'docs', 'manifest.json')
OPENALEX = os.path.normpath(os.path.join(REPO, '..', 'openalex_journals.csv'))

QUADRIENIOS = {
    '2013-2016': [2013, 2014, 2015, 2016],
    '2017-2020': [2017, 2018, 2019, 2020],
    '2021-2024': [2021, 2022, 2023, 2024],
}
SUBTIPOS_BIBLIO = {
    25: 'Artigo em Periódico',
    8:  'Resumo',
    9:  'Trabalho de Congresso',
    26: 'Capítulo de Livro',
    10: 'Texto em Jornal',
}
NON_PQ = ('', 'N', 'NÃO', 'NAO', 'NP', '0', 'NAN', 'NONE', 'S/BOLSA', '-')


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')

def load_csv(fp, **kw):
    """Lê CSV CAPES tentando múltiplas codificações."""
    for enc in ('latin-1', 'utf-8-sig', 'utf-8', 'cp1252'):
        try:
            df = pd.read_csv(fp, sep=';', encoding=enc, low_memory=False, **kw)
            df.columns = [c.strip().upper() for c in df.columns]
            return df
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    return None


# ════════════════════════════════════════════════════════════════════
# CATALOGO DE PROGRAMAS (usado pela fase 1 e pelo --refresh-meta)
# ════════════════════════════════════════════════════════════════════
def mapear_programas(areas_alvo):
    """CD_PROGRAMA -> slug da area, e CD_PROGRAMA -> metadado do programa.

    Le os TRES catalogos em ordem cronologica. Sem o de 2021-2024 todo programa
    criado depois de 2020 fica sem metadado, cai fora de cd_to_slug e tem a
    producao do quadrienio DESCARTADA no filtro da fase 1 — eram 217 programas
    e 23.392 registros de producao 2021-2024.

    A IES titular (sigla/uf) e resolvida POR QUADRIENIO, em 'sigla_quad'.

    Uma sigla unica por programa e insuficiente: a titularidade muda ao longo do
    tempo, por tres motivos distintos e indistinguiveis pelo dado —

      rede com coordenacao rotativa  BIONORTE C.-Oeste: UNB 2013-2020,
                                     UFG 2021-2023, UNEMAT 2024
      renomeacao da IES              FUFPI -> UFPI, UFT -> UFNT
      transferencia entre IES        UFRA -> MPEG

    Congelar no primeiro registro dava o rotulo obsoleto a todos os quadrienios;
    'o mais recente manda' dava o rotulo novo a periodos em que o catalogo diz
    outra coisa — tirou da UnB, em 2013-2016 e 2017-2020, um programa que ela
    coordenou nesses anos. Resolver por quadrienio dispensa distinguir os tres
    casos: cada registro leva a IES que o catalogo daquele periodo declara.

    Dentro do quadrienio vale o ANO mais recente com IES unica (um ano com duas
    IES no mesmo CD e empate sem criterio). Quadrienio sem registro herda o
    anterior; os iniciais herdam o primeiro conhecido.

    'sigla'/'uf' no topo do dict seguem o quadrienio mais recente e existem so
    para quem consome o metadado fora do eixo temporal. Os demais campos (nome,
    area, modalidade, situacao) seguem o registro mais recente sem ressalva.
    """
    print('[1.1] Mapeando programas → área CAPES (programas_*.csv)...')
    cd_to_slug = {}
    cd_meta = {}
    cd_ies = defaultdict(lambda: defaultdict(set))   # cd -> an_base -> {(sigla, uf)}
    pgm_files = sorted(
        glob.glob(os.path.join(DATA_DIR, 'programas_2013a2016_*.csv')) +
        glob.glob(os.path.join(DATA_DIR, 'programas_2017a2020_*.csv')) +
        glob.glob(os.path.join(DATA_DIR, 'programas_2021a2024_*.csv'))
    )
    for fp in pgm_files:
        df = load_csv(fp)
        if df is None: continue
        for _, r in df.iterrows():
            area = str(r.get('NM_AREA_AVALIACAO','')).strip()
            if area not in areas_alvo: continue
            cd = r['CD_PROGRAMA_IES']
            an = int(r['AN_BASE'])
            cd_to_slug[cd] = slugify(area)
            cd_ies[cd][an].add((r.get('SG_ENTIDADE_ENSINO','?'), r.get('SG_UF_PROGRAMA','?')))
            cd_meta.setdefault(cd, {
                'sigla': r.get('SG_ENTIDADE_ENSINO','?'),
                'programa': r.get('NM_PROGRAMA_IES','?'),
                'uf': r.get('SG_UF_PROGRAMA','?'),
                'area': area,
                'cd_area': r.get('CD_AREA_AVALIACAO',''),
                'grande_area': r.get('NM_GRANDE_AREA_CONHECIMENTO',''),
                'modalidade': r.get('NM_MODALIDADE_PROGRAMA',''),
                'situacao': r.get('DS_SITUACAO_PROGRAMA',''),
                'an_base': an,
            })
            if an >= cd_meta[cd]['an_base']:
                cd_meta[cd].update({
                    'programa': r.get('NM_PROGRAMA_IES','?'),
                    'area': area,
                    'cd_area': r.get('CD_AREA_AVALIACAO',''),
                    'grande_area': r.get('NM_GRANDE_AREA_CONHECIMENTO',''),
                    'modalidade': r.get('NM_MODALIDADE_PROGRAMA',''),
                    'situacao': r.get('DS_SITUACAO_PROGRAMA',''),
                    'an_base': an,
                })

    # sigla/uf POR QUADRIENIO (ver docstring)
    mudou = 0
    for cd, por_ano in cd_ies.items():
        sq, ultimo = {}, None
        for q in sorted(QUADRIENIOS):                 # ordem cronologica
            escolha = None
            for an in sorted((a for a in por_ano if a in QUADRIENIOS[q]), reverse=True):
                if len(por_ano[an]) == 1:             # ano com IES unica manda
                    escolha = next(iter(por_ano[an]))
                    break
            if escolha is None:
                escolha = ultimo                      # quadrienio sem registro herda o anterior
            else:
                ultimo = escolha
            sq[q] = escolha
        primeiro = next((v for v in sq.values() if v), None)
        sq = {q: (v or primeiro) for q, v in sq.items()}
        if len({v for v in sq.values() if v}) > 1:
            mudou += 1
        cd_meta[cd]['sigla_quad'] = {q: list(v) for q, v in sq.items() if v}
        if sq[max(sq)]:                               # global = quadrienio mais recente
            cd_meta[cd]['sigla'], cd_meta[cd]['uf'] = sq[max(sq)]
    print(f'  {len(cd_to_slug)} programas mapeados em {len(set(cd_to_slug.values()))} áreas')
    print(f'  {mudou} programas trocaram de IES titular entre quadrienios '
          f'(rede com coordenacao rotativa, renomeacao de sigla, transferencia)')
    return cd_to_slug, cd_meta


_CANON_CACHE = {}


def _canon_ies():
    """sigla legada -> (sigla canonica, uf). Vazio se a tabela nao existir.

    Gerada por gerar_canonico_ies.py a partir de CD_ENTIDADE_CAPES. Siglas em
    colisao (duas instituicoes com a mesma sigla) e aliases de alvo ambiguo
    ficam de FORA da tabela de proposito — aqui nao ha o que tratar.
    """
    if 'map' not in _CANON_CACHE:
        p = os.path.join(REPO, 'build', 'ies_canonico.json')
        m = {}
        if os.path.exists(p):
            tab = json.load(open(p, encoding='utf-8'))
            m = {sg: (v['sigla'], v['uf']) for sg, v in tab.get('canonico', {}).items()}
        else:
            # Sem a tabela o build NAO falha — degrada: a ies_list volta a ter uma
            # entrada por rotulo de epoca (FUFPI e UFPI separados) e o filtro do app
            # deixa de unificar. Silencioso demais para um efeito visivel; avisa.
            print('  AVISO: %s ausente — ies_list sem canonicalizacao de sigla. '
                  'Rode gerar_canonico_ies.py.' % os.path.relpath(p, REPO))
        _CANON_CACHE['map'] = m
    return _CANON_CACHE['map']


def checar_cache_coerente(cd_to_slug):
    """Avisa se o cd->area mudou desde a fase 1 que gerou o cache.

    O --refresh-meta reescreve meta.json a partir dos catalogos, mas
    docentes.csv/prod.csv do cache foram filtrados pelo cd_to_slug vigente na
    fase 1. Se um programa mudou de area (ou e novo), o meta.json da area passa
    a listar um cd cujas linhas NAO estao no cache dela — e a fase 2 o descarta
    em silencio no 'if len(dd) == 0: continue'. Perda de dado sem mensagem.
    """
    antigo = {}
    for p in glob.glob(os.path.join(CACHE_DIR, '*', 'meta.json')):
        sl = os.path.basename(os.path.dirname(p))
        try:
            for cd in json.load(open(p, encoding='utf-8')).get('cds', []):
                antigo[cd] = sl
        except Exception:
            continue
    if not antigo:
        return []                       # sem cache anterior: nada a comparar
    divergentes = [(cd, antigo.get(cd), sl) for cd, sl in cd_to_slug.items()
                   if antigo.get(cd) != sl]
    if divergentes:
        novos = [d for d in divergentes if d[1] is None]
        movidos = [d for d in divergentes if d[1] is not None]
        print('  ATENCAO: %d programas nao batem com o cache (%d novos, %d mudaram de area).'
              % (len(divergentes), len(novos), len(movidos)))
        print('           O cache foi filtrado por outro cd_to_slug: as linhas desses')
        print('           programas NAO estao nele e a fase 2 vai descarta-los em silencio.')
        print('           Rode SEM --skip-fase1 para refazer o cache.')
        for cd, de, para in movidos[:5]:
            print('             %s  %s -> %s' % (cd, de, para))
    return divergentes


def gravar_metas(cd_to_slug, cd_meta):
    """cache/<slug>/meta.json — usado pela fase 1 e pelo --refresh-meta."""
    metas = defaultdict(lambda: {'cds': [], 'cd_meta': {}})
    for cd, sl in cd_to_slug.items():
        metas[sl]['cds'].append(cd)
        metas[sl]['cd_meta'][cd] = cd_meta[cd]
    for sl, m in metas.items():
        os.makedirs(os.path.join(CACHE_DIR, sl), exist_ok=True)
        with open(os.path.join(CACHE_DIR, sl, 'meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(m, fh, ensure_ascii=False, indent=2)
    return len(metas)


# ════════════════════════════════════════════════════════════════════
# FASE 1 — PRÉ-FILTRAR
# ════════════════════════════════════════════════════════════════════
def fase1_prefiltrar(areas_alvo):
    """
    Lê os CSVs do dados_capes UMA ÚNICA VEZ, despacha cada linha para o
    cache da área CAPES correspondente. Grava arquivos pequenos em
    cache/<slug>/.
    """
    print(f'\n══ FASE 1 — PRÉ-FILTRAR ({len(areas_alvo)} áreas) ══')

    # ── 1.1 Construir mapa CD_PROGRAMA → slug_area ─────────────────
    cd_to_slug, cd_meta = mapear_programas(areas_alvo)

    # ── 1.2 Pré-criar pastas de cache e estruturas em memória ────
    os.makedirs(CACHE_DIR, exist_ok=True)
    slugs = sorted(set(cd_to_slug.values()))
    for sl in slugs:
        os.makedirs(os.path.join(CACHE_DIR, sl), exist_ok=True)

    # ── 1.3 Filtrar DOCENTES (single pass) ───────────────────────
    print('\n[1.2] Filtrando docentes_*.csv...')
    doc_dfs_por_area = defaultdict(list)  # slug -> [df]
    for fp in sorted(glob.glob(os.path.join(DATA_DIR, 'docentes_*.csv'))):
        bn = os.path.basename(fp)
        df = load_csv(fp)
        if df is None: continue
        # filtrar por CD_PROGRAMA_IES alvo
        df = df[df['CD_PROGRAMA_IES'].isin(cd_to_slug)]
        df['_SLUG'] = df['CD_PROGRAMA_IES'].map(cd_to_slug)
        for sl, sub in df.groupby('_SLUG'):
            sub = sub.drop(columns=['_SLUG'])
            doc_dfs_por_area[sl].append(sub)
        print(f'  {bn}: {len(df):>8,} reg → {len(set(df["_SLUG"])):>2} áreas')
    # gravar
    print('  → gravando cache/<slug>/docentes.csv ...')
    for sl, parts in doc_dfs_por_area.items():
        d = pd.concat(parts, ignore_index=True)
        d.to_csv(os.path.join(CACHE_DIR, sl, 'docentes.csv'),
                 sep=';', index=False, encoding='utf-8-sig')

    # ── 1.4 Filtrar PRODUÇÃO (prod_intel_*_artpe + prod_autor + prod_artpe) ──
    print('\n[1.3] Filtrando produção...')
    prod_paths = (
        sorted(glob.glob(os.path.join(DATA_DIR, 'prod_intel_*_artpe_*.csv'))) +
        sorted(glob.glob(os.path.join(DATA_DIR, 'prod_autor_*.csv'))) +
        sorted(glob.glob(os.path.join(DATA_DIR, 'prod_artpe_*.csv')))
    )
    prod_partes = defaultdict(list)
    issn_partes = defaultdict(list)
    for fp in prod_paths:
        bn = os.path.basename(fp)
        df = load_csv(fp)
        if df is None: continue
        df = df[df['CD_PROGRAMA_IES'].isin(cd_to_slug)]
        df['_SLUG'] = df['CD_PROGRAMA_IES'].map(cd_to_slug)
        is_artpe = 'CD_IDENTIFICADOR_VEICULO' in df.columns and 'prod_intel' in bn
        for sl, sub in df.groupby('_SLUG'):
            sub = sub.drop(columns=['_SLUG'])
            prod_partes[sl].append(sub)
            if is_artpe:
                cols = [c for c in ['ID_ADD_PRODUCAO_INTELECTUAL','AN_BASE',
                                    'CD_PROGRAMA_IES','CD_IDENTIFICADOR_VEICULO',
                                    'DS_TITULO_PADRONIZADO']
                        if c in sub.columns]
                issn_partes[sl].append(sub[cols].copy())
        print(f'  {bn}: {len(df):>10,} reg')

    # XLSX prod_artpe
    for fp in sorted(glob.glob(os.path.join(DATA_DIR, 'prod_artpe_*.xlsx'))):
        bn = os.path.basename(fp)
        try:
            df = pd.read_excel(fp, engine='openpyxl')
        except Exception as e:
            print(f'  {bn}: erro {e}'); continue
        df.columns = [c.strip().upper() for c in df.columns]
        df = df[df['CD_PROGRAMA_IES'].isin(cd_to_slug)]
        df['_SLUG'] = df['CD_PROGRAMA_IES'].map(cd_to_slug)
        for sl, sub in df.groupby('_SLUG'):
            sub = sub.drop(columns=['_SLUG'])
            prod_partes[sl].append(sub)
        print(f'  {bn}: {len(df):>10,} reg')

    print('  → gravando cache/<slug>/prod.csv e issn.csv ...')
    for sl in slugs:
        if sl in prod_partes:
            try:
                d = pd.concat(prod_partes[sl], ignore_index=True, sort=False)
                d.to_csv(os.path.join(CACHE_DIR, sl, 'prod.csv'),
                         sep=';', index=False, encoding='utf-8-sig')
            except Exception as e:
                print(f'  ! erro concat prod {sl}: {e}')
        if sl in issn_partes:
            try:
                d = pd.concat(issn_partes[sl], ignore_index=True, sort=False)
                d.to_csv(os.path.join(CACHE_DIR, sl, 'issn_raw.csv'),
                         sep=';', index=False, encoding='utf-8-sig')
            except Exception as e:
                print(f'  ! erro concat issn {sl}: {e}')

    # ── 1.5 Mapear ISSN → IF do OpenAlex (uma vez global) ────────
    print('\n[1.4] Carregando OpenAlex (ISSN → IF)...')
    if os.path.exists(OPENALEX):
        oa = pd.read_csv(OPENALEX, sep=';', encoding='utf-8-sig')
        issn_lookup = {}
        for _, r in oa.iterrows():
            info = {
                'name_oa': r.get('name', ''),
                'if_2yr': round(float(r.get('mean_citedness_2yr', 0) or 0), 3),
                'h_index': int(r.get('h_index', 0) or 0),
            }
            issn_l = str(r.get('issn_l','')).strip()
            if issn_l and issn_l != 'nan':
                issn_lookup[issn_l] = info
            for issn in str(r.get('issn_all','')).split('|'):
                issn = issn.strip()
                if issn and issn != 'nan' and issn not in issn_lookup:
                    issn_lookup[issn] = info
        print(f'  {len(issn_lookup):,} ISSNs no OpenAlex')

        # gravar issn_impacto.csv por área
        for sl in slugs:
            ip = os.path.join(CACHE_DIR, sl, 'issn_raw.csv')
            if not os.path.exists(ip):
                continue
            df = pd.read_csv(ip, sep=';', encoding='utf-8-sig', low_memory=False)
            df.columns = [c.strip().upper() for c in df.columns]
            rows = []
            seen = set()
            for _, r in df.iterrows():
                pid = r.get('ID_ADD_PRODUCAO_INTELECTUAL')
                if pd.isna(pid) or pid in seen: continue
                seen.add(pid)
                issn = str(r.get('CD_IDENTIFICADOR_VEICULO','')).strip()
                oa_info = issn_lookup.get(issn, {}) if issn and issn != 'nan' else {}
                rows.append({
                    'ID_PROD': int(pid),
                    'ISSN': issn,
                    'IF_2YR': oa_info.get('if_2yr', 0),
                    'H_INDEX': oa_info.get('h_index', 0),
                    'JOURNAL_CAPES': str(r.get('DS_TITULO_PADRONIZADO','')).strip(),
                    'JOURNAL_OA': oa_info.get('name_oa',''),
                })
            pd.DataFrame(rows).to_csv(
                os.path.join(CACHE_DIR, sl, 'issn_impacto.csv'),
                sep=';', index=False, encoding='utf-8-sig'
            )
    else:
        print(f'  AVISO: {OPENALEX} não encontrado — IF não será incluído')

    # gravar metadata por área
    print('\n[1.5] Gravando metadata por área...')
    n = gravar_metas(cd_to_slug, cd_meta)
    print(f'  ✓ {n} áreas em {CACHE_DIR}/')


# ════════════════════════════════════════════════════════════════════
# FASE 2 — CALCULAR MÉTRICAS POR ÁREA (paralelizável)
# ════════════════════════════════════════════════════════════════════
def is_pq(val):
    if pd.isna(val): return False
    s = str(val).strip().upper()
    return s != '' and s not in NON_PQ

def calcular_area(slug):
    """Calcula métricas para uma área a partir de cache/<slug>/ e
    grava docs/dados/area-<slug>.json. Retorna (slug, ok, msg)."""
    try:
        t0 = time.perf_counter()
        cache = os.path.join(CACHE_DIR, slug)
        meta = json.load(open(os.path.join(cache, 'meta.json'), encoding='utf-8'))
        cds_alvo = set(meta['cds'])

        # --- carregar docentes
        df_doc = pd.read_csv(os.path.join(cache, 'docentes.csv'),
                             sep=';', encoding='utf-8-sig', low_memory=False)
        df_doc.columns = [c.strip().upper() for c in df_doc.columns]
        if 'SG_UF_ENTIDADE_ENSINO' in df_doc.columns and 'SG_UF_PROGRAMA' not in df_doc.columns:
            df_doc['SG_UF_PROGRAMA'] = df_doc['SG_UF_ENTIDADE_ENSINO']

        # --- carregar produção
        prod_path = os.path.join(cache, 'prod.csv')
        if os.path.exists(prod_path):
            df_prod = pd.read_csv(prod_path, sep=';', encoding='utf-8-sig', low_memory=False)
            df_prod.columns = [c.strip().upper() for c in df_prod.columns]
            if 'ID_ADD_PRODUCAO_INTELECTUAL' in df_prod.columns and 'ID_PESSOA_DOCENTE' in df_prod.columns:
                df_prod = df_prod.drop_duplicates(
                    subset=['ID_ADD_PRODUCAO_INTELECTUAL','ID_PESSOA_DOCENTE'], keep='first')
        else:
            df_prod = pd.DataFrame()

        # --- carregar IF
        prod_if = {}
        ip = os.path.join(cache, 'issn_impacto.csv')
        if os.path.exists(ip):
            di = pd.read_csv(ip, sep=';', encoding='utf-8-sig', low_memory=False)
            di.columns = [c.strip().upper() for c in di.columns]
            for _, r in di.iterrows():
                pid = r.get('ID_PROD')
                if pd.notna(pid):
                    prod_if[int(pid)] = {
                        'if2': float(r.get('IF_2YR', 0) or 0),
                        'h':   int(r.get('H_INDEX', 0) or 0),
                    }

        # --- programas info
        programs_info = {}
        for cd, m in meta['cd_meta'].items():
            programs_info[cd] = {'sigla': m['sigla'], 'programa': m['programa'],
                                 'uf': m['uf'], 'sigla_quad': m.get('sigla_quad') or {}}

        all_data = []
        for cd, info in programs_info.items():
            for qlabel, anos in QUADRIENIOS.items():
                mask_d = (df_doc['AN_BASE'].isin(anos)) & (df_doc['CD_PROGRAMA_IES'] == cd)
                dd = df_doc[mask_d]
                if len(dd) == 0:
                    continue
                nota_val = pd.to_numeric(dd['CD_CONCEITO_PROGRAMA'], errors='coerce').dropna()
                if len(nota_val) == 0:
                    continue
                nota = int(nota_val.mode().iloc[0])

                # IES titular DESTE quadrienio (ver mapear_programas). O fallback
                # cobre meta.json antigo, gerado antes de sigla_quad existir.
                sg_q, uf_q = info['sigla_quad'].get(qlabel) or [info['sigla'], info['uf']]

                ids_all = set(dd['ID_PESSOA'].dropna().unique())
                ids_pq = set()
                if 'CD_CAT_BOLSA_PRODUTIVIDADE' in dd.columns:
                    ids_pq = set(dd[dd['CD_CAT_BOLSA_PRODUTIVIDADE'].apply(is_pq)]['ID_PESSOA'].dropna().unique())
                ids_spq = ids_all - ids_pq
                n = len(ids_all); npq = len(ids_pq); nspq = len(ids_spq)
                if n == 0: continue

                cat_col = 'DS_CATEGORIA_DOCENTE'
                ids_perm = set(); ids_colab = set(); ids_visit = set()
                if cat_col in dd.columns:
                    ids_perm = set(dd[dd[cat_col].astype(str).str.strip().str.upper() == 'PERMANENTE']['ID_PESSOA'].dropna().unique())
                    ids_colab = set(dd[dd[cat_col].astype(str).str.strip().str.upper() == 'COLABORADOR']['ID_PESSOA'].dropna().unique())
                    ids_visit = set(dd[dd[cat_col].astype(str).str.strip().str.upper() == 'VISITANTE']['ID_PESSOA'].dropna().unique())
                n_perm, n_colab, n_visit = len(ids_perm), len(ids_colab), len(ids_visit)

                if not df_prod.empty:
                    mask_p = (df_prod['AN_BASE'].isin(anos)) & (df_prod['CD_PROGRAMA_IES'] == cd)
                    if 'ID_PESSOA_DOCENTE' in df_prod.columns:
                        mask_p = mask_p & df_prod['ID_PESSOA_DOCENTE'].notna()
                    dp = df_prod[mask_p]
                else:
                    dp = pd.DataFrame()

                n_anos = len(anos)
                # ── ARTIGOS DISTINTOS, não eventos artigo×autor ─────────────────────
                # Antes: `art = dp.groupby('ID_PESSOA_DOCENTE')[...].nunique()` seguido de
                # `sum(art.get(x,0) for x in ids_*)` — isso conta EVENTOS: um artigo com 3
                # autores permanentes entrava 3 vezes. Como as métricas são TAXAS (por
                # docente, por ano), elas embutiam a coautoria interna do programa, e o
                # fator eventos/distintos varia de 1,00 (Filosofia, Artes — autoria única)
                # a 7,52 (mediana 1,18) entre os 4.375 programas. Por não ser constante,
                # não se cancelava na comparação entre programas.
                # Agora: nº de artigos DISTINTOS com ao menos um autor na categoria.
                _tem = (not dp.empty and 'ID_PESSOA_DOCENTE' in dp.columns
                        and 'ID_ADD_PRODUCAO_INTELECTUAL' in dp.columns)

                def _ndist(ids, base=None):
                    """Artigos distintos com >=1 autor em `ids`."""
                    d = dp if base is None else base
                    if not _tem or d.empty or not ids:
                        return 0
                    return int(d[d['ID_PESSOA_DOCENTE'].isin(ids)]
                               ['ID_ADD_PRODUCAO_INTELECTUAL'].dropna().nunique())

                # ── DENOMINADOR = ANOS-DOCENTE, não headcount × 4 ───────────────────
                # Antes: `ma_X = artigos / len(ids_X) / 4`, onde ids_X é a UNIÃO dos
                # rosters do quadriênio — o que trata quem entrou no último ano como se
                # estivesse presente os quatro. Medido nos 13.536 registros
                # programa×quadriênio, `união×4 / anos-docente` tem mediana 1,15-1,19,
                # p90 até 2,0 e máximo 4,0 (corpo docente inteiramente novo a cada ano).
                # Como o fator varia entre programas, NÃO se cancela na comparação:
                # penaliza quem cresce ou tem rotatividade. Mesmo defeito de medida que
                # eventos-vs-artigos-distintos (ver _ndist), e pela mesma razão.
                # Agora: soma, ano a ano, dos docentes distintos DAQUELA categoria
                # naquele ano. `n_perm` & cia. seguem sendo o headcount (a união), que é
                # o que a tela mostra como "nº de permanentes" e continua correto p/ isso.
                def _anos_doc(mask):
                    """Anos-docente: Σ_ano (docentes distintos da categoria naquele ano)."""
                    sub = dd[mask]
                    if sub.empty:
                        return 0
                    return int(sub.groupby('AN_BASE')['ID_PESSOA'].nunique().sum())

                _cat_up = (dd[cat_col].astype(str).str.strip().str.upper()
                           if cat_col in dd.columns else None)
                ad_all = _anos_doc(dd['ID_PESSOA'].notna())
                ad_pq = _anos_doc(dd['ID_PESSOA'].isin(ids_pq)) if ids_pq else 0
                ad_spq = _anos_doc(dd['ID_PESSOA'].isin(ids_spq)) if ids_spq else 0
                if _cat_up is not None:
                    ad_perm = _anos_doc(_cat_up == 'PERMANENTE')
                    ad_colab = _anos_doc(_cat_up == 'COLABORADOR')
                    ad_visit = _anos_doc(_cat_up == 'VISITANTE')
                else:
                    ad_perm = ad_colab = ad_visit = 0

                t_pq = _ndist(ids_pq)
                t_spq = _ndist(ids_spq)
                t_all = _ndist(ids_all)
                ma_pq = round(t_pq / ad_pq, 2) if ad_pq > 0 else 0
                ma_spq = round(t_spq / ad_spq, 2) if ad_spq > 0 else 0
                ma_all = round(t_all / ad_all, 2) if ad_all > 0 else 0
                t_perm = _ndist(ids_perm)
                t_colab = _ndist(ids_colab)
                t_visit = _ndist(ids_visit)
                ma_perm = round(t_perm / ad_perm, 2) if ad_perm > 0 else 0
                ma_colab = round(t_colab / ad_colab, 2) if ad_colab > 0 else 0
                ma_visit = round(t_visit / ad_visit, 2) if ad_visit > 0 else 0
                razao_pc = round(ma_perm / ma_colab, 2) if ma_colab > 0 else 0

                # subtipos
                prod_sub = {}
                has_sub = ('ID_SUBTIPO_PRODUCAO' in dp.columns) and not dp.empty
                for st_id in SUBTIPOS_BIBLIO:
                    # artigos DISTINTOS por subtipo (ver o comentário em _ndist): era
                    # `sum(art_st.get(x,0) for x in ids_*)`, que contava eventos. O app usa
                    # prod_sub no caminho de filtro de tipo — precisa da MESMA unidade dos
                    # ma_*, senão os dois caminhos discordam.
                    dp_st = dp[dp['ID_SUBTIPO_PRODUCAO'] == st_id] if has_sub else dp.iloc[0:0]
                    prod_sub[str(st_id)] = {
                        'total': _ndist(ids_all, dp_st),
                        'perm':  _ndist(ids_perm, dp_st),
                        'colab': _ndist(ids_colab, dp_st),
                        'visit': _ndist(ids_visit, dp_st),
                        'pq':    _ndist(ids_pq, dp_st),
                        'spq':   _ndist(ids_spq, dp_st),
                    }

                # IF
                if prod_if and not dp.empty and 'ID_ADD_PRODUCAO_INTELECTUAL' in dp.columns:
                    pids = dp['ID_ADD_PRODUCAO_INTELECTUAL'].dropna().unique()
                    ifs = [prod_if[int(p)]['if2'] for p in pids if int(p) in prod_if and prod_if[int(p)]['if2'] > 0]
                    avg_if = round(sum(ifs)/len(ifs), 3) if ifs else 0
                    med_if = round(sorted(ifs)[len(ifs)//2], 3) if ifs else 0
                    max_if = round(max(ifs), 3) if ifs else 0
                    n_if = len(ifs)
                    n_lo = sum(1 for x in ifs if x < 2.2)
                    n_mi = sum(1 for x in ifs if 2.2 <= x <= 8.0)
                    n_hi = sum(1 for x in ifs if x > 8.0)
                    # Faixas de IF por categoria de docente, em artigos DISTINTOS.
                    # Antes o `cnt()` percorria docente por docente somando os artigos de
                    # cada um: um artigo com 3 autores permanentes entrava 3x na faixa.
                    # Agora conta o artigo UMA vez se tiver >=1 autor na categoria — mesma
                    # unidade de avg_if/n_if (que sempre foram sobre pids distintos) e de
                    # ma_*/prod_sub. Ver o comentário em _ndist.
                    def cnt(idset):
                        lo = mi = hi = 0
                        if not _tem or dp.empty or not idset:
                            return lo, mi, hi
                        sub = dp[dp['ID_PESSOA_DOCENTE'].isin(idset)]
                        for p in sub['ID_ADD_PRODUCAO_INTELECTUAL'].dropna().unique():
                            info_if = prod_if.get(int(p))
                            if not info_if or info_if['if2'] <= 0:
                                continue
                            ifv = info_if['if2']
                            if ifv < 2.2: lo += 1
                            elif ifv <= 8.0: mi += 1
                            else: hi += 1
                        return lo, mi, hi
                    perm_lo, perm_mi, perm_hi = cnt(ids_perm)
                    colab_lo, colab_mi, colab_hi = cnt(ids_colab)
                    visit_lo, visit_mi, visit_hi = cnt(ids_visit)
                    all_lo, all_mi, all_hi = cnt(ids_all)
                else:
                    avg_if = med_if = max_if = n_if = 0
                    n_lo=n_mi=n_hi=0
                    perm_lo=perm_mi=perm_hi=0
                    colab_lo=colab_mi=colab_hi=0
                    visit_lo=visit_mi=visit_hi=0
                    all_lo=all_mi=all_hi=0

                # produção por ano
                # Denominador = o roster DAQUELE ano, não a união do quadriênio (que era
                # o defeito: dividia os artigos de 1 ano pelo headcount de 4). Para uma
                # série anual isso é o próprio anos-docente do ano.
                prod_ano = {}
                for ano in anos:
                    # artigos DISTINTOS no ano (ver _ndist): era soma por docente = eventos
                    da = dp[dp['AN_BASE'] == ano] if not dp.empty else dp.iloc[0:0]
                    dd_ano = dd[dd['AN_BASE'] == ano]
                    n_doc_ano = int(dd_ano['ID_PESSOA'].nunique()) if len(dd_ano) > 0 else 0
                    ids_ano = set(dd_ano['ID_PESSOA'].dropna().unique())
                    npq_ano = len(ids_pq & ids_ano)
                    nspq_ano = len(ids_spq & ids_ano)
                    mp = round(_ndist(ids_pq, da) / npq_ano, 2) if npq_ano > 0 else 0
                    ms = round(_ndist(ids_spq, da) / nspq_ano, 2) if nspq_ano > 0 else 0
                    mg = round(_ndist(ids_all, da) / n_doc_ano, 2) if n_doc_ano > 0 else 0
                    prod_ano[str(ano)] = [mp, ms, mg, n_doc_ano]

                m = meta['cd_meta'][cd]
                all_data.append({
                    'cd': cd, 'sigla': sg_q, 'programa': info['programa'],
                    'uf': uf_q, 'nota': nota, 'quad': qlabel,
                    'n_doc': n, 'n_pq': npq, 'n_spq': nspq,
                    'pct_pq': round(npq/n*100, 1),
                    'ma_pq': ma_pq, 'ma_spq': ma_spq, 'ma_all': ma_all,
                    'razao': round(ma_pq/ma_spq, 2) if ma_spq > 0 else 0,
                    'n_perm': n_perm, 'n_colab': n_colab, 'n_visit': n_visit,
                    'ma_perm': ma_perm, 'ma_colab': ma_colab, 'ma_visit': ma_visit,
                    'razao_pc': razao_pc,
                    # ANOS-DOCENTE por categoria = denominador das taxas ma_*.
                    # n_* acima é headcount (união do quadriênio) e serve p/ exibir
                    # "nº de docentes"; NÃO usar n_*×4 como denominador (ver _anos_doc).
                    'ad_all': ad_all, 'ad_pq': ad_pq, 'ad_spq': ad_spq,
                    'ad_perm': ad_perm, 'ad_colab': ad_colab, 'ad_visit': ad_visit,
                    'avg_if': avg_if, 'med_if': med_if, 'max_if': max_if, 'n_if': n_if,
                    'if_lo': n_lo, 'if_mi': n_mi, 'if_hi': n_hi,
                    'if_perm':  [perm_lo, perm_mi, perm_hi],
                    'if_colab': [colab_lo, colab_mi, colab_hi],
                    'if_visit': [visit_lo, visit_mi, visit_hi],
                    'if_all':   [all_lo, all_mi, all_hi],
                    'prod_ano': prod_ano, 'prod_sub': prod_sub,
                    'is_unb': (sg_q == 'UNB'),
                    'modalidade': m.get('modalidade',''),
                    'situacao':   m.get('situacao',''),
                })

        # forward-fill n_doc_ano (último valor conhecido)
        prog_records = defaultdict(list)
        for rec in all_data:
            prog_records[rec['cd']].append(rec)
        for cd, recs in prog_records.items():
            year_doc = {}
            for r in recs:
                for y_str, vals in r['prod_ano'].items():
                    if len(vals) >= 4:
                        year_doc[int(y_str)] = vals[3]
            last = 0
            for y in range(2013, 2025):
                if y in year_doc:
                    if year_doc[y] > 0: last = year_doc[y]
                    elif last > 0: year_doc[y] = last
            for r in recs:
                for y_str, vals in r['prod_ano'].items():
                    if len(vals) >= 4:
                        vals[3] = year_doc.get(int(y_str), vals[3])

        if not all_data:
            return (slug, False, 'sem registros calculados (sem cruzamento docentes/programas)')

        # construir output
        # ies_list agrupada por INSTITUICAO, nao por rotulo. Como a sigla do
        # registro e a da epoca (ver mapear_programas), FUFPI e UFPI sairiam como
        # duas entradas do filtro. O alias vem de build/ies_canonico.json, chaveado
        # por CD_ENTIDADE_CAPES. Os registros MANTEM a sigla de epoca; quem
        # canonicaliza e a lista — e o app filtra por ela via 'alias'.
        canon = _canon_ies()
        grupos = defaultdict(lambda: {'uf': '', 'alias': set()})
        for d in all_data:
            c = canon.get(d['sigla'])
            sg, uf = (c if c else (d['sigla'], d['uf']))
            g = grupos[sg]
            g['uf'] = g['uf'] or uf
            if d['sigla'] != sg:
                g['alias'].add(d['sigla'])
        ies_set = sorted((sg, g['uf'], sorted(g['alias'])) for sg, g in grupos.items())
        notas = sorted(set(d['nota'] for d in all_data))
        unb_cds = sorted(set(d['cd'] for d in all_data if d.get('is_unb')))
        area_name = next(iter(meta['cd_meta'].values()))['area']
        cd_area = next(iter(meta['cd_meta'].values())).get('cd_area','')
        grande = next(iter(meta['cd_meta'].values())).get('grande_area','')
        out = {
            'metadata': {
                'area': area_name,
                'cd_area': cd_area,
                'grande_area': grande,
                'slug': slug,
                'quadrienios': QUADRIENIOS,
                'unb_cd': unb_cds[0] if unb_cds else '',
                'unb_cds': unb_cds,
                'n_unb': len(unb_cds),
                'n_programas': len(programs_info),
                'n_registros': len(all_data),
                'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
                'subtipos_biblio': {str(k): v for k, v in SUBTIPOS_BIBLIO.items()},
                'tem_metricas': True,
                'fonte': 'CAPES — programas + docentes + prod_intel_artpe + OpenAlex (IF 2yr)',
            },
            'ies_list': [({'sigla': s, 'uf': u, 'alias': al} if al else {'sigla': s, 'uf': u})
                         for s, u, al in ies_set],
            'notas': notas,
            'data': all_data,
        }

        out_path = os.path.join(DOCS_DIR, f'area-{slug}.json')
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, ensure_ascii=False, separators=(',',':'))
        sz = os.path.getsize(out_path)/1024
        dt = time.perf_counter() - t0
        return (slug, True, f'{len(all_data)} reg | {sz:.0f} KB | {dt:.1f}s')

    except Exception as e:
        import traceback
        return (slug, False, f'EXCEÇÃO: {e}\n{traceback.format_exc()[-400:]}')


def fase2_paralela(slugs, workers):
    print(f'\n══ FASE 2 — CALCULAR MÉTRICAS ({len(slugs)} áreas, {workers} workers) ══')
    t0 = time.perf_counter()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(calcular_area, sl): sl for sl in slugs}
        for i, fut in enumerate(as_completed(futs), 1):
            sl = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = (sl, False, f'crash: {e}')
            results.append(r)
            tag = '✓' if r[1] else '✗'
            print(f'  [{i:2d}/{len(slugs)}] {tag} {r[0]:<55s} {r[2]}')
    dt = time.perf_counter() - t0
    ok = sum(1 for _,o,_ in results if o)
    print(f'\n✓ {ok}/{len(results)} OK em {dt:.1f}s')
    return results


def atualizar_manifest(slugs_ok):
    """Marca tem_metricas=true para áreas geradas."""
    mf = json.load(open(MANIFEST))
    for a in mf['areas']:
        if a['slug'] in slugs_ok:
            a['tem_metricas'] = True
            p = os.path.join(DOCS_DIR, f"area-{a['slug']}.json")
            if os.path.exists(p):
                a['tamanho_kb'] = round(os.path.getsize(p)/1024)
                d = json.load(open(p))
                a['n_registros'] = len(d['data'])
    mf['atualizado_em'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        json.dump(mf, fh, ensure_ascii=False, indent=2)
    print(f'✓ manifest atualizado: {len(slugs_ok)} áreas com tem_metricas=true')


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════
def listar_areas():
    """Imprime os 42 slugs disponíveis com nome, nº programas UnB e estado de métricas."""
    catalog = json.load(open(REGISTRY))
    try:
        manifest = json.load(open(MANIFEST))
        mf_idx = {a['slug']: a for a in manifest['areas']}
    except Exception:
        mf_idx = {}
    rows = []
    for nome, info in catalog['areas_capes'].items():
        sl = info['slug']
        m = mf_idx.get(sl, {})
        rows.append((sl, nome, info['n_unb'], ','.join(info['sufixos_unb']),
                     m.get('tem_metricas', False), m.get('tamanho_kb', 0)))
    rows.sort(key=lambda r: r[0])
    print(f"\n{'SLUG':<55} {'UnB':>3}  {'KB':>5}  M  ÁREA / SUFIXOS")
    print('─' * 130)
    for sl, nm, n, sufs, tm, kb in rows:
        flag = '✓' if tm else ' '
        print(f"{sl:<55} {n:>3}  {kb:>5}  {flag}  {nm}")
        if sufs:
            print(f"{'':<55} {'':>3}  {'':>5}     ↳ {sufs}")
    print('─' * 130)
    print(f"Total: {len(rows)} áreas | "
          f"{sum(1 for r in rows if r[4])} com métricas | "
          f"{sum(r[5] for r in rows)} KB")
    print(f"\nUso: python3 {os.path.basename(__file__)} --only <SLUG> --skip-fase1")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--skip-fase1', action='store_true', help='reaproveita cache existente')
    ap.add_argument('--refresh-meta', action='store_true',
                    help='so reescreve cache/<slug>/meta.json a partir dos catalogos '
                         'programas_*.csv. Use com --skip-fase1 quando mudar a regra de '
                         'metadado: o meta.json e gravado no FIM da fase 1, entao sem isso '
                         'a fase 2 leria o metadado velho do cache.')
    ap.add_argument('--force', action='store_true',
                    help='segue mesmo com o cache incoerente com o catalogo '
                         '(--refresh-meta + --skip-fase1). Assume a perda dos '
                         'programas cujas linhas nao estao no cache.')
    # Astronomia/Física É processada por padrão (default=False). O default=True
    # anterior era legado de quando a Física vinha do migrar_fisica.py; com
    # store_true ele deixava a flag SEMPRE ligada, e um build completo excluía
    # silenciosamente a área central do projeto (só um --only a alcançava). Passar
    # --skip-fisica ainda pula, mas agora é escolha explícita, não o padrão.
    ap.add_argument('--skip-fisica', action='store_true', default=False,
                    help='pula astronomia-fisica (NÃO recomendado; a Física entra por padrão)')
    ap.add_argument('--only', help='só uma área (slug)')
    ap.add_argument('--list', action='store_true', help='lista as 42 áreas e seus slugs e sai')
    args = ap.parse_args()

    if args.list:
        listar_areas()
        return

    catalog = json.load(open(REGISTRY))
    areas_todas = sorted(catalog['areas_capes'].keys())
    print(f'Áreas no registry: {len(areas_todas)}')

    # Validar --only contra slugs conhecidos
    if args.only:
        all_slugs = set(catalog['areas_capes'][a]['slug'] for a in areas_todas)
        if args.only not in all_slugs:
            print(f"✗ Slug desconhecido: {args.only!r}")
            print(f"  Use --list para ver os {len(all_slugs)} slugs válidos.")
            sys.exit(2)

    if args.refresh_meta:
        cd_to_slug, cd_meta = mapear_programas(set(areas_todas))
        div = checar_cache_coerente(cd_to_slug)
        if div and args.skip_fase1 and not args.force:
            sys.exit('✗ abortado: cache incoerente com o catalogo (use --force para '
                     'assumir a perda, ou rode sem --skip-fase1).')
        n = gravar_metas(cd_to_slug, cd_meta)
        print(f'★ meta.json reescrito em {n} áreas (--refresh-meta)')

    if not args.skip_fase1:
        fase1_prefiltrar(set(areas_todas))
    else:
        print('★ FASE 1 pulada (--skip-fase1)')

    slugs = sorted(set(catalog['areas_capes'][a]['slug'] for a in areas_todas))
    if args.skip_fisica:
        slugs = [s for s in slugs if s != 'astronomia-fisica']
    if args.only:
        slugs = [args.only]

    res = fase2_paralela(slugs, args.workers)
    ok = [s for s,o,_ in res if o]
    fail = [(s,m) for s,o,m in res if not o]
    if fail:
        print('\nFALHAS:')
        for s,m in fail:
            print(f'  ✗ {s}: {m}')

    atualizar_manifest(set(ok))
    print(f'\n=== {len(ok)} áreas com métricas completas ===')

if __name__ == '__main__':
    main()
