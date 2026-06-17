#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reconstrói os caches UnB usados por investiga_quedas.py, lendo os datasets
brutos da CAPES (Dados Abertos) em ../../dados_capes/ e filtrando à UnB
(CD_PROGRAMA_IES começa com 53001010 / SG_ENTIDADE_ENSINO == UNB).

Gera em cache_unb/:
  art_total_ano.json   {f"{cd}|{ano}": n_artigos_distintos}  + names
  roster_ano.json      {f"{cd}|{ano}": {n_doc,n_perm,n_pq,nota}}
  prod_artpe_unb.json  {f"{cd}|{ano}": {art_total,art_perm,n_perm_ativo,n_doc_ativo}}  (2021-24)
  prod_autor_unb.json  {f"{cd}|{ano}": {art_perm,n_perm_ativo}}                          (2013-20)

Métrica de produção = nº de artigos em periódico distintos
(ID_ADD_PRODUCAO_INTELECTUAL, subtipo 25), imune a roster/vínculo. O permanente
de 2013-20 sai de prod_autor por INTERSEÇÃO com o conjunto de IDs artpe (porque
prod_autor mistura todos os subtipos de produção).

Uso:  python3 build_cache_unb.py
(leva ~1-2 min; a parte lenta é ler os .xlsx de prod_artpe)
"""
import os, glob, json, time, collections
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.normpath(os.path.join(AQUI, '..', '..', 'dados_capes')) + os.sep
OUT = os.path.join(AQUI, 'cache_unb')
os.makedirs(OUT, exist_ok=True)
ANOS = range(2013, 2025)


def is_unb(ch):
    ch = ch[ch['CD_PROGRAMA_IES'].astype(str).str.startswith('53001010')]
    if 'SG_ENTIDADE_ENSINO' in ch.columns:
        ch = ch[ch['SG_ENTIDADE_ENSINO'].astype(str).str.upper() == 'UNB']
    return ch


def read_chunks(fp, cols):
    for ch in pd.read_csv(fp, sep=';', encoding='latin-1', low_memory=False,
                          chunksize=300000,
                          usecols=lambda c: c.strip().upper() in cols):
        ch.columns = [c.strip().upper() for c in ch.columns]
        yield is_unb(ch)


# --------------------------------------------------------------------
def art_total_ano():
    print('[1] art_total_ano (prod_intel_*_artpe, 2013-2024)…')
    seen = collections.defaultdict(set); names = {}
    cols = {'CD_PROGRAMA_IES', 'AN_BASE', 'ID_ADD_PRODUCAO_INTELECTUAL',
            'NM_PROGRAMA_IES', 'SG_ENTIDADE_ENSINO'}
    for fp in sorted(glob.glob(D + 'prod_intel_*_artpe_*.csv')):
        for ch in read_chunks(fp, cols):
            ch = ch.dropna(subset=['ID_ADD_PRODUCAO_INTELECTUAL'])
            for (cd, an), g in ch.groupby(['CD_PROGRAMA_IES', 'AN_BASE']):
                try: an = int(an)
                except (ValueError, TypeError): continue
                seen[(cd, an)].update(g['ID_ADD_PRODUCAO_INTELECTUAL'].tolist())
                names[cd] = g['NM_PROGRAMA_IES'].iloc[0]
    art = {f'{cd}|{an}': len(s) for (cd, an), s in seen.items()}
    json.dump({'art': art, 'names': names},
              open(os.path.join(OUT, 'art_total_ano.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    return {(cd, an): set(s) for (cd, an), s in seen.items()}   # reaproveitado em prod_autor


def roster_ano():
    print('[2] roster_ano (docentes_*, 2013-2021)…')
    NON_PQ = {'', 'N', 'NÃO', 'NAO', 'NP', '0', 'NAN', 'NONE', 'S/BOLSA', '-'}
    def is_pq(v):
        if pd.isna(v): return False
        s = str(v).strip().upper(); return s != '' and s not in NON_PQ
    R = collections.defaultdict(lambda: {'all': set(), 'perm': set(), 'pq': set(), 'nota': None})
    cols = {'CD_PROGRAMA_IES', 'AN_BASE', 'ID_PESSOA', 'DS_CATEGORIA_DOCENTE',
            'CD_CAT_BOLSA_PRODUTIVIDADE', 'CD_CONCEITO_PROGRAMA', 'SG_ENTIDADE_ENSINO'}
    files = sorted(glob.glob(D + 'docentes_2013a2016_*.csv') +
                   glob.glob(D + 'docentes_2017a2020_*.csv') + [D + 'docentes_0.csv'])
    for fp in files:
        for ch in read_chunks(fp, cols):
            for (cd, an), g in ch.groupby(['CD_PROGRAMA_IES', 'AN_BASE']):
                try: an = int(an)
                except (ValueError, TypeError): continue
                rr = R[(cd, an)]
                rr['all'].update(g['ID_PESSOA'].dropna().tolist())
                if 'DS_CATEGORIA_DOCENTE' in g.columns:
                    rr['perm'].update(g[g['DS_CATEGORIA_DOCENTE'].astype(str).str.strip().str.upper()
                                        == 'PERMANENTE']['ID_PESSOA'].dropna().tolist())
                if 'CD_CAT_BOLSA_PRODUTIVIDADE' in g.columns:
                    rr['pq'].update(g[g['CD_CAT_BOLSA_PRODUTIVIDADE'].apply(is_pq)]['ID_PESSOA'].dropna().tolist())
                if rr['nota'] is None and 'CD_CONCEITO_PROGRAMA' in g.columns:
                    nn = pd.to_numeric(g['CD_CONCEITO_PROGRAMA'], errors='coerce').dropna()
                    if len(nn): rr['nota'] = int(nn.mode().iloc[0])
    out = {f'{cd}|{an}': {'n_doc': len(v['all']), 'n_perm': len(v['perm']),
                          'n_pq': len(v['pq']), 'nota': v['nota']}
           for (cd, an), v in R.items()}
    json.dump(out, open(os.path.join(OUT, 'roster_ano.json'), 'w', encoding='utf-8'), ensure_ascii=False)


def prod_artpe_unb():
    print('[3] prod_artpe_unb (categoria permanente, 2021-2024; lê .xlsx, lento)…')
    art_all = collections.defaultdict(set); art_perm = collections.defaultdict(set)
    doc_perm = collections.defaultdict(set); doc_all = collections.defaultdict(set)
    def handle(d):
        d.columns = [c.strip().upper() for c in d.columns]
        d = is_unb(d)
        for (cd, an), g in d.groupby(['CD_PROGRAMA_IES', 'AN_BASE']):
            try: an = int(an)
            except (ValueError, TypeError): continue
            k = (cd, an)
            art_all[k].update(g['ID_ADD_PRODUCAO_INTELECTUAL'].dropna().tolist())
            gp = g[g['NM_TP_CATEGORIA_DOCENTE'].astype(str).str.strip().str.upper() == 'PERMANENTE']
            art_perm[k].update(gp['ID_ADD_PRODUCAO_INTELECTUAL'].dropna().tolist())
            doc_perm[k].update(gp['ID_PESSOA_DOCENTE'].dropna().tolist())
            doc_all[k].update(g['ID_PESSOA_DOCENTE'].dropna().tolist())
    for fp in sorted(glob.glob(D + 'prod_artpe_*.csv')):
        for ch in pd.read_csv(fp, sep=';', encoding='latin-1', low_memory=False, chunksize=200000):
            handle(ch)
    for fp in sorted(glob.glob(D + 'prod_artpe_*.xlsx')):
        handle(pd.read_excel(fp, engine='openpyxl'))
    out = {f'{cd}|{an}': {'art_total': len(art_all[k]), 'art_perm': len(art_perm[k]),
                          'n_perm_ativo': len(doc_perm[k]), 'n_doc_ativo': len(doc_all[k])}
           for k in art_all for cd, an in [k]}
    json.dump(out, open(os.path.join(OUT, 'prod_artpe_unb.json'), 'w', encoding='utf-8'), ensure_ascii=False)


def prod_autor_unb(artpe_ids):
    print('[4] prod_autor_unb (permanente 2013-2020, interseção c/ IDs artpe)…')
    art_perm = collections.defaultdict(set); doc_perm = collections.defaultdict(set)
    cols = {'AN_BASE', 'CD_PROGRAMA_IES', 'ID_ADD_PRODUCAO_INTELECTUAL',
            'ID_PESSOA_DOCENTE', 'NM_TP_CATEGORIA_DOCENTE', 'SG_ENTIDADE_ENSINO'}
    files = sorted(glob.glob(D + 'prod_autor_2013a2016_*.csv') +
                   glob.glob(D + 'prod_autor_2017a2020_*.csv'))
    for fp in files:
        for ch in read_chunks(fp, cols):
            for (cd, an), g in ch.groupby(['CD_PROGRAMA_IES', 'AN_BASE']):
                try: an = int(an)
                except (ValueError, TypeError): continue
                ids_ok = artpe_ids.get((cd, an))
                if not ids_ok: continue
                g = g[g['ID_ADD_PRODUCAO_INTELECTUAL'].isin(ids_ok)]
                perm = g[g['NM_TP_CATEGORIA_DOCENTE'].astype(str).str.strip().str.upper() == 'PERMANENTE']
                art_perm[(cd, an)].update(perm['ID_ADD_PRODUCAO_INTELECTUAL'].dropna().tolist())
                doc_perm[(cd, an)].update(perm['ID_PESSOA_DOCENTE'].dropna().tolist())
    out = {f'{cd}|{an}': {'art_perm': len(art_perm[(cd, an)]), 'n_perm_ativo': len(doc_perm[(cd, an)])}
           for (cd, an) in artpe_ids if an <= 2020}
    json.dump(out, open(os.path.join(OUT, 'prod_autor_unb.json'), 'w', encoding='utf-8'), ensure_ascii=False)


def main():
    t0 = time.time()
    ids = art_total_ano()
    roster_ano()
    prod_autor_unb({k: v for k, v in ids.items() if k[1] <= 2020})
    prod_artpe_unb()
    print(f'✓ caches em {OUT}/  ({time.time()-t0:.0f}s)')


if __name__ == '__main__':
    main()
