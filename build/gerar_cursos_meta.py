#!/usr/bin/env python3
"""
Gera, para cada programa UnB no registry, a pasta docs/cursos/<SUFIXO>/
com um meta.json contendo identificadores e link institucional para o
shell do MAPA-PG enriquecer a apresentação.
"""
import json, os, time, re, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(REPO, 'docs', 'registry.json')
CURSOS_DIR = os.path.join(REPO, 'docs', 'cursos')

catalog = json.load(open(REGISTRY))

os.makedirs(CURSOS_DIR, exist_ok=True)
n = 0
for p in catalog['programas_unb']:
    sub = os.path.join(CURSOS_DIR, p['sufixo'])
    os.makedirs(sub, exist_ok=True)
    meta = {
        'mapa_pg_id': f"MAPA-PG-{p['sufixo']}",
        'sufixo': p['sufixo'],
        'cd_programa_ies': p['cd_programa'],
        'nome_programa': p['nome'],
        'graus': p['graus'],
        'modalidade': p['modalidade'],
        'conceito': p['conceito'],
        'situacao': p['situacao'],
        'sigla_ies': p['sigla_ies'],
        'nome_ies': p['nome_ies'],
        'area_capes': p['area_capes'],
        'cd_area_capes': p['cd_area_capes'],
        'slug_area': p['slug_area'],
        'grande_area_cnpq': p['grande_area_cnpq'],
        'area_conhecimento': p['area_conhecimento'],
        'area_basica': p['area_basica'],
        'sigaa_unb': 'https://sigaa.unb.br/sigaa/public/curso/lista.jsf?nivel=S&aba=p-stricto',
        'capes_dataset': 'https://dadosabertos.capes.gov.br/dataset',
        'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
        'shell': '../../index.html?curso=' + p['sufixo'],
    }
    with open(os.path.join(sub, 'meta.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    # README leve de orientação por curso (não documentação automática — apenas
    # ponteiro para o shell e descrição mínima do programa).
    readme_md = (
        f"# MAPA-PG-{p['sufixo']} — {p['nome']}\n\n"
        f"- IES: {p['nome_ies']} ({p['sigla_ies']})\n"
        f"- Área CAPES: **{p['area_capes']}** (CNPq: {p['grande_area_cnpq']})\n"
        f"- Conceito: {', '.join(p['conceito'])}\n"
        f"- Modalidade: {', '.join(p['modalidade'])}\n"
        f"- Graus: {', '.join(p['graus'])}\n\n"
        f"Aplicativo: [`../../index.html?curso={p['sufixo']}`]"
        f"(../../index.html?curso={p['sufixo']})\n"
    )
    with open(os.path.join(sub, 'README.md'), 'w', encoding='utf-8') as fh:
        fh.write(readme_md)
    n += 1

print(f'✓ {n} pastas docs/cursos/<SUFIXO>/ criadas')
