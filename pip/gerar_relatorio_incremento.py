#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relatório — Plano de Incremento de Produtividade (PIP) da UnB: transições 3→4 e 4→5.

Gera DOIS formatos a partir do MESMO conteúdo (tabelas/texto):
  • saida/relatorio_incremento_pip.html  — HTML5 self-contained com gráficos
    INTERATIVOS (Chart.js inline; tooltips mostram o incremento até os 4 alvos).
  • saida/relatorio_incremento_pip.pdf   — via LibreOffice, com os mesmos gráficos
    em versão ESTÁTICA (matplotlib), pois o conversor não executa JavaScript.

Números recalculados ao vivo importando build_pip.
"""
import os
import io
import json
import base64
import subprocess

import build_pip as B
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

SAIDA = B.SAIDA
DOCS = os.path.dirname(B.DADOS)                 # .../mapa-pg-multi/docs
CHARTJS = os.path.join(DOCS, 'chart.umd.min.js')
ATIVO = lambda l: (l['situacao'] == 'EM FUNCIONAMENTO'
                   and 'fallback' not in l['baseline'] and l['ma_atual'] is not None)


def fmt(x, dec=2):
    return '—' if x is None else f'{x:.{dec}f}'.replace('.', ',')


def _coorte(linhas, ref, stats, nota):
    ativos = [l for l in linhas if l['nota'] == nota and ATIVO(l)]
    tot = {'piso': 0, 'wmean': 0, 'mediana': 0, 'media': 0}
    for l in ativos:
        _, incr = B._quatro_alvos(l, ref, stats)
        n = l['n_perm'] or 0
        for k in tot:
            if incr[k] is not None:
                tot[k] += round(incr[k] * n)
    return ativos, tot


# ─────────────────────────── tabelas (compartilhadas) ──────────────────────
def tab_nota(stats):
    out = ''
    for n in (7, 6, 5, 4, 3):
        nac = stats[n]['nac']; u = stats[n]['unb']
        out += (f"<tr><td>{n}</td><td>{nac['n']}</td><td>{fmt(nac['pond'])}</td>"
                f"<td>{fmt(nac['media'])}</td><td>{fmt(nac['mediana'])}</td>"
                f"<td>{u['n'] if u else 0}</td><td>{fmt(u['pond']) if u else '—'}</td></tr>")
    return out


def tab_resumo(linhas, ref, stats):
    a3, c3 = _coorte(linhas, ref, stats, 3)
    a4, c4 = _coorte(linhas, ref, stats, 4)
    html = (f"<tr><td>3 → 4</td><td>{len(a3)}</td><td class='g'>+{c3['piso']}</td>"
            f"<td>+{c3['wmean']}</td><td>+{c3['mediana']}</td><td>+{c3['media']}</td></tr>"
            f"<tr><td>4 → 5</td><td>{len(a4)}</td><td class='g'>+{c4['piso']}</td>"
            f"<td>+{c4['wmean']}</td><td>+{c4['mediana']}</td><td>+{c4['media']}</td></tr>")
    return html, c3, c4


def tab_mediana(linhas, ref, stats, nota):
    """Tabela numérica focada na MEDIANA NACIONAL da nota-alvo: por programa, a
    produção atual, o alvo, o incremento por pesquisador/ano e o incremento
    PERCENTUAL relativo (quanto a produção precisa subir, em %)."""
    med = stats[nota + 1]['nac']['mediana']
    ativos = sorted((l for l in linhas if l['nota'] == nota and ATIVO(l)),
                    key=lambda l: max(0.0, med - l['ma_atual']))
    out = ''
    for l in ativos:
        ma = l['ma_atual']
        incr = round(max(0.0, med - ma), 2)
        if incr == 0:
            inc_c = "<span class='g'>0</span>"
            pct_c = "<span class='g'>já atinge</span>"
        else:
            inc_c = fmt(incr)
            pct_c = '—' if ma <= 0 else f'+{fmt(incr / ma * 100, 1)}%'
        out += (f"<tr><td class='l'>{l['programa']}</td><td class='l'>{l['area']}</td>"
                f"<td>{l['n_perm'] or 0}</td><td>{fmt(ma)}</td><td>{fmt(med)}</td>"
                f"<td>{inc_c}</td><td>{pct_c}</td></tr>")
    return out


def tab_prog(linhas, ref, stats, nota):
    ativos = sorted((l for l in linhas if l['nota'] == nota and ATIVO(l)),
                    key=lambda l: (B._quatro_alvos(l, ref, stats)[1]['mediana'] or 0))
    out = ''
    for l in ativos:
        _, incr = B._quatro_alvos(l, ref, stats)
        def c(k):
            v = incr[k]
            return '—' if v is None else ("<span class='g'>0</span>" if v == 0 else fmt(v))
        out += (f"<tr><td class='l'>{l['programa']}</td><td class='l'>{l['area']}</td>"
                f"<td>{l['n_perm'] or 0}</td><td>{fmt(l['ma_atual'])}</td>"
                f"<td>{c('piso')}</td><td>{c('wmean')}</td><td>{c('mediana')}</td><td>{c('media')}</td></tr>")
    return out


# ─────────────────────────── gráficos estáticos (PDF) ──────────────────────
def _b64(fig, width_cm=16.0):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf)
    dpi = im.width / (width_cm / 2.54)
    out = io.BytesIO()
    im.save(out, format='PNG', dpi=(dpi, dpi))
    return base64.b64encode(out.getvalue()).decode()


def gerar_graficos(stats, linhas, ref):
    figs = {}
    notas = [3, 4, 5, 6, 7]
    br_p = [stats[n]['nac']['pond'] for n in notas]
    br_m = [stats[n]['nac']['mediana'] for n in notas]
    un_p = [stats[n]['unb']['pond'] if stats[n]['unb'] else 0 for n in notas]
    x = range(len(notas)); w = 0.26
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar([i - w for i in x], br_p, w, label='Brasil (ponderada)', color='#5DADE2')
    ax.bar(list(x), br_m, w, label='Brasil (mediana)', color='#AEB6BF')
    ax.bar([i + w for i in x], un_p, w, label='UnB (ponderada)', color='#E74C3C')
    ax.set_xticks(list(x)); ax.set_xticklabels([f'Nota {n}' for n in notas])
    ax.set_ylabel('art/permanente/ano')
    ax.set_title('Produção por pesquisador, por nota (2017-2020)', fontsize=11)
    ax.legend(fontsize=8); ax.grid(axis='y', alpha=.3)
    figs['nota'] = _b64(fig)

    _, t3 = _coorte(linhas, ref, stats, 3)
    _, t4 = _coorte(linhas, ref, stats, 4)
    alvos = ['Piso da\nárea', 'Méd. pond.\nda área', 'Mediana\nnacional', 'Média\nnacional']
    v34 = [t3['piso'], t3['wmean'], t3['mediana'], t3['media']]
    v45 = [t4['piso'], t4['wmean'], t4['mediana'], t4['media']]
    x = range(len(alvos)); w = 0.38
    fig, ax = plt.subplots(figsize=(8, 3.8))
    b1 = ax.bar([i - w/2 for i in x], v34, w, label='3 → 4', color='#48C9B0')
    b2 = ax.bar([i + w/2 for i in x], v45, w, label='4 → 5', color='#F39C12')
    ax.bar_label(b1, fontsize=7, padding=1); ax.bar_label(b2, fontsize=7, padding=1)
    ax.set_xticks(list(x)); ax.set_xticklabels(alvos, fontsize=8)
    ax.set_ylabel('artigos/ano a mais (coorte)')
    ax.set_title('Meta da coorte por definição de alvo', fontsize=11)
    ax.legend(fontsize=8); ax.grid(axis='y', alpha=.3)
    figs['coorte'] = _b64(fig)

    def por_programa(nota):
        med = stats[nota + 1]['nac']['mediana']; mean = stats[nota + 1]['nac']['media']
        ativos = sorted((l for l in linhas if l['nota'] == nota and ATIVO(l)),
                        key=lambda l: l['ma_atual'])
        nomes = [l['programa'][:38] for l in ativos]
        cur = [l['ma_atual'] for l in ativos]
        cores = ['#27AE60' if c >= med else '#5DADE2' for c in cur]
        fig, ax = plt.subplots(figsize=(8, max(2.6, 0.34 * len(ativos) + 1.2)))
        ax.barh(nomes, cur, color=cores)
        ax.axvline(med, color='#C0392B', ls='--', lw=1.3, label=f'Mediana nac. ({fmt(med)})')
        ax.axvline(mean, color='#7D3C98', ls=':', lw=1.3, label=f'Média nac. ({fmt(mean)})')
        ax.invert_yaxis(); ax.set_xlabel('art/permanente/ano (2017-2020)')
        ax.set_title(f'Nota {nota} → {nota+1}: produção atual por programa', fontsize=11)
        ax.legend(fontsize=8, loc='lower right'); ax.grid(axis='x', alpha=.3)
        ax.tick_params(axis='y', labelsize=7.5)
        return _b64(fig)

    figs['n3'] = por_programa(3)
    figs['n4'] = por_programa(4)

    # perfil de impacto agregado (Brasil × UnB por nota)
    labels, baixo, medio, alto = [], [], [], []
    for n in (5, 4, 3):
        for amb, key in (('Brasil', 'nac'), ('UnB', 'unb')):
            s = stats[n][key]
            if not s:
                continue
            labels.append(f'Nota {n} — {amb}')
            baixo.append(s['if_pct'][0]); medio.append(s['if_pct'][1]); alto.append(s['if_pct'][2])
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.barh(labels, baixo, color=IF_CORES[0], label=IF_LABELS[0])
    ax.barh(labels, medio, left=baixo, color=IF_CORES[1], label=IF_LABELS[1])
    ax.barh(labels, alto, left=[b + m for b, m in zip(baixo, medio)], color=IF_CORES[2], label=IF_LABELS[2])
    ax.set_xlim(0, 100); ax.invert_yaxis(); ax.set_xlabel('% dos artigos dos permanentes')
    ax.set_title('Perfil de impacto por nota (Brasil × UnB)', fontsize=11)
    ax.legend(fontsize=8, ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.32))
    ax.tick_params(axis='y', labelsize=8)
    figs['impacto'] = _b64(fig)
    return figs


# ─────────────────────────── dados p/ Chart.js (HTML5) ─────────────────────
def chart_data(stats, linhas, ref):
    notas = [3, 4, 5, 6, 7]
    cd = {'nota': {'labels': [f'Nota {n}' for n in notas],
                   'br_pond': [stats[n]['nac']['pond'] for n in notas],
                   'br_med': [stats[n]['nac']['mediana'] for n in notas],
                   'unb': [stats[n]['unb']['pond'] if stats[n]['unb'] else 0 for n in notas]}}
    _, t3 = _coorte(linhas, ref, stats, 3)
    _, t4 = _coorte(linhas, ref, stats, 4)
    cd['coorte'] = {'labels': ['Piso da área', 'Méd. pond. da área', 'Mediana nacional', 'Média nacional'],
                    'v34': [t3['piso'], t3['wmean'], t3['mediana'], t3['media']],
                    'v45': [t4['piso'], t4['wmean'], t4['mediana'], t4['media']]}

    def grupo(nota):
        med = stats[nota + 1]['nac']['mediana']; media = stats[nota + 1]['nac']['media']
        ativos = sorted((l for l in linhas if l['nota'] == nota and ATIVO(l)),
                        key=lambda l: l['ma_atual'])
        progs = []
        for l in ativos:
            _, incr = B._quatro_alvos(l, ref, stats)
            def s(k):
                v = incr[k]
                return '—' if v is None else ('0' if v == 0 else fmt(v))
            progs.append({'nome': l['programa'], 'area': l['area'], 'cur': round(l['ma_atual'], 2),
                          'incr': {'piso': s('piso'), 'wmean': s('wmean'),
                                   'mediana': s('mediana'), 'media': s('media')}})
        return {'med': med, 'media': media,
                'titulo': f'Nota {nota} → {nota+1}: produção atual por programa', 'progs': progs}

    cd['n3'] = grupo(3); cd['n4'] = grupo(4)

    labels, baixo, medio, alto = [], [], [], []
    for n in (5, 4, 3):
        for amb, key in (('Brasil', 'nac'), ('UnB', 'unb')):
            s = stats[n][key]
            if not s:
                continue
            labels.append(f'Nota {n} — {amb}')
            baixo.append(s['if_pct'][0]); medio.append(s['if_pct'][1]); alto.append(s['if_pct'][2])
    cd['impacto'] = {'labels': labels, 'baixo': baixo, 'medio': medio, 'alto': alto}
    return cd


# ─────────────────────────── corpo do relatório ────────────────────────────
CSS = """
@page { size: A4; margin: 2.0cm 1.8cm; }
body { font-family:'Liberation Serif','Times New Roman',serif; font-size:11pt; color:#222; line-height:1.42; }
h1 { font-size:19pt; color:#1A2A3A; margin:0 0 2pt 0; }
h2 { font-size:13.5pt; color:#1F618D; border-bottom:2px solid #AED6F1; padding-bottom:2px; margin-top:18px; }
.sub { color:#666; font-size:10.5pt; margin:0 0 2px 0; }
.meta { color:#777; font-size:9.5pt; margin-bottom:12px; line-height:1.35; }
p { margin:6px 0; text-align:justify; }
table { border-collapse:collapse; width:100%; margin:8px 0; font-size:9.5pt; }
th { background:#2C3E50; color:#fff; padding:5px 6px; text-align:center; }
td { border:1px solid #ccc; padding:3px 6px; text-align:center; }
td.l { text-align:left; }
.g { color:#1E8449; font-weight:bold; }
.boxb { background:#EAF2F8; border-left:4px solid #2E86C1; padding:8px 12px; margin:10px 0; }
figure { margin:12px 0 6px 0; text-align:center; page-break-inside:avoid; }
figure img { width:16cm; max-width:100%; height:auto; border:1px solid #ddd; display:block; margin:0 auto; }
.chartbox { position:relative; margin:14px 0 2px; }
p.cap { font-size:9.5pt; color:#555; margin:3px 0 0 0; font-style:italic; text-align:center; }
.foot { font-size:9pt; color:#555; } .foot li { margin-bottom:3px; }
.pb { page-break-before:always; }
ul { margin:6px 0; } li { margin:3px 0; }
"""
CSS_SCREEN = "body{max-width:1000px;margin:0 auto;padding:10px 18px;background:#fff;}"
CANVAS = {'nota': ('cNota', 380), 'coorte': ('cCoorte', 380), 'n3': ('cN3', 300),
          'n4': ('cN4', 640), 'impacto': ('cImpacto', 360)}
IF_CORES = ['#BBDEFB', '#1E88E5', '#0D47A1']   # baixo, médio, alto
IF_LABELS = ['Baixo (IF<2,2)', 'Médio (2,2–8,0)', 'Alto (>8,0)']


def tab_impacto(linhas, nota):
    """Perfil de impacto por programa: % dos artigos dos permanentes (2017-2020)
    em cada faixa de fator de impacto. Ordena por qualidade (médio+alto) desc."""
    ativos = [l for l in linhas if l['nota'] == nota and ATIVO(l)]
    def qual(l):
        t = sum(l['if_perm'])
        return (l['if_perm'][1] + l['if_perm'][2]) / t if t else -1
    ativos.sort(key=qual, reverse=True)
    out = ''
    for l in ativos:
        t = sum(l['if_perm'])
        if t == 0:
            pb = pm = pa = '—'; nt = '0'
        else:
            pb, pm, pa = (fmt(v / t * 100, 1) for v in l['if_perm']); nt = str(t)
        out += (f"<tr><td class='l'>{l['programa']}</td><td class='l'>{l['area']}</td>"
                f"<td>{nt}</td><td>{pb}</td><td>{pm}</td><td>{pa}</td></tr>")
    return out


def tab_impacto_agg(stats):
    """Perfil de impacto agregado Brasil × UnB, por nota."""
    out = ''
    for n in (5, 4, 3):
        for amb, key in (('Brasil', 'nac'), ('UnB', 'unb')):
            s = stats[n][key]
            if not s:
                continue
            b, m, a = s['if_pct']
            out += (f"<tr><td class='l'>Nota {n} — {amb}</td><td>{sum(s['if'])}</td>"
                    f"<td>{fmt(b,1)}</td><td>{fmt(m,1)}</td><td>{fmt(a,1)}</td></tr>")
    return out


def chart_el(mode, key, cap, figs):
    if mode == 'pdf':
        return f'<figure><img src="data:image/png;base64,{figs[key]}"><p class="cap">{cap}</p></figure>'
    cid, h = CANVAS[key]
    return (f'<div class="chartbox" style="height:{h}px"><canvas id="{cid}"></canvas></div>'
            f'<p class="cap">{cap}</p>')


def build_body(mode, figs, stats, linhas, ref):
    resumo, c3, c4 = tab_resumo(linhas, ref, stats)
    m4 = stats[4]['nac']; m5 = stats[5]['nac']
    rodape = ''.join(f'<li>{t}</li>' for t in B.RODAPE_PERIODO)
    ce = lambda key, cap: chart_el(mode, key, cap, figs)
    return f"""
<h1>Plano de Incremento de Produtividade — UnB</h1>
<p class="sub">Quanto a produção por pesquisador precisa aumentar para os programas da UnB subirem de nota (3&rarr;4 e 4&rarr;5)</p>
<p class="meta">Prof. Titular David Lima Azevedo — Grupo de Dinâmica e Ab Initio (GDAI), Núcleo de Estrutura da Matéria,
Instituto de Física, Universidade de Brasília (UnB) · ORCID 0000-0002-3456-554X<br>
Sistema <b>MAPA-PG</b> · dados públicos da CAPES (Coleta Sucupira) e fatores de impacto OpenAlex.</p>

<h2>1. Metodologia</h2>
<p>A <b>nota</b> de cada programa é a vigente (registro 2021-2024). A <b>produção</b> é medida no quadriênio
<b>2017-2020</b> (último com coleta CAPES completa), em <b>artigos em periódico por docente permanente por ano</b>.
Só programas <b>acadêmicos</b>. A produção de um grupo usa a <b>média ponderada</b> pelos permanentes
(Σ artigos/ano ÷ Σ permanentes). Comparam-se os programas da UnB com <b>quatro definições de alvo</b> da nota
seguinte, em rigor crescente: <b>piso da área</b> (menor produção da nota-alvo na mesma área CAPES),
<b>média ponderada da área</b>, <b>mediana nacional</b> e <b>média nacional</b>. O incremento tem piso em zero.</p>

<h2>2. Produção por pesquisador, por nota (Brasil &times; UnB)</h2>
<table>
<tr><th>Nota</th><th>Prog. Brasil</th><th>Ponderada Brasil</th><th>Média Brasil</th><th>Mediana Brasil</th><th>Prog. UnB</th><th>Ponderada UnB</th></tr>
{tab_nota(stats)}
</table>
{ce('nota', 'Figura 1 — A produção por pesquisador satura a partir da nota 4: acima dela, o que distingue os programas é o impacto, não o volume.')}

<h2>3. Meta da coorte — artigos/ano a mais, por alvo</h2>
<table>
<tr><th>Transição</th><th>Programas</th><th>&rarr; Piso da área</th><th>&rarr; Média pond. da área</th><th>&rarr; Mediana nacional</th><th>&rarr; Média nacional</th></tr>
{resumo}
</table>
{ce('coorte', 'Figura 2 — Meta da coorte por definição de alvo. Pelo piso da área a meta é ~zero; só cresce ao mirar os programas de referência.')}
<div class="boxb"><b>Leitura.</b> Pelo <b>piso da área</b>, a produção da UnB já é praticamente suficiente: os 6 programas
nota 3 já estão todos no piso da nota 4 (incremento <b>zero</b>) e, na nota 4, só 6 dos 23 têm pequena defasagem
(coorte: <b>+{c4['piso']}</b> artigos/ano). As metas só ficam exigentes ao mirar mediana/média.</div>

<h2 class="pb">4. Detalhe por programa — Nota 3 &rarr; 4</h2>
<p class="sub">Alvos nacionais da nota 4: mediana {fmt(m4['mediana'])} · média {fmt(m4['media'])} art/pesq/ano.
Incremento em art/pesq/ano; <span class="g">0</span> = já atingiu. Botânica (desativação) fora do plano.</p>
{ce('n3', 'Figura 3 — Produção atual de cada programa nota 3; barras verdes já superam a mediana nacional da nota 4. (No HTML, passe o mouse para ver o incremento até cada alvo.)')}
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Perm.</th><th>Prod. atual</th><th>&rarr; Piso área</th><th>&rarr; Méd.pond.</th><th>&rarr; Mediana</th><th>&rarr; Média</th></tr>
{tab_prog(linhas, ref, stats, 3)}
</table>
<h3>Incremento até a MEDIANA NACIONAL (3 &rarr; 4)</h3>
<p class="sub">Quanto a produção por pesquisador de cada programa precisa subir para alcançar a mediana
nacional da nota 4 ({fmt(m4['mediana'])} art/pesq/ano): em valor (art/pesq/ano) e em % relativo sobre a produção atual.</p>
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Perm.</th><th>Produção atual</th><th>Mediana nacional</th><th>Incremento (art/pesq/ano)</th><th>Incremento %</th></tr>
{tab_mediana(linhas, ref, stats, 3)}
</table>

<h2 class="pb">5. Detalhe por programa — Nota 4 &rarr; 5</h2>
<p class="sub">Alvos nacionais da nota 5: mediana {fmt(m5['mediana'])} · média {fmt(m5['media'])} art/pesq/ano.
Botânica nova (sem produção 2017-2020) fora do plano.</p>
{ce('n4', 'Figura 4 — Produção atual de cada programa nota 4; barras verdes já superam a mediana nacional da nota 5. (No HTML, passe o mouse para ver o incremento até cada alvo.)')}
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Perm.</th><th>Prod. atual</th><th>&rarr; Piso área</th><th>&rarr; Méd.pond.</th><th>&rarr; Mediana</th><th>&rarr; Média</th></tr>
{tab_prog(linhas, ref, stats, 4)}
</table>
<h3>Incremento até a MEDIANA NACIONAL (4 &rarr; 5)</h3>
<p class="sub">Quanto a produção por pesquisador de cada programa precisa subir para alcançar a mediana
nacional da nota 5 ({fmt(m5['mediana'])} art/pesq/ano): em valor (art/pesq/ano) e em % relativo sobre a produção atual.</p>
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Perm.</th><th>Produção atual</th><th>Mediana nacional</th><th>Incremento (art/pesq/ano)</th><th>Incremento %</th></tr>
{tab_mediana(linhas, ref, stats, 4)}
</table>

<h2 class="pb">6. Perfil de impacto da produção (baixo, médio, alto)</h2>
<p>Além do volume, a avaliação valoriza o <b>impacto</b>. Cada artigo é classificado pelo fator de
impacto do periódico (OpenAlex, <i>2yr mean citedness</i>, equivalente ao JCR) em três faixas:
<b>baixo</b> (IF&lt;2,2), <b>médio</b> (2,2–8,0) e <b>alto</b> (&gt;8,0). A tabela e o gráfico mostram a
composição da produção dos docentes permanentes (2017-2020) por faixa.</p>
<table>
<tr><th>Âmbito</th><th>Artigos (perm.)</th><th>% Baixo</th><th>% Médio</th><th>% Alto</th></tr>
{tab_impacto_agg(stats)}
</table>
{ce('impacto', 'Figura 5 — Perfil de impacto por nota (Brasil × UnB): a fração de impacto médio/alto cresce com a nota, e a UnB costuma ter menos "baixo" que a média nacional. Passe o mouse para os percentuais.')}
<p class="sub">Perfil de impacto por programa UnB (% dos artigos dos permanentes por faixa; ordenado pela maior fração médio+alto):</p>
<h3>Nota 3</h3>
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Artigos (perm.)</th><th>% Baixo</th><th>% Médio</th><th>% Alto</th></tr>
{tab_impacto(linhas, 3)}
</table>
<h3>Nota 4</h3>
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Artigos (perm.)</th><th>% Baixo</th><th>% Médio</th><th>% Alto</th></tr>
{tab_impacto(linhas, 4)}
</table>

<h2 class="pb">7. Conclusões</h2>
<ul>
<li><b>Impacto distingue as notas mais do que o volume.</b> A fração de produção em periódicos de
impacto médio/alto cresce com a nota (Brasil: ~27% médio+alto na nota 3, ~33% na nota 5); a UnB já
tende a publicar menos em impacto baixo que a média nacional — esse é o eixo a reforçar para subir de nota.</li>
<li><b>Volume não é o gargalo para subir de nota.</b> Contra o piso da própria área, a produção por pesquisador da
UnB já alcança os programas mais fracos da nota seguinte — em 3&rarr;4 para todos os 6, em 4&rarr;5 para 17 dos 23.</li>
<li><b>O salto depende de qualidade/impacto</b> (fator de impacto, internacionalização, formação de mestres e
doutores, proposta), não de produzir mais artigos.</li>
<li><b>Alvos nacionais cruzados penalizam áreas de baixa taxa de artigos</b> (ex.: Matemática/Estatística pode estar
no nível da sua área e ainda parecer distante da mediana nacional). O alvo justo é o da <b>própria área</b>.</li>
<li><b>Maior alavanca absoluta:</b> a Biotecnologia–Rede Pró-Centro-Oeste (63 permanentes) concentra boa parte do
esforço da coorte nota 4 quando o alvo são os programas de referência.</li>
<li><b>Metas de quantidade (quando aplicáveis):</b> p/ a mediana nacional, a coorte nota 3 precisaria de
+{c3['mediana']} e a nota 4 de +{c4['mediana']} artigos/ano; p/ a média, +{c3['media']} e +{c4['media']}.</li>
</ul>

<h2>Nota metodológica — período de referência</h2>
<ul class="foot">{rodape}</ul>
"""


# bloco JS do Chart.js (sem f-string; __DATA__ é substituído pelo JSON)
CHART_JS = r"""
const D = __DATA__;
Chart.defaults.font.family = "'Segoe UI',Arial,sans-serif";
const vLines = {
  id: 'vLines',
  afterDraw(c) {
    const o = (c.options.plugins && c.options.plugins.vLines) || {};
    (o.lines || []).forEach(function(L){
      const x = c.scales.x, a = c.chartArea, ctx = c.ctx, px = x.getPixelForValue(L.value);
      ctx.save(); ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom);
      ctx.lineWidth = 1.6; ctx.strokeStyle = L.color; ctx.setLineDash(L.dash || [6,4]);
      ctx.stroke(); ctx.restore();
    });
  }
};
Chart.register(vLines);

new Chart(document.getElementById('cNota'), {
  type: 'bar',
  data: { labels: D.nota.labels, datasets: [
    { label: 'Brasil (ponderada)', data: D.nota.br_pond, backgroundColor: '#5DADE2' },
    { label: 'Brasil (mediana)',   data: D.nota.br_med,  backgroundColor: '#AEB6BF' },
    { label: 'UnB (ponderada)',    data: D.nota.unb,     backgroundColor: '#E74C3C' } ] },
  options: { responsive: true, maintainAspectRatio: false,
    plugins: { title: { display: true, text: 'Produção por pesquisador, por nota (2017-2020)' } },
    scales: { y: { title: { display: true, text: 'art/permanente/ano' } } } }
});

new Chart(document.getElementById('cCoorte'), {
  type: 'bar',
  data: { labels: D.coorte.labels, datasets: [
    { label: '3 → 4', data: D.coorte.v34, backgroundColor: '#48C9B0' },
    { label: '4 → 5', data: D.coorte.v45, backgroundColor: '#F39C12' } ] },
  options: { responsive: true, maintainAspectRatio: false,
    plugins: { title: { display: true, text: 'Meta da coorte por definição de alvo' },
      tooltip: { callbacks: { label: function(it){ return it.dataset.label + ': +' + it.parsed.y + ' art/ano'; } } } },
    scales: { y: { title: { display: true, text: 'artigos/ano a mais (coorte)' } } } }
});

function progChart(canvasId, g) {
  const labels = g.progs.map(function(p){ return p.nome; });
  const cur = g.progs.map(function(p){ return p.cur; });
  const colors = g.progs.map(function(p){ return p.cur >= g.med ? '#27AE60' : '#5DADE2'; });
  new Chart(document.getElementById(canvasId), {
    type: 'bar',
    data: { labels: labels, datasets: [ { label: 'Produção atual', data: cur, backgroundColor: colors } ] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: { display: true, text: g.titulo + '  (linhas: mediana e média nacionais)' },
        vLines: { lines: [ { value: g.med, color: '#C0392B', dash: [6,4] }, { value: g.media, color: '#7D3C98', dash: [2,3] } ] },
        tooltip: { callbacks: {
          label: function(it){ return 'Produção atual: ' + String(it.parsed.x).replace('.', ',') + ' art/pesq/ano'; },
          afterBody: function(items){ const p = g.progs[items[0].dataIndex];
            return [ 'Área: ' + p.area, 'Falta para o…',
              '  • piso da área: ' + p.incr.piso, '  • média pond. da área: ' + p.incr.wmean,
              '  • mediana nacional: ' + p.incr.mediana, '  • média nacional: ' + p.incr.media ]; }
        } }
      },
      scales: { x: { title: { display: true, text: 'art/permanente/ano (2017-2020)' } } } }
  });
}
progChart('cN3', D.n3);
progChart('cN4', D.n4);

new Chart(document.getElementById('cImpacto'), {
  type: 'bar',
  data: { labels: D.impacto.labels, datasets: [
    { label: 'Baixo (IF<2,2)',    data: D.impacto.baixo, backgroundColor: '#BBDEFB' },
    { label: 'Médio (2,2-8,0)',   data: D.impacto.medio, backgroundColor: '#1E88E5' },
    { label: 'Alto (>8,0)',       data: D.impacto.alto,  backgroundColor: '#0D47A1' } ] },
  options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
    scales: { x: { stacked: true, max: 100, title: { display: true, text: '% dos artigos dos permanentes' } },
              y: { stacked: true } },
    plugins: { title: { display: true, text: 'Perfil de impacto por nota (Brasil x UnB)' },
      tooltip: { callbacks: { label: function(it){ return it.dataset.label + ': ' + it.parsed.x + '%'; } } } } }
});
"""


def build_html5(stats, linhas, ref):
    body = build_body('html5', None, stats, linhas, ref)
    cd = chart_data(stats, linhas, ref)
    chartjs_lib = open(CHARTJS, encoding='utf-8').read()
    js = CHART_JS.replace('__DATA__', json.dumps(cd, ensure_ascii=False))
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'<title>Plano de Incremento de Produtividade — UnB (3→4, 4→5)</title>'
            f'<style>{CSS}{CSS_SCREEN}</style></head><body>{body}'
            f'<script>{chartjs_lib}</script><script>{js}</script></body></html>')


def build_html_pdf(figs, stats, linhas, ref):
    body = build_body('pdf', figs, stats, linhas, ref)
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


def main():
    progs, area_de, areas = B.carregar()
    ref, cont = B.media_referencia(progs, area_de)
    stats = B.stats_por_nota(progs)
    linhas = B.analisar(progs, area_de, ref)
    os.makedirs(SAIDA, exist_ok=True)

    # HTML5 interativo (Chart.js)
    html5_path = os.path.join(SAIDA, 'relatorio_incremento_pip.html')
    open(html5_path, 'w', encoding='utf-8').write(build_html5(stats, linhas, ref))
    print('HTML5 interativo:', html5_path, f"({os.path.getsize(html5_path)/1024:.0f} KB)")

    # PDF estático (matplotlib via LibreOffice)
    figs = gerar_graficos(stats, linhas, ref)
    src = os.path.join(SAIDA, '_pdf_incremento.html')
    open(src, 'w', encoding='utf-8').write(build_html_pdf(figs, stats, linhas, ref))
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', SAIDA, src],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    gerado = os.path.join(SAIDA, '_pdf_incremento.pdf')
    pdf = os.path.join(SAIDA, 'relatorio_incremento_pip.pdf')
    if os.path.exists(gerado):
        os.replace(gerado, pdf)
        print('PDF estático: ', pdf, f"({os.path.getsize(pdf)/1024:.0f} KB)")
    else:
        print('PDF: FALHOU')
    if os.path.exists(src):
        os.remove(src)


if __name__ == '__main__':
    main()
