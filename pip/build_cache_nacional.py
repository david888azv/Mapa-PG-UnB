#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Versão NACIONAL (todas as IES) dos caches do recálculo bruto.
Mesma metodologia de build_cache_unb.py, sem o filtro UnB.

Gera em cache_nac/:
  art_total_ano.json   {f"{cd}|{ano}": n_artigos_distintos} + names + ies (sigla/uf)
  roster_ano.json      {f"{cd}|{ano}": {n_doc,n_perm,n_pq,nota}}

Sinal = nº de artigos em periódico distintos (ID_ADD_PRODUCAO_INTELECTUAL,
subtipo 25) por programa/ano, direto de prod_intel_*_artpe (2013-2024), imune a
roster/vínculo. (Permanente nacional fica para um passo separado, mais pesado.)

Uso:  python3 build_cache_nacional.py
"""
import os, glob, json, time, collections
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.normpath(os.path.join(AQUI, '..', '..', 'dados_capes')) + os.sep
OUT = os.path.join(AQUI, 'cache_nac')
os.makedirs(OUT, exist_ok=True)


def read_chunks(fp, cols):
    for ch in pd.read_csv(fp, sep=';', encoding='latin-1', low_memory=False,
                          chunksize=400000,
                          usecols=lambda c: c.strip().upper() in cols):
        ch.columns = [c.strip().upper() for c in ch.columns]
        yield ch


def art_total_ano():
    print('[1] art_total_ano nacional (prod_intel_*_artpe)…')
    t0 = time.time()
    seen = collections.defaultdict(set); names = {}; ies = {}
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
                if 'SG_ENTIDADE_ENSINO' in g.columns:
                    ies[cd] = str(g['SG_ENTIDADE_ENSINO'].iloc[0])
        print(f'   {os.path.basename(fp)} ({time.time()-t0:.0f}s)')
    art = {f'{cd}|{an}': len(s) for (cd, an), s in seen.items()}
    json.dump({'art': art, 'names': names, 'ies': ies},
              open(os.path.join(OUT, 'art_total_ano.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print(f'   programas: {len({cd for cd, _ in seen})} | {time.time()-t0:.0f}s')


def roster_ano():
    print('[2] roster_ano nacional (docentes_*)…')
    t0 = time.time()
    NON_PQ = {'', 'N', 'NÃO', 'NAO', 'NP', '0', 'NAN', 'NONE', 'S/BOLSA', '-'}
    def is_pq(v):
        if pd.isna(v): return False
        s = str(v).strip().upper(); return s != '' and s not in NON_PQ
    R = collections.defaultdict(lambda: {'all': set(), 'perm': set(), 'pq': set(), 'nota': None})
    cols = {'CD_PROGRAMA_IES', 'AN_BASE', 'ID_PESSOA', 'DS_CATEGORIA_DOCENTE',
            'CD_CAT_BOLSA_PRODUTIVIDADE', 'CD_CONCEITO_PROGRAMA'}
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
        print(f'   {os.path.basename(fp)} ({time.time()-t0:.0f}s)')
    out = {f'{cd}|{an}': {'n_doc': len(v['all']), 'n_perm': len(v['perm']),
                          'n_pq': len(v['pq']), 'nota': v['nota']}
           for (cd, an), v in R.items()}
    json.dump(out, open(os.path.join(OUT, 'roster_ano.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'   pares: {len(out)} | {time.time()-t0:.0f}s')


if __name__ == '__main__':
    art_total_ano()
    roster_ano()
    print(f'✓ caches nacionais em {OUT}/')
