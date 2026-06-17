#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relatório PDF — Plano de Incremento de Produtividade (PIP) da UnB:
transições de nota 3→4 e 4→5.

Reúne, num documento único, a produção ponderada por nota (Brasil × UnB), as
QUATRO definições de alvo (piso e média ponderada da própria área CAPES; mediana
e média nacionais), o detalhe por programa e as conclusões.

Os números são recalculados ao vivo importando build_pip (mesma fonte das abas
do relatorio_pip_unb.xlsx). HTML -> PDF via LibreOffice.
Saída: saida/relatorio_incremento_pip.pdf
"""
import os
import subprocess

import build_pip as B

SAIDA = B.SAIDA


def fmt(x, dec=2):
    if x is None:
        return '—'
    return f'{x:.{dec}f}'.replace('.', ',')


CSS = """
@page { size: A4; margin: 2.0cm 1.8cm; }
body { font-family: 'Liberation Serif','Times New Roman',serif; font-size: 11pt;
       color: #222; line-height: 1.42; }
h1 { font-size: 19pt; color: #1A2A3A; margin: 0 0 2pt 0; }
h2 { font-size: 13.5pt; color: #1F618D; border-bottom: 2px solid #AED6F1;
     padding-bottom: 2px; margin-top: 18px; }
h3 { font-size: 11.5pt; color: #2C3E50; margin-top: 12px; margin-bottom: 4px; }
.sub { color: #666; font-size: 10.5pt; margin: 0 0 2px 0; }
.meta { color: #777; font-size: 9.5pt; margin-bottom: 12px; line-height: 1.35; }
p { margin: 6px 0; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9.5pt; }
th { background: #2C3E50; color: #fff; padding: 5px 6px; text-align: center; font-weight: bold; }
td { border: 1px solid #ccc; padding: 3px 6px; text-align: center; }
td.l { text-align: left; }
tr.sub td { background: #EBF1F7; font-weight: bold; }
.g { color: #1E8449; font-weight: bold; }
.box { background: #FEF9E7; border-left: 4px solid #F1C40F; padding: 8px 12px; margin: 10px 0; }
.boxb { background: #EAF2F8; border-left: 4px solid #2E86C1; padding: 8px 12px; margin: 10px 0; }
.foot { font-size: 9pt; color: #555; }
.foot li { margin-bottom: 3px; }
.pb { page-break-before: always; }
ul { margin: 6px 0; } li { margin: 3px 0; }
"""


def main():
    progs, area_de, areas = B.carregar()
    ref, cont = B.media_referencia(progs, area_de)
    stats = B.stats_por_nota(progs)
    linhas = B.analisar(progs, area_de, ref)

    # ── Tabela 1: produção ponderada por nota (Brasil × UnB) ───────────────
    t1 = ''
    for nota in (7, 6, 5, 4, 3):
        nac = stats[nota]['nac']; u = stats[nota]['unb']
        t1 += (f"<tr><td>{nota}</td><td>{nac['n']}</td><td>{fmt(nac['pond'])}</td>"
               f"<td>{fmt(nac['media'])}</td><td>{fmt(nac['mediana'])}</td>"
               f"<td>{u['n'] if u else 0}</td><td>{fmt(u['pond']) if u else '—'}</td></tr>")

    # ── Coorte (resumo de metas absolutas) + detalhe por programa ──────────
    def coorte(nota):
        ativos = [l for l in linhas if l['nota'] == nota
                  and l['situacao'] == 'EM FUNCIONAMENTO'
                  and 'fallback' not in l['baseline'] and l['ma_atual'] is not None]
        tot = {'piso': 0, 'wmean': 0, 'mediana': 0, 'media': 0}
        for l in ativos:
            _, incr = B._quatro_alvos(l, ref, stats)
            n = l['n_perm'] or 0
            for k in tot:
                if incr[k] is not None:
                    tot[k] += round(incr[k] * n)
        return ativos, tot

    a3, t3 = coorte(3)
    a4, t4 = coorte(4)
    resumo = (
        f"<tr><td>3 → 4</td><td>{len(a3)}</td><td class='g'>+{t3['piso']}</td>"
        f"<td>+{t3['wmean']}</td><td>+{t3['mediana']}</td><td>+{t3['media']}</td></tr>"
        f"<tr><td>4 → 5</td><td>{len(a4)}</td><td class='g'>+{t4['piso']}</td>"
        f"<td>+{t4['wmean']}</td><td>+{t4['mediana']}</td><td>+{t4['media']}</td></tr>")

    def prog_rows(nota):
        ativos = [l for l in linhas if l['nota'] == nota
                  and l['situacao'] == 'EM FUNCIONAMENTO'
                  and 'fallback' not in l['baseline'] and l['ma_atual'] is not None]
        ativos.sort(key=lambda l: (B._quatro_alvos(l, ref, stats)[1]['mediana'] or 0))
        out = ''
        for l in ativos:
            _, incr = B._quatro_alvos(l, ref, stats)

            def cell(k):
                v = incr[k]
                if v is None:
                    return '—'
                return "<span class='g'>0</span>" if v == 0 else fmt(v)
            out += (f"<tr><td class='l'>{l['programa']}</td><td class='l'>{l['area']}</td>"
                    f"<td>{l['n_perm'] or 0}</td><td>{fmt(l['ma_atual'])}</td>"
                    f"<td>{cell('piso')}</td><td>{cell('wmean')}</td>"
                    f"<td>{cell('mediana')}</td><td>{cell('media')}</td></tr>")
        return out

    m4 = stats[4]['nac']; m5 = stats[5]['nac']
    rodape = ''.join(f'<li>{t}</li>' for t in B.RODAPE_PERIODO)

    H = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>

<h1>Plano de Incremento de Produtividade — UnB</h1>
<p class="sub">Quanto a produção por pesquisador precisa aumentar para os programas da UnB subirem de nota (3&rarr;4 e 4&rarr;5)</p>
<p class="meta">Prof. Titular David Lima Azevedo — Grupo de Dinâmica e Ab Initio (GDAI), Núcleo de Estrutura da Matéria,
Instituto de Física, Universidade de Brasília (UnB) · ORCID 0000-0002-3456-554X<br>
Sistema <b>MAPA-PG</b> · dados públicos da CAPES (Coleta Sucupira) e fatores de impacto OpenAlex.</p>

<h2>1. Metodologia</h2>
<p>A <b>nota</b> de cada programa é a vigente (registro do quadriênio 2021-2024). A <b>produção</b> é
medida no quadriênio <b>2017-2020</b> — o último período com coleta CAPES completa — em
<b>artigos em periódico por docente permanente por ano</b> (a métrica de produtividade por pesquisador).
Consideram-se apenas programas <b>acadêmicos</b>. A produção agregada de um grupo de programas usa a
<b>média ponderada</b> pelo número de permanentes (Σ artigos/ano ÷ Σ permanentes).</p>
<p>Para estimar o esforço necessário para subir de nota, comparam-se os programas da UnB de uma nota
com <b>quatro definições de alvo</b> da nota imediatamente superior, em rigor crescente:</p>
<ul>
<li><b>Piso da área</b> — a <i>menor</i> produção entre os programas da nota-alvo <i>na mesma área CAPES</i>
(o limiar empírico para estar naquela nota; é a comparação metodologicamente mais fiel à CAPES).</li>
<li><b>Média ponderada da área</b> — a média (ponderada por permanentes) dos programas da nota-alvo na própria área.</li>
<li><b>Mediana nacional</b> — a mediana dos programas da nota-alvo em todo o país (todas as áreas).</li>
<li><b>Média nacional</b> — a média dos programas da nota-alvo em todo o país.</li>
</ul>
<p>O <i>incremento</i> é quanto falta (art/pesq/ano) para alcançar cada alvo, com piso em zero (programas
já no nível do alvo contam zero, não “sobra”). A meta da coorte em <b>artigos/ano</b> é a soma, por
programa, do incremento × nº de permanentes.</p>

<h2>2. Produção por pesquisador, por nota (Brasil &times; UnB)</h2>
<table>
<tr><th>Nota</th><th>Prog. Brasil</th><th>Ponderada Brasil</th><th>Média Brasil</th><th>Mediana Brasil</th><th>Prog. UnB</th><th>Ponderada UnB</th></tr>
{t1}
</table>
<p class="sub">Artigos por permanente por ano (2017-2020). A produção por pesquisador <b>satura a partir da nota 4</b>
(Brasil ~10,9 na nota 4 e ~11–12 nas notas 5/6/7): acima da nota 4, o que distingue os programas é o
<b>impacto/qualidade</b>, não o volume por pesquisador.</p>

<h2>3. Meta da coorte — artigos/ano a mais, por alvo</h2>
<table>
<tr><th>Transição</th><th>Programas</th><th>&rarr; Piso da área</th><th>&rarr; Média pond. da área</th><th>&rarr; Mediana nacional</th><th>&rarr; Média nacional</th></tr>
{resumo}
</table>
<div class="boxb"><b>Leitura.</b> Pelo <b>piso da área</b>, a produção da UnB já é praticamente suficiente:
os 6 programas nota 3 já estão <i>todos</i> no piso da nota 4 (incremento total <b>zero</b>), e na nota 4
apenas 6 dos 23 ainda têm pequena defasagem (coorte: <b>+{t4['piso']}</b> artigos/ano). As metas só ficam
exigentes quando o alvo são os programas de referência (mediana/média).</div>

<h2 class="pb">4. Detalhe por programa — Nota 3 &rarr; 4</h2>
<p class="sub">Alvos nacionais da nota 4: mediana {fmt(m4['mediana'])} · média {fmt(m4['media'])} art/pesq/ano.
Incremento em art/pesq/ano; <span class="g">0</span> = já atingiu o alvo. Programa em desativação (Botânica) fora do plano.</p>
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Perm.</th><th>Produção atual</th><th>&rarr; Piso área</th><th>&rarr; Méd.pond. área</th><th>&rarr; Mediana nac.</th><th>&rarr; Média nac.</th></tr>
{prog_rows(3)}
</table>

<h2>5. Detalhe por programa — Nota 4 &rarr; 5</h2>
<p class="sub">Alvos nacionais da nota 5: mediana {fmt(m5['mediana'])} · média {fmt(m5['media'])} art/pesq/ano.
Botânica nova (sem produção 2017-2020) fora do plano.</p>
<table>
<tr><th>Programa</th><th>Área CAPES</th><th>Perm.</th><th>Produção atual</th><th>&rarr; Piso área</th><th>&rarr; Méd.pond. área</th><th>&rarr; Mediana nac.</th><th>&rarr; Média nac.</th></tr>
{prog_rows(4)}
</table>

<h2 class="pb">6. Conclusões</h2>
<ul>
<li><b>Volume não é o gargalo para subir de nota.</b> Medida contra o piso da própria área, a produção por
pesquisador da UnB já alcança o nível dos programas mais fracos da nota seguinte — em 3&rarr;4 para todos os
6 programas, e em 4&rarr;5 para 17 dos 23.</li>
<li><b>O salto depende de qualidade/impacto</b> (fator de impacto, internacionalização, formação de
mestres e doutores, proposta do programa), não de simplesmente produzir mais artigos. As faixas de impacto
estão na aba correspondente do relatório em planilha.</li>
<li><b>Alvos nacionais cruzados penalizam áreas de baixa taxa de artigos.</b> Programas de Matemática/Estatística,
por exemplo, podem estar no nível da sua área (incremento zero no piso e na média ponderada) e ainda assim
aparecerem distantes da mediana/média nacionais — que misturam áreas de perfis muito diferentes. O alvo
justo é o da <b>própria área</b> (regra de comparação da CAPES).</li>
<li><b>Maior alavanca absoluta:</b> a Biotecnologia–Rede Pró-Centro-Oeste (63 permanentes) concentra a maior
parte do esforço da coorte nota 4 quando o alvo são os programas de referência.</li>
<li><b>Metas de quantidade (quando aplicáveis):</b> para alcançar a mediana nacional da nota seguinte, a coorte
nota 3 precisaria de +{t3['mediana']} e a nota 4 de +{t4['mediana']} artigos/ano; para a média nacional,
+{t3['media']} e +{t4['media']} artigos/ano.</li>
</ul>

<h2>Nota metodológica — período de referência</h2>
<ul class="foot">{rodape}</ul>

</body></html>"""

    os.makedirs(SAIDA, exist_ok=True)
    html_path = os.path.join(SAIDA, 'relatorio_incremento_pip.html')
    open(html_path, 'w', encoding='utf-8').write(H)
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', SAIDA, html_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(SAIDA, 'relatorio_incremento_pip.pdf')
    print('PDF gerado:', pdf,
          f"({os.path.getsize(pdf)/1024:.0f} KB)" if os.path.exists(pdf) else '(FALHOU)')


if __name__ == '__main__':
    main()
