#!/usr/bin/env python3
"""Testa a v5.8.3: o filtro de REGIÃO aparece em tudo o que sai do app.

O defeito que motivou o teste: com só o Sudeste marcado, o relatório dizia
"IES selecionadas: 59" e não mencionava a região — um recorte regional passava por
nacional depois de impresso. Aqui o recorte é o mesmo de um relatório real
(Astronomia/Física, notas 5-6-7, 2021-2024, Art/ano Permanentes, só Sudeste), em
que a média dos selecionados vale 2,13 e, sem o filtro de região, 2,47.

Exige um servidor em 127.0.0.1:8765 servindo docs/:
    cd docs && python3 -m http.server 8765
    python3 build/teste_regiao_nas_saidas.py
"""
import re
import sys

from playwright.sync_api import sync_playwright

BASE = ('http://127.0.0.1:8765/index.html'
        '?ies=USP-S%C3%83O%20CARLOS&area=astronomia-fisica&curso=33002045002P9')
res = []


def ok(cond, msg):
    res.append(bool(cond))
    print(('  OK    ' if cond else '  FALHA ') + msg, flush=True)


with sync_playwright() as pw:
    br = pw.chromium.launch()
    page = br.new_page(viewport={'width': 1440, 'height': 1000})
    erros = []
    # O beacon de analytics da Cloudflare é bloqueado por CORS em localhost. É ruído
    # do ambiente de teste, não do app, e não deve reprovar a suíte.
    def relevante(t):
        return 'cloudflareinsights' not in t and 'ERR_FAILED' not in t
    page.on('console', lambda m: erros.append(m.text) if m.type == 'error' and relevante(m.text) else None)
    page.on('pageerror', lambda e: erros.append('PAGEERROR: %s' % e))

    page.goto(BASE, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(1200)
    page.click('#licenseOverlay button')
    page.wait_for_timeout(4000)
    ok(not erros, 'sem erro de console na carga (%s)' % (erros[:2] or 'nenhum'))

    # recorte do relatório real: notas 5,6,7 · 2021-2024 · Art/ano Permanentes · só Sudeste
    page.evaluate("""() => {
        [3,4,5,6,7].forEach(n => { const c = document.getElementById('nota'+n); if (c) c.checked = [5,6,7].includes(n); });
        const q = document.getElementById('selQuad'); if (q) q.value = '2021-2024';
        const m = document.getElementById('selMetrica'); if (m) m.value = 'ma_perm';
        document.querySelectorAll('.reg-chk').forEach(c => { c.checked = (c.value === 'Sudeste'); });
        analisar();
    }""")
    page.wait_for_timeout(2500)

    f = page.evaluate("() => getFilters()")
    ok(f['regioes'] == ['Sudeste'], 'filtro ativo: só Sudeste (%s)' % f['regioes'])
    ok(page.evaluate("() => getRegiaoLabel(getFilters())") == 'Sudeste',
       'getRegiaoLabel devolve a região marcada')
    ok(page.evaluate("() => getRegiaoLabel({regioes:['N','NE','CO','SE','S']})") == 'Todas as regiões',
       'com as cinco marcadas, o rótulo é "Todas as regiões"')

    # ── relatório TXT (gerado sem baixar: intercepta o download em memória)
    txt = page.evaluate("() => { gerarRelatorio(); return window._lastReport || ''; }")
    ok('Região: Sudeste' in txt, 'relatório TXT declara a região')
    mies = re.search(r'IES selecionadas: (.+)', txt)
    rot = mies.group(1).strip() if mies else ''
    ok(re.fullmatch(r'(todas as \d+|\d+ de \d+)', rot),
       'relatório diz quantas IES de quantas (%s)' % (rot or '—'))
    nprog = len(re.findall(r'\d{4}-\d{4}\s+\d+\s+\d+', txt))
    ok(nprog == 21, 'o recorte do Sudeste traz 21 linhas de programa (%d)' % nprog)
    m = re.search(r'Média selecionados: ([\d.]+)', txt)
    ok(m and abs(float(m.group(1)) - 2.13) < 0.02,
       'a média ponderada do recorte continua 2,13 (%s)' % (m.group(1) if m else '—'))

    # subconjunto de IES: o rótulo tem de virar "N de TOTAL", que era o número solto
    txt2 = page.evaluate("""() => {
        const chks = [...document.querySelectorAll('.ies-chk')];
        chks[0].checked = false;
        analisar(); gerarRelatorio();
        return window._lastReport || '';
    }""")
    m2 = re.search(r'IES selecionadas: (.+)', txt2)
    ok(m2 and re.fullmatch(r'\d+ de \d+', m2.group(1).strip()),
       'com uma IES desmarcada vira "N de TOTAL" (%s)' % (m2.group(1).strip() if m2 else '—'))
    page.evaluate("() => { document.querySelectorAll('.ies-chk')[0].checked = true; analisar(); }")
    page.wait_for_timeout(1500)

    # ── CSV
    csv = page.evaluate("""() => {
        let capturado = '';
        const antigo = window.download;
        window.download = (nome, conteudo) => { capturado = conteudo; };
        try { exportarCSV(); } finally { window.download = antigo; }
        return capturado;
    }""")
    ok('Região=Sudeste' in csv, 'CSV declara a região no rodapé de filtros')
    ok('Notas=5,6,7' in csv and 'Quadriênio=2021-2024' in csv,
       'CSV declara também notas e quadriênio (antes só tipos e estratos)')

    # ── gráficos na tela
    recortes = page.evaluate(
        "() => [...document.querySelectorAll('p')].map(p => p.textContent.trim())"
        ".filter(t => t.startsWith('Recorte:'))")
    ok(len(recortes) >= 2, 'os cartões de gráfico carimbam o recorte (%d encontrados)' % len(recortes))
    ok(all('Sudeste' in r for r in recortes),
       'todo carimbo traz a região (%s)' % (recortes[0][:80] if recortes else '—'))

    # ── PNG exportado: a marca d'água ganhou a linha do recorte
    fontes = page.evaluate("() => [exportPNG.toString(), exportarPNGs.toString()]")
    ok(all('getRecorteLabel' in f and 'h + 48' in f for f in fontes),
       'os dois exportadores de PNG (um gráfico e todos) escrevem o recorte na 2ª linha')

    ok(not erros, 'sem erro de console ao fim (%s)' % (erros[:2] or 'nenhum'))
    br.close()

print('\n%d de %d checagens passaram' % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
