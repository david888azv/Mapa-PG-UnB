#!/usr/bin/env bash
# =============================================================================
# Inclui no MAPA-PG as 7 Áreas de Avaliação da CAPES que faltavam (437 programas)
# =============================================================================
# O catálogo de áreas era derivado da pegada da UnB (gerar_registry.py montava
# `areas_capes` iterando sobre os programas da UnB), então uma Área em que a UnB
# não tem programa nunca ganhava chave — e como gerar_dados_completos.py usa
# `areas_capes` como universo, ela sumia do app INTEIRO. São elas:
#   CIÊNCIAS BIOLÓGICAS II · ENGENHARIAS II · ZOOTECNIA/RECURSOS PESQUEIROS
#   CIÊNCIA DE ALIMENTOS · MEDICINA III · PLANEJAMENTO URBANO E REGIONAL/DEMOGRAFIA
#   CIÊNCIAS DA RELIGIÃO E TEOLOGIA
#
# Este script executa tudo em ordem, verifica cada etapa e PARA no primeiro erro.
# É idempotente: rodar de novo com tudo pronto não faz nada (o passo 4 detecta).
#
# Uso:   bash build/rodar_49_areas.sh
# Tempo: alguns minutos (a fase 1 relê ~2 GB de CSV uma vez).
# =============================================================================
set -euo pipefail

REPO="/home/david/atual/coleta-capes/mapa-pg-multi"
BUILD="$REPO/build"
DOCS="$REPO/docs"
STAMP="$(date +%Y%m%d-%H%M%S)"
BAK="/tmp/mapapg_backup_$STAMP"
NOVOS="/tmp/mapapg_novos_$STAMP.txt"
SUMS="/tmp/mapapg_sums_$STAMP.txt"

titulo() { echo; echo "═══════════════════════════════════════════════════════════════"; echo "  $1"; echo "═══════════════════════════════════════════════════════════════"; }
ok()     { echo "  ✓ $1"; }
erro()   { echo "  ✗ $1" >&2; exit 1; }

cd "$REPO"

# ── 0. Pré-checagens ─────────────────────────────────────────────────────────
titulo "0/8  Pré-checagens"
[ -f "$BUILD/gerar_registry.py" ]       || erro "não achei build/gerar_registry.py"
[ -f "$BUILD/add_areas_faltantes.py" ]  || erro "não achei build/add_areas_faltantes.py"
[ -d "$DOCS/dados" ]                    || erro "não achei docs/dados/"
python3 -c "import pandas" 2>/dev/null  || erro "pandas não disponível (a fase 2 precisa)"
ok "scripts e dependências presentes"
ok "áreas hoje: $(ls "$DOCS"/dados/area-*.json | wc -l)"

# ── 1. Backup ────────────────────────────────────────────────────────────────
titulo "1/8  Backup"
mkdir -p "$BAK"
cp "$DOCS/registry.json" "$DOCS/manifest.json" "$BAK/"
# checksums dos area-*.json existentes: prova de não-regressão no passo 8
md5sum "$DOCS"/dados/area-*.json > "$SUMS"
ok "registry.json + manifest.json → $BAK"
ok "checksums de $(wc -l < "$SUMS") arquivos → $SUMS"

# ── 2. Catálogo nacional de áreas ────────────────────────────────────────────
titulo "2/8  gerar_registry.py — catálogo nacional (sem filtro UnB)"
python3 "$BUILD/gerar_registry.py"

# ── 3. Verificar o catálogo ──────────────────────────────────────────────────
titulo "3/8  Verificação do catálogo"
python3 - <<'PY' || exit 1
import json, sys
d = json.load(open('docs/registry.json', encoding='utf-8'))
na, np_ = len(d['areas_capes']), len(d['programas_unb'])
sem = [a for a, m in d['areas_capes'].items() if m['n_unb'] == 0]
com = na - len(sem)
print(f'  áreas CAPES no catálogo : {na}')
print(f'  com programa da UnB     : {com}')
print(f'  sem programa da UnB     : {len(sem)}')
for a in sorted(sem):
    print(f'      · {a}')
print(f'  programas_unb           : {np_}')
falhou = False
if na != 49:
    print(f'  ✗ esperava 49 áreas, veio {na}'); falhou = True
if np_ != 92:
    # o recorte da UnB é atributo dela e NÃO pode mudar: 82 acadêmicos + 10 profissionais
    print(f'  ✗ programas_unb mudou de 92 para {np_} — o recorte da UnB não devia mudar'); falhou = True
if len(sem) != 7:
    print(f'  ✗ esperava 7 áreas sem UnB, veio {len(sem)}'); falhou = True
sys.exit(1 if falhou else 0)
PY
ok "catálogo consistente"

# ── 4. Dry-run ───────────────────────────────────────────────────────────────
titulo "4/8  add_areas_faltantes.py — dry-run"
cd "$BUILD"
python3 add_areas_faltantes.py | tee /tmp/mapapg_dryrun_$STAMP.txt
# guarda os slugs novos ANTES de gerar (depois eles passam a existir e somem da lista)
python3 - > "$NOVOS" <<'PY'
import json, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath('build/x')))
d = json.load(open('../docs/registry.json', encoding='utf-8'))
for a, m in sorted(d['areas_capes'].items()):
    if not os.path.exists(f"../docs/dados/area-{m['slug']}.json"):
        print(m['slug'])
PY
N_NOVOS=$(wc -l < "$NOVOS" | tr -d ' ')
ok "$N_NOVOS área(s) a gerar → $NOVOS"
if [ "$N_NOVOS" -eq 0 ]; then
    echo; echo "  Nada a fazer: todas as áreas do catálogo já têm dados. Saindo."; exit 0
fi

# ── 5. Gerar as áreas novas ──────────────────────────────────────────────────
titulo "5/8  add_areas_faltantes.py --aplicar   (fase 1 relê ~2 GB — vários minutos)"
python3 add_areas_faltantes.py --aplicar

# ── 6. Estratos A1–A8/C nas áreas novas ──────────────────────────────────────
# OBRIGATÓRIO: gerar_estratos_app.py injeta os campos estr_* in-place. Sem isto as
# áreas novas ficam sem estratificação e o app as mostra incompletas.
titulo "6/8  gerar_estratos_app.py — estratos nas áreas novas"
while read -r slug; do
    [ -z "$slug" ] && continue
    echo "  → $slug"
    python3 gerar_estratos_app.py "$slug" 2>&1 | tail -2
done < "$NOVOS"
ok "estratos gerados"

# ── 7. Registry por IES + sitemap ────────────────────────────────────────────
titulo "7/8  gerar_registry_ies.py + gerar_sitemap.py"
python3 gerar_registry_ies.py 2>&1 | tail -3
python3 gerar_sitemap.py 2>&1 | tail -3
ok "registry_ies.json e sitemap.xml atualizados"

# ── 8. Verificação final + não-regressão ─────────────────────────────────────
titulo "8/8  Verificação final"
python3 - "$SUMS" "$NOVOS" <<'PY' || exit 1
import json, os, sys, hashlib, subprocess

sums_file, novos_file = sys.argv[1], sys.argv[2]
DADOS = '../docs/dados'
falhou = False

# 8.1 total de áreas
n = len([f for f in os.listdir(DADOS) if f.startswith('area-') and f.endswith('.json')])
print(f'  área-*.json no disco    : {n}')
if n != 49:
    print(f'  ✗ esperava 49'); falhou = True

# 8.2 as novas têm dados E estratos?
novos = [l.strip() for l in open(novos_file) if l.strip()]
print(f'\n  ÁREAS NOVAS ({len(novos)}):')
for sl in novos:
    p = f'{DADOS}/area-{sl}.json'
    if not os.path.exists(p):
        print(f'    ✗ {sl}: arquivo não existe'); falhou = True; continue
    d = json.load(open(p, encoding='utf-8'))
    nreg = len(d['data'])
    nprog = len({r['cd'] for r in d['data']})
    estr_meta = [k for k in d['metadata'] if k.startswith('estratos')]
    estr_reg = [k for k in (d['data'][0] if d['data'] else {}) if k.startswith('estr')]
    marca = '✓' if (nreg and estr_meta and estr_reg) else '✗'
    if marca == '✗': falhou = True
    print(f'    {marca} {sl:44s} {nprog:3d} progs · {nreg:4d} regs · '
          f'estratos_meta={len(estr_meta)} estr_campos={len(estr_reg)}')

# 8.3 manifest
mf = json.load(open('../docs/manifest.json', encoding='utf-8'))
print(f'\n  manifest.areas          : {len(mf["areas"])}')
if len(mf['areas']) != 49:
    print('  ✗ esperava 49 entradas'); falhou = True
if 'estratos_capes' not in mf:
    print('  ✗ CRÍTICO: manifest perdeu a chave estratos_capes'); falhou = True
else:
    print('  ✓ manifest preservou estratos_capes')

# 8.4 NÃO-REGRESSÃO: os 42 arquivos que já existiam não podem ter mudado
print('\n  NÃO-REGRESSÃO (os 42 pré-existentes):')
mud = []
for linha in open(sums_file):
    md5_antes, caminho = linha.split(None, 1)
    caminho = caminho.strip()
    if not os.path.exists(caminho):
        mud.append((caminho, 'SUMIU')); continue
    h = hashlib.md5(open(caminho, 'rb').read()).hexdigest()
    if h != md5_antes:
        mud.append((caminho, 'ALTERADO'))
if mud:
    for c, m in mud[:8]:
        print(f'    ✗ {os.path.basename(c)}: {m}')
    print(f'    ✗ {len(mud)} arquivo(s) pré-existente(s) foram tocados — não deviam')
    falhou = True
else:
    print(f'    ✓ nenhum dos {sum(1 for _ in open(sums_file))} arquivos anteriores foi alterado')

sys.exit(1 if falhou else 0)
PY

titulo "CONCLUÍDO"
echo "  Backup em: $BAK"
echo "  Para reverter:  cp $BAK/registry.json $BAK/manifest.json $DOCS/"
echo "                  (e apagar os docs/dados/area-<slug>.json das 7 áreas novas)"
echo
echo "  PENDENTE (eu faço depois, é texto): atualizar as menções a \"42 áreas\" para 49"
echo "  em docs/index.html, build/gerar_stubs_ies.py e README.md."
echo
