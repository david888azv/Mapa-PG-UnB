#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_estratos_app.py — ENRIQUECE os JSON dos aplicativos (mapa-pg-multi e mapa-pg)
com a estratificação CAPES A1-A8/C (Ficha de Avaliação 2025-2028), por PERCENTIL do
periódico DENTRO da área (classes de 12,5%), para CADA categoria de docente.

Somente ADIÇÃO: nunca altera campos existentes. Para cada registro programa×quad
acrescenta 4 vetores de 9 inteiros (ordem A1..A8,C):
    estr_perm, estr_colab, estr_visit, estr_all
e, no metadata da área, o bloco `estratos` (cortes_if por área, dist_issn, labels_pct).

Reaproveita:
  • build_estratos.py  → percentil ISSN→estrato (CORTES, estrato_de_pct), cortes_if;
  • gerar_dados_completos.py → extração dos id-sets por categoria de docente.

Contagem em EVENTOS artigo×autor (value_counts por estrato) — mesma base de `if_perm`
etc.: Σ estr_X[A1..A8] == Σ if_X(lo+mi+hi); estr_X[C] é aditivo (periódicos sem IF).

Memória: processa UMA área por vez, com usecols e gc entre áreas (brutos grandes).

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
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(AQUI, '..'))          # mapa-pg-multi/
CACHE_DIR = os.path.join(REPO, 'build', 'cache')
DOCS_DADOS = os.path.join(REPO, 'docs', 'dados')           # area-*.json
FISICA_JSON = os.path.normpath(os.path.join(REPO, '..', 'mapa-pg', 'docs', 'dados_fisica.json'))
FISICA_SLUG = 'astronomia-fisica'

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
    'C': 'sem indicador de IF',
}


def estrato_de_pct(p):
    for nome, lim in CORTES:
        if p >= lim:
            return nome
    return 'A8'


def computar_estratos_area(slug):
    """Devolve (cortes_if, dist_issn, programas) para a área.
    programas: {f'{cd}|{quad}': {estr_perm, estr_colab, estr_visit, estr_all}}."""
    cache = os.path.join(CACHE_DIR, slug)

    # ---- 1. ISSN → estrato (percentil de IF dentro da área) ----
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
    com_if = issn2if[issn2if > 0]
    vals = com_if.values
    issn2estrato = {issn: estrato_de_pct(percentileofscore(vals, v, kind='mean'))
                    for issn, v in com_if.items()}
    cortes_if = {}
    for issn, v in com_if.items():
        e = issn2estrato[issn]
        cortes_if[e] = min(cortes_if.get(e, v), v)      # limite inferior de IF do estrato
    dist_issn = {e: 0 for e in ESTRATOS}
    for issn in issn2if.index:
        dist_issn[issn2estrato.get(issn, 'C')] += 1

    def estrato_art(pid):
        issn = art2issn.get(pid)
        return issn2estrato.get(issn, 'C') if issn else 'C'

    # ---- 2. docentes → id-sets por categoria, por (cd, quad) ----
    dd = pd.read_csv(os.path.join(cache, 'docentes.csv'), sep=';',
                     encoding='utf-8-sig', low_memory=False,
                     usecols=lambda c: c.strip().upper() in
                     ('CD_PROGRAMA_IES', 'AN_BASE', 'ID_PESSOA', 'DS_CATEGORIA_DOCENTE'))
    dd.columns = [c.strip().upper() for c in dd.columns]
    dd['QUAD'] = dd['AN_BASE'].map(ANO2QUAD)
    dd = dd.dropna(subset=['QUAD', 'CD_PROGRAMA_IES', 'ID_PESSOA'])
    catcol = (dd['DS_CATEGORIA_DOCENTE'].astype(str).str.strip().str.upper()
              if 'DS_CATEGORIA_DOCENTE' in dd.columns else pd.Series('', index=dd.index))
    sets = {}     # (cd, quad) -> dict(all, perm, colab, visit) of ID_PESSOA
    for (cd, quad), g in dd.groupby(['CD_PROGRAMA_IES', 'QUAD']):
        c = catcol.loc[g.index]
        sets[(cd, quad)] = dict(
            all=set(g['ID_PESSOA'].dropna().unique()),
            perm=set(g[c == 'PERMANENTE']['ID_PESSOA'].dropna().unique()),
            colab=set(g[c == 'COLABORADOR']['ID_PESSOA'].dropna().unique()),
            visit=set(g[c == 'VISITANTE']['ID_PESSOA'].dropna().unique()))
    del dd, catcol

    # ---- 3. prod → estrato por artigo; eventos artigo×autor por categoria ----
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
    dp['ESTRATO'] = [estrato_art(p) for p in dp['ID_ADD_PRODUCAO_INTELECTUAL']]

    def vetor(grupo):
        vc = grupo['ESTRATO'].value_counts().to_dict()
        return [int(vc.get(e, 0)) for e in ESTRATOS]

    programas = {}
    for (cd, quad), g in dp.groupby(['CD_PROGRAMA_IES', 'QUAD']):
        s = sets.get((cd, quad))
        if not s:
            continue
        ids = g['ID_PESSOA_DOCENTE']
        programas[f'{cd}|{quad}'] = dict(
            estr_perm=vetor(g[ids.isin(s['perm'])]),
            estr_colab=vetor(g[ids.isin(s['colab'])]),
            estr_visit=vetor(g[ids.isin(s['visit'])]),
            estr_all=vetor(g[ids.isin(s['all'])]))
    del dp, di, sets, art2issn, issn2if, issn2estrato
    gc.collect()
    return cortes_if, dist_issn, programas


# --------------------------------------------------------------------------- #
def _meta_estratos(cortes_if, dist_issn):
    return {
        'fonte': 'CAPES Ficha de Avaliação 2025-2028 — estratos A1-A8/C por percentil de IF (2 anos OpenAlex) dentro da área',
        'ordem': ESTRATOS,
        'cortes_if': {e: round(float(cortes_if[e]), 3) for e in cortes_if},
        'dist_issn': {e: int(dist_issn.get(e, 0)) for e in ESTRATOS},
        'labels_pct': LABELS_PCT,
    }


def _validar(programas, registros, campo_if):
    """Confere Σ estr_X[A1..A8] == Σ if_X(lo+mi+hi) por categoria; conta órfãos e ΔC."""
    mism = 0
    orf = 0
    deltaC = 0
    pares = [('estr_perm', 'if_perm'), ('estr_colab', 'if_colab'),
             ('estr_visit', 'if_visit'), ('estr_all', 'if_all')]
    for r in registros:
        key = f"{r['cd']}|{r['quad']}"
        e = programas.get(key)
        if not e:
            orf += 1
            continue
        for ec, ic in pares:
            band = r.get(ic) or [0, 0, 0]
            if sum(e[ec][:8]) != sum(int(x) for x in band):
                mism += 1
        deltaC += e['estr_perm'][8]
    return mism, orf, deltaC


def enriquecer(json_path, cortes_if, dist_issn, programas, rotulo):
    d = json.load(open(json_path, encoding='utf-8'))
    registros = d['data']
    mism, orf, deltaC = _validar(programas, registros, 'if_perm')
    for r in registros:
        e = programas.get(f"{r['cd']}|{r['quad']}")
        if e:
            r['estr_perm'] = e['estr_perm']; r['estr_colab'] = e['estr_colab']
            r['estr_visit'] = e['estr_visit']; r['estr_all'] = e['estr_all']
        else:
            z = [0] * 9
            r['estr_perm'] = z[:]; r['estr_colab'] = z[:]
            r['estr_visit'] = z[:]; r['estr_all'] = z[:]
    d.setdefault('metadata', {})['estratos'] = _meta_estratos(cortes_if, dist_issn)
    json.dump(d, open(json_path, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    flag = 'OK' if mism == 0 else f'!! {mism} DIVERGÊNCIAS'
    print(f'  {rotulo:46} {len(registros):4} reg · órfãos {orf} · ΔC(perm) {deltaC} · paridade {flag}')
    return mism


def slug_de_arquivo(path):
    return os.path.basename(path)[len('area-'):-len('.json')]


def main():
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    arquivos = sorted(glob.glob(os.path.join(DOCS_DADOS, 'area-*.json')))
    if alvo:
        arquivos = [a for a in arquivos if slug_de_arquivo(a) == alvo]
        if not arquivos:
            print('Área não encontrada:', alvo); return
    print(f'Enriquecendo {len(arquivos)} área(s) com estratos A1-A8/C ...')
    t0 = time.perf_counter()
    total_mism = 0
    fisica_estr = None
    for path in arquivos:
        slug = slug_de_arquivo(path)
        t = time.perf_counter()
        cortes_if, dist_issn, programas = computar_estratos_area(slug)
        total_mism += enriquecer(path, cortes_if, dist_issn, programas,
                                 f'{slug} ({time.perf_counter()-t:.0f}s)')
        if slug == FISICA_SLUG:
            fisica_estr = (cortes_if, dist_issn, programas)
        del programas
        gc.collect()

    # ---- Física (mapa-pg/docs/dados_fisica.json) a partir do cache astronomia-fisica ----
    if (alvo is None or alvo == FISICA_SLUG) and os.path.exists(FISICA_JSON):
        if fisica_estr is None:
            fisica_estr = computar_estratos_area(FISICA_SLUG)
        total_mism += enriquecer(FISICA_JSON, *fisica_estr, 'dados_fisica.json (mapa-pg)')

    print(f'\nConcluído em {time.perf_counter()-t0:.0f}s · divergências de paridade: {total_mism} '
          f'({"TUDO OK" if total_mism == 0 else "REVISAR"})')


if __name__ == '__main__':
    main()
