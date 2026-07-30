#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch cirúrgico — `metadata.n_programas` dos area-*.json
========================================================
`n_programas` contava o CATÁLOGO da área, não os programas que existem no arquivo.
Em `gerar_dados_completos.py::calcular_area` o campo saía de `len(programs_info)`,
que vem inteiro do `cd_meta`, mas o laço que monta `all_data` descarta o programa
sem docente no quadriênio (`len(dd) == 0`) ou sem conceito numérico — e esses nunca
entram em `data`.

Efeito: 5.010 programas anunciados contra 4.824 reais (+186). O app usa o campo na
linha de status ao carregar a área (`index.html`: "N registros carregados — M
programas"), então a Química exibia 81 tendo 79.

CAUSA RAIZ corrigida em paralelo: `gerar_dados_completos.py` agora grava
`len({d['cd'] for d in all_data})`. Este patch acerta os arquivos JÁ GERADOS.

POR QUE UM PATCH E NÃO REGENERAR: rodar a fase 2 reescreve os `area-*.json` do zero
e DESTRÓI os estratos A1-A8/C que `gerar_estratos_app.py` injeta in-place — foi
exatamente assim que a v5.3.0 saiu sem a camada. Este patch altera UM inteiro por
arquivo e prova que não alterou nada mais.

Uso:
    python3 patch_n_programas.py             # dry-run (padrão)
    python3 patch_n_programas.py --aplicar   # grava
    python3 patch_n_programas.py --verificar # só audita o estado atual
"""
import glob
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(AQUI, '..'))
DADOS = os.path.join(REPO, 'docs', 'dados')


def levantar():
    """Devolve [(slug, path, declarado, real, dados_dict)] por área."""
    itens = []
    for p in sorted(glob.glob(os.path.join(DADOS, 'area-*.json'))):
        d = json.load(open(p, encoding='utf-8'))
        real = len({r['cd'] for r in d['data']})
        itens.append((d['metadata']['slug'], p, d['metadata']['n_programas'], real, d))
    return itens


def main(argv):
    so_verificar = '--verificar' in argv
    gravar = '--aplicar' in argv

    itens = levantar()
    divergentes = [(s, p, dec, real, d) for s, p, dec, real, d in itens if dec != real]

    tot_dec = sum(x[2] for x in itens)
    tot_real = sum(x[3] for x in itens)
    print(f'áreas: {len(itens)}')
    print(f'n_programas declarado: {tot_dec} | real (cd distintos em data): {tot_real} '
          f'| diferença: {tot_dec - tot_real:+d}')
    print(f'áreas divergentes: {len(divergentes)}')
    for s, _, dec, real, _ in divergentes[:10]:
        print(f'   {s[:44]:46s} {dec:5d} -> {real:5d}  ({real - dec:+d})')
    if len(divergentes) > 10:
        print(f'   ... e outras {len(divergentes) - 10}')

    if not divergentes:
        print('\n✓ nada a fazer — todos os n_programas já batem com os dados.')
        return 0
    if so_verificar:
        print('\n--- VERIFICAÇÃO: nada foi gravado. ---')
        return 1

    if not gravar:
        print('\n--- DRY-RUN: nada foi gravado. Use --aplicar para gravar. ---')
        return 0

    for slug, path, dec, real, d in divergentes:
        antes = json.load(open(path, encoding='utf-8'))
        d['metadata']['n_programas'] = real
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False, separators=(',', ':'))

        # prova de não-regressão: relê do disco e compara TUDO menos o campo tocado
        depois = json.load(open(path, encoding='utf-8'))
        ma = {k: v for k, v in antes['metadata'].items() if k != 'n_programas'}
        mb = {k: v for k, v in depois['metadata'].items() if k != 'n_programas'}
        assert ma == mb, f'{slug}: metadata mudou além de n_programas'
        assert antes['data'] == depois['data'], f'{slug}: data mudou'
        assert antes.get('ies_list') == depois.get('ies_list'), f'{slug}: ies_list mudou'
        assert antes.get('notas') == depois.get('notas'), f'{slug}: notas mudou'
        assert depois['metadata']['n_programas'] == real, f'{slug}: valor não gravado'

    print(f'\n✓ {len(divergentes)} área(s) corrigida(s); '
          'não-regressão verificada campo a campo após releitura do disco.')
    print('  Lembrete: se os tamanhos mudarem de faixa, rodar '
          "gerar_dados_completos.atualizar_manifest(slugs) para refrescar tamanho_kb.")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
