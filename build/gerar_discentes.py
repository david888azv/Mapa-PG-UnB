#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conta ALUNOS por programa e ano — o denominador da razão bolsas/matriculados.

Pedido do Prof. Marcos D. Pereira (PPGBq/UFRJ) depois de ver a série de bolsas:
o número absoluto mostra o corte, mas quem quer discutir equidade de cotas
precisa do percentual de alunos cobertos por bolsa. O numerador já existe
(`gerar_bolsas.py`); aqui sai o denominador.

FONTE
-----
`Discentes da Pós-Graduação Stricto Sensu`, dados abertos da CAPES, um arquivo
por ano. Cada linha é um discente-ano, com `CD_PROGRAMA_IES` — a mesma chave do
resto do aplicativo. São ~150 MB por ano; o intervalo 2013-2024 dá ~1,8 GB, e por
isso o processamento é ANO A ANO, descartando os conjuntos de cada ano antes de
abrir o próximo. **Começa em 2013**: os arquivos anteriores têm outro esquema, sem
o nível do aluno (ver a nota no argumento `--anos`).

DUAS CONTAGENS, E ELAS RESPONDEM A PERGUNTAS DIFERENTES
-------------------------------------------------------
- **matriculados**: situação `MATRICULADO` no fechamento do ano. É o número que
  a coordenação reconhece como "tamanho do programa hoje".
- **ativos no ano**: qualquer situação — matriculado, titulado, desligado,
  abandono, mudança de nível. É quem passou pelo programa naquele ano.

A razão do painel usa **ativos**, e não matriculados, por coerência de unidade:
o numerador (bolsistas do ano) também é fluxo, e conta quem teve bolsa em
qualquer parte do ano. Dividir fluxo por estoque superestimaria a cobertura,
justamente nos programas que titulam muito. As duas contagens vão no arquivo,
para o app poder mostrar as duas.

NÍVEIS
------
Dois blocos, casando com o lado das bolsas: **mestrado** (acadêmico e
profissional) e **doutorado** (idem). O conjunto de bolsas quase não tem
mestrado profissional (143 registros em quinze anos), mas o de discentes tem
67 mil só em 2024 — separar os dois lados de formas diferentes daria razão
maior que 100% em programa profissional.

Uso:
    python3 gerar_discentes.py --baixar          # baixa 2013-2024 (~1,8 GB) e conta
    python3 gerar_discentes.py                   # usa o que já está em disco
    python3 gerar_discentes.py --anos 2020 2024  # só um intervalo
Saída: build/cache/discentes_por_programa.json, lido por gerar_bolsas.py.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_CAPES = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
FONTE_DIR = os.path.join(DADOS_CAPES, 'discentes')
SAIDA = os.path.join(REPO, 'build', 'cache', 'discentes_por_programa.json')

CKAN = 'https://dadosabertos.capes.gov.br/api/3/action/package_show?id='
PACOTES = [
    'discentes-dos-programas-de-pos-graduacao-stricto-sensu-no-brasil-2004-a-2012',
    'discentes-da-pos-graduacao-stricto-sensu-do-brasil-2013-a-2016',
    'discentes-da-pos-graduacao-stricto-sensu-do-brasil-2017-a-2019',   # cobre 2017-2020
    '2021-a-2024-discentes-da-pos-graduacao-stricto-sensu-do-brasil',
]

NIVEL = {
    'MESTRADO': 'ME', 'MESTRADO PROFISSIONAL': 'ME',
    'DOUTORADO': 'DO', 'DOUTORADO PROFISSIONAL': 'DO',
}


def _ano_do_arquivo(nome):
    m = re.search(r'DISCENTES-(\d{4})', nome.upper())
    return int(m.group(1)) if m else None


def baixar(ini, fim):
    os.makedirs(FONTE_DIR, exist_ok=True)
    alvos = {}
    for pac in PACOTES:
        with urllib.request.urlopen(CKAN + pac, timeout=60) as r:
            d = json.load(r)['result']
        for rec in d['resources']:
            if rec['format'].upper() != 'CSV':
                continue
            ano = _ano_do_arquivo(rec['name'])
            if ano and ini <= ano <= fim:
                alvos[ano] = rec['url']
    for ano in sorted(alvos):
        destino = os.path.join(FONTE_DIR, os.path.basename(alvos[ano]))
        if os.path.exists(destino) and os.path.getsize(destino) > 1_000_000:
            print(f'  · já tenho {ano}')
            continue
        print(f'  ↓ {ano}  ({os.path.basename(destino)})', flush=True)
        urllib.request.urlretrieve(alvos[ano], destino)
    print(f'✓ fonte em {FONTE_DIR}')


def _abrir(arq):
    """A codificação varia entre os arquivos, como no conjunto de bolsas."""
    for enc in ('utf-8-sig', 'latin-1'):
        try:
            with open(arq, encoding=enc, newline='') as fh:
                fh.read(200000)
            return enc
        except UnicodeDecodeError:
            continue
    return 'latin-1'


def contar(ini, fim):
    arquivos = sorted(glob.glob(os.path.join(FONTE_DIR, '*.csv')))
    if not arquivos:
        raise SystemExit(f'✗ nada em {FONTE_DIR} — rode com --baixar')
    out = defaultdict(dict)          # cd → ano → {'ME': [mat, ativos], 'DO': [...]}
    for arq in arquivos:
        ano = _ano_do_arquivo(os.path.basename(arq))
        if ano is None or not (ini <= ano <= fim):
            continue
        # Conjuntos SÓ deste ano: guardar todos os anos de uma vez estoura a RAM.
        mat = defaultdict(set)
        ativ = defaultdict(set)
        n = 0
        with open(arq, encoding=_abrir(arq), newline='') as fh:
            for r in csv.DictReader(fh, delimiter=';'):
                cd = (r.get('CD_PROGRAMA_IES') or '').strip()
                niv = NIVEL.get((r.get('DS_GRAU_ACADEMICO_DISCENTE') or '').strip().upper())
                if not cd or not niv:
                    continue
                pid = (r.get('ID_PESSOA') or '').strip() or (r.get('NR_DOCUMENTO_DISCENTE') or '').strip()
                if not pid:
                    continue
                ativ[(cd, niv)].add(pid)
                if (r.get('NM_SITUACAO_DISCENTE') or '').strip().upper() == 'MATRICULADO':
                    mat[(cd, niv)].add(pid)
                n += 1
        for (cd, niv), pessoas in ativ.items():
            out[cd].setdefault(str(ano), {})[niv] = [len(mat.get((cd, niv), ())), len(pessoas)]
        print(f'  · {ano}  {n:>9,} discentes-ano  ·  {len({cd for cd, _ in ativ}):>5} programas',
              flush=True)
        del mat, ativ
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--baixar', action='store_true')
    # 2013 e não 2010 de propósito: os arquivos de 2004-2012 têm OUTRO esquema e
    # não trazem o nível do aluno. O que existe lá é `NM_NIVEL_PROGRAMA` (nível do
    # PROGRAMA, e 'MESTRADO/DOUTORADO' em dois terços dos casos) e
    # `NM_NIVEL_TITULACAO_DISCENTE`, que é o grau que o aluno JÁ TEM — usar este
    # classificaria como mestrado todo doutorando que já é mestre. Também não há
    # `ID_PESSOA`, e `NR_SEQUENCIAL_DISCENTE` repete (356 vezes no pior caso).
    # Sem nível do aluno não há razão por nível, e inventá-la seria pior que a
    # série começar três anos depois.
    ap.add_argument('--anos', nargs=2, type=int, default=[2013, 2024],
                    metavar=('INI', 'FIM'))
    a = ap.parse_args()
    t0 = time.perf_counter()
    ini, fim = a.anos

    if a.baixar:
        baixar(ini, fim)

    dados = contar(ini, fim)
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    payload = {
        'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
        'anos': [ini, fim],
        'fonte': 'CAPES — Dados Abertos, Discentes da Pós-Graduação Stricto Sensu',
        'contagens': ['matriculados no fechamento do ano', 'ativos no ano (qualquer situação)'],
        'niveis': {'ME': 'mestrado (acadêmico e profissional)',
                   'DO': 'doutorado (acadêmico e profissional)'},
        'data': dados,
    }
    with open(SAIDA, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(',', ':'))
    print(f'\n✓ {SAIDA}  ({os.path.getsize(SAIDA)/1024/1024:.1f} MB)')
    print(f'  programas com discente: {len(dados):,}')
    print(f'  {time.perf_counter() - t0:.0f}s')


if __name__ == '__main__':
    main()
