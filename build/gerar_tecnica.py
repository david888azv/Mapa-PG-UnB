#!/usr/bin/env python3
"""Gera a camada de PATENTES do MAPA-PG: docs/dados/tec-<area>.json.

Entrada (baixada por `baixar_tecnica.py`):
    dados_capes/tec_detalhe_<quad>_patente.csv   detalhe (resumo, nº de registro, datas, TRL)
    dados_capes/tec_prod_<quad>_patente.csv      tabela-mãe (título 100%, linha de pesquisa)

Saída: um arquivo por área, com o mesmo slug dos area-*.json, contendo
    - contagem de patentes por programa e por ano
    - a lista das patentes de cada programa (título, resumo, nº, datas, estágio)

DECISÕES DE MODELAGEM
---------------------
1. Arquivo SEPARADO, não patch nos area-*.json. `gerar_dados_completos.py` reescreve
   os area-*.json do zero a cada rebuild; um patch seria silenciosamente perdido.
2. Placeholder: a CAPES grava '-' para campo não preenchido. Vira '' aqui.
3. DEDUPLICAÇÃO. Uma mesma patente é declarada por todos os programas coautores:
   em 2021-2024 são 13.128 registros com código para 8.059 patentes distintas
   (2.929 códigos aparecem em >1 programa, 1.280 em >1 IES). Logo:
     - contagem POR PROGRAMA usa os registros como declarados (é o que a CAPES avalia);
     - contagem de ÁREA e NACIONAL usa a chave normalizada de registro, sem repetir.
   Registros sem código não têm como ser deduplicados e contam como distintos.
4. IN_GLOSA = 1 (produção glosada pela CAPES) é descartado, como no pipeline
   bibliográfico.
5. Cobertura: só ~23% das patentes têm DS_FINALIDADE (o resumo) e ~11% têm data de
   concessão. O app precisa exibir isso como ausência de declaração, não como zero.

Uso:
    python3 gerar_tecnica.py                 # 2021-2024, as 49 áreas
    python3 gerar_tecnica.py --area quimica biotecnologia
    python3 gerar_tecnica.py --sem-manifest  # não mexe no docs/manifest.json
"""
import argparse
import glob
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
CACHE_DIR = os.path.join(REPO, 'build', 'cache')
DOCS_DIR = os.path.join(REPO, 'docs', 'dados')
MANIFEST = os.path.join(REPO, 'docs', 'manifest.json')

QUAD_ANOS = {'2013a2016': ('2013-2016', range(2013, 2017)),
             '2017a2020': ('2017-2020', range(2017, 2021)),
             '2021a2024': ('2021-2024', range(2021, 2025))}

VAZIO = {'', '-', '--', 'NAO INFORMADO', 'NÃO INFORMADO', 'NAN', 'NONE'}


def limpar(s):
    """Normaliza célula CAPES: strip + placeholder '-' → ''."""
    if not isinstance(s, str):
        return ''
    s = ' '.join(s.split())
    return '' if s.upper() in VAZIO else s


def chave_registro(cod):
    """Chave de deduplicação: só alfanuméricos, maiúsculo.

    'BR 10 2021 024428-3' e 'br102021024428 3' viram a mesma patente. Códigos com
    menos de 6 caracteres úteis são descartados como chave (curtos demais para
    identificar um depósito e colidiriam entre patentes diferentes).
    """
    k = re.sub(r'[^A-Za-z0-9]', '', cod or '').upper()
    return k if len(k) >= 6 else ''


# DS_FINALIDADE é campo livre: a maioria descreve a invenção, mas ~3% dos preenchidos
# trazem apenas a natureza do ativo ("PATENTE DE INVENÇÃO", "REGISTRO DE CULTIVAR").
# Separar os dois evita anunciar como descrição o que é só rótulo de categoria.
_NAT_TOKENS = {
    'PATENTE', 'PATENTES', 'INVENCAO', 'PI', 'MU', 'DI', 'PRIVILEGIO', 'INOVACAO',
    'MODELO', 'UTILIDADE', 'REGISTRO', 'CULTIVAR', 'PROGRAMA', 'COMPUTADOR',
    'SOFTWARE', 'PROPRIEDADE', 'INTELECTUAL', 'DESENHO', 'INDUSTRIAL', 'MARCA',
    'DEPOSITO', 'DEPOSITADA', 'CONCEDIDA', 'PEDIDO', 'DE', 'DO', 'DA', 'E',
}


def eh_natureza(txt):
    """True se DS_FINALIDADE é só o rótulo da categoria do ativo, não uma descrição."""
    s = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode().upper()
    toks = re.sub(r'[^A-Z0-9 ]', ' ', s).split()
    return bool(toks) and len(toks) <= 6 and all(t in _NAT_TOKENS for t in toks)


def load_csv(fp):
    for enc in ('latin-1', 'utf-8-sig', 'utf-8', 'cp1252'):
        try:
            return pd.read_csv(fp, sep=';', encoding=enc, dtype=str, low_memory=False)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f'não consegui decodificar {fp}')


def mapa_areas():
    """cd_programa → slug da área, lido do cache que o app já usa."""
    cd2slug, slugs = {}, []
    for d in sorted(os.listdir(CACHE_DIR)):
        meta_fp = os.path.join(CACHE_DIR, d, 'meta.json')
        if not os.path.exists(meta_fp):
            continue
        slugs.append(d)
        for cd in json.load(open(meta_fp, encoding='utf-8'))['cds']:
            cd2slug[cd] = d
    return cd2slug, slugs


def nome_area(slug):
    fp = os.path.join(DOCS_DIR, f'area-{slug}.json')
    if not os.path.exists(fp):
        return slug
    with open(fp, encoding='utf-8') as fh:
        # o metadata é o primeiro objeto do arquivo; ler só o começo evita
        # carregar 500 KB de dados só para pegar o nome
        head = fh.read(600)
    m = re.search(r'"area":"(.*?)"', head)
    return m.group(1) if m else slug


def carregar(quad):
    det_fp = os.path.join(DATA_DIR, f'tec_detalhe_{quad}_patente.csv')
    prod_fp = os.path.join(DATA_DIR, f'tec_prod_{quad}_patente.csv')
    if not os.path.exists(det_fp):
        raise SystemExit(f'ERRO: falta {det_fp}\n  rode: python3 baixar_tecnica.py '
                         f'--quadrienio {quad} --subtipo patente')

    det = load_csv(det_fp).fillna('')
    for c in det.columns:
        det[c] = det[c].map(limpar)
    n_bruto = len(det)
    det = det[det['IN_GLOSA'] != '1']
    n_glosa = n_bruto - len(det)

    # A tabela-mãe cobre o título (100%) onde o detalhe falha (99,2% em 2021-2024,
    # 42,5% em 2013-2016) e acrescenta linha de pesquisa / projeto.
    tit, linha = {}, {}
    if os.path.exists(prod_fp):
        prod = load_csv(prod_fp).fillna('')
        for r in prod[['ID_ADD_PRODUCAO_INTELECTUAL', 'NM_PRODUCAO',
                       'NM_LINHA_PESQUISA']].values:
            pid = limpar(r[0])
            if not pid:
                continue
            tit[pid] = limpar(r[1])
            linha[pid] = limpar(r[2])
    else:
        print(f'  ! sem tabela-mãe ({os.path.basename(prod_fp)}); '
              f'título só do detalhe, sem linha de pesquisa')
    return det, tit, linha, n_glosa


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quadrienio', default='2021a2024', choices=sorted(QUAD_ANOS))
    ap.add_argument('--area', nargs='*', help='restringe a estes slugs')
    ap.add_argument('--sem-manifest', action='store_true')
    ap.add_argument('--resumo-max', type=int, default=600,
                    help='corte do resumo da patente, em caracteres (0 = sem corte)')
    a = ap.parse_args()

    t0 = time.perf_counter()
    quad_label, anos = QUAD_ANOS[a.quadrienio]
    anos = [str(x) for x in anos]

    cd2slug, slugs = mapa_areas()
    if a.area:
        desconhecidas = [s for s in a.area if s not in slugs]
        if desconhecidas:
            raise SystemExit(f'ERRO: área(s) fora do cache: {", ".join(desconhecidas)}')
        slugs = a.area
    print(f'══ PATENTES {quad_label} — {len(slugs)} área(s) ══')
    print(f'[1] cache: {len(cd2slug)} programas mapeados em {len(os.listdir(CACHE_DIR))} áreas')

    det, tit, linha, n_glosa = carregar(a.quadrienio)
    print(f'[2] detalhe: {len(det)} registros ({n_glosa} glosados descartados)')

    det['_slug'] = det['CD_PROGRAMA_IES'].map(cd2slug)
    orfas = det['_slug'].isna().sum()
    det = det[det['_slug'].notna()]
    print(f'[3] casadas com área do app: {len(det)} '
          f'({100*len(det)/(len(det)+orfas):.1f}%) — {orfas} órfãs descartadas')

    # 2017-2020 não publica número de registro; 2013-2016 usa CD_REGISTRO.
    col_cod = next((c for c in ('DS_CODIGO_REGISTRO', 'CD_REGISTRO')
                    if c in det.columns), None)
    if col_cod is None:
        print('    ! este quadriênio não publica número de registro: '
              'sem deduplicação de coautoria')

    def col(r, nome):
        return r[nome] if nome in det.columns else ''

    por_area = defaultdict(lambda: defaultdict(list))   # slug → cd → [patente]
    for r in det.to_dict('records'):
        pid = r['ID_ADD_PRODUCAO_INTELECTUAL']
        cod = col(r, col_cod) if col_cod else ''
        titulo = r.get('NM_TITULO', '') or tit.get(pid, '')
        fin = r.get('DS_FINALIDADE', '')
        natureza = fin if eh_natureza(fin) else ''
        resumo = '' if natureza else fin
        if a.resumo_max and len(resumo) > a.resumo_max:
            resumo = resumo[:a.resumo_max].rsplit(' ', 1)[0] + '…'
        # DT_DEPOSITO cobre 539 registros de 2021-2024 em que DT_PEDIDO_DEPOSITO
        # está vazio; juntas levam a cobertura de data de 92,4% para ~96,3%.
        deposito = col(r, 'DT_PEDIDO_DEPOSITO') or col(r, 'DT_DEPOSITO')
        ano = r['AN_BASE_PRODUCAO']
        por_area[r['_slug']][r['CD_PROGRAMA_IES']].append({
            'id': pid,
            'ano': ano if ano in anos else '',
            'tit': titulo,
            'res': resumo,
            'nat': natureza,                   # rótulo de categoria, quando é o caso
            'cls': col(r, 'DS_CORRESP_SUBTIPO'),
            'cod': cod,
            'k': chave_registro(cod),          # chave de dedup (vazia = não dedupável)
            'inst': col(r, 'NM_INST_DEPOSITO'),
            'dep': deposito,
            'con': col(r, 'DT_CONCESSAO'),
            'est': col(r, 'DS_ESTAGIO_TECNOLOGIA'),
            'tt': col(r, 'IN_TRANSF_TEC_CONHECIMENTO'),
            'lp': linha.get(pid, ''),
        })

    # ── nacional (para o app poder situar a área no país) ──
    nac_unicas = set()
    nac_sem_cod = 0
    for cds in por_area.values():
        for pats in cds.values():
            for p in pats:
                if p['k']:
                    nac_unicas.add(p['k'])
                else:
                    nac_sem_cod += 1
    nac_total = sum(len(v) for cds in por_area.values() for v in cds.values())
    nac_dist = len(nac_unicas) + nac_sem_cod
    print(f'[4] nacional: {nac_total} declarações → {nac_dist} patentes distintas '
          f'({nac_total - nac_dist} repetições por coautoria entre programas)')

    # Cobertura declaratória nacional: o app precisa exibir os percentuais reais deste
    # quadriênio, não números fixos no código — eles mudam a cada coleta.
    todos = [p for cds in por_area.values() for v in cds.values() for p in v]
    cobertura = {k: round(100 * sum(1 for p in todos if p[k]) / len(todos), 1)
                 for k in ('tit', 'cod', 'dep', 'con', 'res', 'est')}
    print('[4b] cobertura nacional (%): ' +
          ', '.join(f'{k}={v}' for k, v in cobertura.items()))

    print(f'[5] gravando docs/dados/tec-<area>.json ...')
    os.makedirs(DOCS_DIR, exist_ok=True)
    resumo_areas, tot_kb = [], 0.0
    for slug in slugs:
        cds = por_area.get(slug, {})
        progs, area_unicas, area_sem_cod = {}, set(), 0
        for cd, pats in cds.items():
            pats.sort(key=lambda p: (p['ano'] or '9999', p['tit']))
            por_ano = {y: 0 for y in anos}
            for p in pats:
                if p['ano']:
                    por_ano[p['ano']] += 1
                if p['k']:
                    area_unicas.add(p['k'])
                else:
                    area_sem_cod += 1
            progs[cd] = {
                'n': len(pats),
                'ano': por_ano,
                'n_res': sum(1 for p in pats if p['res']),
                'n_cod': sum(1 for p in pats if p['cod']),
                'n_dep': sum(1 for p in pats if p['dep']),
                'n_con': sum(1 for p in pats if p['con']),
                'pat': [{k: v for k, v in p.items() if v and k != 'k'} for p in pats],
            }
        out = {
            'metadata': {
                'area': nome_area(slug),
                'slug': slug,
                'quadrienio': quad_label,
                'anos': anos,
                'subtipo': 'PATENTE',
                'n_programas': len(progs),
                'n_declaracoes': sum(p['n'] for p in progs.values()),
                'n_distintas': len(area_unicas) + area_sem_cod,
                'n_nacional_declaracoes': nac_total,
                'n_nacional_distintas': nac_dist,
                'cobertura_nacional': cobertura,
                'dedup': bool(col_cod),
                'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
                'fonte': ('CAPES — Detalhes da Produção Intelectual Técnica + '
                          f'Produção Intelectual, {quad_label}'),
            },
            'programas': progs,
        }
        fp = os.path.join(DOCS_DIR, f'tec-{slug}.json')
        with open(fp, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
        kb = os.path.getsize(fp) / 1024
        tot_kb += kb
        resumo_areas.append((slug, out['metadata']['n_declaracoes'],
                             out['metadata']['n_distintas'], len(progs), kb))

    for slug, nd, ndist, npg, kb in sorted(resumo_areas, key=lambda x: -x[1])[:12]:
        print(f'    {slug:<45s} {nd:5d} decl {ndist:5d} dist {npg:4d} progs {kb:7.0f} KB')
    print(f'    ... {len(resumo_areas)} áreas, {tot_kb/1024:.2f} MB no total')

    if not a.sem_manifest and os.path.exists(MANIFEST):
        with open(MANIFEST, encoding='utf-8') as fh:
            man = json.load(fh)
        idx = {s: (nd, ndist, npg) for s, nd, ndist, npg, _ in resumo_areas}
        for ar in man.get('areas', []):
            if ar['slug'] in idx:
                nd, ndist, npg = idx[ar['slug']]
                ar['tec'] = {'arquivo': f'dados/tec-{ar["slug"]}.json',
                             'quadrienio': quad_label, 'subtipo': 'PATENTE',
                             'n_declaracoes': nd, 'n_distintas': ndist,
                             'n_programas': npg}
        man['tecnica'] = {'quadrienio': quad_label, 'subtipos': ['PATENTE'],
                          'n_nacional_declaracoes': nac_total,
                          'n_nacional_distintas': nac_dist,
                          'atualizado_em': time.strftime('%Y-%m-%d %H:%M:%S')}
        with open(MANIFEST, 'w', encoding='utf-8') as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)
        print(f'[6] manifest.json atualizado ({len(idx)} áreas com bloco "tec")')

    print(f'\nConcluído em {time.perf_counter()-t0:.1f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
