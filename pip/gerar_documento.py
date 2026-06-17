#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o documento PDF com a METODOLOGIA + RESULTADOS + CONCLUSÕES da análise
de produção dos programas de pós-graduação (sistema MAPA-PG), incluindo as
figuras de casos críticos e a comparação com a mediana.

Compõe um HTML (com as figuras em base64) e converte para PDF via LibreOffice.
Saída: saida/relatorio_mapa_pg_metodologia.pdf
"""
import os, io, base64, subprocess
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, 'saida')


def img64(nome, width_cm=15.0):
    """Carrega o PNG e RECARIMBA o DPI para que sua largura física = width_cm.
    O LibreOffice usa o DPI embutido (pHYs) para dimensionar a imagem na página,
    evitando que figuras largas sejam renderizadas no tamanho nativo e cortadas."""
    p = os.path.join(SAIDA, nome)
    if not os.path.exists(p):
        return ''
    im = Image.open(p)
    dpi = im.width / (width_cm / 2.54)        # DPI que faz a imagem ter width_cm
    buf = io.BytesIO()
    im.save(buf, format='PNG', dpi=(dpi, dpi))
    b = base64.b64encode(buf.getvalue()).decode()
    return f'data:image/png;base64,{b}'


# --- nota de rodapé sobre o período (mantida do relatório PIP anterior) ----
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

CSS = """
@page { size: A4; margin: 2.0cm 1.8cm; }
body { font-family: 'Liberation Serif','Times New Roman',serif; font-size: 11pt;
       color: #222; line-height: 1.42; }
h1 { font-size: 20pt; color: #1A2A3A; margin: 0 0 2pt 0; }
h2 { font-size: 14pt; color: #1F618D; border-bottom: 2px solid #AED6F1;
     padding-bottom: 2px; margin-top: 20px; }
h3 { font-size: 12pt; color: #2C3E50; margin-top: 14px; margin-bottom: 4px; }
.sub { color: #666; font-size: 10.5pt; margin: 0 0 4px 0; }
.meta { color: #888; font-size: 9.5pt; margin-bottom: 14px; }
p { margin: 6px 0; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 10pt; }
th { background: #2C3E50; color: #fff; padding: 5px 7px; text-align: center; }
td { border: 1px solid #ccc; padding: 4px 7px; text-align: center; }
td.l { text-align: left; }
.g { color: #1E8449; font-weight: bold; } .y { color: #9A7D0A; font-weight: bold; }
.r { color: #C0392B; font-weight: bold; } .k { color: #566573; font-weight: bold; }
.box { background: #Fef9e7; border-left: 4px solid #F1C40F; padding: 8px 12px; margin: 10px 0; }
.boxr { background: #FDEDEC; border-left: 4px solid #E74C3C; padding: 8px 12px; margin: 10px 0; }
figure { margin: 10px 0 4px 0; text-align: center; page-break-inside: avoid; }
/* o DPI recarimbado em img64() define a largura física (~15cm); a largura é
   menor que a área de texto (17.4cm), garantindo margem dos dois lados */
figure img { width: 15cm; height: auto; border: 1px solid #ddd;
             display: block; margin: 0 auto; }
p.cap { font-size: 9.5pt; color: #555; margin: 3px 0 0 0; font-style: italic;
        text-align: center; clear: both; }
.foot { font-size: 9pt; color: #555; }
.foot li { margin-bottom: 4px; }
.pb { page-break-before: always; }
ul { margin: 6px 0 6px 0; } li { margin: 3px 0; }
"""


def build_html():
    fig_unb = img64('quedas_criticas.png')
    fig_unb_prof = img64('quedas_criticas_profissional.png')
    fig_nac = img64('quedas_criticas_nacional.png')
    fig_nac_prof = img64('quedas_criticas_nacional_profissional.png')
    rodape = ''.join(f'<li>{t}</li>' for t in RODAPE_PERIODO)

    H = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>

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
<table>
<tr><th>Ano-base</th><th>2013</th><th>2014</th><th>2015</th><th>2016</th><th>2017</th><th>2018</th>
<th>2019</th><th>2020</th><th>2021</th><th>2022</th><th>2023</th><th>2024</th></tr>
<tr><td class="l"><b>Programas c/ docentes</b></td>
<td>3.568</td><td>3.765</td><td>3.946</td><td>4.186</td><td>4.347</td><td>4.363</td>
<td>4.570</td><td>4.559</td><td><b>4.698</b></td>
<td class="r">0</td><td class="r">0</td><td class="r">0</td></tr>
</table>
<p>Por isso a métrica <i>artigos por pesquisador</i> em 2022-2024 é uma <b>estimativa</b> (denominador
herdado de 2021), enquanto a contagem absoluta de artigos por ano (numerador) é medida diretamente
dos dados.</p>

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

</body></html>"""
    return H


def main():
    html = build_html()
    html_path = os.path.join(SAIDA, 'relatorio_mapa_pg_metodologia.html')
    open(html_path, 'w', encoding='utf-8').write(html)
    # HTML -> PDF via LibreOffice
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', SAIDA, html_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(SAIDA, 'relatorio_mapa_pg_metodologia.pdf')
    print('PDF gerado:', pdf, f"({os.path.getsize(pdf)/1024:.0f} KB)" if os.path.exists(pdf) else '(FALHOU)')


if __name__ == '__main__':
    main()
