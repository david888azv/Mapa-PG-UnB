#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relatório — Plano de Incremento de Produtividade (PIP) da UnB: transições 3→4 e 4→5.

Gera DOIS formatos a partir do MESMO conteúdo:
  • saida/relatorio_incremento_pip.html  (HTML5 self-contained, com gráficos)
  • saida/relatorio_incremento_pip.pdf   (via LibreOffice)

Os gráficos são gerados com matplotlib e embutidos em base64 (o HTML abre offline,
por duplo-clique; o PDF traz as mesmas figuras). Números recalculados ao vivo
importando build_pip (mesma fonte das abas do relatorio_pip_unb.xlsx).
"""
import os
import io
import base64
import subprocess

import build_pip as B
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

SAIDA = B.SAIDA
ATIVO = lambda l: (l['situacao'] == 'EM FUNCIONAMENTO'
                   and 'fallback' not in l['baseline'] and l['ma_atual'] is not None)


def fmt(x, dec=2):
    return '—' if x is None else f'{x:.{dec}f}'.replace('.', ',')


def _b64(fig, width_cm=16.0):
    """Renderiza a figura em PNG e recarimba o DPI p/ largura física = width_cm
    (assim o LibreOffice dimensiona certo na página). Devolve base64."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf)
    dpi = im.width / (width_cm / 2.54)
    out = io.BytesIO()
    im.save(out, format='PNG', dpi=(dpi, dpi))
    return base64.b64encode(out.getvalue()).decode()


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


def gerar_graficos(stats, linhas, ref):
    figs = {}

    # 1) Produção por permanente/ano, por nota (Brasil × UnB) ---------------
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

    # 2) Meta da coorte (artigos/ano a mais), por alvo ---------------------
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

    # 3) e 4) Por programa: produção atual vs mediana/média nacionais ------
    def por_programa(nota):
        med = stats[nota + 1]['nac']['mediana']
        mean = stats[nota + 1]['nac']['media']
        ativos = sorted((l for l in linhas if l['nota'] == nota and ATIVO(l)),
                        key=lambda l: l['ma_atual'])
        nomes = [l['programa'][:38] for l in ativos]
        cur = [l['ma_atual'] for l in ativos]
        cores = ['#27AE60' if c >= med else '#5DADE2' for c in cur]
        fig, ax = plt.subplots(figsize=(8, max(2.6, 0.34 * len(ativos) + 1.2)))
        ax.barh(nomes, cur, color=cores)
        ax.axvline(med, color='#C0392B', ls='--', lw=1.3, label=f'Mediana nac. ({fmt(med)})')
        ax.axvline(mean, color='#7D3C98', ls=':', lw=1.3, label=f'Média nac. ({fmt(mean)})')
        ax.invert_yaxis()
        ax.set_xlabel('art/permanente/ano (2017-2020)')
        ax.set_title(f'Nota {nota} → {nota+1}: produção atual por programa', fontsize=11)
        ax.legend(fontsize=8, loc='lower right'); ax.grid(axis='x', alpha=.3)
        ax.tick_params(axis='y', labelsize=7.5)
        return _b64(fig)

    figs['n3'] = por_programa(3)
    figs['n4'] = por_programa(4)
    return figs


CSS = """
@page { size: A4; margin: 2.0cm 1.8cm; }
body { font-family: 'Liberation Serif','Times New Roman',serif; font-size: 11pt; color:#222; line-height:1.42; }
h1 { font-size: 19pt; color:#1A2A3A; margin:0 0 2pt 0; }
h2 { font-size: 13.5pt; color:#1F618D; border-bottom:2px solid #AED6F1; padding-bottom:2px; margin-top:18px; }
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
p.cap { font-size:9.5pt; color:#555; margin:3px 0 0 0; font-style:italic; text-align:center; }
.foot { font-size:9pt; color:#555; } .foot li { margin-bottom:3px; }
.pb { page-break-before:always; }
ul { margin:6px 0; } li { margin:3px 0; }
"""


def build_html(figs, stats, linhas, ref):
    def t1():
        out = ''
        for n in (7, 6, 5, 4, 3):
            nac = stats[n]['nac']; u = stats[n]['unb']
            out += (f"<tr><td>{n}</td><td>{nac['n']}</td><td>{fmt(nac['pond'])}</td>"
                    f"<td>{fmt(nac['media'])}</td><td>{fmt(nac['mediana'])}</td>"
                    f"<td>{u['n'] if u else 0}</td><td>{fmt(u['pond']) if u else '—'}</td></tr>")
        return out

    a3, c3 = _coorte(linhas, ref, stats, 3)
    a4, c4 = _coorte(linhas, ref, stats, 4)
    resumo = (f"<tr><td>3 → 4</td><td>{len(a3)}</td><td class='g'>+{c3['piso']}</td>"
              f"<td>+{c3['wmean']}</td><td>+{c3['mediana']}</td><td>+{c3['media']}</td></tr>"
              f"<tr><td>4 → 5</td><td>{len(a4)}</td><td class='g'>+{c4['piso']}</td>"
              f"<td>+{c4['wmean']}</td><td>+{c4['mediana']}</td><td>+{c4['media']}</td></tr>")

    def prog_rows(nota):
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

    m4 = stats[4]['nac']; m5 = stats[5]['nac']
    rodape = ''.join(f'<li>{t}</li>' for t in B.RODAPE_PERIODO)

    def fig(key, cap):
        return f'<figure><img src="data:image/png;base64,{figs[key]}"><p class="cap">{cap}</p></figure>'

    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Plano de Incremento de Produtividade — UnB (3→4, 4→5)</title>
<style>{CSS}</style></head><body>

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
{t1()}
</table>
{fig('nota', 'Figura 1 — A produção por pesquisador satura a partir da nota 4: acima dela, o que distingue os programas é o impacto, não o volume.')}

<h2>3. Meta da coorte — artigos/ano a mais, por alvo</h2>
<table>
<tr><th>Transição</th><th>Programas</th><th>&rarr; Piso da área</th><th>&rarr; Média pond. da área</th><th>&rarr; Mediana nacional</th><th>&rarr; Média nacional</th></tr>
{resumo}
</table>
{fig('coorte', 'Figura 2 — Meta da coorte por definição de alvo. Pelo piso da área a meta é ~zero; só cresce ao mirar os programas de referência.')}
<div class="boxb"><b>Leitura.</b> Pelo <b>piso da área</b>, a produção da UnB já é praticamente suficiente: os 6 programas
nota 3 já estão todos no piso da nota 4 (incremento <b>zero</b>) e, na nota 4, só 6 dos 23 têm pequena defasagem
(coorte: <b>+{c4['piso']}</b> artigos/ano). As metas só ficam exigentes ao mirar mediana/média.</div>

<h2 class="pb">4. Detalhe por programa — Nota 3 &rarr; 4</h2>
<p class="sub">Alvos nacionais da nota 4: mediana {fmt(m4['mediana'])} · média {fmt(m4['media'])} art/pesq/ano.
Incremento em art/pesq/ano; <span class="g">0</span> = já atingiu. Botânica (desativação) fora do plano.</p>
{fig('n3', 'Figura 3 — Produção atual de cada programa nota 3; barras verdes já superam a mediana nacional da nota 4.')}
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Perm.</th><th>Prod. atual</th><th>&rarr; Piso área</th><th>&rarr; Méd.pond.</th><th>&rarr; Mediana</th><th>&rarr; Média</th></tr>
{prog_rows(3)}
</table>

<h2 class="pb">5. Detalhe por programa — Nota 4 &rarr; 5</h2>
<p class="sub">Alvos nacionais da nota 5: mediana {fmt(m5['mediana'])} · média {fmt(m5['media'])} art/pesq/ano.
Botânica nova (sem produção 2017-2020) fora do plano.</p>
{fig('n4', 'Figura 4 — Produção atual de cada programa nota 4; barras verdes já superam a mediana nacional da nota 5.')}
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Perm.</th><th>Prod. atual</th><th>&rarr; Piso área</th><th>&rarr; Méd.pond.</th><th>&rarr; Mediana</th><th>&rarr; Média</th></tr>
{prog_rows(4)}
</table>

<h2 class="pb">6. Conclusões</h2>
<ul>
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

</body></html>"""


def main():
    progs, area_de, areas = B.carregar()
    ref, cont = B.media_referencia(progs, area_de)
    stats = B.stats_por_nota(progs)
    linhas = B.analisar(progs, area_de, ref)

    figs = gerar_graficos(stats, linhas, ref)
    html = build_html(figs, stats, linhas, ref)

    os.makedirs(SAIDA, exist_ok=True)
    html_path = os.path.join(SAIDA, 'relatorio_incremento_pip.html')
    open(html_path, 'w', encoding='utf-8').write(html)
    print('HTML5 gerado:', html_path, f"({os.path.getsize(html_path)/1024:.0f} KB)")

    subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', SAIDA, html_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(SAIDA, 'relatorio_incremento_pip.pdf')
    print('PDF gerado:  ', pdf,
          f"({os.path.getsize(pdf)/1024:.0f} KB)" if os.path.exists(pdf) else '(FALHOU)')


if __name__ == '__main__':
    main()
