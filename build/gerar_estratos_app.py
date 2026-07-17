#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_estratos_app.py — ENRIQUECE os JSON dos aplicativos (mapa-pg-multi e mapa-pg)
com a estratificação CAPES A1-A8/C (Ficha de Avaliação 2025-2028), por PERCENTIL do
periódico DENTRO da área (classes de 12,5%), para CADA categoria de docente e para
CADA UMA DE TRÊS BASES de indicador de impacto:

  • cs (CiteScore 2025, Scopus)  — fonte OFICIAL CAPES; é o PADRÃO do app.
  • oa (OpenAlex IF 2 anos)      — base aberta, cobertura máxima (comportamento legado).
  • hb (Híbrido)                 — CiteScore onde há; senão percentil OpenAlex; senão C.

Somente ADIÇÃO: nunca altera campos existentes. Para cada registro programa×quad
acrescenta, POR BASE, 4 vetores de 9 inteiros (ordem A1..A8,C):
    estr_perm_<b>, estr_colab_<b>, estr_visit_<b>, estr_all_<b>   (b em cs/oa/hb)
e mantém os campos SEM sufixo (estr_perm, ...) = base CiteScore (padrão), p/
retrocompatibilidade do app. No metadata.estratos_<b> vai cortes_if/dist_issn/labels_pct/
fonte/frac_c por base; metadata.estratos = cópia de metadata.estratos_cs.

Fontes: OpenAlex = IF_2YR de build/cache/<slug>/issn_impacto.csv; CiteScore =
../pip-2-refatorado-citescore/dados_citescore/citescore_2025_TODAS_AREAS.csv (casado por
ISSN via crosswalk ISSN->ISSN-L de ../../openalex_journals.csv).

Contagem em EVENTOS artigo×autor. Invariante: Σ dos 9 estratos é IGUAL entre as 3 bases
(muda só a distribuição). Na base oa, Σ A1..A8 == Σ if_<cat>(lo+mi+hi) (paridade legada).

Uso:
    python3 gerar_estratos_app.py                 # todas as 42 áreas + Física
    python3 gerar_estratos_app.py <slug>          # só uma área (teste/validação)
"""
import os
import gc
import sys
import glob
import json
import time

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(AQUI, '..'))          # mapa-pg-multi/
CACHE_DIR = os.path.join(REPO, 'build', 'cache')
DOCS_DADOS = os.path.join(REPO, 'docs', 'dados')           # area-*.json
FISICA_JSON = os.path.normpath(os.path.join(REPO, '..', 'mapa-pg', 'docs', 'dados_fisica.json'))
FISICA_SLUG = 'astronomia-fisica'
OPENAL = os.path.normpath(os.path.join(REPO, '..', 'openalex_journals.csv'))
CS_CSV = os.path.join(REPO, 'pip-2-refatorado-citescore', 'dados_citescore',
                      'citescore_2025_TODAS_AREAS.csv')

QUADRIENIOS = {'2013-2016': [2013, 2014, 2015, 2016],
               '2017-2020': [2017, 2018, 2019, 2020],
               '2021-2024': [2021, 2022, 2023, 2024]}
ANO2QUAD = {a: q for q, anos in QUADRIENIOS.items() for a in anos}
SUBTIPO_ARTIGO = 25
ESTRATOS = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'C']
CORTES = [('A1', 87.5), ('A2', 75.0), ('A3', 62.5), ('A4', 50.0),
          ('A5', 37.5), ('A6', 25.0), ('A7', 12.5), ('A8', 0.0)]
LABELS_PCT = {
    'A1': 'percentil 87,5–100%', 'A2': 'percentil 75–87,5%',
    'A3': 'percentil 62,5–75%', 'A4': 'percentil 50–62,5%',
    'A5': 'percentil 37,5–50%', 'A6': 'percentil 25–37,5%',
    'A7': 'percentil 12,5–25%', 'A8': 'percentil 0–12,5%',
    'C': 'sem indicador',
}
BASES = ['cs', 'oa', 'hb']
FONTE_BASE = {
    'cs': 'CiteScore 2025 (Scopus) — fonte oficial CAPES 2025-2028 (C = sem CiteScore)',
    'oa': 'OpenAlex — IF de 2 anos (mean citedness) por periódico (C = sem indicador)',
    'hb': 'Híbrido — CiteScore (Scopus) onde há; senão percentil OpenAlex; C = sem nenhum',
}


def estrato_de_pct(p):
    for nome, lim in CORTES:
        if p >= lim:
            return nome
    return 'A8'


def _norm(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    x = str(x).strip().upper()
    if x.endswith('.0'):
        x = x[:-2]
    x = x.replace('-', '').replace(' ', '')
    if len(x) == 7:
        x = '0' + x
    return x if len(x) == 8 and x[:7].isdigit() else None


def carregar_crosswalk():
    oa = pd.read_csv(OPENAL, sep=';', usecols=['issn_l', 'issn_all'],
                     dtype=str, encoding='utf-8-sig')
    canon = {}
    for l, allv in zip(oa['issn_l'], oa['issn_all']):
        nl = _norm(l)
        if not nl:
            continue
        canon.setdefault(nl, nl)
        if isinstance(allv, str):
            for t in allv.split('|'):
                n = _norm(t)
                if n:
                    canon[n] = nl
    return canon


def carregar_citescore(canon):
    def ca(n):
        n = _norm(n)
        return canon.get(n, n) if n else None
    cs = pd.read_csv(CS_CSV, encoding='utf-8-sig', low_memory=False,
                     usecols=['issn', 'eissn', 'citescore'])
    cs['citescore'] = pd.to_numeric(cs['citescore'], errors='coerce')
    cs = cs.dropna(subset=['citescore'])
    cs = cs[cs['citescore'] > 0]
    issn2cs = {}
    for p, e, v in zip(cs['issn'], cs['eissn'], cs['citescore']):
        for issn in (p, e):
            c = ca(issn)
            if c and c not in issn2cs:
                issn2cs[c] = float(v)
    return issn2cs, ca


def _mapa_estratos(issn_index, issn2if, issn2csv):
    """Para uma base, devolve (issn2estrato, cortes_if, dist_issn) das 3 regras."""
    # OpenAlex
    oa_vals = np.array([v for v in issn2if.values if v > 0]) if len(issn2if) else np.array([])
    # CiteScore
    cs_vals = np.array(list(issn2csv.values()))
    out = {}
    for base in BASES:
        e_map = {}
        for issn in issn_index:
            if base == 'oa':
                v = issn2if.get(issn, 0.0)
                if v > 0 and len(oa_vals):
                    e_map[issn] = estrato_de_pct(percentileofscore(oa_vals, v, kind='mean'))
            elif base == 'cs':
                v = issn2csv.get(issn)
                if v and len(cs_vals):
                    e_map[issn] = estrato_de_pct(percentileofscore(cs_vals, v, kind='mean'))
            else:  # hb
                v = issn2csv.get(issn)
                if v and len(cs_vals):
                    e_map[issn] = estrato_de_pct(percentileofscore(cs_vals, v, kind='mean'))
                else:
                    vo = issn2if.get(issn, 0.0)
                    if vo > 0 and len(oa_vals):
                        e_map[issn] = estrato_de_pct(percentileofscore(oa_vals, vo, kind='mean'))
        # cortes de indicador observados por estrato (limite inferior) — p/ rótulos
        cortes = {}
        for issn, e in e_map.items():
            val = (issn2csv.get(issn) if base in ('cs', 'hb') and issn in issn2csv
                   else issn2if.get(issn, 0.0))
            cortes[e] = min(cortes.get(e, val), val)
        dist = {x: 0 for x in ESTRATOS}
        for issn in issn_index:
            dist[e_map.get(issn, 'C')] += 1
        out[base] = (e_map, cortes, dist)
    return out


def computar_estratos_area(slug, issn2cs, ca):
    """Devolve dict base -> (cortes_if, dist_issn, programas, frac_c). programas:
    {f'{cd}|{quad}': {estr_perm/colab/visit/all}}."""
    cache = os.path.join(CACHE_DIR, slug)

    # ---- 1. ISSN → IF OpenAlex + CiteScore; 3 mapas de estrato ----
    di = pd.read_csv(os.path.join(cache, 'issn_impacto.csv'), sep=';',
                     encoding='utf-8-sig', low_memory=False,
                     usecols=lambda c: c.strip().upper() in ('ID_PROD', 'ISSN', 'IF_2YR'))
    di.columns = [c.strip().upper() for c in di.columns]
    di['ID_PROD'] = pd.to_numeric(di['ID_PROD'], errors='coerce')
    di = di.dropna(subset=['ID_PROD'])
    di['ID_PROD'] = di['ID_PROD'].astype(np.int64)
    di['IF_2YR'] = pd.to_numeric(di['IF_2YR'], errors='coerce').fillna(0.0)
    di['ISSN'] = di['ISSN'].astype(str).str.strip()
    art2issn = dict(zip(di['ID_PROD'], di['ISSN']))
    issn2if = di.groupby('ISSN')['IF_2YR'].first()
    issn_index = list(issn2if.index)
    issn2csv = {}
    for issn in issn_index:
        c = ca(issn)
        v = issn2cs.get(c) if c else None
        if v and v > 0:
            issn2csv[issn] = v

    mapas = _mapa_estratos(issn_index, issn2if, issn2csv)   # base -> (e_map, cortes, dist)

    # ---- 2. docentes → id-sets por categoria ----
    dd = pd.read_csv(os.path.join(cache, 'docentes.csv'), sep=';',
                     encoding='utf-8-sig', low_memory=False,
                     usecols=lambda c: c.strip().upper() in
                     ('CD_PROGRAMA_IES', 'AN_BASE', 'ID_PESSOA', 'DS_CATEGORIA_DOCENTE'))
    dd.columns = [c.strip().upper() for c in dd.columns]
    dd['QUAD'] = dd['AN_BASE'].map(ANO2QUAD)
    dd = dd.dropna(subset=['QUAD', 'CD_PROGRAMA_IES', 'ID_PESSOA'])
    catcol = (dd['DS_CATEGORIA_DOCENTE'].astype(str).str.strip().str.upper()
              if 'DS_CATEGORIA_DOCENTE' in dd.columns else pd.Series('', index=dd.index))
    sets = {}
    for (cd, quad), g in dd.groupby(['CD_PROGRAMA_IES', 'QUAD']):
        c = catcol.loc[g.index]
        sets[(cd, quad)] = dict(
            all=set(g['ID_PESSOA'].dropna().unique()),
            perm=set(g[c == 'PERMANENTE']['ID_PESSOA'].dropna().unique()),
            colab=set(g[c == 'COLABORADOR']['ID_PESSOA'].dropna().unique()),
            visit=set(g[c == 'VISITANTE']['ID_PESSOA'].dropna().unique()))
    del dd, catcol

    # ---- 3. prod → estrato por artigo (por base); eventos artigo×autor por categoria ----
    usecols = ['CD_PROGRAMA_IES', 'AN_BASE', 'ID_ADD_PRODUCAO_INTELECTUAL',
               'ID_SUBTIPO_PRODUCAO', 'ID_PESSOA_DOCENTE']
    dp = pd.read_csv(os.path.join(cache, 'prod.csv'), sep=';', encoding='utf-8-sig',
                     low_memory=False,
                     usecols=lambda c: c.strip().upper() in [u.upper() for u in usecols])
    dp.columns = [c.strip().upper() for c in dp.columns]
    dp = dp[dp['ID_SUBTIPO_PRODUCAO'] == SUBTIPO_ARTIGO]
    dp = dp.dropna(subset=['ID_ADD_PRODUCAO_INTELECTUAL', 'ID_PESSOA_DOCENTE',
                           'CD_PROGRAMA_IES', 'AN_BASE'])
    dp = dp.drop_duplicates(subset=['ID_ADD_PRODUCAO_INTELECTUAL', 'ID_PESSOA_DOCENTE'])
    dp['QUAD'] = dp['AN_BASE'].map(ANO2QUAD)
    dp = dp.dropna(subset=['QUAD'])
    dp['ID_ADD_PRODUCAO_INTELECTUAL'] = dp['ID_ADD_PRODUCAO_INTELECTUAL'].astype(np.int64)
    dp['ISSN'] = [art2issn.get(p, '') for p in dp['ID_ADD_PRODUCAO_INTELECTUAL']]
    for base in BASES:
        e_map = mapas[base][0]
        dp['E_' + base] = [e_map.get(i, 'C') if i else 'C' for i in dp['ISSN']]

    resultado = {}
    for base in BASES:
        col = 'E_' + base

        def vetor(grupo):
            # ARTIGOS DISTINTOS, não eventos artigo×autor. Antes era
            # `grupo[col].value_counts()`, que conta uma linha por (artigo, autor): um
            # artigo com 3 autores permanentes entrava 3x no estrato. Como o app usa
            # estr_* como TAXA (soma/n_perm/4) no caminho de filtro de estrato, isso
            # embutia a coautoria interna — e o fator eventos/distintos varia de 1,00
            # (Filosofia, Artes) a 7,52 (mediana 1,18) entre os 4.375 programas, logo
            # não se cancela na comparação. `nunique` conta o artigo UMA vez.
            # Precisa casar com prod_sub/ma_*/if_perm do gerar_dados_completos.py, que
            # também passaram a distintos — a validação de paridade abaixo cobre isso.
            vc = (grupo.groupby(col)['ID_ADD_PRODUCAO_INTELECTUAL'].nunique().to_dict()
                  if not grupo.empty else {})
            return [int(vc.get(e, 0)) for e in ESTRATOS]

        programas = {}
        tot_all = 0; tot_c = 0
        for (cd, quad), g in dp.groupby(['CD_PROGRAMA_IES', 'QUAD']):
            s = sets.get((cd, quad))
            if not s:
                continue
            ids = g['ID_PESSOA_DOCENTE']
            va = vetor(g[ids.isin(s['all'])])
            programas[f'{cd}|{quad}'] = dict(
                estr_perm=vetor(g[ids.isin(s['perm'])]),
                estr_colab=vetor(g[ids.isin(s['colab'])]),
                estr_visit=vetor(g[ids.isin(s['visit'])]),
                estr_all=va)
            tot_all += sum(va); tot_c += va[8]
        cortes, dist = mapas[base][1], mapas[base][2]
        frac_c = (tot_c / tot_all) if tot_all else 0.0
        resultado[base] = (cortes, dist, programas, frac_c)

    del dp, di, sets, art2issn, issn2if, mapas
    gc.collect()
    return resultado


# --------------------------------------------------------------------------- #
def _meta_estratos(base, cortes_if, dist_issn, frac_c):
    return {
        'fonte': FONTE_BASE[base],
        'base': base,
        'ordem': ESTRATOS,
        'cortes_if': {e: round(float(cortes_if[e]), 3) for e in cortes_if},
        'dist_issn': {e: int(dist_issn.get(e, 0)) for e in ESTRATOS},
        'labels_pct': LABELS_PCT,
        'frac_c': round(float(frac_c), 4),
    }


def _validar_oa(programas_oa, registros):
    """Base oa: Σ estr_X[A1..A8] == Σ if_X(lo+mi+hi) por categoria (paridade legada)."""
    mism = orf = 0
    pares = [('estr_perm', 'if_perm'), ('estr_colab', 'if_colab'),
             ('estr_visit', 'if_visit'), ('estr_all', 'if_all')]
    for r in registros:
        e = programas_oa.get(f"{r['cd']}|{r['quad']}")
        if not e:
            orf += 1
            continue
        for ec, ic in pares:
            band = r.get(ic) or [0, 0, 0]
            if sum(e[ec][:8]) != sum(int(x) for x in band):
                mism += 1
    return mism, orf


def _validar_invariante(resultado, registros):
    """Σ dos 9 estratos deve ser IGUAL entre as 3 bases, por registro/categoria."""
    difs = 0
    for r in registros:
        key = f"{r['cd']}|{r['quad']}"
        for cat in ('estr_perm', 'estr_colab', 'estr_visit', 'estr_all'):
            somas = set()
            for base in BASES:
                p = resultado[base][2].get(key)
                somas.add(sum(p[cat]) if p else 0)
            if len(somas) > 1:
                difs += 1
    return difs


def enriquecer(json_path, resultado, rotulo):
    d = json.load(open(json_path, encoding='utf-8'))
    registros = d['data']
    mism, orf = _validar_oa(resultado['oa'][2], registros)
    difs = _validar_invariante(resultado, registros)
    for r in registros:
        key = f"{r['cd']}|{r['quad']}"
        for base in BASES:
            p = resultado[base][2].get(key)
            for cat in ('estr_perm', 'estr_colab', 'estr_visit', 'estr_all'):
                r[f'{cat}_{base}'] = (p[cat] if p else [0] * 9)
        # unsuffixed = CiteScore (padrão do app)
        for cat in ('estr_perm', 'estr_colab', 'estr_visit', 'estr_all'):
            r[cat] = r[f'{cat}_cs']
    meta = d.setdefault('metadata', {})
    for base in BASES:
        cortes, dist, _, frac_c = resultado[base]
        meta[f'estratos_{base}'] = _meta_estratos(base, cortes, dist, frac_c)
    meta['estratos'] = meta['estratos_cs']            # padrão = CiteScore
    json.dump(d, open(json_path, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    fc = {b: f"{resultado[b][3]*100:.0f}%" for b in BASES}
    flag = 'OK' if (mism == 0 and difs == 0) else f'!! oa_mism={mism} invar={difs}'
    print(f'  {rotulo:44} {len(registros):4} reg · órfãos {orf} · '
          f'C cs/oa/hb {fc["cs"]}/{fc["oa"]}/{fc["hb"]} · {flag}')
    return mism + difs


def slug_de_arquivo(path):
    return os.path.basename(path)[len('area-'):-len('.json')]


def main():
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    print('Carregando crosswalk ISSN-L e CiteScore...')
    canon = carregar_crosswalk()
    issn2cs, ca = carregar_citescore(canon)
    print(f'  CiteScore: {len(issn2cs):,} ISSN-L com valor'.replace(',', '.'))

    arquivos = sorted(glob.glob(os.path.join(DOCS_DADOS, 'area-*.json')))
    if alvo:
        arquivos = [a for a in arquivos if slug_de_arquivo(a) == alvo]
        if not arquivos:
            print('Área não encontrada:', alvo); return
    print(f'Enriquecendo {len(arquivos)} área(s) com estratos A1-A8/C × 3 bases (cs/oa/hb) ...')
    t0 = time.perf_counter()
    total_err = 0
    fisica_res = None
    for path in arquivos:
        slug = slug_de_arquivo(path)
        t = time.perf_counter()
        resultado = computar_estratos_area(slug, issn2cs, ca)
        total_err += enriquecer(path, resultado, f'{slug} ({time.perf_counter()-t:.0f}s)')
        if slug == FISICA_SLUG:
            fisica_res = resultado
        del resultado
        gc.collect()

    # ── mapa-pg (app LEGADO, repositório SEPARADO e PUBLICADO) ──────────────────
    # DESLIGADO em 16/07/2026. Este bloco enriquecia ../mapa-pg/docs/dados_fisica.json,
    # que é de OUTRO app publicado (github.com/david888azv/Mapa-PG) e cujo pipeline
    # (preparar_dados_pos_d.py) está fora deste repositório.
    #
    # Ao migrar o mapa-pg-multi para ARTIGOS DISTINTOS, este bloco levava junto os
    # `estr_*` do app legado — mas o `if_perm` dele continua em EVENTOS, porque não há
    # como regerá-lo daqui. Resultado: o legado ficava com metade dos campos em cada
    # unidade, e a validação de paridade acusava 439 erros (que eram REAIS: o arquivo
    # publicado ficava incoerente).
    #
    # Enquanto os dois apps não estiverem na mesma unidade, este enriquecimento
    # cross-repo faz mais mal que bem. Para reativar: regerar o dados_fisica.json pelo
    # pipeline do próprio mapa-pg, em artigos distintos, e só então religar.
    if os.environ.get('ENRIQUECER_MAPA_PG_LEGADO') and os.path.exists(FISICA_JSON):
        if fisica_res is None:
            fisica_res = computar_estratos_area(FISICA_SLUG, issn2cs, ca)
        total_err += enriquecer(FISICA_JSON, fisica_res, 'dados_fisica.json (mapa-pg)')

    print(f'\nConcluído em {time.perf_counter()-t0:.0f}s · erros (paridade oa + invariante): '
          f'{total_err} ({"TUDO OK" if total_err == 0 else "REVISAR"})')


if __name__ == '__main__':
    main()
