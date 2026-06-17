#!/usr/bin/env python3
"""
Gera mapa-pg-multi/docs/registry.json com os programas UnB EM FUNCIONAMENTO
(92 = 82 acadêmicos + 10 profissionais; desativados são descartados).
Cada entrada: { sufixo, cd_programa, nome, grau, area_capes, slug_area,
                grande_area, conceito, situacao, modalidade }.

UMA entrada por CD_PROGRAMA_IES: programas renomeados entre quadriênios
(ex.: ARTES→ARTES VISUAIS) NÃO geram entradas duplicadas — usa-se o nome do
registro mais recente.

Sufixo: até 6 letras maiúsculas, A-Z, sem acento. Único por programa.
Mapeamento manual para casos ambíguos; auto-derivação para o restante.
"""
import csv, glob, json, os, re, unicodedata
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
OUT_PATH = os.path.join(REPO, 'docs', 'registry.json')

# ── 1. Carregar programas UnB da base CAPES 2017-2020 ───────────────
files = sorted(glob.glob(os.path.join(DATA_DIR, 'programas_2017a2020_*.csv')))
all_rows = []  # cada linha = um (cd, nome, grau) por AN_BASE
for f in files:
    with open(f, encoding='latin-1') as fh:
        rd = csv.DictReader(fh, delimiter=';')
        for r in rd:
            if (r.get('SG_ENTIDADE_ENSINO') or '').strip() != 'UNB':
                continue
            all_rows.append(r)

# Para cada cd, pegar o registro do AN_BASE mais recente (estado mais atual)
latest = {}
for r in all_rows:
    cd = r['CD_PROGRAMA_IES']
    an = int(r['AN_BASE'])
    if cd not in latest or an > int(latest[cd]['AN_BASE']):
        latest[cd] = r

# Filtrar apenas programas EM FUNCIONAMENTO (descarta desativados)
ativos = {cd: r for cd, r in latest.items()
          if r.get('DS_SITUACAO_PROGRAMA','').strip().upper() == 'EM FUNCIONAMENTO'}

# Fundir todas as ocorrências de cada CD ativo em UMA entrada por CD.
# (Programas renomeados entre anos — ex.: ARTES→ARTES VISUAIS — NÃO podem virar
#  duas entradas; usa-se o nome do registro mais recente.)
prog_map = defaultdict(list)
for r in all_rows:
    cd = r['CD_PROGRAMA_IES']
    if cd in ativos:
        prog_map[cd].append(r)

# ── 2. Mapeamento manual canônico de sufixos ────────────────────────
# Quando vazio, será auto-derivado (primeiras 6 letras sem acento).
SUFFIX_MANUAL = {
    'FÍSICA': 'FISICA',
    'QUÍMICA': 'QUIMIC',
    'MATEMÁTICA': 'MATEMA',
    'ESTATISTICA': 'ESTATI',
    'INFORMÁTICA': 'INFORM',
    'COMPUTAÇÃO APLICADA': 'COMPAP',
    'GEOLOGIA': 'GEOLOG',
    'GEOCIÊNCIAS APLICADAS E GEODINÂMICA': 'GEOAPL',
    'AGRONOMIA': 'AGRONO',
    'AGRONEGÓCIOS': 'AGRNEG',
    'FITOPATOLOGIA': 'FITOPA',
    'CIÊNCIAS FLORESTAIS': 'FLORES',
    'CIÊNCIAS BIOLÓGICAS (BIOLOGIA MOLECULAR)': 'BIOMOL',
    'BIOLOGIA ANIMAL': 'BIOANI',
    'BIOLOGIA MICROBIANA': 'BIOMIC',
    'ECOLOGIA': 'ECOLOG',
    'BOTÂNICA': 'BOTANI',
    'ZOOLOGIA': 'ZOOLOG',
    'BIOTECNOLOGIA E BIODIVERSIDADE - REDE PRÓ-CENTRO-OESTE': 'BIOTEC',
    'NANOCIÊNCIA E NANOBIOTECNOLOGIA': 'NANOBI',
    'PATOLOGIA MOLECULAR': 'PATMOL',
    'CIÊNCIAS ANIMAIS': 'CIANIM',
    'SAÚDE ANIMAL': 'SAUANI',
    'CIÊNCIAS DA SAÚDE': 'CIASAU',
    'CIÊNCIAS FARMACÊUTICAS': 'FARMAC',
    'MEDICINA TROPICAL': 'MEDTRO',
    'CIENCIAS MEDICAS': 'CIAMED',
    'CIÊNCIAS MÉDICAS': 'CIAMED',
    'NUTRIÇÃO HUMANA': 'NUTRIC',
    'ODONTOLOGIA': 'ODONTO',
    'ENFERMAGEM': 'ENFERM',
    'SAÚDE COLETIVA': 'SAUCOL',
    'BIOÉTICA': 'BIOETI',
    'CIÊNCIAS E TECNOLOGIAS EM SAÚDE': 'CTESAU',
    'CIÊNCIAS DA REABILITAÇÃO': 'REABIL',
    'EDUCAÇÃO FÍSICA': 'EDUFIS',
    'CIÊNCIAS DO COMPORTAMENTO': 'PSCCOM',
    'PROCESSOS DE DESENVOLVIMENTO HUMANO E SAÚDE': 'PROCDH',
    'PSICOLOGIA CLÍNICA E CULTURA': 'PSCCLI',
    'PSICOLOGIA DO DESENVOLVIMENTO E ESCOLAR': 'PSCDES',
    'PSICOLOGIA SOCIAL, DO TRABALHO E DAS ORGANIZAÇÕES (PSTO)': 'PSCSTO',
    'ANTROPOLOGIA': 'ANTROP',
    'SOCIOLOGIA': 'SOCIOL',
    'CIÊNCIA POLÍTICA': 'POLITI',
    'RELAÇÕES INTERNACIONAIS': 'RELINT',
    'HISTÓRIA': 'HISTOR',
    'GEOGRAFIA': 'GEOGRA',
    'FILOSOFIA': 'FILOSO',
    'METAFÍSICA': 'METAFI',
    'POLÍTICA SOCIAL': 'POLSOC',
    'EDUCAÇÃO': 'EDUCAC',  # acadêmico (cd P0); profissional vira EDUCAP via regra abaixo
    'EDUCAÇÃO EM CIÊNCIAS': 'EDUCIE',
    'ENSINO DE CIÊNCIAS': 'ENSCIE',
    'ECONOMIA': 'ECONOM',
    'ADMINISTRAÇÃO': 'ADMIN',
    'CIÊNCIAS CONTÁBEIS': 'CONTAB',
    'CONTABILIDADE - UNB - UFPB - UFRN': 'CONUNB',
    'GESTÃO PÚBLICA': 'GESPUB',
    'TURISMO': 'TURISM',
    'DIREITO': 'DIREIT',
    'DIREITO, REGULAÇÃO E POLÍTICAS PÚBLICAS': 'DIRREG',
    'COMUNICAÇÃO': 'COMUNI',
    'CIÊNCIAS DA INFORMAÇÃO': 'INFOCI',
    'ARTES': 'ARTES',
    'ARTES CÊNICAS': 'ARTCEN',
    'ARTES VISUAIS': 'ARTVIS',
    'MÚSICA': 'MUSICA',
    'DESIGN': 'DESIGN',
    'ARQUITETURA E URBANISMO': 'ARQURB',
    'LINGÜÍSTICA': 'LINGUI',
    'LINGÜÍSTICA APLICADA': 'LINAPL',
    'LITERATURA': 'LITERA',
    'ESTUDOS DE TRADUÇÃO': 'TRADUC',
    'ESTRUTURAS E CONSTRUÇÃO CIVIL': 'ESTRCC',
    'GEOTECNIA': 'GEOTEC',
    'TRANSPORTES': 'TRANSP',
    'TECNOLOGIA AMBIENTAL E RECURSOS HÍDRICOS': 'TECARH',
    'CIÊNCIAS MECÂNICAS': 'MECANI',
    'SISTEMAS MECATRÔNICOS': 'MECATR',
    'INTEGRIDADE DE MATERIAIS DA ENGENHARIA': 'INTMAT',
    'ENGENHARIA BIOMÉDICA': 'ENGBIO',
    'ENGENHARIA ELÉTRICA': 'ENGELE',
    'ENGENHARIA DE SISTEMAS ELETRÔNICOS E DE AUTOMAÇÃO': 'ESELET',
    'CIÊNCIAS AMBIENTAIS': 'CIAMBI',
    'DESENVOLVIMENTO SUSTENTÁVEL': 'DESSUS',
    'MEIO AMBIENTE E DESENVOLVIMENTO RURAL': 'MADER',
    'SUSTENTABILIDADE JUNTO A POVOS E TERRITÓRIOS TRADICIONAIS': 'SUSPOV',
    'TECNOLOGIAS QUÍMICA E BIOLÓGICA': 'TECQUB',
    'CIÊNCIAS DE MATERIAIS': 'MATERI',
    'DESENVOLVIMENTO, SOCIEDADE E COOPERAÇÃO INTERNACIONAL': 'DESCOO',
    'DIREITOS HUMANOS E CIDADANIA': 'DIRHUM',
    'ESTUDOS COMPARADOS SOBRE AS AMÉRICAS': 'AMERIC',
}

def slugify_area(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

def auto_suffix(nome):
    s = unicodedata.normalize('NFKD', nome).encode('ascii','ignore').decode().upper()
    s = re.sub(r'[^A-Z]', '', s)
    return s[:6] or 'PROGRA'

# ── 3. Construir o registry ─────────────────────────────────────────
registry = []
suffixes_used = {}
for cd, recs in sorted(prog_map.items(), key=lambda x: (ativos[x[0]].get('NM_PROGRAMA_IES') or '')):
    r0 = ativos[cd]                                   # registro do AN_BASE mais recente
    nome = (r0.get('NM_PROGRAMA_IES') or '').strip()  # nome oficial mais recente do CD
    is_prof = (r0.get('NM_MODALIDADE_PROGRAMA','').strip().upper() == 'PROFISSIONAL')
    base = SUFFIX_MANUAL.get(nome) or auto_suffix(nome)
    # Se for mestrado profissional e existir versão acadêmica do mesmo nome,
    # usar sufixo terminado em "P" para diferenciar.
    if is_prof:
        # Verificar se existe acadêmico para o mesmo nome
        academico = any(
            (cd2 != cd and (ativos[cd2].get('NM_PROGRAMA_IES') or '').strip() == nome and
             any((rr.get('NM_MODALIDADE_PROGRAMA','').strip().upper() == 'ACADÊMICO') for rr in rs))
            for cd2, rs in prog_map.items()
        )
        if academico:
            suf = (base[:5] + 'P')[:6]
        else:
            suf = base
    else:
        suf = base
    # garante unicidade
    base2 = suf
    i = 1
    while suf in suffixes_used and suffixes_used[suf] != (cd, nome):
        suf = (base2[:5] + str(i))[:6]
        i += 1
    suffixes_used[suf] = (cd, nome)
    graus = sorted(set(x['NM_GRAU_PROGRAMA'] for x in recs))
    notas = sorted(set(x['CD_CONCEITO_PROGRAMA'] for x in recs))
    modalid = sorted(set(x['NM_MODALIDADE_PROGRAMA'] for x in recs))
    registry.append({
        'sufixo': suf,
        'cd_programa': cd,
        'nome': nome,
        'graus': graus,
        'modalidade': modalid,
        'conceito': notas,
        'situacao': r0['DS_SITUACAO_PROGRAMA'],
        'area_capes': r0['NM_AREA_AVALIACAO'],
        'cd_area_capes': r0['CD_AREA_AVALIACAO'],
        'slug_area': slugify_area(r0['NM_AREA_AVALIACAO']),
        'grande_area_cnpq': r0['NM_GRANDE_AREA_CONHECIMENTO'],
        'area_conhecimento': r0['NM_AREA_CONHECIMENTO'],
        'area_basica': r0['NM_AREA_BASICA'],
        'sigla_ies': 'UNB',
        'nome_ies': r0['NM_ENTIDADE_ENSINO'],
    })

# ── 4. Validação ────────────────────────────────────────────────────
sufs = [e['sufixo'] for e in registry]
dups = {s: sufs.count(s) for s in sufs if sufs.count(s) > 1}
assert not dups, f'Sufixos duplicados: {dups}'

# Catálogo agregado
areas = defaultdict(list)
grandes = defaultdict(set)
for e in registry:
    areas[e['area_capes']].append(e['sufixo'])
    grandes[e['grande_area_cnpq']].add(e['area_capes'])

catalog = {
    'gerado_em': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
    'n_programas_unb': len(registry),
    'grandes_areas': {g: sorted(a) for g, a in grandes.items()},
    'areas_capes': {
        a: {
            'slug': slugify_area(a),
            'sufixos_unb': sufs,
            'n_unb': len(sufs),
        } for a, sufs in areas.items()
    },
    'programas_unb': registry,
}

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, 'w', encoding='utf-8') as fh:
    json.dump(catalog, fh, ensure_ascii=False, indent=2)

print(f'✓ {OUT_PATH}')
print(f'  Programas: {len(registry)}')
print(f'  Áreas CAPES: {len(areas)}')
print(f'  Grandes Áreas CNPq: {len(grandes)}')
print(f'  Tamanho: {os.path.getsize(OUT_PATH)/1024:.1f} KB')

# Lista sufixos
print('\n=== SUFIXOS ATRIBUÍDOS ===')
for e in sorted(registry, key=lambda x: (x['grande_area_cnpq'], x['area_capes'], x['nome'])):
    print(f"  {e['sufixo']:<6}  {e['nome'][:55]:<55}  [{e['area_capes']}]")
