#!/usr/bin/env python3
"""
Migra dados_fisica.json (métricas completas, gerado pelo pipeline original
preparar_dados_pos_d.py) para o slot area-astronomia-fisica.json do
shell multi-área. Atualiza o manifest indicando que essa área tem métricas.
"""
import json, os, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.normpath(os.path.join(REPO, '..', 'mapa-pg', 'dados_fisica.json'))
DST = os.path.join(REPO, 'docs', 'dados', 'area-astronomia-fisica.json')
MANIFEST = os.path.join(REPO, 'docs', 'manifest.json')

assert os.path.exists(SRC), f'Não encontrei {SRC}'

# ATENÇÃO — este script SOBRESCREVE o DST inteiro com o JSON legado. Se o DST já foi
# enriquecido in-place por gerar_estratos_app.py, rodar aqui DESTRÓI os estratos A1–A8/C
# (metadata.estratos / estratos_cs / estratos_oa / estratos_hb + campos estr_* dos
# registros), dos quais dependem o app e todos os estudos PIP-2. Para só repor
# modalidade/situacao num DST existente, use `patch_fisica_meta.py` (cirúrgico).
if os.path.exists(DST) and '--forcar' not in sys.argv:
    _dst = json.load(open(DST, encoding='utf-8'))
    _estr = [k for k in _dst.get('metadata', {}) if k.startswith('estratos')]
    if _estr:
        sys.exit(
            f'ABORTADO: {DST} já contém estratos ({", ".join(_estr)}) e este script o\n'
            f'sobrescreveria com o legado, destruindo-os.\n'
            f'  • só repor modalidade/situacao → python3 patch_fisica_meta.py --aplicar\n'
            f'  • realmente remigrar do zero  → python3 migrar_fisica.py --forcar\n'
            f'    (e depois OBRIGATORIAMENTE: python3 gerar_estratos_app.py astronomia-fisica)')

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

# Preenche 'modalidade'/'situacao' a partir do cache da fase 1 (build/cache/<slug>/
# meta.json), que os deriva dos CSVs da CAPES (NM_MODALIDADE_PROGRAMA /
# DS_SITUACAO_PROGRAMA) — a MESMA fonte que gerar_dados_completos.py usa nas outras 41
# áreas. O SRC legado (mapa-pg/dados_fisica.json) nunca teve essas chaves.
#
# Aqui havia um `setdefault(campo, '')`, que sobre chaves inexistentes gravava '' nos 193
# registros — e como esta é a única área que não passa pelo pipeline padrão, era a única
# com os campos vazios. O estrago não era cosmético: `modalidade` vazia é lida como
# ACADÊMICO (convenção is_academico), o que punha o MNPEF (33283010001P5, profissional,
# 813 permanentes) nas referências acadêmicas e, por ser peso ~61% da célula da nota 5,
# fazia a mediana ponderada colapsar sobre ele (topo 0,12 em vez de 2,10). Já `situacao`
# vazia falha ao contrário — filtros que exigem == 'EM FUNCIONAMENTO' excluíam a
# FÍSICA/UnB em silêncio do simulador de impacto.
META = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'cache', 'astronomia-fisica', 'meta.json')
assert os.path.exists(META), (
    f'Não encontrei {META} — rode a fase 1 de gerar_dados_completos.py antes; sem ele os '
    f'campos modalidade/situacao ficariam vazios (ver patch_fisica_meta.py).')
cd_meta = json.load(open(META, encoding='utf-8'))['cd_meta']
faltam = sorted({d['cd'] for d in src['data']} - set(cd_meta))
assert not faltam, f'{len(faltam)} cd(s) sem meta: {faltam[:5]} — join incompleto, abortando.'
for d in src['data']:
    m = cd_meta[d['cd']]
    d['modalidade'] = m.get('modalidade', '')
    d['situacao'] = m.get('situacao', '')
_vaz = sum(1 for d in src['data'] for c in ('modalidade', 'situacao') if not d[c])
assert not _vaz, f'{_vaz} campo(s) modalidade/situacao ficaram vazios — verifique o meta.json.'

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
