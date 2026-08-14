#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sem_nota — programas aprovados pela CAPES que ainda não têm nota
================================================================
O app compara por nota, e por isso a fase 2 do `gerar_dados_completos.py`
descarta em silêncio todo programa cujo `CD_CONCEITO_PROGRAMA` não é numérico
(`continue` logo depois do `pd.to_numeric(...).dropna()`). São os aprovados por
APCN, marcados com **'A'** no catálogo, quase todos abertos em 2024.

O efeito colateral apareceu em 13/08/2026, quando a Presidência da SBG escreveu
perguntando por que não achava a UFG na área de Geociências: a instituição TEM
o programa (`52001016114P2`, mestrado, início 2024), mas ele não existia em
lugar nenhum do aplicativo — nem na lista da instituição, nem como ausência
explicada. Programa invisível é lido como programa inexistente.

Este módulo não muda a regra de comparação: quem não tem nota continua fora de
médias, rankings e gráficos. Ele só devolve a LISTA, para o app poder dizer que
existe e por que não está sendo comparado.

Fonte: os três catálogos `dados_capes/programas_<quad>_*.csv` — os mesmos que o
`gerar_dados_completos.py` lê. Vale o registro MAIS RECENTE de cada programa,
pela mesma razão do `ies_core`: o catálogo é uma série anual, não um cadastro.
"""
import csv
import glob
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(AQUI, '..'))
DADOS_CAPES = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
DADOS_APP = os.path.join(REPO, 'docs', 'dados')

QUAD_ORDER = {'2013a2016': 0, '2017a2020': 1, '2021a2024': 2}
DESATIVADOS = {'EM DESATIVACAO', 'EM DESATIVAÇÃO'}


def _norm(s):
    """Nome de área comparável: sem acento, sem caixa, só alfanumérico."""
    s = ''.join(c for c in unicodedata.normalize('NFD', s or '')
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^A-Z0-9]', '', s.upper())


def mapa_areas():
    """Duas chaves para a mesma área: (por_codigo, por_nome).

    Cada valor é `(nome exibido, slug, grande área CNPq)`, tirado dos próprios
    `area-*.json` para o slug bater com o `?area=` do app e com o
    `MANIFEST.areas[].slug`.

    O **código** (`CD_AREA_AVALIACAO`) manda, e o nome é só o desempate: a CAPES
    renomeia a área sem trocar o código — a 2 virou 'COMPUTAÇÃO' (era 'CIÊNCIA DA
    COMPUTAÇÃO') e a 21 virou 'EDUCAÇÃO FÍSICA, FISIOTERAPIA, FONOAUDIOLOGIA E
    TERAPIA OCUPACIONAL' (era 'EDUCAÇÃO FÍSICA'). Casar só por nome perdia 14
    programas em silêncio.
    """
    por_codigo, por_nome = {}, {}
    for f in sorted(glob.glob(os.path.join(DADOS_APP, 'area-*.json'))):
        md = json.load(open(f, encoding='utf-8'))['metadata']
        v = (md['area'], md['slug'], md.get('grande_area', ''))
        por_nome[_norm(md['area'])] = v
        cd = md.get('cd_area')
        if cd is not None:
            por_codigo[str(cd).strip()] = v
    if not por_nome:
        raise SystemExit(f'✗ nenhum area-*.json em {DADOS_APP}')
    return por_codigo, por_nome


def _mais_recentes():
    """{cd_programa: registro mais recente dos três catálogos}."""
    melhor = {}
    arquivos = 0
    for quad, ordem in QUAD_ORDER.items():
        for f in sorted(glob.glob(os.path.join(DADOS_CAPES, f'programas_{quad}_*.csv'))):
            arquivos += 1
            # latin-1: o catálogo da CAPES vem em ISO-8859-1; ler como UTF-8
            # quebra os acentos dos nomes de programa.
            with open(f, encoding='latin-1', newline='') as fh:
                for r in csv.DictReader(fh, delimiter=';'):
                    cd = (r.get('CD_PROGRAMA_IES') or '').strip()
                    if not cd:
                        continue
                    try:
                        ano = int(r.get('AN_BASE') or 0)
                    except ValueError:
                        ano = 0
                    chave = (ordem, ano)
                    cur = melhor.get(cd)
                    if cur is None or chave > cur[0]:
                        melhor[cd] = (chave, r)
    if not arquivos:
        raise SystemExit(f'✗ nenhum programas_*.csv em {DADOS_CAPES}')
    return {cd: r for cd, (_k, r) in melhor.items()}


def coletar(verbose=False):
    """Lista de programas sem nota, um dict por programa.

    Campos: cd_programa, nome, sigla (a de época, para o chamador canonicalizar),
    area_capes, slug_area, grande_area_cnpq, modalidade, grau, ano_inicio,
    an_base (último ano em que o programa aparece no catálogo).
    """
    por_codigo, por_nome = mapa_areas()
    fora_de_area = defaultdict(int)
    out = []
    for cd, r in _mais_recentes().items():
        conceito = (r.get('CD_CONCEITO_PROGRAMA') or '').strip()
        if conceito.isdigit():
            continue
        situacao = (r.get('DS_SITUACAO_PROGRAMA') or '').strip().upper()
        if situacao in DESATIVADOS:
            continue
        nome_bruto = (r.get('NM_AREA_AVALIACAO') or '').strip()
        area = (por_codigo.get((r.get('CD_AREA_AVALIACAO') or '').strip())
                or por_nome.get(_norm(nome_bruto)))
        if area is None:
            # Área que o app ainda não tem — a 51 ('Ciências e Humanidades para a
            # Educação Básica') foi criada no catálogo de 2024. O programa entra
            # assim mesmo, com o nome oficial da área e sem slug: aparece na lista
            # da instituição, mas não tem painel de área para onde levar.
            fora_de_area[nome_bruto] += 1
            nome_area, slug_area, grande = nome_bruto, '', ''
        else:
            nome_area, slug_area, grande = area
        graus = (r.get('NM_GRAU_PROGRAMA') or '').strip()
        out.append({
            'cd_programa': cd,
            'nome': (r.get('NM_PROGRAMA_IES') or '').strip(),
            'sigla': (r.get('SG_ENTIDADE_ENSINO') or '').strip(),
            'area_capes': nome_area,
            'slug_area': slug_area,
            'grande_area_cnpq': grande,
            'modalidade': (r.get('NM_MODALIDADE_PROGRAMA') or '').strip(),
            'grau': graus,
            'ano_inicio': (r.get('AN_INICIO_PROGRAMA') or '').strip(),
            'an_base': (r.get('AN_BASE') or '').strip(),
            'conceito_bruto': conceito,
        })
    out.sort(key=lambda p: (p['sigla'], p['area_capes'], p['nome']))
    if verbose and fora_de_area:
        for nome, n in sorted(fora_de_area.items(), key=lambda x: -x[1]):
            print(f'  ⚠ área sem correspondência nos area-*.json: {nome!r} ({n})',
                  file=sys.stderr)
    return out


def main():
    progs = coletar(verbose=True)
    por_sigla = defaultdict(list)
    for p in progs:
        por_sigla[p['sigla']].append(p)
    print(f'programas aprovados e ainda sem nota: {len(progs)}')
    print(f'instituições (sigla de época) com algum: {len(por_sigla)}')
    anos = defaultdict(int)
    for p in progs:
        anos[p['ano_inicio']] += 1
    print('por ano de início: ' + ', '.join(f'{a}: {n}' for a, n in sorted(anos.items())))
    for sigla in sorted(por_sigla)[:8]:
        nomes = ', '.join(p['nome'] for p in por_sigla[sigla][:3])
        print(f'  {sigla}: {len(por_sigla[sigla])} — {nomes}')


if __name__ == '__main__':
    main()
