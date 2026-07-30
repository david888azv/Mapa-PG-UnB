#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ies_core — regra ÚNICA de "quais programas pertencem a uma instituição"
=======================================================================
Compartilhado por `gerar_registry_ies.py` (as 27 IFES de referência) e
`gerar_ies_catalogo.py` (o catálogo das ~490 instituições com busca no app).

Existe para NÃO reimplementar a regra de metadado em script auxiliar: o
antecessor de `verificar_titularidade.py` fazia isso e passou a mentir no dia em
que a regra mudou. Quem precisa da lista de programas de uma instituição importa
daqui.

AS TRÊS REGRAS QUE MORAM AQUI
-----------------------------
1. **Identidade é `CD_ENTIDADE_CAPES`, não a sigla.** A sigla é o rótulo do ano
   (FUFPI→UFPI, 'UFSC - BLUMENAU'→'UFSC-BLUMENAU'). Uma instituição é um conjunto
   de entidades; campus é entidade própria (UFSC-BLUMENAU=41001028 ≠
   UFSC=41001010) e só se agrega a outra por decisão editorial explícita.
2. **Titularidade por quadriênio.** O programa entra na lista da instituição pelo
   registro MAIS RECENTE cuja sigla é dela — não pelo primeiro nem pelo mais
   recente global. Programa em rede/rodízio de coordenação pertence a
   instituições diferentes conforme o quadriênio analisado, e é isso que o app
   mostra (BIONORTE Centro-Oeste: UnB 2013-2020, UNEMAT 2021-2024).
3. **Descarta apenas o que está EM DESATIVAÇÃO no registro mais recente dessa
   instituição.** Situação vazia é MANTIDA (programa ativo pode vir sem o campo).
"""
import glob
import json
import os
import re
import unicodedata
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(AQUI, '..'))
DADOS = os.path.join(REPO, 'docs', 'dados')
IES_CANONICO = os.path.join(AQUI, 'ies_canonico.json')
REGISTRY_UNB = os.path.join(REPO, 'docs', 'registry.json')

QUAD_ORDER = {'2013-2016': 0, '2017-2020': 1, '2021-2024': 2}
DESATIVADOS = {'EM DESATIVACAO', 'EM DESATIVAÇÃO'}


# ── normalização e slug ──────────────────────────────────────────────
def sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def norm_busca(s):
    """Chave de busca: sem acento, sem caixa, sem espaço/pontuação.

    É o que faz "FIO CRUZ" achar FIOCRUZ e "ufpb joao pessoa" achar
    UFPB-JOÃO PESSOA. Aplicar dos DOIS lados (consulta e alvo).
    """
    return re.sub(r'[^A-Z0-9]', '', sem_acento(s).upper())


def slug_ies(sigla):
    """Sigla → nome de arquivo seguro.

    Várias siglas têm espaço, acento ou barra ('UFPB-JOÃO PESSOA',
    'FIOCRUZ-NESC/CPQAM', 'FIOCRUZ-EGS BRASÍLIA'), que não podem ir cru para uma
    URL. Colisão é erro do chamador — `catalogo()` aborta.
    """
    s = sem_acento(sigla).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s or 'ies'


# ── fontes ───────────────────────────────────────────────────────────
def carregar_canonico():
    if not os.path.exists(IES_CANONICO):
        raise SystemExit(f'✗ {IES_CANONICO} ausente — necessário para agrupar as siglas.')
    ic = json.load(open(IES_CANONICO, encoding='utf-8'))
    por_entidade = ic['por_entidade']
    ent_de_sigla = {s: e for e, v in por_entidade.items() for s in v['siglas']}
    # sigla de época → sigla canônica (a do ano mais recente da entidade)
    canon_de_sigla = {s: v['sigla'] for s, v in ic['canonico'].items()}
    return por_entidade, ent_de_sigla, canon_de_sigla


def sufixos_unb():
    """cd_programa → sufixo MAPA-PG-XXXXXX (retrocompat dos deep-links ?curso=)."""
    if not os.path.exists(REGISTRY_UNB):
        return {}
    reg = json.load(open(REGISTRY_UNB, encoding='utf-8'))
    return {p['cd_programa']: p['sufixo'] for p in reg.get('programas_unb', [])}


def varrer_areas():
    """Lê os area-*.json uma vez. Devolve (registros, siglas_vistas).

    registros: lista de dicts achatados com o que as duas saídas precisam.
    """
    registros = []
    siglas = set()
    for f in sorted(glob.glob(os.path.join(DADOS, 'area-*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        md = d['metadata']
        for r in d['data']:
            siglas.add(r['sigla'])
            registros.append({
                'cd': r['cd'], 'sigla': r['sigla'], 'quad': r.get('quad'),
                'nome': r['programa'], 'nota': r['nota'],
                'situacao': (r.get('situacao') or '').upper(),
                'area_capes': md['area'], 'slug_area': md['slug'],
                'grande_area_cnpq': md.get('grande_area', ''),
            })
    if not registros:
        raise SystemExit(f'✗ nenhum area-*.json encontrado em {DADOS}')
    return registros, siglas


# ── a regra ──────────────────────────────────────────────────────────
def programas_por_ies(registros, siglas_de_ies, cd2sufixo=None):
    """{sigla_ies: {'grandes_areas': {...}, 'programas': [...]}}.

    `siglas_de_ies`: {sigla_ies: set(siglas CAPES que são dela)}.
    Aplica as regras 2 e 3 do cabeçalho do módulo.
    """
    cd2sufixo = cd2sufixo or {}
    var2ies = {v: k for k, vs in siglas_de_ies.items() for v in vs}

    # melhor registro por (ies, cd) = mais recente cuja sigla é da instituição
    melhor = defaultdict(dict)
    for r in registros:
        ies = var2ies.get(r['sigla'])
        if not ies:
            continue
        q = QUAD_ORDER.get(r['quad'], -1)
        cur = melhor[ies].get(r['cd'])
        if cur is None or q > cur['_q']:
            melhor[ies][r['cd']] = dict(r, _q=q)

    out = {}
    for ies in siglas_de_ies:
        escolhidos = [e for e in melhor.get(ies, {}).values()
                      if e['situacao'] not in DESATIVADOS]
        escolhidos.sort(key=lambda e: (e['grande_area_cnpq'], e['area_capes'], e['nome']))
        grandes = defaultdict(set)
        progs = []
        for e in escolhidos:
            entry = {
                'cd_programa': e['cd'], 'nome': e['nome'], 'nota': e['nota'],
                'area_capes': e['area_capes'], 'slug_area': e['slug_area'],
                'grande_area_cnpq': e['grande_area_cnpq'],
            }
            if e['cd'] in cd2sufixo:
                entry['sufixo'] = cd2sufixo[e['cd']]
            progs.append(entry)
            grandes[e['grande_area_cnpq']].add(e['area_capes'])
        out[ies] = {'grandes_areas': {g: sorted(a) for g, a in sorted(grandes.items())},
                    'programas': progs}
    return out


def siglas_de_entidades(entidades, por_entidade):
    """Todas as siglas que um conjunto de entidades já usou (imune a renomeação)."""
    return sorted({s for e in entidades for s in por_entidade[e]['siglas']})
