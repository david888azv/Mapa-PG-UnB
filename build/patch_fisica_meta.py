#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch cirúrgico — repõe `modalidade`/`situacao` em area-astronomia-fisica.json
==============================================================================
Corrige um defeito de dados isolado: os 193 registros (66 programas × 3 quadriênios) da
área ASTRONOMIA / FÍSICA têm `modalidade=''` e `situacao=''`, enquanto as outras 41 áreas
estão 100% preenchidas. Preenche os DOIS campos a partir de
`build/cache/astronomia-fisica/meta.json` — que já tem o dado correto, derivado dos CSVs
da CAPES (`NM_MODALIDADE_PROGRAMA` / `DS_SITUACAO_PROGRAMA`) — e NÃO TOCA em mais nada.

CAUSA RAIZ (corrigida em paralelo, ver migrar_fisica.py): `migrar_fisica.py` copiava o
JSON do app legado `mapa-pg/dados_fisica.json`, onde essas chaves NUNCA existiram, e fazia
`setdefault('modalidade','')` — gravando vazio sempre. O pipeline correto
(`gerar_dados_completos.py`) pula a área via `--skip-fisica`.

POR QUE UM PATCH E NÃO REGENERAR: `gerar_dados_completos.py --only astronomia-fisica`
sobrescreveria o arquivo e DESTRUIRIA os estratos A1–A8/C (`estratos`, `estratos_cs`,
`estratos_oa`, `estratos_hb`), que `gerar_estratos_app.py` injeta in-place; além disso o
recálculo pode divergir do pipeline legado (`preparar_dados_pos_d.py`, fora do repo) e
mover números que hoje estão publicados. Este patch altera 2 campos e prova que não
alterou nenhum outro.

IMPACTO DO DEFEITO (medido antes da correção):
  • `modalidade=''` é lida como ACADÊMICO (convenção `is_academico`: "profissional é
    explicitamente rotulado"). Isso põe 2 programas PROFISSIONAIS nas referências
    acadêmicas — entre eles o MNPEF (`33283010001P5`, 'ENSINO DE FÍSICA - PROFIS'), com
    813 permanentes. Como as medianas/médias do PIP são ponderadas por n_perm, ele sozinho
    detém ~61% do peso da célula da nota 5 da área e a mediana COLAPSA sobre os valores
    dele: topo 0,12 em vez de 2,10 (erro de 17x).
  • O vazamento é NACIONAL: a média ponderada nacional da nota 5 sai 11,81 em vez de
    12,20 (−3,2%) — número publicado em `pip/saida/relatorio_pip_unb.xlsx` (aba 'Projeção
    por nota') e nos dois `relatorio_incremento_pip.html`.
  • `situacao=''` faz o oposto: filtros que exigem `== 'EM FUNCIONAMENTO'` falham FECHADO
    e excluem em silêncio. A FÍSICA/UnB (53001010002P6) está AUSENTE do
    `simulador_impacto.html` publicado — único dos 74 programas UnB nota 4/5/6 omitido.
  • 2 programas de física EM DESATIVACAO nunca entram na contagem nacional de desativações.

APÓS APLICAR, regerar o que consome estes dados (nada disso é feito aqui):
  pip/ e pip-2-refatorado-*/: relatorio_pip_unb.xlsx, relatorio_incremento_pip.*,
  simulador_impacto.html, alvos_q2q3, e o consolidado. Ver o relatório final da auditoria.

Uso:
    python3 patch_fisica_meta.py             # DRY-RUN: mostra o que mudaria, não grava
    python3 patch_fisica_meta.py --aplicar   # grava (com backup .bak-<timestamp>)
    python3 patch_fisica_meta.py --verificar # só confere o estado atual do arquivo
"""
import json
import os
import shutil
import sys
import time
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
META = os.path.join(AQUI, 'cache', 'astronomia-fisica', 'meta.json')
ALVO = os.path.join(REPO, 'docs', 'dados', 'area-astronomia-fisica.json')
CAMPOS = ('modalidade', 'situacao')


def carregar():
    if not os.path.exists(META):
        sys.exit(f'ERRO: não encontrei {META} — o cache da fase 1 é a fonte da correção.')
    if not os.path.exists(ALVO):
        sys.exit(f'ERRO: não encontrei {ALVO}')
    return json.load(open(META, encoding='utf-8'))['cd_meta'], \
        json.load(open(ALVO, encoding='utf-8'))


def conferir_join(cd_meta, d):
    """O join é por `cd`. Aborta se a cobertura não for total ou se sigla/programa
    divergirem — nesse caso o meta.json não descreve este arquivo e o patch seria cego."""
    cds = {r['cd'] for r in d['data']}
    faltam = cds - set(cd_meta)
    if faltam:
        sys.exit(f'ERRO: {len(faltam)} cd(s) do JSON não existem no meta.json: '
                 f'{sorted(faltam)[:5]} — abortando (join incompleto).')
    div = []
    for r in d['data']:
        m = cd_meta[r['cd']]
        for k in ('sigla', 'programa'):
            if m.get(k) and r.get(k) and m[k] != r[k]:
                div.append((r['cd'], k, r[k], m[k]))
    if div:
        print(f'AVISO: {len(div)} divergência(s) de rótulo entre JSON e meta (não bloqueia '
              f'— só os 2 campos serão escritos):')
        for cd, k, a, b in div[:5]:
            print(f'   {cd} {k}: JSON={a!r} meta={b!r}')
    return True


def estado(d):
    """Contagem atual dos dois campos, por quadriênio."""
    out = {}
    for c in CAMPOS:
        out[c] = Counter(r.get(c, '') for r in d['data'])
    return out


def aplicar(cd_meta, d):
    """Escreve os 2 campos em cada registro. Devolve (n_alterados, detalhe)."""
    n = 0
    det = Counter()
    for r in d['data']:
        m = cd_meta[r['cd']]
        for c in CAMPOS:
            novo = m.get(c, '')
            if r.get(c, '') != novo:
                r[c] = novo
                det[c] += 1
                n += 1
    return n, det


def provar_intocado(antes, depois):
    """Prova que NADA além dos 2 campos mudou: compara os registros com os campos
    removidos, e o metadata inteiro. Esta é a garantia central do 'cirúrgico'."""
    def limpo(d):
        return [{k: v for k, v in r.items() if k not in CAMPOS} for r in d['data']]
    if antes['metadata'] != depois['metadata']:
        return False, 'metadata foi alterado'
    a, b = limpo(antes), limpo(depois)
    if len(a) != len(b):
        return False, f'nº de registros mudou: {len(a)} → {len(b)}'
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            dif = [k for k in set(x) | set(y) if x.get(k) != y.get(k)]
            return False, f'registro {i} ({antes["data"][i]["cd"]}) mudou em: {dif}'
    return True, f'{len(a)} registros: tudo idêntico exceto {CAMPOS}'


def relatorio(cd_meta, d):
    """Quem muda de classificação e por quê — o que o leitor precisa ver antes de gravar."""
    prof = [(cd, m) for cd, m in cd_meta.items() if m.get('modalidade') == 'PROFISSIONAL']
    desat = [(cd, m) for cd, m in cd_meta.items() if m.get('situacao') == 'EM DESATIVACAO']
    perm = {}
    for r in d['data']:
        if r['quad'] == '2017-2020':
            perm[r['cd']] = r.get('n_perm') or 0
    print(f'\n  Passam a ser PROFISSIONAIS (saem das referências acadêmicas): {len(prof)}')
    for cd, m in sorted(prof, key=lambda t: -perm.get(t[0], 0)):
        p = perm.get(cd, 0)
        alerta = '  <<< peso decisivo nas medianas ponderadas' if p > 200 else ''
        print(f'     {cd}  {m["sigla"]:8s} {m["programa"][:34]:36s} {p:4d} perm{alerta}')
    print(f'\n  Passam a EM DESATIVACAO (entram nas contagens de desativação): {len(desat)}')
    for cd, m in desat:
        print(f'     {cd}  {m["sigla"]:8s} {m["programa"][:34]:36s}')


def main(argv):
    so_verificar = '--verificar' in argv
    gravar = '--aplicar' in argv

    cd_meta, d = carregar()
    conferir_join(cd_meta, d)
    antes = json.loads(json.dumps(d))          # cópia profunda para a prova

    print(f'ALVO : {ALVO}')
    print(f'FONTE: {META}')
    print(f'\nESTADO ATUAL ({len(d["data"])} registros):')
    for c, cnt in estado(d).items():
        print(f'  {c:11s}: {dict(cnt)}')

    if so_verificar:
        vazios = sum(1 for r in d['data'] for c in CAMPOS if r.get(c, '') == '')
        print(f'\n{"DEFEITO PRESENTE" if vazios else "OK — campos preenchidos"} '
              f'({vazios} campo(s) vazio(s))')
        return 0 if not vazios else 1

    n, det = aplicar(cd_meta, d)
    print(f'\nALTERAÇÕES: {n} campo(s) em {len(d["data"])} registros — {dict(det)}')
    print(f'\nESTADO APÓS O PATCH:')
    for c, cnt in estado(d).items():
        print(f'  {c:11s}: {dict(cnt)}')

    ok, msg = provar_intocado(antes, d)
    print(f'\nPROVA DE NÃO-REGRESSÃO: {"OK" if ok else "FALHOU"} — {msg}')
    if not ok:
        sys.exit('ABORTADO: o patch alteraria mais que os 2 campos.')

    relatorio(cd_meta, d)

    if not gravar:
        print(f'\n--- DRY-RUN: nada foi gravado. Use --aplicar para gravar. ---')
        return 0

    bak = ALVO + '.bak-' + time.strftime('%Y%m%d-%H%M%S')
    shutil.copy2(ALVO, bak)
    tmp = ALVO + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, ALVO)                       # troca atômica
    print(f'\n  backup : {bak}')
    print(f'  gravado: {ALVO} ({os.path.getsize(ALVO)/1024:.1f} KB)')

    # reler do disco e reconferir — não confiar no objeto em memória
    _, d2 = carregar()
    ok2, msg2 = provar_intocado(antes, d2)
    vaz = sum(1 for r in d2['data'] for c in CAMPOS if r.get(c, '') == '')
    est = estado(d2)
    print(f'  releitura: prova {"OK" if ok2 else "FALHOU"} ({msg2}); {vaz} campo(s) vazio(s)')
    print(f'  modalidade: {dict(est["modalidade"])}')
    print(f'  situacao  : {dict(est["situacao"])}')
    if not ok2 or vaz:
        sys.exit('ERRO: verificação pós-gravação falhou — restaure o backup.')
    print('\n✓ patch aplicado e verificado.')
    print('  REGERAR agora os artefatos do PIP que consomem esta área '
          '(relatorio_pip_unb.xlsx, relatorio_incremento_pip.*, simulador_impacto.html).')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
