#!/usr/bin/env python3
"""
Confere docs/dados/area-*.json contra o catalogo CAPES: titularidade (sigla/uf)
por quadrienio, cobertura da producao e integridade da ies_list canonica.

SUBSTITUI o preflight_catalogo_2021a2024.py, que REIMPLEMENTAVA a regra de
metadado e por isso saiu do ar assim que a regra mudou (previa 'o mais recente
manda' depois que o build ja resolvia por quadrienio). Aqui a regra e IMPORTADA
de gerar_dados_completos.mapear_programas — nao ha como divergir.

Uso:
    python3 verificar_titularidade.py            # relatorio
    python3 verificar_titularidade.py --ies UNB  # detalha uma instituicao
"""
import os, sys, json, glob, csv, argparse
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_dados_completos import mapear_programas, REPO, DATA_DIR, QUADRIENIOS  # noqa: E402

csv.field_size_limit(10 ** 9)
DOCS = os.path.join(REPO, 'docs', 'dados')


def ler(fp):
    for enc in ('latin-1', 'utf-8-sig', 'utf-8', 'cp1252'):
        try:
            with open(fp, encoding=enc, errors='strict', newline='') as fh:
                return list(csv.DictReader(fh, delimiter=';'))
        except UnicodeDecodeError:
            continue
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ies', help='detalha os programas de uma sigla')
    a = ap.parse_args()

    registry = json.load(open(os.path.join(REPO, 'docs', 'registry.json'), encoding='utf-8'))
    _, cd_meta = mapear_programas(set(registry['areas_capes'].keys()))

    # o que esta publicado
    pub, ies_list, alias_de = {}, defaultdict(set), {}
    for fp in sorted(glob.glob(os.path.join(DOCS, 'area-*.json'))):
        j = json.load(open(fp, encoding='utf-8'))
        ar = j['metadata']['area']
        for i in j['ies_list']:
            ies_list[ar].add(i['sigla'])
            for al in i.get('alias', []):
                alias_de[(ar, al)] = i['sigla']
        for r in j['data']:
            pub[(r['cd'], r['quad'])] = (r['sigla'], r['uf'], ar)

    print('=' * 66)
    print('publicado: %d registros | catalogo: %d programas' % (len(pub), len(cd_meta)))

    # 1. titularidade por quadrienio bate com o catalogo?
    divs = []
    for (cd, q), (sg, uf, ar) in pub.items():
        m = cd_meta.get(cd)
        if not m:
            divs.append((cd, q, sg, 'FORA DO CATALOGO'))
            continue
        esp = (m.get('sigla_quad') or {}).get(q)
        if esp and esp[0] != sg:
            divs.append((cd, q, sg, esp[0]))
    print('\n[1] titularidade divergente do catalogo: %d' % len(divs))
    for d in divs[:8]:
        print('    %s %s  publicado=%s  catalogo=%s' % d)

    # 2. todo registro e alcancavel por alguma caixa do filtro?
    orfaos = [(ar, sg) for (cd, q), (sg, uf, ar) in pub.items()
              if sg not in ies_list[ar] and (ar, sg) not in alias_de]
    print('\n[2] registros sem caixa correspondente na ies_list: %d' % len(orfaos))
    for o in sorted(set(orfaos))[:8]:
        print('    %s | %s' % o)

    # 3. producao 2021-2024 sem metadado (o que o catalogo novo veio resolver)
    prod = Counter()
    for fp in sorted(glob.glob(os.path.join(DATA_DIR, 'prod_intel_2021a2024_artpe_*.csv'))):
        for r in ler(fp):
            cd = r.get('CD_PROGRAMA_IES')
            if cd:
                prod[cd] += 1
    fora = [cd for cd in prod if cd not in cd_meta]
    print('\n[3] producao 2021-2024 sem metadado: %d registros em %d programas'
          % (sum(prod[c] for c in fora), len(fora)))

    # 4. programas do catalogo que nao aparecem publicados (esperado: sem nota)
    ausentes = {cd for cd in cd_meta} - {cd for cd, _ in pub}
    print('\n[4] programas no catalogo e ausentes do app: %d '
          '(esperado: conceito "A", sem nota da CAPES)' % len(ausentes))

    if a.ies:
        alvo = a.ies.upper()
        print('\n--- %s ---' % alvo)
        for cd, m in sorted(cd_meta.items(), key=lambda kv: kv[1]['programa']):
            sq = m.get('sigla_quad') or {}
            if alvo not in {v[0] for v in sq.values()}:
                continue
            linha = '  '.join('%s=%s' % (q[:4], (sq.get(q) or ['—'])[0])
                              for q in sorted(QUADRIENIOS))
            no_app = any((cd, q) in pub for q in QUADRIENIOS)
            print('  %-46s %s  %s' % (m['programa'][:46], linha,
                                      '' if no_app else '[fora do app]'))

    print('\n' + '=' * 66)
    ruim = len(divs) + len(orfaos)
    print('OK' if ruim == 0 else '%d inconsistencias' % ruim)
    return 1 if ruim else 0


if __name__ == '__main__':
    sys.exit(main())
