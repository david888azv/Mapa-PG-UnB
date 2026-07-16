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

# ── 5. Catálogo agregado ────────────────────────────────────────────
# DUAS responsabilidades distintas, deliberadamente separadas:
#
#   (a) o CATÁLOGO DE ÁREAS é da CAPES — nacional, independente da UnB;
#   (b) `sufixos_unb`/`n_unb`/`programas_unb` são atributos da UnB, legitimamente.
#
# Antes, (a) era derivado de `registry` (que o filtro da linha ~29 restringe à UnB):
# `for e in registry: areas[e['area_capes']].append(...)`. Consequência — uma Área de
# Avaliação em que a UnB não tem NENHUM programa jamais ganhava chave, e como
# `gerar_dados_completos.py` usa `catalog['areas_capes'].keys()` como universo de áreas,
# ela sumia do app INTEIRO. Eram 7 áreas e 437 programas invisíveis (CIÊNCIAS BIOLÓGICAS
# II, ENGENHARIAS II, ZOOTECNIA/RECURSOS PESQUEIROS, CIÊNCIA DE ALIMENTOS, MEDICINA III,
# PLANEJAMENTO URBANO E REGIONAL/DEMOGRAFIA, CIÊNCIAS DA RELIGIÃO E TEOLOGIA) — a origem
# UnB do projeto fossilizada num app que hoje é nacional. Usuários de SC reportaram
# programas "faltando" por causa disto.
#
# Agora (a) vem de uma passada pelos CSVs SEM filtro de IES. Áreas sem UnB entram com
# n_unb=0 e sufixos_unb=[] — presentes no catálogo, sem fingir presença da UnB.
# TAXONOMIA ATUAL, e só ela: o catálogo sai de `programas_2017a2020` (o mesmo `files` já
# lido acima), NÃO de 2013a2016. A CAPES renomeia e reorganiza Áreas de Avaliação entre
# quadriênios, e varrer também 2013-2016 traz 8 nomes LEGADOS que não existem mais —
# davam 57 áreas em vez de 49, e cada legado viraria uma área fantasma no app. Os
# programas desses nomes antigos não se perdem: eles reaparecem sob o nome atual, porque
# `gerar_dados_completos.py` mapeia cd→área lendo 2013-2016 e depois 2017-2020, ficando
# com o último (a taxonomia vigente). Este é também o critério sob o qual as 42 áreas
# originais foram construídas — mudá-lo aqui seria uma alteração silenciosa de escopo.
areas_nac = {}      # area_capes -> {'grande': ..., 'cd': ...}
for f in files:
    with open(f, encoding='latin-1') as fh:
        for r in csv.DictReader(fh, delimiter=';'):
            a = (r.get('NM_AREA_AVALIACAO') or '').strip()
            if not a:
                continue
            areas_nac.setdefault(a, {'grande': (r.get('NM_GRANDE_AREA_CONHECIMENTO') or '').strip(),
                                     'cd': (r.get('CD_AREA_AVALIACAO') or '').strip()})

# Atributos da UnB por área (vazios onde a UnB não atua)
areas_unb = defaultdict(list)
for e in registry:
    areas_unb[e['area_capes']].append(e['sufixo'])

# Sanidade: toda área com programa da UnB precisa existir no catálogo nacional.
orfas = sorted(set(areas_unb) - set(areas_nac))
assert not orfas, f'Áreas da UnB ausentes do catálogo nacional: {orfas}'

grandes = defaultdict(set)
for a, info in areas_nac.items():
    grandes[info['grande']].add(a)

catalog = {
    'gerado_em': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
    'n_programas_unb': len(registry),
    'n_areas_capes': len(areas_nac),
    'grandes_areas': {g: sorted(a) for g, a in sorted(grandes.items())},
    'areas_capes': {
        a: {
            'slug': slugify_area(a),
            'cd_area_capes': areas_nac[a]['cd'],
            'sufixos_unb': sorted(areas_unb.get(a, [])),
            'n_unb': len(areas_unb.get(a, [])),
        } for a in sorted(areas_nac)
    },
    'programas_unb': registry,
}
print(f'  catálogo: {len(areas_nac)} áreas CAPES '
      f'({sum(1 for a in areas_nac if areas_unb.get(a))} com programa da UnB, '
      f'{sum(1 for a in areas_nac if not areas_unb.get(a))} sem)')

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, 'w', encoding='utf-8') as fh:
    json.dump(catalog, fh, ensure_ascii=False, indent=2)

print(f'✓ {OUT_PATH}')
print(f'  Programas: {len(registry)}')
print(f'  Áreas CAPES: {len(areas_nac)}')
print(f'  Grandes Áreas CNPq: {len(grandes)}')
print(f'  Tamanho: {os.path.getsize(OUT_PATH)/1024:.1f} KB')

# Lista sufixos
print('\n=== SUFIXOS ATRIBUÍDOS ===')
for e in sorted(registry, key=lambda x: (x['grande_area_cnpq'], x['area_capes'], x['nome'])):
    print(f"  {e['sufixo']:<6}  {e['nome'][:55]:<55}  [{e['area_capes']}]")
