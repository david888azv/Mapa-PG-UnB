#!/usr/bin/env python3
"""Baixa a PRODUÇÃO TÉCNICA da CAPES (Dados Abertos) para dados_capes/.

A produção técnica NÃO vem nos arquivos que o app já usa: `gerar_dados_completos.py`
só lê o recorte bibliográfico (SUBTIPOS_BIBLIO, todos ID_TIPO_PRODUCAO=2). Patentes
e demais produtos tecnológicos moram em datasets separados do portal:

  - "Detalhes da Produção Intelectual Técnica"  → campos próprios de cada subtipo
    (para PATENTE: DS_FINALIDADE = resumo, DS_CODIGO_REGISTRO = nº do depósito,
     DT_PEDIDO_DEPOSITO, DT_CONCESSAO, DS_ESTAGIO_TECNOLOGIA, ...)
  - "Produção Intelectual" (tabela-mãe)         → NM_PRODUCAO (título, 100% preenchido),
    NM_LINHA_PESQUISA, NM_PROJETO, NM_AREA_CONCENTRACAO

As duas casam por ID_ADD_PRODUCAO_INTELECTUAL; ambas trazem CD_PROGRAMA_IES, que é a
mesma chave que build/cache/<area>/meta.json já mapeia para as 49 áreas do app.

Uso:
    python3 baixar_tecnica.py                    # patente 2021-2024 (padrão)
    python3 baixar_tecnica.py --subtipo dprodu deapli
    python3 baixar_tecnica.py --quadrienio 2017a2020 --subtipo patente
    python3 baixar_tecnica.py --listar           # só mostra o que existe no portal
"""
import argparse
import json
import os
import sys
import urllib.request

CKAN = 'https://dadosabertos.capes.gov.br/api/3/action'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
UA = {'User-Agent': 'Mozilla/5.0 (MAPA-PG build script)'}

# Dataset CKAN de cada quadriênio. `detalhe` traz os campos específicos do subtipo;
# `prod` é a tabela-mãe da produção intelectual (fatiada por TECNICA-<SUBTIPO>).
DATASETS = {
    '2013a2016': {
        'detalhe': 'detalhes-da-producao-intelectual-tecnica-2013a2016',
        'prod':    'producao-intelectual-de-programas-de-pos-graduacao-2013-a-2016',
    },
    '2017a2020': {
        'detalhe': '2017-a-2020-detalhes-da-producao-intelectual-tecnica-de-programas-de-pos-graduacao-stricto-sensu',
        'prod':    '2017-a-2020-producao-intelectual-de-pos-graduacao-stricto-sensu-no-brasil',
    },
    '2021a2024': {
        'detalhe': '2021-a-2024-detalhes-da-producao-intelectual-tecnica-de-programas-de-pos-graduacao-stricto-sensu',
        'prod':    '2021-a-2024-producao-intelectual-de-pos-graduacao-stricto-sensu-no-brasil',
    },
}


def ckan_package(name):
    req = urllib.request.Request(f'{CKAN}/package_show?id={name}', headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)['result']


def csv_resources(pkg):
    return [r for r in pkg['resources'] if (r.get('format') or '').upper() == 'CSV']


def achar(pkg, sufixo):
    """Resource cujo nome de arquivo termina em `-<sufixo>.csv` (case-insensitive)."""
    alvo = f'-{sufixo}.csv'.lower()
    for r in csv_resources(pkg):
        if r['url'].lower().endswith(alvo):
            return r
    return None


def baixar(url, destino):
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        print(f'  = {os.path.basename(destino)} (já existe, {os.path.getsize(destino)/1e6:.1f} MB)')
        return
    print(f'  ↓ {os.path.basename(destino)} ...', end='', flush=True)
    req = urllib.request.Request(url, headers=UA)
    tmp = destino + '.part'
    with urllib.request.urlopen(req, timeout=900) as r, open(tmp, 'wb') as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    os.replace(tmp, destino)
    print(f' {os.path.getsize(destino)/1e6:.1f} MB')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quadrienio', default='2021a2024', choices=sorted(DATASETS))
    ap.add_argument('--subtipo', nargs='+', default=['patente'],
                    help='sufixos CAPES: patente, dprodu, deapli, destec, servtec, ...')
    ap.add_argument('--listar', action='store_true',
                    help='lista os subtipos disponíveis no quadriênio e sai')
    ap.add_argument('--sem-mae', action='store_true',
                    help='baixa só o arquivo de detalhe (dispensa a tabela-mãe)')
    a = ap.parse_args()

    ds = DATASETS[a.quadrienio]
    print(f'[CKAN] package_show: {ds["detalhe"]}')
    pkg_det = ckan_package(ds['detalhe'])

    if a.listar:
        print(f'\nSubtipos de produção técnica em {a.quadrienio}:')
        for r in csv_resources(pkg_det):
            suf = r['url'].rsplit('-', 1)[-1][:-4]
            print(f'  {suf:<12} {r.get("name")}')
        return 0

    print(f'[CKAN] package_show: {ds["prod"]}')
    pkg_prod = None if a.sem_mae else ckan_package(ds['prod'])

    os.makedirs(DATA_DIR, exist_ok=True)
    faltou = []
    for st in a.subtipo:
        print(f'\n[{a.quadrienio} / {st}]')
        rd = achar(pkg_det, st)
        if rd is None:
            faltou.append(f'detalhe:{st}')
            print(f'  ! sem arquivo de detalhe para "{st}" neste quadriênio')
        else:
            baixar(rd['url'], os.path.join(DATA_DIR, f'tec_detalhe_{a.quadrienio}_{st}.csv'))
        if pkg_prod is not None:
            rp = achar(pkg_prod, f'tecnica-{st}')
            if rp is None:
                faltou.append(f'prod:{st}')
                print(f'  ! sem fatia TECNICA-{st.upper()} na tabela-mãe')
            else:
                baixar(rp['url'], os.path.join(DATA_DIR, f'tec_prod_{a.quadrienio}_{st}.csv'))

    print(f'\nDestino: {DATA_DIR}')
    if faltou:
        print('Não encontrados: ' + ', '.join(faltou))
    return 0


if __name__ == '__main__':
    sys.exit(main())
