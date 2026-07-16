#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Acrescenta ao app as Áreas de Avaliação da CAPES que faltavam
=============================================================
O catálogo de áreas era derivado da pegada da UnB (`gerar_registry.py` montava
`areas_capes` iterando sobre os programas da UnB), então as Áreas de Avaliação em que a
UnB não tem nenhum programa nunca entravam — e como `gerar_dados_completos.py` usa
`areas_capes` como universo, elas sumiam do app inteiro. Eram 7 áreas / 437 programas:
CIÊNCIAS BIOLÓGICAS II, ENGENHARIAS II, ZOOTECNIA/RECURSOS PESQUEIROS, CIÊNCIA DE
ALIMENTOS, MEDICINA III, PLANEJAMENTO URBANO E REGIONAL/DEMOGRAFIA e CIÊNCIAS DA RELIGIÃO
E TEOLOGIA. Usuários de SC reportaram programas "faltando" por causa disto.

`gerar_registry.py` já foi corrigido (catálogo nacional, sem filtro de IES). Este script
faz o resto, SEM reprocessar as áreas que já existem.

POR QUE UM SCRIPT PRÓPRIO, e não o pipeline normal:
  • `gerar_dados_completos.py` sem `--skip-fase1` chama `fase1_prefiltrar(TODAS as áreas)`,
    relendo ~2 GB de CSV e reescrevendo os 42 caches que já estão corretos. Aqui a fase 1
    roda só para as áreas novas.
  • `atualizar_manifest()` só atualiza entradas QUE JÁ EXISTEM no manifest — as áreas novas
    nunca seriam adicionadas. Este script as acrescenta.
  • `gerar_dados_minimos.py` (que criaria as entradas) SOBRESCREVE os `area-*.json` com a
    camada mínima (`tem_metricas: false`, métricas zeradas) e recria o manifest do zero —
    destruiria os 42 arquivos completos E os estratos A1–A8/C. NÃO rodar.

DEPOIS DESTE SCRIPT, obrigatoriamente:
    python3 gerar_estratos_app.py <slug>     # para cada área nova (injeta estr_* in-place)
    python3 gerar_registry_ies.py            # as novas áreas entram no menu por IES
    python3 gerar_sitemap.py

Uso:
    python3 add_areas_faltantes.py            # DRY-RUN: diz o que faria
    python3 add_areas_faltantes.py --aplicar  # executa (fase 1 relê os CSVs: alguns minutos)
"""
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import gerar_dados_completos as G          # noqa: E402

REPO = os.path.dirname(AQUI)
DADOS = os.path.join(REPO, 'docs', 'dados')
MANIFEST = os.path.join(REPO, 'docs', 'manifest.json')


def levantar():
    """(catalog, [(area, slug)] que ainda não têm area-<slug>.json)."""
    catalog = json.load(open(G.REGISTRY, encoding='utf-8'))
    faltam = []
    for a, meta in sorted(catalog['areas_capes'].items()):
        sl = meta['slug']
        if not os.path.exists(os.path.join(DADOS, f'area-{sl}.json')):
            faltam.append((a, sl))
    return catalog, faltam


def acrescentar_ao_manifest(catalog, novas):
    """Acrescenta as áreas novas ao manifest PRESERVANDO tudo o que já existe
    (entradas antigas, `estratos_capes`, `shell_version`). Idempotente."""
    mf = json.load(open(MANIFEST, encoding='utf-8'))
    ja = {a['slug'] for a in mf['areas']}
    add = 0
    for area, sl in novas:
        if sl in ja:
            continue
        p = os.path.join(DADOS, f'area-{sl}.json')
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding='utf-8'))
        info = catalog['areas_capes'][area]
        mf['areas'].append({
            'slug': sl,
            'nome': area,
            'arquivo': f'dados/area-{sl}.json',
            'tamanho_kb': round(os.path.getsize(p) / 1024),
            'n_registros': len(d['data']),
            'n_unb': info['n_unb'],            # 0 nestas áreas — a UnB não atua nelas
            'sufixos_unb': info['sufixos_unb'],
            'tem_metricas': True,
        })
        add += 1
    mf['areas'].sort(key=lambda a: a['nome'])
    mf['grandes_areas'] = catalog['grandes_areas']   # passa a cobrir as 49 áreas
    mf['atualizado_em'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        json.dump(mf, fh, ensure_ascii=False, indent=2)
    return add, len(mf['areas'])


def main(argv):
    aplicar = '--aplicar' in argv
    catalog, faltam = levantar()

    print(f'registry.json : {len(catalog["areas_capes"])} áreas CAPES')
    print(f'docs/dados/   : {len(catalog["areas_capes"]) - len(faltam)} áreas já geradas')
    print()
    if not faltam:
        print('✓ Nada a fazer — toda área do registry já tem area-<slug>.json.')
        return 0
    print(f'ÁREAS A ACRESCENTAR ({len(faltam)}):')
    for a, sl in faltam:
        n = catalog['areas_capes'][a]['n_unb']
        print(f'  {a[:46]:48s} → area-{sl}.json  (n_unb={n})')
    print()
    if not aplicar:
        print('--- DRY-RUN: nada foi executado. Use --aplicar. ---')
        print('    A fase 1 relê ~2 GB de CSV (alguns minutos); as 42 áreas existentes')
        print('    NÃO são tocadas.')
        return 0

    areas_alvo = {a for a, _ in faltam}
    slugs = [sl for _, sl in faltam]

    print('══ FASE 1 (só as áreas novas) ══')
    G.fase1_prefiltrar(areas_alvo)

    print('\n══ FASE 2 ══')
    res = G.fase2_paralela(slugs, 8)
    ok = [s for s, o, _ in res if o]
    fail = [(s, m) for s, o, m in res if not o]
    for s, m in fail:
        print(f'  ✗ {s}: {m}')

    add, tot = acrescentar_ao_manifest(catalog, [(a, sl) for a, sl in faltam if sl in ok])
    print(f'\n✓ {len(ok)}/{len(slugs)} áreas geradas · +{add} no manifest (total {tot})')
    if fail:
        print(f'✗ {len(fail)} falharam — ver acima')
    print('\nAGORA, obrigatoriamente:')
    for s in ok:
        print(f'  python3 gerar_estratos_app.py {s}')
    print('  python3 gerar_registry_ies.py')
    print('  python3 gerar_sitemap.py')
    return 0 if not fail else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
