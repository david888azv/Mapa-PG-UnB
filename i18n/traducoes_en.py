# -*- coding: utf-8 -*-
"""
Tabela PT -> EN do MAPA-PG. Aplicada por gerar_ingles.py sobre as paginas de
docs/, que continuam sendo as unicas editaveis a mao.

Regra: cada chave e um trecho LITERAL da pagina em portugues e tem de aparecer
nela o numero exato de vezes declarado (uma, por omissao). Chave que nao bate =
o gerador para. E o que impede a versao inglesa de envelhecer em silencio.

O CUIDADO PRINCIPAL, aqui mais do que no MAPA-GR: neste app as strings do
JavaScript misturam rotulo de interface com DADO. Ao lado de
'Carregando catálogo de áreas CAPES...' convivem 'FUNDAÇÃO OSWALDO CRUZ
(FIOCRUZ)' e 'UFPB-JOÃO PESSOA', que sao tabelas de canonicalizacao de
instituicao. Traduzir em bloco quebraria o aplicativo em silencio. So entra
aqui o que o leitor ve como interface.

Tambem NAO se traduz:
  - siglas e nomes proprios: CAPES, CNPq, PQ, IF, CiteScore, OpenAlex, Scopus,
    MAPA-PG, os estratos A1-A8/C;
  - nomes de area de avaliacao, de programa e de instituicao (sao dados, vem
    dos JSON e continuam em portugues nas duas versoes);
  - as chaves de metrica (ma_pq, ma_all, avg_if...), que sao campos do dado.
"""

INDEX = [

    # ------------------------------------------------------------------ <head>
    ("<title>MAPA-PG — Programas de pós-graduação do Brasil por área CAPES</title>",
     "<title>MAPA-PG — Brazilian graduate programmes by CAPES field</title>"),

    # --------------------------------------------------------------- cabecalho
    ("<h1><span>MAPA-PG</span> — Monitoramento e Análise de Produção Acadêmica da "
     "Pós-Graduação</h1>",
     "<h1><span>MAPA-PG</span> — Monitoring and Analysis of Graduate Research Output</h1>"),
    # "fator de impacto" aqui era impreciso e colidia com a métrica `avg_if` do
    # seletor, que é o IF de 2 anos do OpenAlex: a régua dos estratos é o
    # CiteScore do Scopus, a fonte que a CAPES prescreve para 2025-2028.
    ("<strong>Novo:</strong> estratificação CAPES <strong>A1–A8/C</strong> (Ficha de Avaliação "
     "2025–2028) por percentil de CiteScore (Scopus).",
     "<strong>New:</strong> CAPES <strong>A1–A8/C</strong> stratification (2025–2028 assessment "
     "rules) by CiteScore (Scopus) percentile."),

    # ------------------------------------------------------- seletor de programa
    ('<h3 id="refHead" style="color:var(--accent);">Selecionar Programa</h3>',
     '<h3 id="refHead" style="color:var(--accent);">Select a programme</h3>'),
    ("cursor:pointer;\">↺ Trocar universidade de referência</button>",
     "cursor:pointer;\">↺ Change reference university</button>"),
    ('<label style="font-size:12px;">Grande Área CNPq</label>',
     '<label style="font-size:12px;">CNPq broad field</label>'),
    ('<label style="font-size:12px;margin-top:6px;display:block;">Área de Avaliação CAPES</label>',
     '<label style="font-size:12px;margin-top:6px;display:block;">CAPES assessment field</label>'),
    ("<span>Ver <strong>todas as 49 áreas</strong> da CAPES, inclusive as que a referência não "
     "tem</span>",
     "<span>Show <strong>all 49 CAPES fields</strong>, including those the reference institution "
     "does not have</span>"),
    ('<label id="refCursoLbl" style="font-size:12px;margin-top:6px;display:block;">Curso — '
     'referência</label>',
     '<label id="refCursoLbl" style="font-size:12px;margin-top:6px;display:block;">Programme — '
     'reference</label>'),
    ("Comparações são feitas dentro da mesma Área CAPES (regra CAPES).</p>",
     "Comparisons are always made within the same CAPES field, as CAPES requires.</p>"),
    ('title="Pedir um ajuste, apontar um dado errado ou sugerir uma melhoria">💡 Sugerir '
     'melhoria</button>',
     'title="Ask for a change, report wrong data or suggest an improvement">💡 Suggest an '
     'improvement</button>', 2),

    # ------------------------------------------------------------------ filtros
    ("<h3>Nota CAPES</h3>", "<h3>CAPES grade</h3>"),
    ('id="nota3" value="3"> Nota 3</label>', 'id="nota3" value="3"> Grade 3</label>'),
    ('id="nota4" value="4"> Nota 4</label>', 'id="nota4" value="4"> Grade 4</label>'),
    ('id="nota5" value="5" checked> Nota 5</label>',
     'id="nota5" value="5" checked> Grade 5</label>'),
    ('id="nota6" value="6"> Nota 6</label>', 'id="nota6" value="6"> Grade 6</label>'),
    ('id="nota7" value="7"> Nota 7</label>', 'id="nota7" value="7"> Grade 7</label>'),

    ("<h3>Quadriênio</h3>", "<h3>Four-year cycle</h3>"),
    ('<option value="all">Todos os quadriênios</option>',
     '<option value="all">All cycles</option>'),

    ("<h3>Métrica de Comparação</h3>", "<h3>Comparison metric</h3>"),
    ('<option value="ma_pq">Art/ano — Bolsistas PQ</option>',
     '<option value="ma_pq">Articles/year — CNPq research fellows (PQ)</option>'),
    ('<option value="ma_spq">Art/ano — Sem bolsa PQ</option>',
     '<option value="ma_spq">Articles/year — without a PQ fellowship</option>'),
    ('<option value="ma_all" selected>Art/ano — Média geral (PQ + sem PQ)</option>',
     '<option value="ma_all" selected>Articles/year — overall mean (PQ + non-PQ)</option>'),
    ('<option value="ma_perm">Art/ano — Docentes Permanentes</option>',
     '<option value="ma_perm">Articles/year — permanent faculty</option>'),
    ('<option value="ma_colab">Art/ano — Docentes Colaboradores</option>',
     '<option value="ma_colab">Articles/year — collaborating faculty</option>'),
    ('<option value="ma_visit">Art/ano — Docentes Visitantes</option>',
     '<option value="ma_visit">Articles/year — visiting faculty</option>'),
    ('<option value="avg_if">Fator de Impacto Médio (OpenAlex 2yr)</option>',
     '<option value="avg_if">Mean impact factor (OpenAlex 2yr)</option>'),

    ("<h3>Região</h3>", "<h3>Region</h3>"),
    ('onclick="toggleRegioes(true)" style="flex:1;margin:0;">Todas</button>',
     'onclick="toggleRegioes(true)" style="flex:1;margin:0;">All</button>'),
    ('onclick="toggleIES(true)" style="flex:1;margin:0;">Todas</button>',
     'onclick="toggleIES(true)" style="flex:1;margin:0;">All</button>'),
    ('onclick="toggleIES(false)" style="flex:1;margin:0;">Nenhuma</button>',
     'onclick="toggleIES(false)" style="flex:1;margin:0;">None</button>'),
    ('onclick="toggleRegioes(false)" style="flex:1;margin:0;">Nenhuma</button>',
     'onclick="toggleRegioes(false)" style="flex:1;margin:0;">None</button>'),
    ('value="Centro-Oeste" checked onchange="analisar()"> Centro-Oeste (CO)</label>',
     'value="Centro-Oeste" checked onchange="analisar()"> Central-West (CO)</label>'),
    ('value="Nordeste" checked onchange="analisar()"> Nordeste (NE)</label>',
     'value="Nordeste" checked onchange="analisar()"> Northeast (NE)</label>'),
    ('value="Norte" checked onchange="analisar()"> Norte (N)</label>',
     'value="Norte" checked onchange="analisar()"> North (N)</label>'),
    ('value="Sudeste" checked onchange="analisar()"> Sudeste (SE)</label>',
     'value="Sudeste" checked onchange="analisar()"> Southeast (SE)</label>'),
    ('value="Sul" checked onchange="analisar()"> Sul (S)</label>',
     'value="Sul" checked onchange="analisar()"> South (S)</label>'),

    ("<h3>Instituições (IES)</h3>", "<h3>Institutions</h3>"),
    ('<label><input type="checkbox" id="chkAllIES" checked> <strong>Todas as IES</strong></label>',
     '<label><input type="checkbox" id="chkAllIES" checked> <strong>All institutions</strong></label>'),

    ("<h3>Tipo de Produção</h3>", "<h3>Output type</h3>"),
    ('onclick="toggleSubtipos(true)" style="flex:1;margin:0;">Todos</button>',
     'onclick="toggleSubtipos(true)" style="flex:1;margin:0;">All</button>'),
    ('onclick="toggleSubtipos(false)" style="flex:1;margin:0;">Nenhum</button>',
     'onclick="toggleSubtipos(false)" style="flex:1;margin:0;">None</button>'),
    ('value="25" checked onchange="analisar()"> Artigo em Periódico</label>',
     'value="25" checked onchange="analisar()"> Journal article</label>'),
    ('value="8" onchange="analisar()"> Resumo</label>',
     'value="8" onchange="analisar()"> Abstract</label>'),
    ('value="9" onchange="analisar()"> Trabalho de Congresso</label>',
     'value="9" onchange="analisar()"> Conference paper</label>'),
    ('value="26" onchange="analisar()"> Capítulo de Livro</label>',
     'value="26" onchange="analisar()"> Book chapter</label>'),
    ('value="10" onchange="analisar()"> Texto em Jornal</label>',
     'value="10" onchange="analisar()"> Newspaper piece</label>'),

    ("<h3>Estratos CAPES (Ficha 2025-2028)</h3>", "<h3>CAPES strata (2025-2028 rules)</h3>"),
    ('onclick="toggleEstratos(true)" style="flex:1;margin:0;">Todos</button>',
     'onclick="toggleEstratos(true)" style="flex:1;margin:0;">All</button>'),
    ('onclick="toggleEstratos(false)" style="flex:1;margin:0;">Nenhum</button>',
     'onclick="toggleEstratos(false)" style="flex:1;margin:0;">None</button>'),
    ('onchange="toggleEstratos(this.checked)"> <strong>Todos os estratos</strong></label>',
     'onchange="toggleEstratos(this.checked)"> <strong>All strata</strong></label>'),
    ('<span id="lblC">C · sem indicador</span>',
     '<span id="lblC">C · no indicator</span>'),
    ("Estrato = percentil do CiteScore (Scopus) do periódico <strong>dentro da área</strong>\n"
     "                (A1 = topo 12,5%; C = sem indicador). Afeta <strong>ma_all, ma_perm, "
     "ma_colab,\n                ma_visit</strong> (passam a contar só artigos nos estratos "
     "marcados). <strong>ma_pq,\n                ma_spq, avg_if</strong> e contagens por tipo de "
     "produção mantêm os valores agregados.",
     "Stratum = the journal's CiteScore (Scopus) percentile <strong>within the field</strong>\n"
     "                (A1 = top 12.5%; C = no indicator). It affects <strong>ma_all, "
     "ma_perm, ma_colab,\n                ma_visit</strong> (which then count only articles in "
     "the ticked strata). <strong>ma_pq,\n                ma_spq, avg_if</strong> and the counts "
     "by output type keep their aggregate values."),

    ("<h3>Média Nacional (Todas as Áreas)</h3>", "<h3>National mean (all fields)</h3>"),
    ('onchange="showNatlAvg=this.checked;analisar()"> Incluir média nacional de todas as áreas '
     'nos gráficos e tabelas</label>',
     'onchange="showNatlAvg=this.checked;analisar()"> Include the national mean of all fields in '
     'charts and tables</label>'),

    ("<h3>Relatório Detalhado IF</h3>", "<h3>Detailed impact report</h3>"),
    ('<label><input type="checkbox" id="chkIFDetail"> Análise detalhada por Fator de Impacto</label>',
     '<label><input type="checkbox" id="chkIFDetail"> Detailed analysis by impact factor</label>'),
    ("Abre no próprio painel (sem novas abas): <strong>Página 1</strong> detalhamento numérico e "
     "<strong>Página 2</strong> gráficos, alternáveis por botão.</p>",
     "Opens inside the panel itself (no new tabs): <strong>Page 1</strong> the numbers and "
     "<strong>Page 2</strong> the charts, switched by a button.</p>"),
    ("Base do indicador de impacto (percentil dos estratos A1–A8/C)</div>",
     "Impact indicator used for the A1–A8/C percentiles</div>"),
    ("<strong>CiteScore</strong> (Scopus) — fonte oficial CAPES <span "
     "style=\"color:#7F8C8D;\">· padrão</span></label>",
     "<strong>CiteScore</strong> (Scopus) — the source CAPES prescribes <span "
     "style=\"color:#7F8C8D;\">· default</span></label>"),
    ('value="oa" onchange="setIFBase(this.value)"> OpenAlex (IF de 2 anos)</label>',
     'value="oa" onchange="setIFBase(this.value)"> OpenAlex (2-year impact factor)</label>'),
    ('value="hb" onchange="setIFBase(this.value)"> Híbrido: CiteScore + OpenAlex</label>',
     'value="hb" onchange="setIFBase(this.value)"> Hybrid: CiteScore + OpenAlex</label>'),
    ("A base escolhida recalcula os percentis de <strong>todos</strong> os estratos no app "
     "(filtro, métricas, rótulos e o Relatório Detalhado IF). No CiteScore, periódicos sem "
     "CiteScore vão para <strong>C</strong>; o Híbrido usa OpenAlex onde falta CiteScore.</p>",
     "The chosen source recalculates the percentiles of <strong>every</strong> stratum in the app "
     "(filter, metrics, labels and the detailed impact report). Under CiteScore, journals without "
     "a CiteScore fall into <strong>C</strong>; the hybrid uses OpenAlex wherever CiteScore is "
     "missing.</p>"),

    # ------------------------------------------------------------------ botoes
    ('<button class="btn btn-primary" onclick="analisar()">Analisar</button>',
     '<button class="btn btn-primary" onclick="analisar()">Analyse</button>'),
    ('style="background:#D4AF37;color:#fff;">🏆 TOP / Ranking de programas</button>',
     'style="background:#D4AF37;color:#fff;">🏆 TOP / programme ranking</button>'),
    ('style="background:#00897B;color:#fff;">⚙ Patentes / Produção Técnica</button>',
     'style="background:#00897B;color:#fff;">⚙ Patents / technical output</button>'),
    ('style="background:#7B1FA2;color:#fff;">🎓 Bolsas CAPES por ano</button>',
     'style="background:#7B1FA2;color:#fff;">🎓 CAPES scholarships by year</button>'),
    ('onclick="gerarRelatorio()">Gerar Relatório</button>',
     'onclick="gerarRelatorio()">Generate report</button>'),
    ('onclick="exportarCSV()">Exportar CSV</button>', 'onclick="exportarCSV()">Export CSV</button>'),
    ('onclick="exportarPNGs()" style="background:#FF9800;">Exportar Gráficos PNG</button>',
     'onclick="exportarPNGs()" style="background:#FF9800;">Export charts as PNG</button>'),
    ('style="background:#607D8B;color:#fff;margin-top:16px;">? Ajuda / Documentação</button>',
     'style="background:#607D8B;color:#fff;margin-top:16px;">? Help / Documentation</button>'),
]


# ==========================================================================
# index — strings do JAVASCRIPT.
# Nenhuma traducao usa apostrofe: estas strings vivem entre aspas simples no JS
# e uma apostrofe fecharia a string, matando a pagina inteira (foi o que
# aconteceu na primeira geracao do MAPA-GR; ver testar_ingles.py).
# ==========================================================================
INDEX += [

    # ------------------------------------------------- modal de licenca
    ("Monitoramento e Analise de Producao Academica da Pos-Graduacao</p>",
     "Monitoring and Analysis of Graduate Research Output</p>"),
    # O mes da versao nao se traduz mais: sai de VERSION_DATA pelo locale da pagina.
    ("const LOCALE_APP = 'pt-BR';", "const LOCALE_APP = 'en-GB';"),
    ("Prof. Titular David Lima Azevedo</p>", "Prof. David Lima Azevedo, Full Professor</p>"),
    ("Grupo de Dinâmica e Ab Initio (GDAI) · Núcleo de Estrutura da Matéria · Instituto de "
     "Física — UnB<br>",
     "Dynamics and Ab Initio Group (GDAI) · Matter Structure Centre · Institute of Physics "
     "— UnB<br>"),

    ("<p><strong>Fonte dos dados:</strong> todos os dados deste sistema sao publicos e foram "
     "obtidos exclusivamente do <strong>Portal de Dados Abertos da CAPES</strong> "
     "(<a href=\"https://dadosabertos.capes.gov.br/\" target=\"_blank\" "
     "style=\"color:#1565C0;\">dadosabertos.capes.gov.br</a>), ao amparo da Lei de Acesso a "
     "Informacao (Lei n. 12.527/2011). As URLs dos arquivos brutos da Coleta CAPES estao "
     "documentadas no arquivo de ajuda, acessivel pelo botao <strong>Help</strong> na barra "
     "lateral.</p>",
     "<p><strong>Data source:</strong> every figure in this system is public and comes solely "
     "from the <strong>CAPES Open Data Portal</strong> "
     "(<a href=\"https://dadosabertos.capes.gov.br/\" target=\"_blank\" "
     "style=\"color:#1565C0;\">dadosabertos.capes.gov.br</a>), under the Brazilian Freedom of "
     "Information Act (no. 12.527/2011). The URLs of the raw CAPES collection files are "
     "documented in the help page, reachable through the <strong>Help</strong> button in the "
     "sidebar.</p>"),

    ("<strong>CiteScore / Scopus (Elsevier):</strong> a estratificação A1–A8/C na base padrão "
     "usa o <strong>CiteScore 2025</strong>, métrica <em>powered by Scopus®</em> (Elsevier), "
     "obtida via API Scopus (<code>api.elsevier.com</code> · <code>www.scopus.com</code>) em "
     "<strong>3 jul 2026</strong>. Este aplicativo é gratuito, não-comercial e não substitui a "
     "base Scopus: publica apenas <strong>resultados agregados por percentil</strong>, sem "
     "redistribuir registros brutos, em conformidade com os termos da API gratuita da Elsevier. "
     "Detalhes na aba <strong>Help</strong> (fonte 10).",
     "<strong>CiteScore / Scopus (Elsevier):</strong> the default A1–A8/C stratification uses "
     "<strong>CiteScore 2025</strong>, a metric <em>powered by Scopus®</em> (Elsevier), obtained "
     "through the Scopus API (<code>api.elsevier.com</code> · <code>www.scopus.com</code>) on "
     "<strong>3 July 2026</strong>. This application is free, non-commercial and no substitute "
     "for Scopus: it publishes only <strong>percentile-aggregated results</strong>, redistributing "
     "no raw records, in line with the terms of Elsevier's free API. Details in the "
     "<strong>Help</strong> tab (source 10)."),

    ("<strong>Termos de uso e solucoes sob medida:</strong> ao utilizar este software, voce "
     "concorda em nao remover, alterar ou ocultar informacoes de autoria, mantendo a "
     "identificacao <strong>\"Prof. David L. Azevedo\"</strong> e <strong>\"MAPA-PG\"</strong> "
     "<strong>em todas as copias, resultados obtidos e aplicativos derivados</strong>. Tambem "
     "desenvolvemos analises especificas para qualquer programa de pos-graduacao de qualquer "
     "universidade do pais. Contato:",
     "<strong>Terms of use and tailored analyses:</strong> by using this software you agree not "
     "to remove, alter or conceal authorship information, keeping the attribution "
     "<strong>\"Prof. David L. Azevedo\"</strong> and <strong>\"MAPA-PG\"</strong> "
     "<strong>in every copy, in results obtained and in derived applications</strong>. We also "
     "produce specific analyses for any graduate programme at any university in the country. "
     "Contact:"),
    ("· conheca o projeto em <a href=\"https://daciencia.org\"",
     "· learn about the project at <a href=\"https://daciencia.org\""),

    ("<strong>Como citar:</strong> AZEVEDO, D. L. <em>MAPA-PG — um sistema interativo para "
     "monitoramento e análise de produção acadêmica: aplicação à área de Astronomia e "
     "Física</em>. Physicae Organum, v. 11, n. 1, 2026. DOI:",
     "<strong>How to cite:</strong> AZEVEDO, D. L. <em>MAPA-PG — um sistema interativo para "
     "monitoramento e análise de produção acadêmica: aplicação à área de Astronomia e "
     "Física</em> [in Portuguese]. Physicae Organum, vol. 11, no. 1, 2026. DOI:"),

    (">Concordo e desejo continuar</button>", ">I agree and wish to continue</button>"),
]

# ---------------------------------------------------- SEO / dado estruturado
INDEX += [
    ('"description": "Sistema interativo e gratuito para comparar a produção acadêmica de 4.824 '
     'programas de pós-graduação do Brasil (495 instituições) em todas as 49 áreas de avaliação '
     'da CAPES; escolha qualquer uma das 470 instituições como referência, buscando por sigla ou '
     'nome, e compare-a com seus pares nacionais, sempre dentro da mesma área, ao longo de '
     'três quadriênios (2013–2024), usando dados públicos da CAPES.",',
     '"description": "A free, interactive system for comparing the research output of 4,824 '
     'Brazilian graduate programmes (495 institutions) across all 49 CAPES assessment fields; '
     'pick any of 470 institutions as your reference, searching by acronym or name, and compare '
     'it with its national peers, always within the same field, across three four-year cycles '
     '(2013–2024), using public CAPES data.",'),
    ('"keywords": "pós-graduação, CAPES, avaliação CAPES, nota CAPES, produção científica, '
     'universidades federais, comparar programas, estratos A1-A8, CiteScore, OpenAlex, '
     'cientometria, dados abertos",',
     '"keywords": "graduate education, CAPES, CAPES assessment, CAPES grade, research output, '
     'Brazilian federal universities, compare programmes, A1-A8 strata, CiteScore, OpenAlex, '
     'scientometrics, open data",'),
    ('"Cobertura das 49 Áreas de Avaliação da CAPES — 4.824 programas de 495 instituições",',
     '"Covers all 49 CAPES assessment fields — 4,824 programmes at 495 institutions",'),
    ('"Comparação entre programas sempre dentro da mesma Área de Avaliação da CAPES",',
     '"Programmes are always compared within the same CAPES assessment field",'),
    ('"470 instituições selecionáveis como referência, com busca por sigla ou nome",',
     '"470 institutions can be set as the reference, searchable by acronym or name",'),
    ('"Três quadriênios (2013-2016, 2017-2020, 2021-2024)",',
     '"Three four-year cycles (2013-2016, 2017-2020, 2021-2024)",'),
    ('"Estratificação A1–A8/C por percentil de impacto do periódico (Ficha CAPES 2025-2028)",',
     '"A1–A8/C stratification by journal impact percentile (CAPES 2025-2028 rules)",'),
    ('"Relatórios exportáveis em TXT e CSV"', '"Reports exportable as TXT and CSV"'),
    ('"audienceType": "Coordenadores de pós-graduação, pró-reitorias, pesquisadores, candidatos '
     'a mestrado e doutorado"',
     '"audienceType": "Graduate programme coordinators, university administrators, researchers, '
     "and prospective master's and doctoral students\"" ),
    ('"operatingSystem": "Qualquer (navegador web)",',
     '"operatingSystem": "Any (web browser)",'),

    # ------------------------------------------------ carregamento e erros
    ("Carregando catálogo de áreas CAPES...", "Loading the CAPES field catalogue...", 2),
    ('<p style="color:#E74C3C;font-size:16px;">Erro ao carregar catálogo.</p>',
     '<p style="color:#E74C3C;font-size:16px;">Failed to load the catalogue.</p>'),
    ("`Instituição desconhecida: ${sigla}`", "`Unknown institution: ${sigla}`"),
    ('<p style="color:#E74C3C;font-size:16px;">Não foi possível carregar os programas de '
     '${REF}.</p>',
     '<p style="color:#E74C3C;font-size:16px;">Could not load the programmes of ${REF}.</p>'),
    ('<button class="btn btn-primary" onclick="trocarIes()">Escolher outra instituição</button>',
     '<button class="btn btn-primary" onclick="trocarIes()">Choose another institution</button>'),
    ("`Carregando dados da área ${slug}...`", "`Loading data for field ${slug}...`"),
    ("`Área desconhecida: ${slug}`", "`Unknown field: ${slug}`"),
    ("'Selecione uma Área CAPES e um Programa para iniciar a análise.'",
     "'Select a CAPES field and a programme to start the analysis.'"),
    ("'Selecione uma área primeiro.'", "'Select a field first.'"),
    ("'Carregue uma área primeiro.'", "'Load a field first.'", 2),

    # --------------------------------------- programas aprovados sem nota
    ("${n} programa${n > 1 ? 's' : ''} da ${refSigla()} ainda sem nota da CAPES</p>",
     "${n} ${refSigla()} programme${n > 1 ? 's' : ''} still without a CAPES grade</p>"),
    ("Aprovado${n > 1 ? 's' : ''} pela CAPES e ainda não avaliado${n > 1 ? 's' : ''} — o catálogo "
     "traz a marca\n            de programa aprovado no lugar da nota. Aparece${n > 1 ? 'm' : ''} "
     "aqui para constar,\n            mas fica${n > 1 ? 'm' : ''} fora de médias, rankings e "
     "gráficos, porque toda a comparação\n            do MAPA-PG se apoia na nota.</p>",
     "Approved by CAPES and not yet assessed — the catalogue carries the\n            "
     "approved-programme mark in place of a grade. ${n > 1 ? 'They appear' : 'It appears'} here "
     "for the record,\n            but ${n > 1 ? 'stay' : 'stays'} out of means, rankings and "
     "charts, because every comparison\n            in MAPA-PG rests on the grade.</p>"),

    # ------------------------------------------------ seletor de instituicao
    ("`Digite acima para buscar entre as <strong>${IES_IDX.n_ies}</strong> instituições.`",
     "`Type above to search among <strong>${IES_IDX.n_ies}</strong> institutions.`"),
    ("`<strong>${lista.length}</strong> instituição(ões) para “${esc(termo.trim())}”`",
     "`<strong>${lista.length}</strong> institution(s) for “${esc(termo.trim())}”`"),
    ("`Nenhuma instituição para “${esc(termo.trim())}”. Tente a sigla ou parte do nome.`",
     "`No institution matches “${esc(termo.trim())}”. Try the acronym or part of the name.`"),
    ('placeholder="Buscar por sigla ou nome — ex.: FIO CRUZ, UFPB, federal do pará"',
     'placeholder="Search by acronym or name — e.g. FIO CRUZ, UFPB, federal do pará"'),

    # ------------------------------------------------ rotulos de producao
    ("const SUBTIPO_LABELS = { '25': 'Art. Periódico', '8': 'Resumo', '9': 'Trab. Congresso', "
     "'26': 'Cap. Livro', '10': 'Texto Jornal' };",
     "const SUBTIPO_LABELS = { '25': 'Journal art.', '8': 'Abstract', '9': 'Conf. paper', "
     "'26': 'Book chap.', '10': 'Newspaper' };"),
    ("const stLabels = { '25': 'Art. Periódico', '8': 'Resumo', '9': 'Trab. Congresso', "
     "'26': 'Cap. Livro', '10': 'Texto Jornal' };",
     "const stLabels = { '25': 'Journal art.', '8': 'Abstract', '9': 'Conf. paper', "
     "'26': 'Book chap.', '10': 'Newspaper' };"),
    ('<div class="label">Média Nacional (Todas as Áreas)</div>',
     '<div class="label">National mean (all fields)</div>'),
    ("Contagem total de produções no(s) quadriênio(s) selecionado(s). Tipos ativos destacados "
     "com borda colorida.</p>",
     "Total output count in the selected cycle(s). Active types are marked with a coloured "
     "border.</p>"),
]

# --------------------------------------- painel de analise, graficos e ranking
INDEX += [
    ('<div class="label">Selecionados — IF Médio</div>',
     '<div class="label">Selected — mean IF</div>'),
    ('<div class="label">Selecionados — IF Mediana</div>',
     '<div class="label">Selected — median IF</div>'),
    ("Estratos A1–A8/C por percentil de <strong>${IF_BASE_LABEL[IF_BASE]}</strong> dentro da área.",
     "A1–A8/C strata by <strong>${IF_BASE_LABEL[IF_BASE]}</strong> percentile within the field."),
    ("'Fonte: CiteScore 2025 — Scopus® (Elsevier), indicador oficial CAPES 2025–2028; dados via "
     "API Scopus (api.elsevier.com), jul/2026 — ver Ajuda.'",
     "'Source: CiteScore 2025 — Scopus® (Elsevier), the indicator CAPES prescribes for 2025–2028; "
     "data via the Scopus API (api.elsevier.com), July 2026 — see Help.'"),
    ("'Fonte: OpenAlex.org (IF de 2 anos, CC0).'",
     "'Source: OpenAlex.org (2-year impact factor, CC0).'"),
    ("'Fonte: CiteScore — Scopus® (Elsevier) onde disponível; OpenAlex onde ausente — ver Ajuda.'",
     "'Source: CiteScore — Scopus® (Elsevier) where available; OpenAlex where missing — see Help.'"),

    ('<div class="card"><h2>Comparativo por Quadriênio — ${metricaLabel}</h2>',
     '<div class="card"><h2>Comparison by four-year cycle — ${metricaLabel}</h2>'),
    ("'<br><em style=\"color:var(--laranja);\">Nota: para esta métrica, a análise ano a ano "
     "utiliza Art/ano Média Geral.</em>'",
     "'<br><em style=\"color:var(--laranja);\">Note: for this metric, the year-by-year analysis "
     "uses articles/year, overall mean.</em>'"),
    ("nYrs === 12 ? '12 Anos' : `${nYrs} Anos`", "nYrs === 12 ? '12 years' : `${nYrs} years`"),
    ('<div class="card"><h2 class="unb">Produção Dinâmica — Médias Ano a Ano por Pesquisador '
     '(${metricaLabel})</h2>',
     '<div class="card"><h2 class="unb">Output over time — year-by-year means per researcher '
     '(${metricaLabel})</h2>'),
    ("Análise dinâmica: produção intelectual média por pesquisador, ano a ano, para cada programa "
     "selecionado. Passe o mouse sobre os pontos do gráfico para ver nota, nº de pesquisadores e "
     "média naquele ano. ${refSigla()} e média nacional destacados.${mIdxNote}</p>",
     "Mean research output per researcher, year by year, for each selected programme. Hover over "
     "the points to see the grade, the number of researchers and the mean in that year. "
     "${refSigla()} and the national mean are highlighted.${mIdxNote}</p>"),
    ('<div class="label">${refSigla()} — Média Geral ${yrsLabel}</div>',
     '<div class="label">${refSigla()} — overall mean, ${yrsLabel}</div>'),
    ('<div class="label">Média ${areaShort()} ${yrsLabel}</div>',
     '<div class="label">${areaShort()} mean, ${yrsLabel}</div>'),
    ('<div class="label">Programas Analisados</div>',
     '<div class="label">Programmes analysed</div>'),
    ('<div class="label">Média Nacional (Todas as Áreas) ${yrsLabel}</div>',
     '<div class="label">National mean, all fields, ${yrsLabel}</div>'),

    ("`Melhores programas por estado — ${CURRENT_AREA_NAME}`",
     "`Best programmes by state — ${CURRENT_AREA_NAME}`"),
    ("`TOP ${picks.length} nacional — programas mais bem avaliados — ${CURRENT_AREA_NAME}`",
     "`TOP ${picks.length} nationwide — best rated programmes — ${CURRENT_AREA_NAME}`"),
    ("'quadriênio mais recente de cada programa'", "'most recent cycle of each programme'"),
    ("const notaTxt = 'todas as notas';", "const notaTxt = 'all grades';"),
    ("btn('uf',  false, '🗺️ Melhores por UF')", "btn('uf',  false, '🗺️ Best per state')"),
    ("btn('nac', false, '🏆 Top melhores N')", "btn('nac', false, '🏆 Top N')"),
    ('onclick="exportarRankingCSV()" style="margin-left:8px;display:inline-block;width:auto;">'
     'Baixar .csv</button>',
     'onclick="exportarRankingCSV()" style="margin-left:8px;display:inline-block;width:auto;">'
     'Download .csv</button>'),
    ("${picks.length} de ${pool.length} programa(s) no recorte · ordenado por "
     "<strong>${metricaLabel}</strong> (${worst?'menores primeiro':'maiores primeiro'})\n"
     "            <br>Filtros: ${notaTxt} · ${quadTxt} · ${regTxt} · IES: ${getIESLabel(filters)}",
     "${picks.length} of ${pool.length} programme(s) in the selection · ordered by "
     "<strong>${metricaLabel}</strong> (${worst?'menores primeiro':'maiores primeiro'})\n"
     "            <br>Filters: ${notaTxt} · ${quadTxt} · ${regTxt} · institutions: ${getIESLabel(filters)}"),
    ("${worst?'menores primeiro':'maiores primeiro'})", "${worst?'lowest first':'highest first'})"),
    ("'<br><span style=\"color:#E65100;\">Filtros de tipo/estrato ativos — a métrica reflete o "
     "recorte.</span>'",
     "'<br><span style=\"color:#E65100;\">Type/stratum filters are on — the metric reflects the "
     "selection.</span>'"),
    ('<p style="color:var(--vermelho);">Nenhum programa com a métrica disponível nos filtros '
     'atuais.</p>',
     '<p style="color:var(--vermelho);">No programme has this metric available under the current '
     'filters.</p>'),

    # --------------------------------------------- relatorio detalhado de IF
    ("toast('Nenhum programa selecionado para o relatório de IF.')",
     "toast('No programme selected for the impact report.')"),
    ("'Página ' + n + '/2 — ' + (n === 1 ? 'Detalhamento numérico' : 'Gráficos comparativos')",
     "'Page ' + n + '/2 — ' + (n === 1 ? 'The numbers' : 'Comparative charts')"),
    (">Ver gráficos →</button>", ">See charts →</button>"),
    ("n === 1 ? 'Ver gráficos →' : '← Ver detalhamento numérico'",
     "n === 1 ? 'See charts →' : '← Back to the numbers'"),
    ('<div class="sep">Artigos por Estrato CAPES (A1 = topo \\u00b7 C = sem IF)</div>',
     '<div class="sep">Articles by CAPES stratum (A1 = top \\u00b7 C = no indicator)</div>'),
    ('<p class="note">Cada programa tem 9 barras, uma por estrato CAPES (A1 = topo \u00b7 '
     'C = sem indicador). ${refSigla()} destacada com \u2605.</p>',
     '<p class="note">Each programme has 9 bars, one per CAPES stratum (A1 = top \u00b7 '
     'C = no indicator). ${refSigla()} marked with \u2605.</p>'),
    ("Base do indicador: <strong>${IF_BASE_LABEL[IF_BASE]}</strong> — ${(EST.fonte) || "
     "'estratos por percentil dentro da área'}",
     "Indicator base: <strong>${IF_BASE_LABEL[IF_BASE]}</strong> — ${(EST.fonte) || "
     "'strata by percentile within the field'}"),
    ("toast('Nenhum gráfico para exportar.')", "toast('No chart to export.')"),
    ("toast(`${canvases.length} gráfico(s) exportado(s) como PNG`)",
     "toast(`${canvases.length} chart(s) exported as PNG`)"),
]

# ------------------------------------- metricas, relatorio TXT, bolsas e patentes
INDEX += [
    # rotulos de metrica (usados em graficos, tabelas e relatorio)
    ("'ma_pq': 'Art/ano Bolsistas PQ',", "'ma_pq': 'Articles/yr PQ fellows',"),
    ("'ma_spq': 'Art/ano Sem PQ',", "'ma_spq': 'Articles/yr non-PQ',"),
    ("'ma_all': 'Art/ano Média Geral',", "'ma_all': 'Articles/yr overall',"),
    ("'ma_perm': 'Art/ano Permanentes',", "'ma_perm': 'Articles/yr permanent',", 2),
    ("'ma_colab': 'Art/ano Colaboradores',", "'ma_colab': 'Articles/yr collaborating',", 2),
    ("'ma_visit': 'Art/ano Visitantes',", "'ma_visit': 'Articles/yr visiting',", 2),
    ("'avg_if': 'IF Médio (OpenAlex 2yr)',", "'avg_if': 'Mean IF (OpenAlex 2yr)',"),
    ("`Curso (${rs}) — referência`", "`Programme (${rs}) — reference`"),

    # relatorio TXT
    ("p(`  UNIVERSIDADE DE REFERÊNCIA: ${REF_NOME} (${refSigla()}${REF_UF ? '/' + REF_UF : ''})`)",
     "p(`  REFERENCE UNIVERSITY: ${REF_NOME} (${refSigla()}${REF_UF ? '/' + REF_UF : ''})`)"),
    ("p('  Todos os indicadores e marcações ★ abaixo referem-se a esta universidade.')",
     "p('  Every indicator and ★ mark below refers to this university.')"),
    ("p('  FILTROS APLICADOS:')", "p('  FILTERS APPLIED:')"),
    ("p(`    Notas: ${filters.notas.join(', ')}`)", "p(`    Grades: ${filters.notas.join(', ')}`)"),
    ("p(`    Quadriênio: ${filters.quad === 'all' ? 'Todos' : filters.quad}`)",
     "p(`    Cycle: ${filters.quad === 'all' ? 'All' : filters.quad}`)"),
    ("p(`    Métrica: ${metricaLabel}`)", "p(`    Metric: ${metricaLabel}`)"),
    ("p(`    Tipos de Produção: ${getSubtipoLabel(subtipos)}`)",
     "p(`    Output types: ${getSubtipoLabel(subtipos)}`)"),
    ("'Todos (A1-A8,C)'", "'All (A1-A8,C)'"),
    ("p(`    Estratos CAPES: ", "p(`    CAPES strata: "),
    ("p(`    Região: ${getRegiaoLabel(filters)}`)", "p(`    Region: ${getRegiaoLabel(filters)}`)"),
    ("p(`    IES selecionadas: ${getIESLabel(filters)}`)",
     "p(`    Institutions selected: ${getIESLabel(filters)}`)"),
    # rotulos do recorte (regiao, IES e a linha unica usada em grafico e PNG)
    ("    if (r.length === 0) return 'Nenhuma região selecionada';",
     "    if (r.length === 0) return 'No region selected';"),
    ("return r.length >= TOTAL_REGIOES ? 'Todas as regiões' : r.join(', ');",
     "return r.length >= TOTAL_REGIOES ? 'All regions' : r.join(', ');"),
    ("return n >= tot ? `todas as ${tot}` : `${n} de ${tot}`;",
     "return n >= tot ? `all ${tot}` : `${n} of ${tot}`;"),
    ("const notas = filters.notas.length === 5 ? 'todas as notas' : 'notas ' + filters.notas.join(', ');",
     "const notas = filters.notas.length === 5 ? 'all grades' : 'grades ' + filters.notas.join(', ');"),
    ("const quad = filters.quad === 'all' ? 'todos os quadriênios' : filters.quad;",
     "const quad = filters.quad === 'all' ? 'all cycles' : filters.quad;"),
    ("return `${notas} · ${quad} · ${getRegiaoLabel(filters)} · IES: ${getIESLabel(filters)}`;",
     "return `${notas} · ${quad} · ${getRegiaoLabel(filters)} · institutions: ${getIESLabel(filters)}`;"),
    ('margin:-4px 0 8px;">Recorte: ${getRecorteLabel(filters)}</p>',
     'margin:-4px 0 8px;">Selection: ${getRecorteLabel(filters)}</p>', 3),
    ("ctx.fillText('Recorte: ' + getRecorteLabel(getFilters()), 10, h + 34);",
     "ctx.fillText('Selection: ' + getRecorteLabel(getFilters()), 10, h + 34);"),
    ("ctx.fillText(`Recorte: ${getRecorteLabel(getFilters())}`, 10, h + 34);",
     "ctx.fillText(`Selection: ${getRecorteLabel(getFilters())}`, 10, h + 34);"),
    # rodape do CSV
    ("csv += `# Filtros: Notas=${filters.notas.join(',')} | Quadriênio=${filters.quad === 'all' ? 'Todos' : filters.quad} | ` +",
     "csv += `# Filters: Grades=${filters.notas.join(',')} | Cycle=${filters.quad === 'all' ? 'All' : filters.quad} | ` +"),
    ("`Região=${getRegiaoLabel(filters)} | IES=${getIESLabel(filters)} | ` +",
     "`Region=${getRegiaoLabel(filters)} | Institutions=${getIESLabel(filters)} | ` +"),
    ("`Tipos=${getSubtipoLabel(subtipos)} | Estratos IF=${estratos_if.join(',')}\\n`;",
     "`Types=${getSubtipoLabel(subtipos)} | IF strata=${estratos_if.join(',')}\\n`;"),
    ("p(`  PROGRAMA — ${getRefName().toUpperCase()}`)",
     "p(`  PROGRAMME — ${getRefName().toUpperCase()}`)"),
    ("p('  COMPARATIVO GERAL')", "p('  OVERALL COMPARISON')"),
    ("p(`  Média selecionados: ${othersAvg.toFixed(2)}`)",
     "p(`  Mean of selected: ${othersAvg.toFixed(2)}`)"),
    ("p(`  Diferença: ", "p(`  Difference: "),
    ("p(`  ${refSigla()} está ${diff >= 0 ? 'ACIMA' : 'ABAIXO'} da média dos programas "
     "selecionados.`)",
     "p(`  ${refSigla()} is ${diff >= 0 ? 'ABOVE' : 'BELOW'} the mean of the selected "
     "programmes.`)"),
    ("return `  Média Nacional: ${val} ${metricaLabel}`",
     "return `  National mean: ${val} ${metricaLabel}`"),

    # bolsas
    ("['DO', 'Doutorado', '#4A148C'], ['PD', 'Pós-doutorado', '#CE93D8']]",
     "['DO', 'Doctorate', '#4A148C'], ['PD', 'Postdoc', '#CE93D8']]"),
    ('<div class="card"><h2>Programa de referência</h2>',
     '<div class="card"><h2>Reference programme</h2>'),
    ('<button class="btn csv" onclick="exportarBolsasCSV()">⬇ CSV da série completa</button>',
     '<button class="btn csv" onclick="exportarBolsasCSV()">⬇ CSV of the full series</button>'),
    ('<div class="card"><h2>O que esta série é, e o que ela não é</h2>',
     '<div class="card"><h2>What this series is, and what it is not</h2>'),

    # patentes
    ("`sem patentes declaradas em ${quad} nesta área`",
     "`no patents reported in ${quad} for this field`"),
    ("toast('Esta área não tem patentes declaradas em nenhum quadriênio.')",
     "toast('This field has no patents reported in any cycle.')"),
    ('<div class="l">Declarações<br>de patente</div>',
     '<div class="l">Patent<br>declarations</div>'),
    ('<div class="l">Patentes distintas<br>não apurável</div>',
     '<div class="l">Distinct patents<br>not determinable</div>'),
    ('<div class="l">dos ${nProgArea}<br>programas da área</div>',
     '<div class="l">of the ${nProgArea}<br>programmes in the field</div>'),
    ("<div class=\"l\">do total nacional<br>${semDedup ? 'de declarações' : 'de distintas'}</div>",
     "<div class=\"l\">of the national total<br>${semDedup ? 'de declarações' : 'de distintas'}</div>"),
    ("${semDedup ? 'de declarações' : 'de distintas'}</div>",
     "${semDedup ? 'of declarations' : 'of distinct patents'}</div>"),
    ("<div class=\"l\">${semDedup ? 'Declarações' : 'Patentes distintas'}<br>no país</div>",
     "<div class=\"l\">${semDedup ? 'Declarations' : 'Distinct patents'}<br>nationwide</div>"),
    ('<div class="l">com descrição<br>declarada</div>',
     '<div class="l">with a reported<br>description</div>'),
    ('<div class="l">com data<br>de concessão</div>',
     '<div class="l">with a grant<br>date</div>'),
    ('<div class="card"><h2>${escHTML(getRefName())} nesta área</h2>',
     '<div class="card"><h2>${escHTML(getRefName())} in this field</h2>', 2),
    ('<div class="card"><h2>Programas da área por número de patentes — ${md.quadrienio}</h2>',
     '<div class="card"><h2>Programmes in the field by number of patents — ${md.quadrienio}</h2>'),
    ('placeholder="palavra no título ou na descrição (ex.: sensor, vacina, biodiesel)"',
     'placeholder="a word in the title or description (e.g. sensor, vacina, biodiesel)"'),
    ("'<i style=\"color:#B0BEC5;\">não coletado</i>'",
     "'<i style=\"color:#B0BEC5;\">not collected</i>'"),
    ("`${md.area} — ${md.quadrienio} — ${nDecl} declarações`",
     "`${md.area} — ${md.quadrienio} — ${nDecl} declarations`"),
    ("<div class=\"t\">${escHTML(p.tit || '(título não declarado)')}</div>",
     "<div class=\"t\">${escHTML(p.tit || '(title not reported)')}</div>"),
    ('`<div class="semr">descrição não declarada à CAPES</div>`',
     '`<div class="semr">description not reported to CAPES</div>`'),
]

# ----------------------------- blocos de prosa (chaves extraidas do proprio
# arquivo pelo utilitario de blocos: exatas por construcao)
INDEX += [
    ('<h2 style="border:none;font-size:18px;color:var(--azul);">Selecione uma Área CAPES e um Programa</h2>',
     '<h2 style="border:none;font-size:18px;color:var(--azul);">Select a CAPES field and a programme</h2>'),
    ('<strong style="font-size:12px;color:#922B21;">Atenção — 2021-2024 só tem Artigo em Periódico:</strong>',
     '<strong style="font-size:12px;color:#922B21;">Careful — 2021-2024 has journal articles only:</strong>'),
    ('<h2>Produção por Categoria de Docente</h2>',
     '<h2>Output by faculty category</h2>'),
    ('<h2>Produção por Estrato de IF — Barras Agrupadas (Art/Docente)</h2>',
     '<h2>Output by impact stratum — grouped bars (articles/faculty member)</h2>'),
    ('<h2>Perfil de Produção por Estrato de IF — Multi-Linhas (Art/Docente)</h2>',
     '<h2>Output profile by impact stratum — multi-line (articles/faculty member)</h2>'),
    ('<h2>3 IES Mais Próximas da ${refSigla()} — Comparação por Estrato de IF</h2>',
     '<h2>The 3 institutions closest to ${refSigla()} — comparison by impact stratum</h2>'),
    ('<h2>Programas da área em ${anoTab}</h2>',
     '<h2>Programmes in the field in ${anoTab}</h2>'),
    ('Nenhum programa da <b>${refSigla()}</b> está selecionado nesta área,\n            então não há série individual a mostrar. A comparação da área, abaixo, continua valendo.</p>',
     'No <b>${refSigla()}</b> programme is selected in this field,\n             so there is no individual series to show. The field-wide comparison below still stands.</p>'),
    ('Este programa tem bolsas na série, mas não há contagem de alunos para\n                   nenhum dos anos no conjunto de discentes da CAPES, então a razão não pode\n                   ser calculada. As outras medidas continuam disponíveis nos botões acima.',
     'This programme has scholarships in the series, but there is no student count\n                for any of the years in the CAPES student dataset, so the ratio cannot be computed.\n                The other measures remain available in the buttons above.'),
    ('<div class="l">alunos com bolsa<br>em ${ultimo}</div>',
     '<div class="l">students with a scholarship<br>in ${ultimo}</div>'),
    ('<div class="l">pós-doutorado<br>(não é aluno)</div>',
     '<div class="l">postdocs<br>(not students)</div>'),
    ('<div class="l">bolsas-equivalentes<br>de aluno em ${ultimo}</div>',
     '<div class="l">student scholarship-equivalents<br>in ${ultimo}</div>'),
    ('A linha tracejada é a <b>mediana da área</b> no mesmo ano, entre os\n            programas que tinham alguma bolsa — serve para separar o que é movimento do programa\n            do que é movimento de todo mundo.<br>\n            A contagem do ano é <b>fluxo, não foto de um mês</b>: entra quem teve bolsa em\n            qualquer parte do ano, e a maioria não fica os doze meses. Por isso',
     'The dashed line is the <b>field median</b> in the same year, among the\n            programmes that had any scholarship — it separates what is a move by this programme\n            from what is a move by everyone.<br>\n            The yearly count is a <b>flow, not a snapshot of one month</b>: anyone who held a\n            scholarship at any point in the year is counted, and most do not hold it for twelve months. Hence'),
    ('A contagem de patentes de cada programa muda com o\n        quadriênio — são coletas distintas da CAPES, com campos e cobertura\n        diferentes. Ver "Como ler estes dados", ao final.</p>',
     'The patent count of each programme changes with the\n         cycle — these are separate CAPES collections, with different fields and coverage.\n         See "How to read these data", at the end.</p>'),
    ('A coleta ${md.quadrienio} <b>não publica o número de registro</b> da patente,\n           então não há como saber quantas declarações são a mesma patente declarada por\n           programas coautores. Por isso só se conta declarações aqui — o número de\n           patentes distintas <b>não é apurável</b> nesta base.',
     "The ${md.quadrienio} collection <b>does not publish the patent's registration number</b>,\n             so there is no way to know how many declarations are the same patent reported by\n             co-authoring programmes. Only declarations are counted here — the number of distinct\n             patents <b>cannot be determined</b> in this base."),
    ('A diferença entre <b>declarações</b> e <b>patentes distintas</b> é coautoria:\n           a mesma patente é declarada por cada programa que participou dela.',
     'The difference between <b>declarations</b> and <b>distinct patents</b> is co-authorship:\n             the same patent is reported by each programme that took part in it.'),
    ('Nenhuma patente declarada por programa de ${escHTML(refSigla())}\n            nesta área no quadriênio ${md.quadrienio}.</p>',
     'No patent reported by any ${escHTML(refSigla())} programme\n             in this field in the ${md.quadrienio} cycle.</p>'),
    ('<th class="l">Quadriênio</th><th>Título</th>\n        <th>Nº de registro</th><th>Data de depósito</th><th>Descrição</th>\n        <th>Estágio</th><th>Data de concessão</th><th>Deduplicação</th></tr>',
     '<th class="l">Cycle</th><th>Title</th>\n        <th>Registration no.</th><th>Filing date</th><th>Description</th>\n        <th>Stage</th><th>Grant date</th><th>Deduplication</th></tr>'),
    ('<b>A cobertura muda a cada quadriênio</b> — são coletas distintas,\n    com formulários distintos. Percentuais nacionais de preenchimento, sobre o total de\n    declarações de patente de cada coleta (a linha destacada é a que está em exibição):</p>',
     '<b>Coverage changes with every cycle</b> — these are separate collections,\n     with different forms. National completion rates, over the total patent declarations of each\n     collection (the highlighted row is the one on display):</p>'),
    ('<b>Nº de registro e deduplicação.</b> É o número do depósito (BR…, PI…, MU…) que\n    permite reconhecer a mesma patente declarada por programas coautores. Em\n    <b>2017-2020 o campo não existe na base da CAPES</b>: naquele quadriênio só se pode\n    contar declarações, e nenhum total de',
     '<b>Registration number and deduplication.</b> This is the filing number (BR…, PI…, MU…) that\n     makes it possible to recognise the same patent reported by co-authoring programmes. In\n     <b>2017-2020 the field does not exist in the CAPES base</b>: in that cycle only declarations can\n     be counted, and no total of'),
]

INDEX += [
    (' a coleta da CAPES desse quadriênio não\n            inclui ${nomes}. Os valores de 2021-2024 aparecem como zero para esses tipos por\n            <em>ausência de dado</em>, não por queda de produção. Para comparar os três\n            quadriênios, deixe marcado apenas <strong>Artigo em Periódico</strong>.</span>',
     ' the CAPES collection for that cycle does not\n            include ${nomes}. The 2021-2024 values appear as zero for those types because the\n            <em>data are absent</em>, not because output fell. To compare the three\n            cycles, leave only <strong>Journal article</strong> ticked.</span>'),
    ('Este programa não tem nenhuma bolsa da CAPES registrada entre\n                   ${anos[0]} e ${ultimo} nos programas da Diretoria de Programas e Bolsas no País.\n                   Isso não quer dizer que ele não tenha bolsistas: bolsa de outra agência, de fundação\n                   estadual ou da própria instituição não entra nesta base.',
     'This programme has no CAPES scholarship on record between\n                   ${anos[0]} and ${ultimo} in the datasets of the CAPES scholarship directorate.\n                   That does not mean it has no funded students: a scholarship from another agency,\n                   from a state foundation or from the institution itself is not in this base.'),
]

# ------------------------------------------- modal de escolha da instituicao
INDEX += [
    ('<h2 style="color:#E91E63;margin:0 0 4px;font-size:20px;font-weight:800;text-align:center;">'
     'Escolha a instituição de referência</h2>',
     '<h2 style="color:#E91E63;margin:0 0 4px;font-size:20px;font-weight:800;text-align:center;">'
     'Choose the reference institution</h2>'),
    ("Ela será usada como referência — <span style=\"color:#E91E63;font-weight:700;\">destacada "
     "em vermelho</span> —\n            na comparação com todos os programas de cada área da "
     "CAPES. (Você pode trocar depois.)</p>",
     "It will be used as the reference — <span style=\"color:#E91E63;font-weight:700;\">"
     "highlighted in red</span> —\n            against every programme in each CAPES field. (You "
     "can change it later.)</p>"),
    ("A escolha <strong>não filtra a base</strong>: cada área continua mostrando todos os "
     "programas do país.\n            A instituição serve para destacar os programas dela e "
     "situá-los entre os pares.</p>",
     "The choice <strong>does not filter the data</strong>: each field still shows every "
     "programme in the country.\n            The institution serves to highlight its own "
     "programmes and place them among their peers.</p>"),
    ("`<strong>${lista.length} universidades federais</strong> — uma por UF. `",
     "`<strong>${lista.length} federal universities</strong> — one per state. `"),
    ("' — refine a busca para ver todas.'", "' — narrow the search to see them all.'"),
    ("const progs = `${i.np} prog${i.np === 1 ? '' : 's'}`;",
     "const progs = `${i.np} programme${i.np === 1 ? '' : 's'}`;"),
    ("return sn ? `${progs} · ${sn} sem nota` : progs;",
     "return sn ? `${progs} · ${sn} without a grade` : progs;"),
    ("` · ${sn} sem nota`", "` · ${sn} without a grade`"),
    ("new Option(`${p.nome} — aprovado, ainda sem nota`, '')",
     "new Option(`${p.nome} — approved, not yet graded`, '')"),
]


# ==========================================================================
# help-doc.html — so cabecalho e navegacao. O CORPO e traduzido secao a secao
# pelos arquivos de i18n/doc_en/ (ver secoes_de_documento no gerador): e texto
# longo, e fatiar prosa em centenas de pares seria ilegivel e quebradico.
# ==========================================================================
HELP_DOC = [
    ("<title>MAPA-PG — Documentação e Fontes de Dados</title>",
     "<title>MAPA-PG — Documentation and Data Sources</title>"),
    ("<h1><em>MAPA-PG</em> — Documentação</h1>", "<h1><em>MAPA-PG</em> — Documentation</h1>"),
    ("id=\"nav-sobre\">Sobre</a>", "id=\"nav-sobre\">About</a>"),
    ("id=\"nav-uso\">Como Usar</a>", "id=\"nav-uso\">How to use</a>"),
    ("id=\"nav-siglas\">Siglas e Programas</a>", "id=\"nav-siglas\">Acronyms and programmes</a>"),
    ("id=\"nav-patentes\">Patentes</a>", "id=\"nav-patentes\">Patents</a>"),
    ("id=\"nav-fontes\">Fontes de Dados e URLs</a>", "id=\"nav-fontes\">Data sources and URLs</a>"),
    ("id=\"nav-versoes\">Versões</a>", "id=\"nav-versoes\">Versions</a>"),
]

# ------------------------------------ ultimos rotulos do painel de analise
INDEX += [
    ('<div class="card"><h2>Fator de Impacto — OpenAlex (2yr mean citedness)</h2>',
     '<div class="card"><h2>Impact factor — OpenAlex (2-year mean citedness)</h2>'),
    ('<div class="card"><h2>Produção por Tipo de Publicação</h2>',
     '<div class="card"><h2>Output by publication type</h2>'),
    ('<div class="card"><h2>Comparativo por IES — ${metricaLabel}</h2>',
     '<div class="card"><h2>Comparison by institution — ${metricaLabel}</h2>'),
    ("<h2 class=\"unb\">Tabela Detalhada${!allSubsSelected ? ' — ' + subtipoLabel : ''}</h2>",
     "<h2 class=\"unb\">Detailed table${!allSubsSelected ? ' — ' + subtipoLabel : ''}</h2>"),
    ('<div class="label">Média Selecionados — ${metricaLabel}</div>',
     '<div class="label">Mean of selected — ${metricaLabel}</div>'),
    ('<div class="label">Programas</div>', '<div class="label">Programmes</div>'),
    ('<div class="label">Docentes</div>', '<div class="label">Faculty</div>'),
    ('<div class="label">${refSigla()} — Permanentes</div>',
     '<div class="label">${refSigla()} — permanent</div>'),
    ('<div class="label">${refSigla()} — Colaboradores</div>',
     '<div class="label">${refSigla()} — collaborating</div>'),
    ('<div class="label">${refSigla()} — Visitantes</div>',
     '<div class="label">${refSigla()} — visiting</div>'),
    ('<div class="label">${refSigla()} — Razão Perm/Colab</div>',
     '<div class="label">${refSigla()} — perm./collab. ratio</div>'),
    ('<div class="label">Selecionados — Permanentes</div>',
     '<div class="label">Selected — permanent</div>'),
    ('<div class="label">Selecionados — Colaboradores</div>',
     '<div class="label">Selected — collaborating</div>'),
    ('<div class="label">Selecionados — Razão Perm/Colab</div>',
     '<div class="label">Selected — perm./collab. ratio</div>'),
    # cabecalhos de tabela: abreviacoes, mantendo a largura das colunas
    ("<th>Nota</th>", "<th>Grade</th>", 5),
    ("<th>Quad</th>", "<th>Cycle</th>", 2),
    ("<th>Doc</th>", "<th>Fac.</th>", 2),
    ("<th>Perm</th>", "<th>Perm.</th>"),
    ("<th>Colab</th>", "<th>Collab.</th>"),
    ("<th>Razão</th>", "<th>Ratio</th>"),
    ("<th>A/a Perm</th>", "<th>A/y perm.</th>"),
    ("<th>A/a Colab</th>", "<th>A/y collab.</th>"),
    ("<th>Art/a PQ</th>", "<th>Art/y PQ</th>"),
    ("<th>Art/a sPQ</th>", "<th>Art/y non-PQ</th>"),
    ("<th>Art/a Ger</th>", "<th>Art/y overall</th>"),
    ("<th>Total Prod</th>", "<th>Total output</th>"),
]

INDEX += [
    ('<h2>Relatório</h2><div class="report-box" id="reportBox"></div>',
     '<h2>Report</h2><div class="report-box" id="reportBox"></div>'),
    ('onclick="downloadReport()">Baixar .txt</button>',
     'onclick="downloadReport()">Download .txt</button>'),
    ('onclick="downloadReportCSV()">Baixar .csv</button>',
     'onclick="downloadReportCSV()">Download .csv</button>'),
]

INDEX += [
    ("h.textContent = `Selecionar Programa ${rs}`", "h.textContent = `Select a ${rs} programme`"),
    ("filterDesc.push('Tipo: ' + subtipoLabel)", "filterDesc.push('Type: ' + subtipoLabel)"),
    ("filterDesc.push('Estratos: ' + estratos_if.join(', '))",
     "filterDesc.push('Strata: ' + estratos_if.join(', '))"),
    ('<strong style="font-size:12px;color:#E65100;">Filtros ativos:</strong>',
     '<strong style="font-size:12px;color:#E65100;">Active filters:</strong>'),
    ("Razão Perm/Colab: número de vezes que a produção do permanente supera a do colaborador "
     "(ex: 4.85x = permanente produz 4.85 vezes mais)</p>",
     "Perm./collab. ratio: how many times the output of a permanent faculty member exceeds that "
     "of a collaborating one (e.g. 4.85x = the permanent one produces 4.85 times as much)</p>"),
    ('<div class="label">${refSigla()} — IF Médio</div>',
     '<div class="label">${refSigla()} — mean IF</div>'),
    ('<div class="label">${refSigla()} — IF Mediana</div>',
     '<div class="label">${refSigla()} — median IF</div>'),
    ('<div class="label">${refSigla()} — IF Máximo</div>',
     '<div class="label">${refSigla()} — max IF</div>'),
    ('<div class="label">${refSigla()} — Arts c/ IF</div>',
     '<div class="label">${refSigla()} — articles with IF</div>'),
    ('<div class="label">Selecionados — ${stLabels[st]}</div>',
     '<div class="label">Selected — ${stLabels[st]}</div>'),
]

INDEX += [
    ("<h2>Patentes — Produção Técnica</h2>", "<h2>Patents — technical output</h2>"),
    ('<div class="card quad-card"><h2>Quadriênio</h2><div class="quadsel">',
     '<div class="card quad-card"><h2>Four-year cycle</h2><div class="quadsel">'),
    ("<h2>${escHTML(md.area)} — patentes ${md.quadrienio}</h2>",
     "<h2>${escHTML(md.area)} — patents ${md.quadrienio}</h2>"),
    ('<h2>Bolsas CAPES — série por ano</h2>', '<h2>CAPES scholarships — series by year</h2>'),
    ("<h2>Detalhamento de Fator de Impacto</h2>", "<h2>Impact factor in detail</h2>"),
    (">✕ Fechar</button>", ">✕ Close</button>", 3),
]

INDEX += [
    ('<span id="statusLeft">Aguardando dados...</span>',
     '<span id="statusLeft">Waiting for data...</span>'),
]

INDEX += [
    ('"alternateName": "Monitoramento e Análise de Produção Acadêmica da Pós-Graduação",',
     '"alternateName": "Monitoring and Analysis of Graduate Research Output",'),
    ('"name": "Grupo de Dinâmica e Ab Initio (GDAI), Núcleo de Estrutura da Matéria, Instituto de Física, Universidade de Brasília (UnB)"',
     '"name": "Dynamics and Ab Initio Group (GDAI), Matter Structure Centre, Institute of Physics, University of Brasilia (UnB)"'),
    ("'sem patente na área'",
     "'no patent in this field'"),
    ("${BOL_MED === 'r' ? 'a área inteira<br>em ' + anoTab : 'total da área<br>em ' + anoTab}",
     "${BOL_MED === 'r' ? 'the whole field<br>in ' + anoTab : 'field total<br>in ' + anoTab}"),
    ('`Percentual de alunos com bolsa em cada nível, separadamente. Mestrado e\n                   doutorado costumam ter coberturas bem diferentes, e a média dos dois\n                   esconde isso — é a diferença entre "metade do programa tem bolsa" e\n                   "quase todo doutorando tem, quase nenhum mestrando tem".`',
     '`Share of students with a scholarship at each level, separately. Master\'s and\n                   doctorate usually have very different coverage, and averaging the two\n                   hides it — it is the difference between "half the programme has a scholarship" and\n                   "nearly every doctoral student has one, nearly no master\'s student does".`'),
    ('`Mestrado, doutorado e pós-doutorado somados dão a série acima.\n                   A troca de composição costuma dizer mais que o total: perder doutorado e ganhar\n                   mestrado mantém a contagem e muda o programa.`',
     "`Master's, doctorate and postdoc together make the series above.\n                   A change of composition usually says more than the total: losing doctoral students and gaining\n                   master's ones keeps the count and changes the programme.`"),
]
