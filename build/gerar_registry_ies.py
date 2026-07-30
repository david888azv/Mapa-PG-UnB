#!/usr/bin/env python3
"""
Gera docs/registry_ies.json — catálogo das 27 IFES de referência (26 federais
"capitais", uma por UF, + UnB).

Continua existindo depois do catálogo geral (`gerar_ies_catalogo.py`, ~490
instituições) porque duas ferramentas de build o consomem: `gerar_stubs_ies.py`
(as landings de SEO em docs/ies/<sigla>/) e `gerar_sitemap.py`. O APP não o
baixa mais — ele carrega `ies_index.json` + `dados/ies-<slug>.json`.

A regra de "quais programas são desta instituição" mora em `ies_core.py` e é
compartilhada com o catálogo geral. Aqui ficam só as 27 e a decisão editorial de
quais ENTIDADES compõem cada uma.

A tabela abaixo é SEMENTE DE ENTIDADES, não de siglas: as variantes de sigla são
derivadas de `por_entidade` no ies_canonico.json. Manter siglas à mão defasou
duas vezes — Piauí sem a sigla atual (4 programas invisíveis) e a renomeação da
v5.3.0 ('UFSC - BLUMENAU' → 'UFSC-BLUMENAU') derrubando outros 5.
"""
import json
import os
import sys

import ies_core as C

OUT_PATH = os.path.join(C.REPO, 'docs', 'registry_ies.json')

# ── 27 IFES de referência: sigla canônica → (UF, nome, [siglas-semente]) ──
# As siglas-semente servem para localizar as ENTIDADES da instituição, inclusive
# campi que são entidade própria e que a decisão editorial agrega à sede.
IFES = {
    'UFAC':    ('AC', 'Universidade Federal do Acre',                 ['UFAC']),
    'UFAL':    ('AL', 'Universidade Federal de Alagoas',              ['UFAL']),
    'UNIFAP':  ('AP', 'Universidade Federal do Amapá',                ['UNIFAP']),
    'UFAM':    ('AM', 'Universidade Federal do Amazonas',             ['UFAM']),
    'UFBA':    ('BA', 'Universidade Federal da Bahia',                ['UFBA']),
    'UFC':     ('CE', 'Universidade Federal do Ceará',                ['UFC']),
    'UNB':     ('DF', 'Universidade de Brasília',                     ['UNB']),
    'UFES':    ('ES', 'Universidade Federal do Espírito Santo',       ['UFES']),
    'UFG':     ('GO', 'Universidade Federal de Goiás',                ['UFG']),
    'UFMA':    ('MA', 'Universidade Federal do Maranhão',             ['UFMA']),
    'UFMT':    ('MT', 'Universidade Federal de Mato Grosso',          ['UFMT']),
    'UFMS':    ('MS', 'Universidade Federal de Mato Grosso do Sul',   ['UFMS']),
    'UFMG':    ('MG', 'Universidade Federal de Minas Gerais',         ['UFMG']),
    'UFPA':    ('PA', 'Universidade Federal do Pará',                 ['UFPA']),
    'UFPB':    ('PB', 'Universidade Federal da Paraíba',
               ['UFPB-JP', 'UFPB/AREIA', 'UFPB/J.P.', 'UFPB/RT', 'UFPB']),
    'UFPR':    ('PR', 'Universidade Federal do Paraná',               ['UFPR']),
    'UFPE':    ('PE', 'Universidade Federal de Pernambuco',           ['UFPE']),
    'UFPI':    ('PI', 'Universidade Federal do Piauí',                ['FUFPI']),
    'UFRJ':    ('RJ', 'Universidade Federal do Rio de Janeiro',       ['UFRJ']),
    'UFRN':    ('RN', 'Universidade Federal do Rio Grande do Norte',  ['UFRN']),
    'UFRGS':   ('RS', 'Universidade Federal do Rio Grande do Sul',    ['UFRGS']),
    'UNIR':    ('RO', 'Universidade Federal de Rondônia',             ['UNIR']),
    'UFRR':    ('RR', 'Universidade Federal de Roraima',              ['UFRR']),
    'UFSC':    ('SC', 'Universidade Federal de Santa Catarina',
               ['UFSC', 'UFSC - BLUMENAU']),
    'UNIFESP': ('SP', 'Universidade Federal de São Paulo',            ['UNIFESP']),
    'UFS':     ('SE', 'Universidade Federal de Sergipe',
               ['FUFSE', 'FUFSE/ITAB']),
    'UFT':     ('TO', 'Universidade Federal do Tocantins',            ['UFT']),
}


def entidades_das_ifes(ent_de_sigla):
    """{sigla_ifes: set(CD_ENTIDADE_CAPES)} a partir das siglas-semente."""
    ents = {}
    for canon, (_uf, _nome, semente) in IFES.items():
        e = {ent_de_sigla[s] for s in ({canon} | set(semente)) if s in ent_de_sigla}
        if not e:
            sys.exit(f'✗ nenhuma entidade CAPES para {canon} '
                     f'(sementes {sorted(semente)} não aparecem em por_entidade)')
        ents[canon] = e
    return ents


def construir():
    por_entidade, ent_de_sigla, _ = C.carregar_canonico()
    ents = entidades_das_ifes(ent_de_sigla)
    siglas_de = {k: set(C.siglas_de_entidades(v, por_entidade)) for k, v in ents.items()}

    registros, siglas_vistas = C.varrer_areas()

    # guarda: sigla dos dados cuja ENTIDADE é de uma das 27 e ficou fora da lista.
    # Checar por sigla é justamente o que deixava a renomeação passar.
    ent2ifes = {e: k for k, es in ents.items() for e in es}
    todas = {s for v in siglas_de.values() for s in v}
    orfas = sorted(s for s in siglas_vistas
                   if ent2ifes.get(ent_de_sigla.get(s)) and s not in todas)
    if orfas:
        sys.exit(f'✗ abortado: siglas nos dados cuja entidade é de uma IFES de '
                 f'referência e ficaram fora de siglas_capes: {orfas}. '
                 'Programas sob elas ficariam invisíveis na cascata.')
    desconhecidas = sorted(s for s in siglas_vistas if s not in ent_de_sigla)
    if desconhecidas:
        print(f'⚠ {len(desconhecidas)} sigla(s) sem entidade em ies_canonico.json: '
              f'{desconhecidas[:8]}', file=sys.stderr)

    por_ies = C.programas_por_ies(registros, siglas_de, C.sufixos_unb())

    ifes_list = [{'sigla': k, 'uf': IFES[k][0], 'nome': IFES[k][1],
                  'siglas_capes': sorted(siglas_de[k]),
                  'n_prog': len(por_ies[k]['programas'])}
                 for k in IFES]
    ifes_list.sort(key=lambda x: x['uf'])   # seletor por UF ("uma por estado")
    return ifes_list, por_ies


def main():
    ifes_list, por_ies = construir()
    catalog = {
        'gerado_em': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
        'padrao': 'UNB',
        'n_ifes': len(ifes_list),
        'ifes': ifes_list,
        'por_ies': por_ies,
    }
    with open(OUT_PATH, 'w', encoding='utf-8') as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=1)

    print(f'✓ {OUT_PATH}  ({os.path.getsize(OUT_PATH)/1024:.1f} KB)')
    print(f'  IFES: {len(ifes_list)}')
    faltando = [i['sigla'] for i in ifes_list if i['n_prog'] == 0]
    if faltando:
        print(f'  ⚠ SEM PROGRAMAS: {faltando}')
    for i in sorted(ifes_list, key=lambda x: -x['n_prog']):
        print(f"  {i['uf']}  {i['sigla']:<8} {i['n_prog']:>3} prog  "
              f"{len(por_ies[i['sigla']]['grandes_areas'])} grandes áreas")


if __name__ == '__main__':
    main()
