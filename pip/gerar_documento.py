#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o relatório METODOLOGIA + RESULTADOS + CONCLUSÕES da análise de produção
dos programas de pós-graduação (sistema MAPA-PG), em DOIS formatos:

  • saida/relatorio_mapa_pg_metodologia.html  — HTML5 self-contained com gráficos
    INTERATIVOS (Chart.js v4 inline): distribuição por retenção (4 coortes) e
    nº de docentes por ano-base. As 4 figuras de séries de quedas seguem como
    imagens estáticas (são figuras multi-painel pré-renderizadas).
  • saida/relatorio_mapa_pg_metodologia.pdf   — via LibreOffice, com os mesmos
    gráficos em versão ESTÁTICA (matplotlib), pois o conversor não roda JS.
"""
import os
import io
import json
import base64
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, 'saida')
DOCS = os.path.join(AQUI, '..', 'docs')
CHARTJS = os.path.join(DOCS, 'chart.umd.min.js')

# ── Dados das tabelas (também alimentam os gráficos) ───────────────────────
DIST = {
    'UnB acadêmicos (84)':        {'verde': 68,   'amarelo': 11,  'vermelho': 2,   'estrutural': 3},
    'UnB profissionais (13)':     {'verde': 9,    'amarelo': 0,   'vermelho': 1,   'estrutural': 3},
    'Brasil acadêmicos (3.866)':  {'verde': 2966, 'amarelo': 615, 'vermelho': 110, 'estrutural': 175},
    'Brasil profissionais (909)': {'verde': 642,  'amarelo': 150, 'vermelho': 41,  'estrutural': 76},
}
CLASSES = [('verde', '🟢 Verde', '#27AE60'), ('amarelo', '🟡 Amarelo', '#E1B12C'),
           ('vermelho', '🔴 Vermelho', '#C0392B'), ('estrutural', '⬛ Estrutural', '#566573')]
DOCENTES = {2013: 3568, 2014: 3765, 2015: 3946, 2016: 4186, 2017: 4347, 2018: 4363,
            2019: 4570, 2020: 4559, 2021: 4698, 2022: 0, 2023: 0, 2024: 0}

RODAPE_PERIODO = [
    'A NOTA de cada programa é a vigente (registro do quadriênio 2021-2024). A PRODUÇÃO, '
    'porém, é medida no quadriênio 2017-2020 — último período com coleta CAPES completa e confiável.',
    'Motivo: a coleta do quadriênio 2021-2024 ainda está em andamento na Plataforma Sucupira. '
    'Apenas ~1/3 dos artigos foi lançado (a mediana nacional cai de ~8 para ~3 artigos/docente/ano '
    'de 2020 para 2021, sem queda real de produtividade — é subnotificação).',
    'Além disso, a Avaliação Quadrienal 2021-2024 ainda não foi realizada pela CAPES (a de '
    '2017-2020 só saiu em 2022; a de 2021-2024 deve sair por volta de 2026-2027). As notas '
    'exibidas para 2021-2024 são o RESULTADO da avaliação de 2017-2020, carregado para frente.',
    'Logo, mede-se a produtividade no período fechado que de fato sustentou a nota vigente. '
    'Quando a CAPES consolidar 2021-2024, basta reprocessar com o novo período.',
]


def img64(nome, width_cm=15.0):
    """PNG existente em saida/ -> data URI, recarimbando o DPI p/ largura física."""
    p = os.path.join(SAIDA, nome)
    if not os.path.exists(p):
        return ''
    im = Image.open(p)
    dpi = im.width / (width_cm / 2.54)
    buf = io.BytesIO(); im.save(buf, format='PNG', dpi=(dpi, dpi))
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def _b64(fig, width_cm=16.0):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig); buf.seek(0)
    im = Image.open(buf)
    dpi = im.width / (width_cm / 2.54)
    out = io.BytesIO(); im.save(out, format='PNG', dpi=(dpi, dpi))
    return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()


# ── gráficos estáticos (PDF) ───────────────────────────────────────────────
def gerar_graficos():
    figs = {}
    cohorts = list(DIST.keys())
    fig, ax = plt.subplots(figsize=(8, 3.2))
    left = [0] * len(cohorts)
    for k, lbl, col in CLASSES:
        vals = [DIST[c][k] / sum(DIST[c].values()) * 100 for c in cohorts]
        ax.barh(cohorts, vals, left=left, color=col, label=lbl.split(' ', 1)[1])  # sem emoji (fonte matplotlib)
        left = [a + b for a, b in zip(left, vals)]
    ax.set_xlim(0, 100); ax.set_xlabel('% dos programas'); ax.invert_yaxis()
    ax.set_title('Distribuição por retenção de produção (2021-24 / 2017-20)', fontsize=11)
    ax.legend(fontsize=7.5, ncol=4, loc='lower center', bbox_to_anchor=(0.5, -0.38))
    ax.tick_params(axis='y', labelsize=8)
    figs['dist'] = _b64(fig)

    anos = [str(a) for a in DOCENTES]; vals = list(DOCENTES.values())
    cores = ['#5DADE2' if v > 0 else '#C0392B' for v in vals]
    fig, ax = plt.subplots(figsize=(8, 3.0))
    ax.bar(anos, vals, color=cores)
    ax.set_ylabel('programas c/ docentes')
    ax.set_title('Programas com nº de docentes lançado, por ano-base', fontsize=11)
    ax.grid(axis='y', alpha=.3)
    figs['doc'] = _b64(fig)
    return figs


# ── dados p/ Chart.js (HTML5) ──────────────────────────────────────────────
def chart_data():
    cohorts = list(DIST.keys())
    datasets = []
    for k, lbl, col in CLASSES:
        datasets.append({'label': lbl, 'color': col,
                         'pct': [round(DIST[c][k] / sum(DIST[c].values()) * 100, 1) for c in cohorts],
                         'cnt': [DIST[c][k] for c in cohorts]})
    return {'dist': {'cohorts': cohorts, 'datasets': datasets},
            'doc': {'anos': [str(a) for a in DOCENTES], 'vals': list(DOCENTES.values())}}


CSS = """
@page { size: A4; margin: 2.0cm 1.8cm; }
body { font-family:'Liberation Serif','Times New Roman',serif; font-size:11pt; color:#222; line-height:1.42; }
h1 { font-size:20pt; color:#1A2A3A; margin:0 0 2pt 0; }
h2 { font-size:14pt; color:#1F618D; border-bottom:2px solid #AED6F1; padding-bottom:2px; margin-top:20px; }
h3 { font-size:12pt; color:#2C3E50; margin-top:14px; margin-bottom:4px; }
.sub { color:#666; font-size:10.5pt; margin:0 0 4px 0; }
.meta { color:#888; font-size:9.5pt; margin-bottom:14px; }
p { margin:6px 0; text-align:justify; }
table { border-collapse:collapse; width:100%; margin:8px 0; font-size:10pt; }
th { background:#2C3E50; color:#fff; padding:5px 7px; text-align:center; }
td { border:1px solid #ccc; padding:4px 7px; text-align:center; }
td.l { text-align:left; }
.g { color:#1E8449; font-weight:bold; } .y { color:#9A7D0A; font-weight:bold; }
.r { color:#C0392B; font-weight:bold; } .k { color:#566573; font-weight:bold; }
.box { background:#Fef9e7; border-left:4px solid #F1C40F; padding:8px 12px; margin:10px 0; }
.boxr { background:#FDEDEC; border-left:4px solid #E74C3C; padding:8px 12px; margin:10px 0; }
figure { margin:10px 0 4px 0; text-align:center; page-break-inside:avoid; }
figure img { width:15cm; max-width:100%; height:auto; border:1px solid #ddd; display:block; margin:0 auto; }
.chartbox { position:relative; margin:12px 0 2px; }
p.cap { font-size:9.5pt; color:#555; margin:3px 0 0 0; font-style:italic; text-align:center; clear:both; }
.foot { font-size:9pt; color:#555; } .foot li { margin-bottom:4px; }
.pb { page-break-before:always; }
ul { margin:6px 0; } li { margin:3px 0; }
"""
CSS_SCREEN = "body{max-width:1000px;margin:0 auto;padding:10px 18px;background:#fff;}"
CANVAS = {'dist': ('cDist', 360), 'doc': ('cDoc', 320)}


def chart_el(mode, key, cap, figs):
    if mode == 'pdf':
        return f'<figure><img src="{figs[key]}"/><p class="cap">{cap}</p></figure>'
    cid, h = CANVAS[key]
    return (f'<div class="chartbox" style="height:{h}px"><canvas id="{cid}"></canvas></div>'
            f'<p class="cap">{cap}</p>')


def build_body(mode, figs):
    rodape = ''.join(f'<li>{t}</li>' for t in RODAPE_PERIODO)
    ce = lambda k, cap: chart_el(mode, k, cap, figs)
    fig_unb = img64('quedas_criticas.png')
    fig_unb_prof = img64('quedas_criticas_profissional.png')
    fig_nac = img64('quedas_criticas_nacional.png')
    fig_nac_prof = img64('quedas_criticas_nacional_profissional.png')
    return f"""
<h1>Produção dos Programas de Pós-Graduação — 2013-2024</h1>
<p class="sub">Metodologia, Resultados e Conclusões · Sistema <b>MAPA-PG</b> · recálculo a partir dos
dados abertos da CAPES</p>
<p class="meta">UnB e panorama nacional · três quadriênios CAPES (2013-2016, 2017-2020, 2021-2024)</p>

<h2>1. Introdução</h2>
<p>O sistema <b>MAPA-PG</b> analisou a produção bibliográfica (artigos em periódico) dos programas de
pós-graduação no período <b>2013-2024</b>, abrangendo os três quadriênios de avaliação da CAPES
(2013-2016, 2017-2020 e 2021-2024), a partir dos <i>datasets</i> dos Dados Abertos da CAPES.</p>
<p>A análise foi conduzida separadamente para as duas modalidades de programa — <b>acadêmica</b> e
<b>profissional</b> — porque os critérios de avaliação e o perfil de produção diferem entre elas.
O universo analisado:</p>
<table>
<tr><th>Âmbito</th><th>Acadêmicos</th><th>Profissionais</th><th>Total</th><th>IES</th></tr>
<tr><td class="l"><b>UnB</b></td><td>84</td><td>13</td><td>97</td><td>1</td></tr>
<tr><td class="l"><b>Brasil (nacional)</b></td><td>3.866</td><td>909</td><td>4.775</td><td>~530</td></tr>
</table>
<p>Para cada programa foi reconstruída a série anual de artigos de 2013 a 2024 e medida a evolução
da produção, com destaque para o quadriênio vigente (2021-2024).</p>

<h2>2. Metodologia</h2>

<h3>2.1 Fonte e sinal de produção</h3>
<p>Foram usados os <b>dados brutos</b> da CAPES (Dados Abertos): cadastro de programas, corpo
docente e produção intelectual. O <b>sinal de produção</b> adotado é o <b>número de artigos
distintos em periódico</b> (campo <code>ID_ADD_PRODUCAO_INTELECTUAL</code>, da base
<code>prod_intel_artpe</code>) por programa e por ano. Esse sinal cobre 2013-2024 e <b>não depende</b>
nem do vínculo autor-artigo nem do cadastro de docentes — por isso é imune aos artefatos descritos
adiante.</p>

<h3>2.2 Por que recalcular a partir dos dados brutos</h3>
<p>A camada pré-processada original credita um artigo ao programa apenas quando o docente-autor
consta do <b>cadastro de docentes de 2021</b>. Como esse é o único ano de docentes do quadriênio
atual, grande parte da produção de 2021-2024 é descartada, gerando uma <b>falsa queda</b>. Exemplo
verificado: o programa de Antropologia da UnB tem 128 artigos em 2021, mas só 34 mapeiam ao cadastro
de 2021 — o pré-processamento aparentava uma queda de 92% que <b>não é real</b> (produção estável:
128/122/104/95 artigos/ano). O recálculo pelo sinal limpo elimina esse viés.</p>

<h3>2.3 Ressalva — número de docentes só existe em 2021</h3>
<div class="boxr">
<p style="margin-top:0"><b>Limitação dos datasets da CAPES.</b> No quadriênio 2021-2024, os datasets
trazem o <b>número de docentes apenas para o ano-base 2021</b>. Não há cadastro de docentes para
2022, 2023 e 2024. Assim, para estimar a produção <b>por pesquisador ano a ano</b> nesses anos, o
número de docentes de 2021 foi <b>repetido</b> (mantido constante) para 2022-2024.</p>
<p style="margin-bottom:0"><b>Isso é um problema geral, não pontual.</b> A verificação em
<i>todos</i> os programas cadastrados nos datasets confirma que a ausência é universal: nenhum
programa do país tem número de pesquisadores lançado para 2022-2024.</p>
</div>
{ce('doc', 'Figura — Programas com nº de docentes lançado por ano-base: o cadastro existe até 2021 e zera em 2022-2024 (limitação universal dos datasets).')}

<h3>2.4 Período de referência (nota de rodapé mantida)</h3>
<p>A comparação de desempenho usa a produção do quadriênio <b>2017-2020</b> como base (último período
com coleta completa) frente ao quadriênio vigente <b>2021-2024</b>. A justificativa detalhada está
nas <a href="#notas">notas de rodapé</a> ao final, mantidas do relatório anterior.</p>

<h3>2.5 Classificação: verde, amarelo, vermelho (e estrutural)</h3>
<p>Para cada programa calcula-se a <b>retenção limpa</b> = média de artigos de 2021-2024 dividida
pela média de 2017-2020. Como a coleta de 2021-2024 ainda está incompleta para todos, a classificação
é feita <b>relativamente ao comportamento coletivo</b>:</p>
<table>
<tr><th>Cor</th><th>Critério (retenção)</th><th>Interpretação</th></tr>
<tr><td class="g">🟢 VERDE</td><td>≥ 0,85</td><td class="l">Manteve ou cresceu a produção</td></tr>
<tr><td class="y">🟡 AMARELO</td><td>0,50 – 0,85</td><td class="l">Queda moderada</td></tr>
<tr><td class="r">🔴 VERMELHO</td><td>&lt; 0,50</td><td class="l">Queda acentuada (alerta)</td></tr>
<tr><td class="k">⬛ ESTRUTURAL</td><td>—</td><td class="l">Não é alerta: programa em desativação, sucedido
por novo código, ou encerrado/recodificado antes de 2021 (sem produção desde 2020)</td></tr>
</table>
<div class="box"><b>Cautela (programas profissionais):</b> a avaliação CAPES de mestrados/doutorados
profissionais valoriza fortemente a <b>produção técnica/aplicada</b> (produtos, software, patentes),
não só artigos. O sinal aqui (artigos) subnotifica essas modalidades mais que as acadêmicas — os
alertas profissionais devem ser lidos como <b>indicativos</b>.</div>

<h2 class="pb">3. Resultados</h2>
<h3>3.1 Achado central</h3>
<p>No agregado, a produção <b>não caiu</b> em 2021-2024 — a retenção limpa mediana fica em torno de
<b>1,1</b> (UnB e Brasil), ou seja, os programas em geral <b>mantiveram ou cresceram</b> a produção
de artigos. A "queda" que aparecia na camada pré-processada e na mediana ingênua (de ~8 para ~3
artigos/docente/ano) é <b>artefato de coleta</b> (Sucupira em andamento + atribuição ao cadastro de
2021), não perda real de produtividade.</p>
{ce('dist', 'Figura — Distribuição por retenção nas 4 coortes (% dos programas). A grande maioria é verde (manteve/cresceu); o vermelho é minoria. Passe o mouse para ver as contagens.')}

<h3>3.2 UnB — programas acadêmicos (84)</h3>
<table>
<tr><th>🟢 Verde</th><th>🟡 Amarelo</th><th>🔴 Vermelho</th><th>⬛ Estrutural</th></tr>
<tr><td class="g">68</td><td class="y">11</td><td class="r">2</td><td class="k">3</td></tr>
</table>
<p><b>Vermelhos:</b> Engenharia de Sistemas Eletrônicos e de Automação (reportou 2021 e silenciou
depois — subnotificação) e Biotecnologia e Biodiversidade — Rede Pró-Centro-Oeste (programa em rede;
verificar produção nas IES parceiras). <b>Estruturais:</b> Botânica (desativada, sucedida por novo
código), Tecnologias Química e Biológica (desativada) e Contabilidade UnB-UFPB-UFRN (rede encerrada).</p>
<figure><img src="{fig_unb}"/>
<p class="cap">Figura 1 — UnB, programas acadêmicos: casos críticos vs. mediana institucional
(artigos por docente/ano). A mediana permanece estável no período 2021-2024.</p></figure>

<h3>3.3 UnB — programas profissionais (13)</h3>
<table>
<tr><th>🟢 Verde</th><th>🟡 Amarelo</th><th>🔴 Vermelho</th><th>⬛ Estrutural</th></tr>
<tr><td class="g">9</td><td class="y">0</td><td class="r">1</td><td class="k">3</td></tr>
</table>
<p>Retenção mediana ≈ 1,48 (os profissionais que produzem artigos cresceram). Único vermelho:
Ensino de Ciências (já vinha em declínio). Estruturais: Turismo (desativado) e dois programas sem
artigos no período (produção tipicamente técnica).</p>
<figure><img src="{fig_unb_prof}"/>
<p class="cap">Figura 2 — UnB, programas profissionais: casos críticos vs. mediana institucional.</p></figure>

<h3 class="pb">3.4 Brasil — programas acadêmicos (3.866, 377 IES)</h3>
<table>
<tr><th>🟢 Verde</th><th>🟡 Amarelo</th><th>🔴 Vermelho</th><th>⬛ Estrutural</th></tr>
<tr><td class="g">2.966</td><td class="y">615</td><td class="r">110</td><td class="k">175</td></tr>
</table>
<p>80% dos programas mantiveram ou cresceram; apenas ~3% têm queda acentuada genuína. Os críticos
concentram-se em áreas onde a métrica de artigo é menos adequada (humanas, interdisciplinar) ou em
programas com subnotificação/encerramento.</p>
<figure><img src="{fig_nac}"/>
<p class="cap">Figura 3 — Brasil, programas acadêmicos: (A) mediana nacional estável × leque de programas
críticos colapsando; (B) concentração dos críticos por área CAPES.</p></figure>

<h3>3.5 Brasil — programas profissionais (909, 341 IES)</h3>
<table>
<tr><th>🟢 Verde</th><th>🟡 Amarelo</th><th>🔴 Vermelho</th><th>⬛ Estrutural</th></tr>
<tr><td class="g">642</td><td class="y">150</td><td class="r">41</td><td class="k">76</td></tr>
</table>
<figure><img src="{fig_nac_prof}"/>
<p class="cap">Figura 4 — Brasil, programas profissionais: casos críticos vs. mediana nacional.</p></figure>

<h2 class="pb">4. Conclusões</h2>
<ul>
<li>A produção de artigos dos programas de pós-graduação <b>não caiu</b> em 2021-2024; o que se
observava era <b>artefato de coleta e de atribuição</b> (cadastro de docentes só de 2021).</li>
<li>O <b>sinal limpo</b> (artigos distintos por programa/ano) reproduz fielmente os dados brutos e
remove o viés que subnotificava 2021-2024.</li>
<li>Há uma <b>limitação universal</b> nos datasets: o número de docentes existe apenas até 2021 no
quadriênio vigente; a produtividade por pesquisador em 2022-2024 é estimada repetindo o cadastro de
2021.</li>
<li>Na UnB, dos 97 programas, só <b>3 acadêmicos e 1 profissional</b> têm alerta real de queda; os
demais alertas aparentes eram <b>casos estruturais</b> (desativação, sucessão de código, redes
encerradas), confirmados nos dados brutos.</li>
<li>Para programas <b>profissionais</b>, os alertas são apenas indicativos, dada a relevância da
produção técnica não captada por artigos.</li>
<li>Quando a CAPES consolidar a coleta de 2021-2024, basta <b>reprocessar</b> com o mesmo método.</li>
</ul>

<h2 id="notas">Notas de rodapé — escolha do período de referência</h2>
<ol class="foot">{rodape}</ol>
<p class="meta">Documento gerado pelo sistema MAPA-PG (mapa-pg-multi/pip) a partir dos Dados Abertos da
CAPES. Sinal: artigos distintos por programa/ano (prod_intel_artpe).</p>
"""


CHART_JS = r"""
const D = __DATA__;
Chart.defaults.font.family = "'Segoe UI',Arial,sans-serif";

new Chart(document.getElementById('cDist'), {
  type: 'bar',
  data: { labels: D.dist.cohorts, datasets: D.dist.datasets.map(function(ds){
    return { label: ds.label, data: ds.pct, backgroundColor: ds.color, _cnt: ds.cnt }; }) },
  options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
    scales: { x: { stacked: true, max: 100, title: { display: true, text: '% dos programas' } },
              y: { stacked: true } },
    plugins: { title: { display: true, text: 'Distribuição por retenção de produção (2021-24 / 2017-20)' },
      tooltip: { callbacks: { label: function(it){
        return it.dataset.label + ': ' + it.dataset._cnt[it.dataIndex] + ' (' + it.parsed.x + '%)'; } } } } }
});

new Chart(document.getElementById('cDoc'), {
  type: 'bar',
  data: { labels: D.doc.anos, datasets: [ { label: 'Programas c/ docentes', data: D.doc.vals,
    backgroundColor: D.doc.vals.map(function(v){ return v > 0 ? '#5DADE2' : '#C0392B'; }) } ] },
  options: { responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false },
      title: { display: true, text: 'Programas com nº de docentes lançado, por ano-base' },
      tooltip: { callbacks: { label: function(it){
        return it.parsed.y === 0 ? '0 — sem cadastro de docentes' : it.parsed.y + ' programas'; } } } },
    scales: { y: { title: { display: true, text: 'programas' } } } }
});
"""


def build_html5():
    body = build_body('html5', None)
    chartjs_lib = open(CHARTJS, encoding='utf-8').read()
    js = CHART_JS.replace('__DATA__', json.dumps(chart_data(), ensure_ascii=False))
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'<title>Produção dos Programas de Pós-Graduação — MAPA-PG</title>'
            f'<style>{CSS}{CSS_SCREEN}</style></head><body>{body}'
            f'<script>{chartjs_lib}</script><script>{js}</script></body></html>')


def build_html_pdf(figs):
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<style>{CSS}</style></head><body>{build_body("pdf", figs)}</body></html>')


def main():
    os.makedirs(SAIDA, exist_ok=True)
    html5_path = os.path.join(SAIDA, 'relatorio_mapa_pg_metodologia.html')
    open(html5_path, 'w', encoding='utf-8').write(build_html5())
    print('HTML5 interativo:', html5_path, f"({os.path.getsize(html5_path)/1024:.0f} KB)")

    figs = gerar_graficos()
    src = os.path.join(SAIDA, '_pdf_metodologia.html')
    open(src, 'w', encoding='utf-8').write(build_html_pdf(figs))
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', SAIDA, src],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    gerado = os.path.join(SAIDA, '_pdf_metodologia.pdf')
    pdf = os.path.join(SAIDA, 'relatorio_mapa_pg_metodologia.pdf')
    if os.path.exists(gerado):
        os.replace(gerado, pdf)
        print('PDF estático: ', pdf, f"({os.path.getsize(pdf)/1024:.0f} KB)")
    else:
        print('PDF: FALHOU')
    if os.path.exists(src):
        os.remove(src)


if __name__ == '__main__':
    main()
