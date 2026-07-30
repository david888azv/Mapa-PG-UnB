#!/usr/bin/env python3
"""
Gera docs/registry_ies.json — catálogo de programas EM FUNCIONAMENTO das 27
IFES de referência (26 federais "capitais", uma por UF, + UnB), para alimentar
a cascata Grande Área → Área CAPES → Curso quando o usuário escolhe qual
universidade federal usar como referência (destaque em vermelho).

FONTE: os próprios docs/dados/area-*.json (a mesma base que o app renderiza),
garantindo que a cascata só ofereça programas que existem nos dados carregados
e capture todas as variantes de sigla por campus/fundação em qualquer quadriênio.

Cada IFES → variantes de sigla CAPES. A lista MANUAL abaixo é só um piso: as
variantes reais são derivadas de `build/ies_canonico.json` (chaveado por
CD_ENTIDADE_CAPES, a identidade estável da instituição) e unidas à sigla canônica.
Manter isso à mão defasou: o Piauí estava declarado só como `FUFPI` e Sergipe só
como `FUFSE`/`FUFSE/ITAB`, sem a sigla ATUAL. Como `REF_SIGLAS_CAPES` no app filtra
`UNB_CDS` por sigla de época, programa que só existe sob o rótulo novo (criado no
quadriênio 2021-2024) ficava FORA da cascata Grande Área → Área → Curso daquela
universidade: 4 programas da UFPI e 1 da UFS, invisíveis para quem escolhia essas
duas como referência.

id do curso = cd_programa. Para a UnB reaproveita-se o sufixo de registry.json
(retrocompat de deep-links).
"""
import glob, json, os, sys, time
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(REPO, 'docs', 'dados')
OUT_PATH = os.path.join(REPO, 'docs', 'registry_ies.json')
REGISTRY_UNB = os.path.join(REPO, 'docs', 'registry.json')
IES_CANONICO = os.path.join(REPO, 'build', 'ies_canonico.json')

# ── 27 IFES de referência: sigla canônica → (UF, nome, [variantes CAPES]) ──
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

# ── variantes DERIVADAS por CD_ENTIDADE_CAPES ───────────────────────
# A tabela manual acima é só a SEMENTE: ela diz quais ENTIDADES CAPES compõem
# cada universidade de referência (inclusive campi, que são entidades próprias:
# UFSC-BLUMENAU=41001028 ≠ UFSC=41001010; UFS-ITABAIANA=27001024 ≠ UFS=27001016).
# As variantes de sigla vêm de `por_entidade` em ies_canonico.json — TODAS as
# siglas que cada entidade usou ao longo dos anos.
#
# Manter a lista de siglas à mão defasou duas vezes:
#   • Piauí declarado só como FUFPI e Sergipe só como FUFSE — sem a sigla ATUAL.
#     Programa criado em 2021-2024, que só existe sob o rótulo novo, ficava fora
#     da cascata: 4 da UFPI e 1 da UFS.
#   • A v5.3.0 renomeou rótulos ('UFSC - BLUMENAU' → 'UFSC-BLUMENAU',
#     'UFPB-JP' → 'UFPB-JOÃO PESSOA') e as entradas manuais deixaram de casar,
#     derrubando 5 programas EM FUNCIONAMENTO.
# Derivar da entidade é imune a renomeação: a sigla é o rótulo do ano, a entidade
# é a identidade estável.
if not os.path.exists(IES_CANONICO):
    sys.exit(f'✗ {IES_CANONICO} ausente — necessário para derivar as variantes de sigla.')
_ic = json.load(open(IES_CANONICO, encoding='utf-8'))
POR_ENTIDADE = _ic['por_entidade']
ENT_DE_SIGLA = {s: ent for ent, v in POR_ENTIDADE.items() for s in v['siglas']}

ENTIDADES_DE = {}
IFES_DERIVADA = {}
for canon, (uf, nome, semente) in IFES.items():
    ents = {ENT_DE_SIGLA[s] for s in ({canon} | set(semente)) if s in ENT_DE_SIGLA}
    if not ents:
        sys.exit(f'✗ nenhuma entidade CAPES encontrada para {canon} '
                 f'(siglas-semente {sorted(semente)} não aparecem em por_entidade)')
    ENTIDADES_DE[canon] = ents
    IFES_DERIVADA[canon] = (uf, nome,
                            sorted({s for e in ents for s in POR_ENTIDADE[e]['siglas']}))
IFES = IFES_DERIVADA

# sigla-variante CAPES → sigla canônica
VAR2CANON = {v: canon for canon, (_, _, vs) in IFES.items() for v in vs}
ENT2CANON = {e: canon for canon, ents in ENTIDADES_DE.items() for e in ents}

QUAD_ORDER = {'2013-2016': 0, '2017-2020': 1, '2021-2024': 2}

# ── sufixos UnB (retrocompat de deep-links ?curso=SUFIXO) ────────────
unb_cd2suf = {}
if os.path.exists(REGISTRY_UNB):
    for p in json.load(open(REGISTRY_UNB, encoding='utf-8')).get('programas_unb', []):
        unb_cd2suf[p['cd_programa']] = p['sufixo']

# ── varre as áreas: por IFES, junta programas (1 por cd, quad mais recente) ──
# prog[canon][cd] = {registro mais recente + metadados da área}
prog = defaultdict(dict)
siglas_vistas = set()
for f in sorted(glob.glob(os.path.join(DADOS, 'area-*.json'))):
    d = json.load(open(f, encoding='utf-8'))
    md = d['metadata']
    area_nome = md['area']
    slug = md['slug']
    grande = md.get('grande_area', '')
    for r in d['data']:
        siglas_vistas.add(r['sigla'])
        canon = VAR2CANON.get(r['sigla'])
        if not canon:
            continue
        cd = r['cd']
        q = QUAD_ORDER.get(r.get('quad'), -1)
        cur = prog[canon].get(cd)
        if cur is None or q > cur['_q']:
            prog[canon][cd] = {
                '_q': q,
                'cd_programa': cd,
                'nome': r['programa'],
                'nota': r['nota'],
                'situacao': (r.get('situacao') or '').upper(),
                'sigla_capes': r['sigla'],
                'area_capes': area_nome,
                'slug_area': slug,
                'grande_area_cnpq': grande,
            }

# descarta apenas programas EM DESATIVAÇÃO no registro mais recente.
# (situação vazia '' é mantida: vários programas ativos — inclusive FÍSICA/UnB —
#  não trazem o campo preenchido nos area-*.json, mas constam de metadata.unb_cds.)
DESATIVADOS = {'EM DESATIVACAO', 'EM DESATIVAÇÃO'}
for canon in prog:
    prog[canon] = {cd: e for cd, e in prog[canon].items()
                   if e['situacao'] not in DESATIVADOS}

# ── guarda: sigla que pertence a uma das 27 pelo canônico mas ficou fora de
#    VAR2CANON. Era o defeito silencioso — os programas simplesmente não
#    apareciam na cascata, sem erro em lugar nenhum.
# Checa pela ENTIDADE, não pela sigla: era a renomeação de rótulo que escapava.
orfas = sorted(s for s in siglas_vistas
               if ENT2CANON.get(ENT_DE_SIGLA.get(s)) and s not in VAR2CANON)
if orfas:
    sys.exit('✗ abortado: siglas nos dados cuja ENTIDADE CAPES pertence a uma IFES '
             f'de referência e que ficaram fora de siglas_capes: {orfas}. '
             'Programas sob elas ficariam invisíveis na cascata.')
desconhecidas = sorted(s for s in siglas_vistas if s not in ENT_DE_SIGLA)
if desconhecidas:
    print(f'⚠ {len(desconhecidas)} sigla(s) dos dados sem entidade em '
          f'ies_canonico.json: {desconhecidas[:8]}', file=sys.stderr)

# ── monta a saída ────────────────────────────────────────────────────
por_ies = {}
ifes_list = []
for canon, (uf, nome, variantes) in IFES.items():
    progs = []
    grandes = defaultdict(set)
    for cd, e in sorted(prog.get(canon, {}).items(),
                        key=lambda kv: (kv[1]['grande_area_cnpq'],
                                        kv[1]['area_capes'], kv[1]['nome'])):
        entry = {
            'cd_programa': e['cd_programa'],
            'nome': e['nome'],
            'nota': e['nota'],
            'area_capes': e['area_capes'],
            'slug_area': e['slug_area'],
            'grande_area_cnpq': e['grande_area_cnpq'],
        }
        if canon == 'UNB' and cd in unb_cd2suf:
            entry['sufixo'] = unb_cd2suf[cd]
        progs.append(entry)
        grandes[e['grande_area_cnpq']].add(e['area_capes'])
    por_ies[canon] = {
        'grandes_areas': {g: sorted(a) for g, a in sorted(grandes.items())},
        'programas': progs,
    }
    ifes_list.append({
        'sigla': canon, 'uf': uf, 'nome': nome,
        'siglas_capes': variantes, 'n_prog': len(progs),
    })

# ordena o seletor por UF (natural p/ "uma por estado")
ifes_list.sort(key=lambda x: x['uf'])

catalog = {
    'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
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
