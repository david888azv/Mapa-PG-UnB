#!/usr/bin/env python3
"""
Gera dados mínimos por área CAPES — apenas a lista de programas com
sigla, UF, conceito, modalidade, situação. Sem métricas de produção.

Esta é a 1ª camada do pipeline: rápida (<1 min, lê só programas_*.csv).
A 2ª camada (gerar_dados_completos.py) adiciona n_doc, ma_*, IF, etc.
O app HTML+JS aceita ambos os schemas e mostra aviso quando
'metadata.tem_metricas' = false.

Saída: docs/dados/area-<slug>.json para todas as 42 áreas onde a UnB
tem programa.
"""
import csv, glob, json, os, time, unicodedata, re
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
REGISTRY = os.path.join(REPO, 'docs', 'registry.json')
OUT_DIR = os.path.join(REPO, 'docs', 'dados')

QUADRIENIOS = {
    '2013-2016': [2013,2014,2015,2016],
    '2017-2020': [2017,2018,2019,2020],
    '2021-2024': [2021,2022,2023,2024],  # sem dados de programas ainda
}
SUBTIPOS = {
    '25':'Artigo em Periódico','8':'Resumo','9':'Trabalho de Congresso',
    '26':'Capítulo de Livro','10':'Texto em Jornal',
}

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')

# Carrega registry
catalog = json.load(open(REGISTRY))
areas_unb = {a: meta['sufixos_unb'] for a, meta in catalog['areas_capes'].items()}
unb_cds = {p['cd_programa']: p['sufixo'] for p in catalog['programas_unb']}

print(f"[1/3] {len(areas_unb)} áreas-alvo, {len(unb_cds)} programas UnB")

# Carrega TODOS os programas (todas as IES, todas as áreas, todos os anos)
print(f"[2/3] Lendo programas_*.csv...")
files = sorted(
    glob.glob(os.path.join(DATA_DIR, 'programas_2013a2016_*.csv')) +
    glob.glob(os.path.join(DATA_DIR, 'programas_2017a2020_*.csv'))
)
# Para cada programa, pegar última situação
prog_state = {}  # cd -> dict
for f in files:
    with open(f, encoding='latin-1') as fh:
        rd = csv.DictReader(fh, delimiter=';')
        for r in rd:
            cd = r['CD_PROGRAMA_IES']
            an = int(r['AN_BASE'])
            existing = prog_state.get(cd)
            if existing is None or an > existing['_an']:
                r['_an'] = an
                prog_state[cd] = r
print(f"  {len(prog_state)} programas únicos no Brasil (todas as áreas)")

# Histórico de notas por (cd, quad)
print("  Coletando série histórica de notas...")
cd_quad_nota = defaultdict(dict)  # cd -> quad -> [notas]
for f in files:
    with open(f, encoding='latin-1') as fh:
        rd = csv.DictReader(fh, delimiter=';')
        for r in rd:
            cd = r['CD_PROGRAMA_IES']
            try:
                an = int(r['AN_BASE'])
                nota = r['CD_CONCEITO_PROGRAMA']
            except: continue
            for qlbl, anos in QUADRIENIOS.items():
                if an in anos:
                    cd_quad_nota[cd].setdefault(qlbl, []).append(nota)
                    break

# Agrupa programas por área
print(f"\n[3/3] Gerando JSONs por área...")
os.makedirs(OUT_DIR, exist_ok=True)

# Agrupar a programs_state pela área CAPES
by_area = defaultdict(list)
for cd, r in prog_state.items():
    area = r.get('NM_AREA_AVALIACAO','').strip()
    if area in areas_unb:
        by_area[area].append(r)

# Gerar JSON por área
gerados = []
for area, programs in sorted(by_area.items()):
    sl = slug(area)
    out = {
        'metadata': {
            'area': area,
            'cd_area': programs[0].get('CD_AREA_AVALIACAO',''),
            'grande_area': programs[0].get('NM_GRANDE_AREA_CONHECIMENTO',''),
            'slug': sl,
            'quadrienios': QUADRIENIOS,
            'subtipos_biblio': SUBTIPOS,
            'n_programas': len(programs),
            'n_unb': len([p for p in programs if p.get('SG_ENTIDADE_ENSINO')=='UNB']),
            'unb_cds': [p['CD_PROGRAMA_IES'] for p in programs if p.get('SG_ENTIDADE_ENSINO')=='UNB'],
            'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
            'tem_metricas': False,  # camada mínima
            'fonte': 'CAPES — programas_2013a2016 + programas_2017a2020',
        },
        'ies_list': sorted(set(
            (p.get('SG_ENTIDADE_ENSINO',''), p.get('SG_UF_PROGRAMA',''))
            for p in programs
        )),
        'notas': [],
        'data': [],
    }
    notas_glob = set()
    for p in programs:
        cd = p['CD_PROGRAMA_IES']
        sigla = p.get('SG_ENTIDADE_ENSINO','?')
        uf = p.get('SG_UF_PROGRAMA','?')
        nome = p.get('NM_PROGRAMA_IES','?')
        is_unb = (sigla == 'UNB')
        for qlbl in QUADRIENIOS:
            notas_q = cd_quad_nota.get(cd, {}).get(qlbl, [])
            if not notas_q: continue
            # nota mais frequente
            from collections import Counter
            n_str = Counter(notas_q).most_common(1)[0][0]
            try: nota = int(n_str)
            except:
                # Mestrado profissional: A,B,C → mapear para 4,3,2 só p/ ordenação
                nota = {'A':4,'B':3,'C':2}.get(n_str, 0)
            if nota: notas_glob.add(nota)
            out['data'].append({
                'cd': cd,
                'sigla': sigla,
                'programa': nome,
                'uf': uf,
                'nota': nota,
                'quad': qlbl,
                'is_unb': is_unb,
                'modalidade': p.get('NM_MODALIDADE_PROGRAMA',''),
                'situacao': p.get('DS_SITUACAO_PROGRAMA',''),
                # campos métricos vazios (preenchidos na camada completa)
                'n_doc': 0, 'n_pq': 0, 'n_spq': 0, 'pct_pq': 0,
                'ma_pq': 0, 'ma_spq': 0, 'ma_all': 0, 'razao': 0,
                'n_perm': 0, 'n_colab': 0, 'n_visit': 0,
                'ma_perm': 0, 'ma_colab': 0, 'ma_visit': 0, 'razao_pc': 0,
                'avg_if': 0, 'med_if': 0, 'max_if': 0, 'n_if': 0,
                'if_lo': 0, 'if_mi': 0, 'if_hi': 0,
                'if_perm': [0,0,0], 'if_colab': [0,0,0],
                'if_visit': [0,0,0], 'if_all': [0,0,0],
                'prod_ano': {}, 'prod_sub': {},
            })
    out['notas'] = sorted(notas_glob)
    out['ies_list'] = [{'sigla':s,'uf':u} for s,u in out['ies_list']]
    out_file = os.path.join(OUT_DIR, f'area-{sl}.json')
    with open(out_file, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',',':'))
    sz = os.path.getsize(out_file) / 1024
    gerados.append((sl, area, len(out['data']), sz))
    print(f"  area-{sl}.json — {len(programs):3d} programas | {sz:.1f} KB | {area}")

# Manifesto / índice de áreas
manifest = {
    'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
    'shell_version': '2.0-multi',
    'areas': [
        {
            'slug': sl,
            'nome': area,
            'arquivo': f'dados/area-{sl}.json',
            'tamanho_kb': round(sz),
            'n_registros': nr,
            'n_unb': len(areas_unb.get(area, [])),
            'sufixos_unb': areas_unb.get(area, []),
        } for sl, area, nr, sz in sorted(gerados, key=lambda x: x[1])
    ],
    'grandes_areas': catalog['grandes_areas'],
}
with open(os.path.join(REPO,'docs','manifest.json'), 'w', encoding='utf-8') as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=2)

print(f"\n✓ {len(gerados)} áreas geradas em {OUT_DIR}/")
print(f"✓ manifest.json em docs/")
print(f"  Total: {sum(s for _,_,_,s in gerados):.0f} KB")
