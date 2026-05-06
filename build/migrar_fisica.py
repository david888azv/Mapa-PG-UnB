#!/usr/bin/env python3
"""
Migra dados_fisica.json (métricas completas, gerado pelo pipeline original
preparar_dados_pos_d.py) para o slot area-astronomia-fisica.json do
shell multi-área. Atualiza o manifest indicando que essa área tem métricas.
"""
import json, os, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.normpath(os.path.join(REPO, '..', 'mapa-pg', 'dados_fisica.json'))
DST = os.path.join(REPO, 'docs', 'dados', 'area-astronomia-fisica.json')
MANIFEST = os.path.join(REPO, 'docs', 'manifest.json')

assert os.path.exists(SRC), f'Não encontrei {SRC}'

src = json.load(open(SRC))
md = src['metadata']

# Adaptar metadata para o novo schema
md.setdefault('slug', 'astronomia-fisica')
md.setdefault('grande_area', 'CIÊNCIAS EXATAS E DA TERRA')
md.setdefault('cd_area', '1')
md['tem_metricas'] = True
md['fonte'] = 'CAPES — programas + docentes + prod_artpe + prod_intel_artpe (2013-2024) + OpenAlex (IF 2yr)'
md.setdefault('migrado_em', time.strftime('%Y-%m-%d %H:%M:%S'))
md['unb_cds'] = sorted(set(d['cd'] for d in src['data'] if d.get('is_unb')))
md['n_unb'] = len(set(md['unb_cds']))
src['metadata'] = md

# Garante que cada item tem campo 'modalidade'/'situacao' (vazios)
for d in src['data']:
    d.setdefault('modalidade', '')
    d.setdefault('situacao', '')

with open(DST, 'w', encoding='utf-8') as fh:
    json.dump(src, fh, ensure_ascii=False, separators=(',',':'))
print(f'✓ {DST}  ({os.path.getsize(DST)/1024:.1f} KB)')

# Atualiza manifest
mf = json.load(open(MANIFEST))
for a in mf['areas']:
    if a['slug'] == 'astronomia-fisica':
        a['tem_metricas'] = True
        a['n_registros'] = len(src['data'])
        a['tamanho_kb'] = round(os.path.getsize(DST)/1024)
        break
mf['atualizado_em'] = time.strftime('%Y-%m-%d %H:%M:%S')
with open(MANIFEST, 'w', encoding='utf-8') as fh:
    json.dump(mf, fh, ensure_ascii=False, indent=2)
print(f'✓ manifest atualizado: astronomia-fisica.tem_metricas = true')
