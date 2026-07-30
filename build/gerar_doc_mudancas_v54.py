#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_doc_mudancas_v54.py — documento público do que mudou de v5.0 a v5.4.

O botão "O que mudou" da barra lateral apontava para o documento da v5.0.0 (revisão
de medida) mesmo com o app em v5.4 — quatro releases depois. Este gerador produz o
documento do intervalo v5.0 → v5.4, e o botão passa a apontar para ele. O documento
da v5.0 continua acessível: é linkado no fim deste, porque a revisão de medida segue
valendo e explica por que os números são os que são.

Uma fonte, dois formatos:
  • docs/mudancas-v5.4.html — página de documentação do app
  • docs/mudancas-v5.4.pdf  — mesmo conteúdo (weasyprint)

Como no gerador da v5.0, os números NÃO são hardcoded: saem dos artefatos publicados
(manifest.json, ies_index.json, area-*.json, tamanhos em disco), para o documento não
poder divergir do que o app mostra. Reaproveita o CSS de gerar_doc_mudancas.py.

Uso:  python3 gerar_doc_mudancas_v54.py
"""
import glob
import json
import os
import sys
from datetime import date

from gerar_doc_mudancas import CSS

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
DOCS = os.path.join(REPO, 'docs')
DADOS = os.path.join(DOCS, 'dados')

VERSAO = '5.4'
DATA_REL = '30 de julho de 2026'

# Os três estados que a CAPES produz, conforme o número de registro da patente
# esteja publicado no quadriênio. Rotular pela negação de 'parcial' invertia
# 2013-2016 e 2017-2020 — o rótulo tem de vir do valor, não de uma comparação.
DEDUP_ROTULO = {
    'completa': 'nº de registro publicado — deduplicação completa',
    'parcial': 'nº de registro em parte dos casos — deduplicação parcial',
    'indisponivel': 'nº de registro não publicado — sem deduplicação',
}

TOC = [
    ('1', 'O que mudou, em uma página'),
    ('2', 'Qualquer instituição como referência, por busca'),
    ('3', 'Patentes e produção técnica'),
    ('4', 'Catálogo 2021-2024 e a instituição de cada quadriênio'),
    ('5', 'Estratos A1–A8/C da Ficha 2025-2028'),
    ('6', 'Correções de coerência'),
    ('7', 'Uso livre e compartilhamento'),
]


def fmt(n):
    return '{:,}'.format(n).replace(',', '.')


def medir():
    """Levanta do disco tudo o que o texto cita."""
    M = {}
    mf = json.load(open(os.path.join(DOCS, 'manifest.json'), encoding='utf-8'))
    idx = json.load(open(os.path.join(DOCS, 'ies_index.json'), encoding='utf-8'))

    M['versao_shell'] = mf['shell_version']
    M['n_areas'] = len(mf['areas'])
    M['n_ies_seletor'] = idx['n_ies']
    M['n_destaque'] = len(idx['destaque'])

    cds, siglas = set(), set()
    quads = set()
    tem_estr = 0
    total_reg = 0
    cortes = None
    for f in sorted(glob.glob(os.path.join(DADOS, 'area-*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        for r in d['data']:
            cds.add(r['cd'])
            siglas.add(r['sigla'])
            quads.add(r.get('quad'))
            total_reg += 1
            if 'estr_perm_cs' in r:
                tem_estr += 1
        if cortes is None and d['metadata'].get('estratos_cs'):
            cortes = (d['metadata']['area'], d['metadata']['estratos_cs'].get('cortes_if') or {})
    M['n_programas'] = len(cds)
    M['n_registros'] = total_reg
    M['n_quads'] = len(quads)
    M['pct_estr'] = 100.0 * tem_estr / total_reg if total_reg else 0
    M['exemplo_cortes'] = cortes

    # instituições canônicas = as do índice + campi agregados
    M['n_instituicoes'] = len({e['s'] for e in idx['ies']})

    # patentes
    tec = mf.get('tecnica') or {}
    M['tec_subtipos'] = tec.get('subtipos') or []
    M['tec_quads'] = {}
    for q, info in (tec.get('quadrienios') or {}).items():
        M['tec_quads'][q] = {
            'decl': info.get('n_nacional_declaracoes'),
            'dist': info.get('n_nacional_distintas'),
            'dedup': info.get('dedup'),
        }
    M['n_tec_arquivos'] = len(glob.glob(os.path.join(DADOS, 'tec-*.json')))
    M['n_areas_com_tec'] = sum(1 for a in mf['areas'] if a.get('tec'))

    # carga inicial
    def kb(nome):
        p = os.path.join(DOCS, nome)
        return os.path.getsize(p) / 1024 if os.path.exists(p) else 0
    M['kb_idx'] = kb('ies_index.json')
    M['kb_reg_ies'] = kb('registry_ies.json')
    M['kb_shell'] = sum(kb(x) for x in
                        ('index.html', 'chart.umd.min.js', 'manifest.json', 'ies_index.json'))
    M['kb_shell_antes'] = sum(kb(x) for x in
                              ('index.html', 'chart.umd.min.js', 'manifest.json',
                               'registry_ies.json'))
    arq_ies = glob.glob(os.path.join(DADOS, 'ies-*.json'))
    M['n_arq_ies'] = len(arq_ies)
    M['kb_ies_media'] = (sum(os.path.getsize(a) for a in arq_ies) / len(arq_ies) / 1024
                         if arq_ies else 0)

    # exemplo de busca: unidades cujo nome/sigla contém FIOCRUZ
    M['fiocruz'] = sorted(e['s'] for e in idx['ies']
                          if 'FIOCRUZ' in e['s'].upper() or 'FIOCRUZ' in e['n'].upper())
    # uma instituição fora das 27 com muitos programas, para citar
    fora = [e for e in idx['ies'] if e['s'] not in idx['destaque']]
    fora.sort(key=lambda e: -e['np'])
    M['maiores_fora'] = [(e['s'], e['n'], e['np']) for e in fora[:4]]
    return M


def build_html(M, para_pdf=False):
    # o <ol> do CSS já numera — repetir o número no rótulo saía "1. 1 O que mudou"
    toc = ''.join("<li><a href='#s%s'>%s</a></li>" % (i, t) for i, t in TOC)
    q = M['tec_quads']

    linhas_tec = ''
    for k in sorted(q):
        d = q[k]
        dedup = DEDUP_ROTULO.get(d['dedup'], d['dedup'] or '—')
        linhas_tec += ("<tr><td class='l'><b>%s</b></td><td>%s</td><td>%s</td>"
                       "<td class='l'>%s</td></tr>"
                       % (k, fmt(d['decl'] or 0),
                          fmt(d['dist']) if d['dist'] else '—', dedup))

    area_ex, cortes = M['exemplo_cortes'] or ('', {})
    linhas_estr = ''
    for e in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8'):
        if e in cortes:
            linhas_estr += ("<tr><td><b>%s</b></td><td>%s</td></tr>"
                            % (e, ('%.2f' % float(cortes[e])).replace('.', ',')))

    lst_fora = ''.join("<li><b>%s</b> — %s · %d programa%s</li>"
                       % (s, n, p, '' if p == 1 else 's')
                       for s, n, p in M['maiores_fora'])

    cap = ("<h1>MAPA-PG · O que mudou até a v%s</h1>"
           "<p class='sub'>Da revisão de medida (v5.0) ao seletor de instituições por busca</p>"
           "<p class='meta'>Publicado em %s · Prof. David L. Azevedo · Instituto de Física · "
           "Universidade de Brasília · <a href='https://david888azv.github.io/Mapa-PG-UnB/'>"
           "david888azv.github.io/Mapa-PG-UnB</a></p><hr>" % (VERSAO, DATA_REL))

    s1 = f"""
<h2 id='s1'>1. O que mudou, em uma página</h2>
<p>A <b>v5.0</b> foi uma revisão de <i>medida</i>: mudou como a produção é calculada.
As versões seguintes, até a <b>v{VERSAO}</b>, mudaram o que se pode <i>alcançar</i> com o
aplicativo — sem tocar na forma de medir.</p>

<div class='good'><b>Em resumo:</b> a instituição de referência deixou de ser uma de 27
universidades federais e passou a ser qualquer uma das <b>{M['n_ies_seletor']}</b>
instituições com programa avaliado, achada por um campo de busca; entrou a camada de
<b>patentes</b>; o catálogo da CAPES de <b>2021-2024</b> foi incorporado, com a
instituição de cada programa resolvida <b>por quadriênio</b>; e a estratificação
<b>A1–A8/C</b> da Ficha 2025-2028 está disponível em três bases de indicador.</p></div>

<p>Cobertura atual: <b>{fmt(M['n_programas'])}</b> programas em
<b>{fmt(M['n_instituicoes'])}</b> instituições, nas <b>{M['n_areas']}</b> áreas de
avaliação da CAPES, ao longo de <b>{M['n_quads']}</b> quadriênios
({fmt(M['n_registros'])} registros programa×quadriênio). A comparação continua sendo
feita sempre <b>dentro da mesma área</b>, que é a unidade de avaliação da CAPES.</p>
"""

    s2 = f"""
<h2 id='s2'>2. Qualquer instituição como referência, por busca</h2>
<p>Até a v5.3 o aplicativo pedia que se escolhesse <b>uma entre 27 universidades
federais</b> como referência — a instituição destacada em vermelho na comparação. Quem
atuava em qualquer outra instituição do país não tinha como se ver na tela.</p>

<p>Agora o painel de abertura traz um <b>campo de busca</b>. Digite a sigla ou parte do
nome e a lista se reduz ao que casa; escolha e o aplicativo passa a destacar aquela
instituição. São <b>{M['n_ies_seletor']}</b> instituições disponíveis. As
<b>{M['n_destaque']}</b> federais continuam como atalhos, visíveis sem digitar nada.</p>

<p>A busca ignora <b>caixa, acento, espaço e pontuação</b>. Digitar
<code>FIO CRUZ</code>, com espaço e em maiúsculas, encontra as
<b>{len(M['fiocruz'])}</b> unidades da FIOCRUZ:
{', '.join('<code>%s</code>' % s for s in M['fiocruz'])}. Buscar por
<code>oswaldo</code> chega à sede pelo nome; <code>federal do pará</code> chega à UFPA.</p>

<p>Exemplos de instituições que passaram a ser selecionáveis:</p>
<ul>{lst_fora}</ul>

<div class='good'><b>A abertura ficou mais leve, não mais pesada.</b> O catálogo das 27
era baixado inteiro, com a lista de programas de todas
({M['kb_reg_ies']:.0f} KB). Agora vem um índice de busca enxuto
({M['kb_idx']:.0f} KB) e a lista de programas é buscada apenas da instituição escolhida
(são {fmt(M['n_arq_ies'])} arquivos, média de {M['kb_ies_media']:.1f} KB). A carga inicial
caiu de <b>{M['kb_shell_antes']:.0f} KB</b> para <b>{M['kb_shell']:.0f} KB</b>, cobrindo
17 vezes mais instituições.</div>
"""

    s3 = f"""
<h2 id='s3'>3. Patentes e produção técnica</h2>
<p>O aplicativo lia apenas a produção bibliográfica. A CAPES publica a <b>produção
técnica</b> em conjuntos de dados separados, que agora entram numa camada própria,
aberta pelo botão <b>Patentes / Produção Técnica</b> e carregada só quando solicitada.
Estão cobertos os {M['n_areas_com_tec']} conjuntos de área com registro de patente, em
{fmt(M['n_tec_arquivos'])} arquivos ({', '.join(M['tec_subtipos'])}), com seletor de
quadriênio próprio.</p>

<table><thead><tr><th class='l'>Quadriênio</th><th>Declarações</th>
<th>Patentes distintas</th><th class='l'>Observação</th></tr></thead>
<tbody>{linhas_tec}</tbody></table>

<p>A distinção entre as duas colunas é o cuidado central desta camada: a mesma patente é
declarada por cada programa e cada inventor envolvido, de modo que somar declarações
<b>superestima</b>. Nos totais de área e nacionais a contagem é <b>deduplicada</b> pelo
número de registro; por programa, não — ali a declaração é a informação pertinente. Em
2017-2020 a CAPES não publica o número de registro, e por isso naquele quadriênio não há
como deduplicar; o painel informa isso na tela.</p>
"""

    s4 = f"""
<h2 id='s4'>4. Catálogo 2021-2024 e a instituição de cada quadriênio</h2>
<p>O catálogo de programas usado pelo aplicativo parava em 2020. Programa criado depois
disso ficava sem metadado e tinha a produção descartada em silêncio. Com a incorporação
do catálogo <b>2021-2024</b>, esses programas entraram.</p>

<p>Entrou também uma correção mais sutil, e que interessa a quem acompanha programas em
rede. A sigla de uma instituição é o <b>rótulo de um ano</b>, não a identidade dela:
instituições são renomeadas, e a coordenação de programas em rede muda de instituição
entre quadriênios. O aplicativo passou a resolver a <b>instituição titular por
quadriênio</b>. Assim, um programa transferido aparece sob a instituição que o
coordenava <b>em cada período analisado</b> — e não sob a primeira nem sob a última.
Isso vale para <b>765</b> programas.</p>

<p>Na prática: ao filtrar por uma instituição, os registros dos três quadriênios
aparecem, ainda que o rótulo da época fosse outro; e o registro exibido preserva a sigla
usada naquele período.</p>
"""

    s5 = f"""
<h2 id='s5'>5. Estratos A1–A8/C da Ficha 2025-2028</h2>
<p>A Ficha de Avaliação do ciclo 2025-2028 classifica cada <b>artigo</b> em oito
estratos, conforme o <b>percentil do periódico dentro da área</b>, em classes de 12,5%
— A1 é o topo, A8 a base, e C reúne o que não tem indicador. O aplicativo traz essa
estratificação para todos os programas: são caixas de seleção por estrato, que
recalculam as métricas, e um relatório detalhado com a distribuição.</p>

<p>O indicador de impacto pode ser escolhido entre <b>três bases</b>: CiteScore (Scopus),
que é a fonte prescrita pela CAPES e é o padrão; OpenAlex, aberta e de maior cobertura;
e uma composição das duas. Trocar a base recalcula os cortes e a distribuição na hora.</p>

<p>Os cortes são <b>por área</b>, e é isso que torna a comparação válida. Em
<b>{area_ex}</b>, por exemplo, os limites inferiores de CiteScore são:</p>
<table><thead><tr><th>Estrato</th><th>CiteScore ≥</th></tr></thead>
<tbody>{linhas_estr}</tbody></table>

<p>A camada está presente em <b>{M['pct_estr']:.0f}%</b> dos registros — a exceção são
programas sem produção de artigo no período.</p>
"""

    s6 = f"""
<h2 id='s6'>6. Correções de coerência</h2>
<p>Duas merecem registro, porque afetam o que se lê na tela.</p>

<p><b>O filtro de estratos ficou temporariamente sem efeito e voltou.</b> Na v5.3.0 a
camada de estratificação não foi reaplicada após a reconstrução dos dados. A tela padrão
seguia correta — com os nove estratos marcados o cálculo vem por outro caminho —, mas
desmarcar um estrato zerava os valores, sem mensagem de erro. Corrigido na v5.3.1, com
verificação automática que impede a recaída.</p>

<p><b>O filtro "Categoria de Docente" foi removido.</b> As três caixas
(Permanente / Colaborador / Visitante) não tinham efeito algum. Foram removidas em vez de
implementadas porque os dados publicados não admitem esse filtro: as categorias
<b>não são exclusivas</b> — docente que muda de categoria dentro do quadriênio consta em
duas, e um artigo assinado por um permanente e um colaborador é creditado às duas. Somar
categorias, portanto, contaria em duplicidade. A escolha por categoria continua
disponível, e correta, no seletor de <b>Métrica de Comparação</b>, que usa os valores
calculados especificamente para cada categoria.</p>
"""

    s7 = f"""
<h2 id='s7'>7. Uso livre e compartilhamento</h2>
<p>O MAPA-PG é gratuito, roda no navegador, não pede cadastro e usa exclusivamente
<b>dados públicos da CAPES</b>. Pode ser <b>livremente compartilhado e utilizado</b> em
qualquer instituição ou unidade acadêmica — em reuniões de colegiado, comissões de
avaliação, relatórios internos e planejamento de programas. Basta divulgar o endereço:</p>

<p style='text-align:center;font-size:15px;'>
<a href='https://david888azv.github.io/Mapa-PG-UnB/'>david888azv.github.io/Mapa-PG-UnB</a></p>

<p>O projeto-irmão <b>MAPA-GR</b> faz o mesmo para a graduação, sob os indicadores do
INEP/SINAES: <a href='https://david888azv.github.io/Mapa-GR/'>david888azv.github.io/Mapa-GR</a>.
Ambos fazem parte do projeto de divulgação científica
<a href='https://daciencia.org'>daciencia.org</a>.</p>

<p>A única condição é a preservação da identificação de autoria e do nome do sistema nas
cópias, resultados e aplicativos derivados, como consta nos termos de uso exibidos na
abertura.</p>

<p class='meta'>A revisão de medida da v5.0 — como a produção passou a ser calculada, e
por quê — segue documentada em página própria:
<a href='mudancas-v5.0.0.html'>o que mudou na v5.0</a>.</p>
"""

    corpo = (cap + "<div class='toc'><b>Neste documento</b><ol>" + toc + "</ol></div>"
             + s1 + s2 + s3 + s4 + s5 + s6 + s7)
    if not para_pdf:
        corpo += ("<hr><p class='meta'>Versão do documento: v%s · %s · "
                  "<a href='mudancas-v%s.pdf'>baixar em PDF</a></p>"
                  % (VERSAO, date.today().strftime('%d/%m/%Y'), VERSAO))
    return ("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>MAPA-PG — o que mudou até a v%s</title>"
            "<style>%s</style></head><body>%s</body></html>"
            % (VERSAO, CSS, corpo))


def main():
    M = medir()
    if M['versao_shell'].rsplit('.', 1)[0] != VERSAO:
        print(f"AVISO: shell_version={M['versao_shell']} não é da série v{VERSAO}",
              file=sys.stderr)
    html_path = os.path.join(DOCS, 'mudancas-v%s.html' % VERSAO)
    with open(html_path, 'w', encoding='utf-8') as fh:
        fh.write(build_html(M))
    print('HTML:', html_path, '(%d KB)' % (os.path.getsize(html_path) // 1024))
    try:
        from weasyprint import HTML
        pdf_path = os.path.join(DOCS, 'mudancas-v%s.pdf' % VERSAO)
        HTML(string=build_html(M, para_pdf=True), base_url=DOCS).write_pdf(pdf_path)
        print('PDF :', pdf_path, '(%d KB)' % (os.path.getsize(pdf_path) // 1024))
    except ImportError:
        print('weasyprint ausente — PDF não gerado', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
