#!/usr/bin/env python3
"""Cinco testes visuais do MAPA-PG apos a canonicalizacao de IES."""
import json, sys, os
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8765/index.html?ies=UNB&area=quimica'
OUT = os.path.dirname(os.path.abspath(__file__))
res = []


def shot(page, nome):
    p = os.path.join(OUT, f'shot_{nome}.png')
    page.screenshot(path=p, full_page=False)
    return p


def ok(cond, msg):
    res.append(('OK  ' if cond else 'FALHA', msg))
    print(('  OK   ' if cond else '  FALHA ') + msg, flush=True)


with sync_playwright() as pw:
    br = pw.chromium.launch()
    page = br.new_page(viewport={'width': 1440, 'height': 1000})
    erros = []
    page.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: erros.append('PAGEERROR: %s' % e))

    print('\n=== carga inicial ===', flush=True)
    page.goto(BASE, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(1500)
    shot(page, '0_licenca')
    page.click('#licenseOverlay button')          # "Concordo e desejo continuar"
    page.wait_for_timeout(4000)
    shot(page, '0_carga')
    ok(not erros, 'sem erro de console na carga (%s)' % (erros[:2] or 'nenhum'))

    # ── seleciona a área QUÍMICA
    page.evaluate("async () => { await switchArea('quimica'); }")
    page.wait_for_timeout(3000)

    # ── TESTE 1: filtro de IES canonicalizado
    print('\n=== 1. filtro de IES ===', flush=True)
    d = page.evaluate("""() => {
        const chks = [...document.querySelectorAll('.ies-chk')];
        const labels = chks.map(c => ({v: c.value, t: c.closest('label').getAttribute('title')}));
        return {
            n: chks.length,
            temFUFPI: labels.some(l => l.v === 'FUFPI'),
            ufpi: labels.find(l => l.v === 'UFPI') || null,
            comTitle: labels.filter(l => l.t).length,
            area: (DATA && DATA.metadata && DATA.metadata.area) || '?',
            nIesList: DATA.ies_list.length,
        };
    }""")
    print('   area=%s | caixas=%d | ies_list=%d | com title=%d'
          % (d['area'], d['n'], d['nIesList'], d['comTitle']), flush=True)
    ok(not d['temFUFPI'], 'nao existe caixa separada "FUFPI"')
    ok(d['ufpi'] is not None, 'existe caixa "UFPI"')
    ok(d['ufpi'] and d['ufpi']['t'] and 'FUFPI' in d['ufpi']['t'],
       'title da UFPI declara os rotulos incluidos: %r' % (d['ufpi'] or {}).get('t'))
    page.evaluate("""() => { const c=[...document.querySelectorAll('.ies-chk')]
        .find(x=>x.value==='UFPI'); c.scrollIntoView({block:'center'}); }""")
    shot(page, '1_filtro_ies')

    # ── TESTE 2: desmarcar UFPI remove TODOS os quadrienios
    print('\n=== 2. desmarcar UFPI apaga tambem 2013-2016 ===', flush=True)
    # marca TODAS as notas (o padrao restringe e esconderia o Piaui)
    page.evaluate("() => { ['nota3','nota4','nota5','nota6','nota7']"
                  ".forEach(i => { const e=document.getElementById(i); if(e) e.checked=true; }); }")
    antes = page.evaluate("""() => {
        const f = getFilters(); const r = filterData(f);
        return {tot: r.length,
                pi: r.filter(x => ['UFPI','FUFPI'].includes(x.sigla)).length,
                pi13: r.filter(x => x.sigla === 'FUFPI').length};
    }""")
    page.evaluate("""() => { const c=[...document.querySelectorAll('.ies-chk')]
        .find(x=>x.value==='UFPI'); c.checked=false; c.dispatchEvent(new Event('change')); }""")
    page.wait_for_timeout(2500)
    depois = page.evaluate("""() => {
        const f = getFilters(); const r = filterData(f);
        return {tot: r.length,
                pi: r.filter(x => ['UFPI','FUFPI'].includes(x.sigla)).length};
    }""")
    print('   antes: %d registros (%d do Piaui, %d rotulados FUFPI) | depois: %d (%d do Piaui)'
          % (antes['tot'], antes['pi'], antes['pi13'], depois['tot'], depois['pi']), flush=True)
    ok(antes['pi13'] > 0, 'existem registros com o rotulo antigo FUFPI (%d)' % antes['pi13'])
    ok(depois['pi'] == 0, 'desmarcar UFPI removeu TODOS os registros do Piaui, inclusive FUFPI')
    shot(page, '2_desmarcado')
    page.evaluate("""() => { const c=[...document.querySelectorAll('.ies-chk')]
        .find(x=>x.value==='UFPI'); c.checked=true; c.dispatchEvent(new Event('change')); }""")
    page.wait_for_timeout(2500)

    # ── TESTE 3: rotulo de epoca preservado na exibicao
    print('\n=== 3. rotulo de epoca preservado nos registros ===', flush=True)
    ep = page.evaluate("""() => {
        const q = DATA.data.filter(d => ['UFPI','FUFPI'].includes(d.sigla));
        const porQuad = {};
        q.forEach(d => { (porQuad[d.quad] = porQuad[d.quad] || new Set()).add(d.sigla); });
        return Object.fromEntries(Object.entries(porQuad).map(([k,v]) => [k, [...v]]));
    }""")
    print('   Piaui por quadrienio:', json.dumps(ep, ensure_ascii=False), flush=True)
    ok(ep.get('2013-2016') == ['FUFPI'], '2013-2016 mantem o rotulo FUFPI')
    ok('UFPI' in (ep.get('2021-2024') or []), '2021-2024 usa UFPI')

    # ── TESTE 4: BIONORTE Centro-Oeste na Biotecnologia
    print('\n=== 4. BIONORTE Centro-Oeste (UnB por quadrienio) ===', flush=True)
    page.evaluate("async () => { await switchArea('biotecnologia'); }")
    page.wait_for_timeout(3000)
    bio = page.evaluate("""() => DATA.data.filter(d => d.cd === '53001010100P8')
        .map(d => ({quad: d.quad, sigla: d.sigla, uf: d.uf, is_unb: d.is_unb}))
        .sort((a,b) => a.quad.localeCompare(b.quad))""")
    for r in bio:
        print('   %s -> %s/%s is_unb=%s' % (r['quad'], r['sigla'], r['uf'], r['is_unb']), flush=True)
    ok([r['sigla'] for r in bio] == ['UNB', 'UNB', 'UNEMAT'],
       'titularidade por quadrienio: UNB, UNB, UNEMAT')
    shot(page, '4_biotecnologia')

    # ── TESTE 5: Física — regressão
    print('\n=== 5. Fisica: integridade e MNPEF ===', flush=True)
    page.evaluate("async () => { await switchArea('astronomia-fisica'); }")
    page.wait_for_timeout(3000)
    fis = page.evaluate("""() => ({
        n: DATA.data.length,
        vazios: DATA.data.filter(d => !d.modalidade || !d.situacao).length,
        mnpef: [...new Set(DATA.data.filter(d => d.cd === '33283010001P5').map(d => d.sigla + '/' + d.uf))],
        area: DATA.metadata.area,
    })""")
    print('   %s | %d registros | modalidade/situacao vazios: %d | MNPEF: %s'
          % (fis['area'], fis['n'], fis['vazios'], fis['mnpef']), flush=True)
    ok(fis['n'] == 193, 'Fisica com 193 registros')
    ok(fis['vazios'] == 0, 'nenhum registro com modalidade/situacao vazios')
    ok(fis['mnpef'] == ['SBF/SP'], 'MNPEF/PROFIS como SBF/SP')
    shot(page, '5_fisica')

    # ── grafico por IES (Química) para inspecao visual
    page.evaluate("async () => { await switchArea('quimica'); }")
    page.wait_for_timeout(3000)
    page.evaluate("() => document.getElementById('chartIES').scrollIntoView({block:'center'})")
    page.wait_for_timeout(800)
    shot(page, '3_grafico_ies')

    print('\n=== erros de console acumulados: %d ===' % len(erros), flush=True)
    for e in erros[:5]:
        print('   ', e[:160], flush=True)
    br.close()

print('\n' + '=' * 60)
falhas = [m for s, m in res if s == 'FALHA']
print('%d checagens | %d falhas' % (len(res), len(falhas)))
for m in falhas:
    print('  FALHA:', m)
sys.exit(1 if falhas else 0)
