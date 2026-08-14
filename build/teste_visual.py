#!/usr/bin/env python3
"""Testes visuais do MAPA-PG em Chromium headless.

1-3. canonicalizacao de IES (filtro unico, rotulo de epoca preservado)
4.   titularidade por quadrienio (BIONORTE Centro-Oeste)
5.   Fisica: modalidade/situacao preenchidas, MNPEF sob a sigla certa
6.   camada de estratos A1-A8/C e o filtro por estrato
7.   seletor de instituicao com busca (470 IES, atalhos das 27, carga sob demanda)

Exige um servidor em 127.0.0.1:8765 servindo docs/:
    cd docs && python3 -m http.server 8765
"""
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

    print('\n=== 0. versoes sincronizadas ===', flush=True)
    page.goto(BASE, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(1500)
    shot(page, '0_licenca')
    page.click('#licenseOverlay button')          # "Concordo e desejo continuar"
    page.wait_for_timeout(4000)
    shot(page, '0_carga')
    ok(not erros, 'sem erro de console na carga (%s)' % (erros[:2] or 'nenhum'))

    # shell_version do manifest era escrito a mao e ficou 4 releases atras (5.0.0
    # contra 5.4.0 do app). Agora atualizar_manifest() o deriva de index.html; esta
    # checagem impede a defasagem de voltar em silencio.
    vs = page.evaluate("""() => ({
        app: VERSION,
        header: (document.getElementById('headerVersion') || {}).textContent || '',
        manifest: (MANIFEST || {}).shell_version || '',
    })""")
    print('   app=%s | cabecalho=%s | manifest.shell_version=%s'
          % (vs['app'], vs['header'], vs['manifest']), flush=True)
    ok(vs['manifest'] == vs['app'],
       'manifest.shell_version == VERSION do app (%s vs %s)' % (vs['manifest'], vs['app']))
    ok(vs['header'].strip() == 'v' + vs['app'],
       'cabecalho mostra a mesma versao (%r)' % vs['header'])

    # o filtro "Categoria de Docente" foi REMOVIDO em v5.4.1: coletava `categorias`
    # e nada lia. As categorias nao sao particao (soma excede n_doc em 65% dos
    # registros), entao nao havia como implementa-lo certo com os dados servidos.
    cat = page.evaluate("""() => ({
        caixas: document.querySelectorAll('.cat-chk').length,
        campo: 'categorias' in getFilters(),
        metricas: [...document.getElementById('selMetrica').options]
                    .map(o => o.value).filter(v => /perm|colab|visit/.test(v)),
    })""")
    ok(cat['caixas'] == 0, 'nao ha mais caixas de Categoria de Docente (%d)' % cat['caixas'])
    ok(not cat['campo'], 'getFilters() nao devolve mais o campo morto `categorias`')
    ok(len(cat['metricas']) == 3,
       'a categoria segue escolhivel no seletor de metrica (%s)' % cat['metricas'])

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

    # ── TESTE 6: camada de ESTRATOS A1-A8/C
    # Nao havia checagem de estrato aqui, e por isso a v5.3.0 foi publicada sem a
    # camada: `gerar_dados_completos.py` reescreve os area-*.json do zero e
    # `gerar_estratos_app.py` os enriquece depois, in-place. Sem os campos estr_*,
    # `sumIF()` recebe undefined e devolve 0 — TODA metrica ia a 0,00 ao desmarcar
    # um estrato, sem erro de console. A tela padrao marca os nove e cai no caminho
    # de prod_sub, que esta correto, entao nada parecia errado.
    print('\n=== 6. estratos A1-A8/C ===', flush=True)
    page.evaluate("async () => { await switchArea('quimica'); }")
    page.wait_for_timeout(3000)
    est = page.evaluate("""() => {
        const r = DATA.data[0];
        const campos = ['estr_perm','estr_colab','estr_visit','estr_all'].concat(
            ['cs','oa','hb'].flatMap(b => ['estr_perm_'+b,'estr_all_'+b]));
        return {
            faltam: campos.filter(c => !(c in r)),
            meta: ['estratos','estratos_cs','estratos_oa','estratos_hb']
                    .filter(k => !DATA.metadata[k]),
            rotulo: (document.getElementById('lblA1') || {}).textContent || '',
        };
    }""")
    print('   rotulo A1: %r' % est['rotulo'], flush=True)
    ok(not est['faltam'], 'campos estr_* nos registros (faltam: %s)' % (est['faltam'] or 'nenhum'))
    ok(not est['meta'], 'metadata.estratos por base (faltam: %s)' % (est['meta'] or 'nenhum'))
    ok('percentil' in est['rotulo'], 'rotulo de A1 traz percentil e corte do indicador')

    ef = page.evaluate("""() => {
        const todos = getFilters();
        const antes = calcWeightedAvgEff(filterData(todos), 'ma_perm', 'n_perm',
                                         todos.subtipos, todos.estratos_if);
        const c = [...document.querySelectorAll('.estr-chk')].find(x => x.value === 'C');
        c.checked = false;
        const parc = getFilters();
        const alvo = filterData(parc);
        const depois = calcWeightedAvgEff(alvo, 'ma_perm', 'n_perm',
                                          parc.subtipos, parc.estratos_if);
        const ifrep = getEffectiveIF(alvo[0] || DATA.data[0], parc.estratos_if);
        c.checked = true;
        return {antes: antes, depois: depois, n: parc.estratos_if.length,
                ifrep: ifrep.total, vetor: ifrep.porEstrato};
    }""")
    print('   ma_perm ponderado: 9 estratos = %.2f | 8 estratos = %.2f'
          % (ef['antes'], ef['depois']), flush=True)
    print('   relatorio de IF: %d artigos %s' % (ef['ifrep'], ef['vetor']), flush=True)
    ok(ef['n'] == 8, 'desmarcar C deixa 8 estratos selecionados')
    ok(ef['antes'] > 0, 'metrica com os 9 estratos e maior que zero')
    ok(ef['depois'] > 0, 'desmarcar um estrato NAO zera a metrica (o bug da v5.3.0)')
    ok(ef['depois'] < ef['antes'], 'metrica com 8 estratos e menor que com 9')
    ok(ef['ifrep'] > 0, 'Relatorio Detalhado de IF conta artigos por estrato')

    # Guardas com `|| {}` em todo acesso: sem a camada, o metadata.estratos nao
    # existe e um acesso direto lancaria excecao, abortando a suite inteira com
    # traceback em vez de reportar FALHA e seguir para o resumo final.
    base = page.evaluate("""() => {
        const cortes = b => JSON.stringify(((DATA.metadata || {})['estratos_'+b] || {}).cortes_if || {});
        const ativos = () => JSON.stringify(((DATA.metadata || {}).estratos || {}).cortes_if || {});
        const cs = cortes('cs');
        setIFBase('oa');
        const oa = ativos();
        setIFBase('cs');
        return {ativo: oa !== '{}', igual: oa === cs};
    }""")
    page.wait_for_timeout(1500)
    ok(base['ativo'], 'trocar a base para OpenAlex mantem metadata.estratos populado')
    ok(not base['igual'], 'os cortes mudam ao trocar de base (CiteScore != OpenAlex)')
    shot(page, '6_estratos')

    # ── TESTE 7: seletor de instituicao com busca (v5.4.0)
    # A referencia deixou de ser uma de 27 federais e passou a ser qualquer uma das
    # ~470 instituicoes com programa avaliado, achada por sigla ou nome. O indice
    # (ies_index.json) traz nome/UF/apelidos; a lista de programas vem sob demanda
    # em dados/ies-<slug>.json. Roda numa aba NOVA, sem ?ies=, para cair no painel.
    print('\n=== 7. seletor de instituicao com busca ===', flush=True)
    p2 = br.new_page(viewport={'width': 1440, 'height': 1000})
    erros2 = []
    p2.on('console', lambda m: erros2.append(m.text) if m.type == 'error' else None)
    p2.on('pageerror', lambda e: erros2.append('PAGEERROR: %s' % e))
    p2.goto('http://127.0.0.1:8765/index.html', wait_until='networkidle', timeout=60000)
    p2.wait_for_timeout(1200)
    p2.click('#licenseOverlay button')
    p2.wait_for_timeout(1800)
    ab = p2.evaluate("""() => ({
        n_ies: (IES_IDX || {}).n_ies || 0,
        destaque: ((IES_IDX || {}).destaque || []).length,
        temBusca: !!document.getElementById('iesPickerBusca'),
        atalhos: document.querySelectorAll('#iesPickerLista .ies-opt').length,
        okOff: (document.getElementById('iesPickerOk') || {}).disabled,
    })""")
    print('   indice: %s IES (%s em destaque) | atalhos visiveis: %s'
          % (ab['n_ies'], ab['destaque'], ab['atalhos']), flush=True)
    ok(ab['temBusca'], 'painel tem campo de busca')
    ok(ab['n_ies'] > 400, 'indice cobre mais de 400 instituicoes (%s)' % ab['n_ies'])
    ok(ab['destaque'] == 27 and ab['atalhos'] == 27,
       'sem busca, aparecem as 27 federais como atalho (%s)' % ab['atalhos'])
    ok(ab['okOff'] is True, 'OK desabilitado antes de escolher')

    # a busca precisa ser cega a caixa, acento e ESPACO: "FIO CRUZ" -> FIOCRUZ
    bu = p2.evaluate("""() => {
        const f = t => { filtrarIes(t); return [...document.querySelectorAll(
            '#iesPickerLista .ies-opt')].map(c => c.dataset.sig); };
        return {espaco: f('FIO CRUZ'), junto: f('fiocruz'),
                nome: f('oswaldo'), campus: f('blumenau'), nada: f('zzzq')};
    }""")
    print('   "FIO CRUZ" -> %d | "fiocruz" -> %d | "oswaldo" -> %s | "blumenau" -> %s'
          % (len(bu['espaco']), len(bu['junto']), bu['nome'], bu['campus']), flush=True)
    ok(bu['espaco'] == bu['junto'] and len(bu['espaco']) > 1,
       '"FIO CRUZ" acha o mesmo que "fiocruz" (espaco e caixa ignorados)')
    ok('FIOCRUZ' in bu['nome'], 'busca por parte do NOME encontra a instituicao')
    ok('UFSC' in bu['campus'], 'campus agregado e achavel pelo nome (blumenau -> UFSC)')
    ok(bu['nada'] == [], 'termo sem correspondencia nao lista nada')

    # escolher uma instituicao FORA das 27 e conferir que a cascata monta
    esc = p2.evaluate("""async () => {
        filtrarIes('FIO CRUZ');
        [...document.querySelectorAll('#iesPickerLista .ies-opt')]
            .find(c => c.dataset.sig === 'FIOCRUZ').click();
        confirmIesPicker();
        await new Promise(r => setTimeout(r, 4000));
        return {ref: REF, nome: REF_NOME, n: REGISTRY.programas_unb.length,
                grandes: Object.keys(REGISTRY.grandes_areas).length,
                cache: Object.keys(IES_CACHE), url: location.search};
    }""")
    print('   REF=%s (%s) | %d programas | %d grandes areas | cache=%s | %s'
          % (esc['ref'], esc['nome'], esc['n'], esc['grandes'], esc['cache'], esc['url']), flush=True)
    ok(esc['ref'] == 'FIOCRUZ', 'referencia fora das 27 federais e aceita')
    ok(esc['n'] > 0 and esc['grandes'] > 0, 'cascata monta para ela (%d programas)' % esc['n'])
    ok(esc['cache'] == ['FIOCRUZ'], 'baixou SO o arquivo da instituicao escolhida')
    ok('ies=FIOCRUZ' in esc['url'], 'a URL passa a refletir ?ies=FIOCRUZ')
    ok(esc['nome'].upper().count('FIOCRUZ') <= 1,
       'nome nao repete a sigla no rotulo (%r)' % esc['nome'])
    ok(not erros2, 'sem erro de console no fluxo do seletor (%s)' % (erros2[:2] or 'nenhum'))
    p2.close()

    # ══════════════════════════════════════════════════════════════════
    print('\n=== 8. programa sem nota e area fora do portfolio da referencia ===', flush=True)
    # A UFG nao tem programa COM NOTA em Geociencias, mas tem um mestrado aprovado
    # em 2024 e ainda nao avaliado. Ate a v5.5.1 ele nao existia em lugar nenhum do
    # app e a area era inalcancavel pela cascata — foi o que a Presidencia da SBG
    # leu, com razao, como "a UFG nao esta na plataforma".
    p3 = br.new_page()
    erros3 = []
    p3.on('console', lambda m: erros3.append(m.text) if m.type == 'error' else None)
    p3.on('pageerror', lambda e: erros3.append(str(e)))
    p3.goto(BASE.replace('ies=UNB&area=quimica', 'ies=UFG'), wait_until='networkidle', timeout=60000)
    p3.click('#licenseOverlay button')
    p3.wait_for_selector('#results', timeout=20000)
    ini = p3.inner_text('#results')
    ok('ainda sem nota da CAPES' in ini, 'tela inicial avisa dos programas sem nota')
    ok('GEOCI' in ini.upper(), 'e cita o mestrado em Geociencias')

    cas = p3.evaluate('''() => {
        const ga = document.getElementById('selGrandeArea');
        ga.value = 'CIÊNCIAS EXATAS E DA TERRA'; rebuildAreaOptions();
        const area = document.getElementById('selArea');
        return {areas: [...area.options].map(o => o.textContent),
                semNota: semNotaDaRef('geociencias').length};
    }''')
    geo = [a for a in cas['areas'] if 'GEOCI' in a.upper()]
    print('   area na cascata da UFG: %s | sem nota: %d' % (geo[:1], cas['semNota']), flush=True)
    ok(bool(geo), 'Geociencias alcancavel pela cascata mesmo sem programa com nota')
    ok(bool(geo) and 'sem nota' in geo[0], 'o rotulo da area marca o programa sem nota')

    ar = p3.evaluate('''async () => {
        await switchArea('geociencias', null);
        await new Promise(r => setTimeout(r, 1500));
        return {unb: UNB_CD, n: new Set(DATA.data.map(d => d.cd)).size,
                txt: document.getElementById('results').innerText,
                desab: [...document.getElementById('selCurso').options].filter(o => o.disabled).length};
    }''')
    print('   Geociencias: %d programas no pais | destaque=%s' % (ar['n'], ar['unb']), flush=True)
    ok(ar['n'] > 50, 'a area nacional inteira carrega (%d programas)' % ar['n'])
    ok(ar['unb'] is None, 'nenhum programa fica destacado em vermelho')
    ok('Sem programa da UFG nesta área' in ar['txt'], 'o painel explica a ausencia da referencia')
    ok('aprovado e ainda sem nota' in ar['txt'], 'o painel lista o programa aprovado sem nota')
    ok(ar['desab'] == 1, 'o seletor de curso mostra o sem nota, desabilitado')

    tot = p3.evaluate('''() => {
        const conta = () => {
            const ga = document.getElementById('selGrandeArea');
            const area = document.getElementById('selArea');
            const orig = ga.value; let t = 0;
            for (const o of ga.options) { ga.value = o.value; rebuildAreaOptions(); t += area.options.length; }
            ga.value = orig; rebuildAreaOptions();
            return t;
        };
        const antes = conta();
        document.getElementById('chkTodasAreas').checked = true;
        onTodasAreasChange();
        return {antes, depois: conta()};
    }''')
    print('   areas alcancaveis: %d -> %d com "todas as areas"' % (tot['antes'], tot['depois']), flush=True)
    ok(tot['depois'] > tot['antes'], 'o modo "todas as areas" abre as 49 (%d -> %d)'
       % (tot['antes'], tot['depois']))
    ok(tot['depois'] == 49, 'sao exatamente as 49 areas da CAPES (%d)' % tot['depois'])
    ok(not erros3, 'sem erro de console no fluxo da UFG (%s)' % (erros3[:2] or 'nenhum'))
    p3.close()

    # Instituição que só tem programa aprovado e ainda sem nota: até a v5.6.0 ela
    # não existia no seletor, porque a lista saía dos area-*.json e ela não tem
    # programa avaliado. Procurar pelo nome não achava nada.
    p4 = br.new_page()
    erros4 = []
    p4.on('console', lambda m: erros4.append(m.text) if m.type == 'error' else None)
    p4.on('pageerror', lambda e: erros4.append(str(e)))
    p4.goto(BASE.replace('ies=UNB&area=quimica', 'ies=IBC'), wait_until='networkidle', timeout=60000)
    p4.click('#licenseOverlay button')
    p4.wait_for_selector('#results', timeout=20000)
    t4 = p4.inner_text('#results')
    ok('INSTITUTO BENJAMIN CONSTANT' in t4.upper(),
       'instituicao so-com-programa-sem-nota entra no seletor')
    ok('ainda não tem programa com nota' in t4, 'a tela diz que nao ha programa com nota')
    ok('ainda sem nota da CAPES' in t4, 'e lista o programa aprovado')
    est = p4.evaluate("""() => ({n: REGISTRY.programas_unb.length, sn: semNotaDaRef().length,
                                 ga: [...document.getElementById('selGrandeArea').options].length})""")
    print('   IBC: %d com nota | %d sem nota | %d grande(s) area(s) na cascata'
          % (est['n'], est['sn'], est['ga']), flush=True)
    ok(est['n'] == 0 and est['sn'] >= 1, 'cascata monta a partir do programa sem nota')
    cart = p4.evaluate("""() => { trocarIes();
        filtrarIes('benjamin constant');
        return [...document.querySelectorAll('#iesPickerLista .ies-opt')].map(c => c.innerText); }""")
    ok(bool(cart) and '0 prog' not in cart[0],
       'o cartao do seletor nao diz "0 progs" (%s)' % (cart[0].replace('\n', ' | ') if cart else '-'))
    # Curitibanos e campus da UFSC: vai para a mae, como Blumenau, e nao vira entrada
    cur = p4.evaluate("""() => { filtrarIes('curitibanos');
        return [...document.querySelectorAll('#iesPickerLista .ies-opt')].map(c => c.dataset.sig); }""")
    ok(cur == ['UFSC'], 'campus da UFSC agregado a sede, sem entrada propria (%s)' % cur)
    ok(not erros4, 'sem erro de console no fluxo da instituicao nova (%s)' % (erros4[:2] or 'nenhum'))
    p4.close()

    # ══════════════════════════════════════════════════════════════════
    print('\n=== 9. bolsas CAPES: serie anual por programa ===', flush=True)
    # Pedido de um coordenador pelo formulario do app: ver as bolsas do programa
    # ao longo dos anos. Camada dados/bol-<area>.json, carregada sob demanda.
    p5 = br.new_page()
    erros5 = []
    p5.on('console', lambda m: erros5.append(m.text) if m.type == 'error' else None)
    p5.on('pageerror', lambda e: erros5.append(str(e)))
    p5.goto(BASE, wait_until='networkidle', timeout=60000)   # UNB + quimica
    p5.click('#licenseOverlay button')
    p5.wait_for_timeout(2500)
    ok(p5.is_visible('#bolBtn'), 'botao de bolsas na barra lateral')
    p5.click('#bolBtn')
    p5.wait_for_timeout(2500)
    ok('show' in (p5.get_attribute('#bolOverlay', 'class') or ''), 'painel de bolsas abre')
    est = p5.evaluate("""() => ({anos: BOL.metadata.anos.length, progs: Object.keys(BOL.data).length,
                                 charts: _bolCharts.length, med: BOL_MED})""")
    print('   %d anos | %d programas com bolsa | %d graficos'
          % (est['anos'], est['progs'], est['charts']), flush=True)
    ok(est['anos'] >= 16, 'serie cobre 2010-2025 (%d anos)' % est['anos'])
    ok(est['charts'] == 2, 'desenha serie e composicao por nivel')
    txt5 = p5.inner_text('#bolOverlayBody')
    ok('CNPq' in txt5 and 'nominal' in txt5,
       'ressalvas presentes (outras agencias, valor nominal)')
    ok('tr.ref-row' and p5.evaluate(
        "() => document.querySelectorAll('#bolOverlayBody tr.ref-row').length") == 1,
       'programa de referencia destacado na tabela da area')
    # a troca de medida muda o texto (o rotulo do box vem em CAIXA ALTA pelo CSS)
    p5.evaluate("() => bolMedida('m')")
    p5.wait_for_timeout(600)
    t5m = p5.inner_text('#bolOverlayBody').upper()
    ok('MESES DE BOLSA' in t5m and 'BOLSAS-EQUIVALENTES' in t5m,
       'medida "meses de bolsa" traz a bolsa-equivalente')
    p5.evaluate("() => bolMedida('v')")
    p5.wait_for_timeout(600)
    ok('R$' in p5.inner_text('#bolOverlayBody'), 'medida "valor pago" em reais')
    # numero conferido contra o dado bruto da CAPES
    fis = p5.evaluate("""async () => { await switchArea('astronomia-fisica', null);
        await new Promise(r => setTimeout(r, 1200));
        await abrirBolsas(); await new Promise(r => setTimeout(r, 800));
        bolMedida('b');
        return _bolSerie('53001010002P6'); }""")
    print('   Fisica/UnB pessoas com bolsa 2010-2025: %s' % fis, flush=True)
    # Conferido no CSV cru da CAPES, ja com deduplicacao por PESSOA: 2025 tem 49
    # registros e 46 pessoas — tres alunos passaram de mestrado a doutorado no
    # mesmo ano e apareciam duas vezes na primeira versao da camada.
    ok(fis[7] == 68 and fis[11] == 41 and fis[15] == 46,
       'serie da Fisica/UnB bate com a fonte (2017=68, 2021=41, 2025=46)')
    dedup = p5.evaluate("""() => {
        const r = BOL.data['53001010002P6']['2025'];
        const somaNiveis = Object.values(r.n).reduce((a, x) => a + x[0], 0);
        return {b: r.b, ba: r.ba, somaNiveis: somaNiveis, m: r.m, ma: r.ma};
    }""")
    print('   2025: %d pessoas | %d alunos | soma dos niveis %d | %d meses'
          % (dedup['b'], dedup['ba'], dedup['somaNiveis'], dedup['m']), flush=True)
    ok(dedup['b'] < dedup['somaNiveis'],
       'total de pessoas NAO e a soma dos niveis (%d < %d)' % (dedup['b'], dedup['somaNiveis']))
    ok(dedup['ba'] <= dedup['b'] and dedup['ma'] <= dedup['m'],
       'alunos sao subconjunto do total, e os meses de aluno tambem')
    ok('fluxo' in p5.inner_text('#bolOverlayBody').lower(),
       'o painel avisa que a contagem do ano e fluxo, nao foto de um mes')
    ok(not erros5, 'sem erro de console no painel de bolsas (%s)' % (erros5[:2] or 'nenhum'))
    p5.close()

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
