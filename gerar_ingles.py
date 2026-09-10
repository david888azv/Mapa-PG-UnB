#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera a versao em INGLES do MAPA-PG em docs/en/, a partir das paginas em portugues.

    python3 gerar_ingles.py             # escreve docs/en/*.html
    python3 gerar_ingles.py --conferir  # so diz se docs/en/ esta em dia

As paginas de docs/ continuam sendo as UNICAS editaveis a mao; docs/en/ e
derivado, como en/ no daciencia.org e como mapa-pg-offline e derivado do online.
A tabela de traducao vive em i18n/traducoes_en.py e cada trecho dela tem de
existir **exatamente uma vez** na pagina PT: se o texto mudar em portugues sem
que a tabela acompanhe, este script PARA com erro, em vez de publicar um ingles
defasado — que e como versao estrangeira apodrece sem ninguem notar.

Nada e traduzido por acidente: so o que esta na tabela. Isso importa aqui mais do
que na landing, porque as strings do JS misturam rotulo de interface com DADO
(nome de instituicao, sigla, chave de objeto). O que nao esta na tabela fica
exatamente como estava.

COMO A PAGINA EM en/ ACHA OS DADOS
Um `<base href="../">` no <head>: toda URL relativa passa a resolver a partir da
raiz do app. Assim `fetch('dados/metadata.json')`, `fetch(meta.arquivo)` (que vem
de dentro do JSON, fora do alcance de qualquer substituicao), os icones, o
Chart.js e o manifesto continuam achando seus arquivos sem que exista uma copia
deles em en/. O preco e que os links ENTRE paginas do app precisam do prefixo
`en/` — sao poucos e enumeraveis, e o audit no fim confere se sobrou algum.

Nao ha `href="#..."` em nenhuma das paginas (conferido), que e a armadilha
classica de <base>: ali ele mandaria o clique para a pagina de cima.

O service worker e o manifesto PWA continuam sendo os do app (escopo /Mapa-PG-UnB/,
que cobre /Mapa-PG-UnB/en/). O nome que aparece ao instalar fica em portugues — e a
troca por um manifesto proprio em ingles seria uma decisao de identidade do app,
nao de traducao.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n"))
import traducoes_en as T

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
SAIDA = os.path.join(DOCS, "en")

PAGINAS = ["index", "help-doc"]
# faixas-if.html fica SO em portugues: e a pagina legada de faixas de IF,
# orfa desde a v5.0 (nada linka para ela, e ela nao esta no sitemap).
# Traduzir uma tela superada so criaria uma porta de entrada para o que
# o app nao usa mais.
# paginas que sao TEXTO, nao interface: traduzidas por secao (ver secoes_de_documento)
PAGINAS_DOCUMENTO = ["help-doc"]
# historico de versoes: fica em portugues (decisao de escopo), e por isso os
# links para ele nao levam o prefixo en/
PAGINAS_SO_EM_PORTUGUES = ["mudancas-v5.0.0.html", "mudancas-v5.4.html", "mudancas-v5.8.html"]
URL = "https://david888azv.github.io/Mapa-PG-UnB/"

# palavras-funcao do portugues: sobrando no texto visivel do ingles, algum
# trecho escapou da tabela (rede de seguranca, nao trava)
MARCAS_PT = re.compile(
    r"\b(de|da|do|das|dos|é|são|está|com|para|não|uma|mais|sem|também|já|pelo|"
    r"pela|que|seu|sua|nos|nas|como|ser|foi|entre|sobre|todos|todas|ou)\b", re.I)


class Falha(SystemExit):
    pass


def aplica(html, tabela, pagina):
    """Aplica a tabela exigindo que a contagem BATA.

    Cada entrada e (pt, en) — o trecho tem de aparecer uma vez — ou
    (pt, en, n), quando o mesmo texto aparece n vezes de proposito (o rotulo de
    um eixo repetido em dois graficos, por exemplo) e as n devem ser trocadas.
    Exigir o numero exato, e nao "pelo menos uma", e o que mantem a trava: se a
    pagina ganhar uma sexta ocorrencia amanha, o gerador para e pergunta.
    """
    for entrada in tabela:
        pt, en = entrada[0], entrada[1]
        esperado = entrada[2] if len(entrada) > 2 else 1
        n = html.count(pt)
        if n == 0:
            raise Falha(
                "\n%s.html: trecho da tabela nao existe mais na pagina em portugues.\n"
                "O texto PT mudou e i18n/traducoes_en.py ficou para tras. Atualize:\n\n  %r\n"
                % (pagina, pt[:200]))
        if n != esperado:
            raise Falha(
                "\n%s.html: trecho aparece %d vezes, a tabela esperava %d.\n"
                "Se as %d sao legitimas, declare (pt, en, %d); se nao, ponha mais\n"
                "contexto na chave:\n\n  %r\n" % (pagina, n, esperado, n, n, pt[:200]))
        html = html.replace(pt, en)
    return html


def estrutura(html, pagina):
    url_pt = URL + ("" if pagina == "index" else pagina + ".html")
    url_en = URL + "en/" + ("" if pagina == "index" else pagina + ".html")

    # 1) idioma e URLs proprias
    html = html.replace('<html lang="pt-BR">', '<html lang="en">', 1)
    html = html.replace('<link rel="canonical" href="%s">' % url_pt,
                        '<link rel="canonical" href="%s">' % url_en, 1)
    html = html.replace('<meta property="og:url" content="%s">' % url_pt,
                        '<meta property="og:url" content="%s">' % url_en, 1)
    html = html.replace('<meta property="og:locale" content="pt_BR">',
                        '<meta property="og:locale" content="en_US">\n'
                        '<meta property="og:locale:alternate" content="pt_BR">', 1)

    # 2) <base>: as URLs relativas passam a valer a partir da raiz do app
    marca = '<meta charset="UTF-8">'
    if marca not in html:
        raise Falha("%s.html: sem <meta charset> para ancorar o <base>" % pagina)
    html = html.replace(
        marca,
        marca + '\n<!-- en/ e subpasta: sem isto, dados, icones e Chart.js seriam\n'
                '     procurados em /Mapa-PG-UnB/en/ e nao existiriam la. -->\n'
                '<base href="../">', 1)

    # 3) links ENTRE paginas do app: apontam para a irma em ingles
    for outra in PAGINAS:
        for aspas in ("'", '"'):
            html = html.replace("%s%s.html" % (aspas, outra),
                                "%sen/%s.html" % (aspas, outra))
    # As notas de versao (mudancas-*.html) NAO sao traduzidas — ficam em
    # portugues, por decisao de escopo. Como o <base> aponta para a raiz do app,
    # o link relativo ja as acha; so nao pode ganhar o prefixo en/.
    for legada in PAGINAS_SO_EM_PORTUGUES:
        for aspas in ("'", '"'):
            html = html.replace("%sen/%s" % (aspas, legada), "%s%s" % (aspas, legada))

    # 4) numeros e datas no formato local do leitor
    html = html.replace("toLocaleString('pt-BR')", "toLocaleString('en-US')")
    html = html.replace("toLocaleDateString('pt-BR'", "toLocaleDateString('en-US'")
    html = html.replace('toLocaleString("pt-BR")', 'toLocaleString("en-US")')

    # 5) o alternador, virado de lado
    alvo = "index" if pagina == "index" else pagina
    velho = ('<div class="langsel"><span class="cur" aria-current="true">PT</span>'
             '<a href="en/%s.html" hreflang="en" lang="en">EN</a></div>' % alvo)
    if velho not in html:
        raise Falha("%s.html: alternador PT|EN nao encontrado na pagina de origem" % pagina)
    html = html.replace(
        velho,
        '<div class="langsel"><a href="../%s.html" hreflang="pt-BR" lang="pt-BR">PT</a>'
        '<span class="cur" aria-current="true">EN</span></div>' % alvo, 1)
    return html


def secoes_de_documento(html, pagina):
    """Troca secao inteira de documento pela versao em ingles de i18n/doc_en/.

    A pagina de Ajuda nao e um punhado de rotulos: e um texto de milhares de
    palavras. Fatiar prosa em centenas de pares "trecho PT -> trecho EN" seria
    ilegivel e frageil (qualquer virgula mexida quebraria uma chave). Aqui a
    unidade e a SECAO: cada `<div class="section" id="sec-x">` do documento tem
    um arquivo i18n/doc_en/<pagina>__<sec-x>.html com a versao inglesa inteira.

    A trava continua existindo, so que por SELO: junto de cada arquivo em ingles
    fica o sha256 do bloco em portugues que ele traduz (primeira linha do
    arquivo, num comentario). Se o portugues for editado, o selo nao bate e o
    gerador PARA — a revisao do ingles vira obrigatoria, que e o que se quer num
    documento. Secao sem arquivo fica em portugues de proposito (e o caso do
    historico de versoes) e recebe um aviso em ingles no topo.
    """
    import hashlib

    def bloco(m):
        ini = m.end()
        prox = html.find('<div class="section', ini)
        return ini, (prox if prox != -1 else html.find("</div>\n</div>\n<script", ini))

    saida, pos = [], 0
    for m in re.finditer(r'<div class="section(?: active)?" id="(sec-[\w-]+)">', html):
        sec = m.group(1)
        ini, fim = bloco(m)
        pt = html[ini:fim]
        selo = hashlib.sha256(pt.encode("utf-8")).hexdigest()[:16]
        caminho = os.path.join(BASE, "i18n", "doc_en", "%s__%s.html" % (pagina, sec))

        saida.append(html[pos:ini])
        if os.path.exists(caminho):
            texto = io.open(caminho, encoding="utf-8").read()
            cab, _, corpo = texto.partition("\n")
            esperado = cab.replace("<!-- sha:", "").replace("-->", "").strip()
            if esperado != selo:
                raise Falha(
                    "\n%s.html, secao %s: o texto EM PORTUGUES mudou (selo %s, o arquivo\n"
                    "em ingles traduz %s). Revise i18n/doc_en/%s__%s.html e atualize a\n"
                    "primeira linha para <!-- sha:%s -->\n"
                    % (pagina, sec, selo, esperado, pagina, sec, selo))
            saida.append(corpo)
        else:
            saida.append(
                '\n<div class="info-box" style="border-left-color:#F39C12;background:#FFF8E1;">\n'
                '    <strong>In Portuguese.</strong> This section is the version history and is\n'
                '    kept in the original language.\n</div>\n' + pt)
        pos = fim
    saida.append(html[pos:])
    return "".join(saida)


def audita(html, pagina):
    """Referencia relativa que o <base> mandaria para o lugar errado."""
    problemas = []
    for m in re.finditer(r"""(?:href|src|action)=["']([^"'#][^"']*)["']""", html):
        u = m.group(1)
        if u.startswith(("http", "//", "mailto:", "data:", "../", "en/", "?")):
            continue
        if u.endswith(".html") and u not in PAGINAS_SO_EM_PORTUGUES:
            problemas.append("link relativo nao redirecionado: %s" % u)
    for m in re.finditer(r"""(?:window\.open|location\.href\s*=)\s*\(?["']([^"']+)["']""", html):
        u = m.group(1)
        if (u.endswith(".html") and not u.startswith(("../", "en/", "http"))
                and u not in PAGINAS_SO_EM_PORTUGUES):
            problemas.append("navegacao relativa nao redirecionada: %s" % u)
    return problemas


def sobrou_pt(html):
    """Portugues que sobrou — no HTML estatico E dentro do JavaScript.

    Olhar so o HTML estatico nao basta: boa parte da interface destas paginas e
    montada em template literal dentro do JS, as vezes em blocos de varias
    linhas que nenhum extrator de strings simples enxerga. Foi assim que um
    bloco inteiro da tela do modo TOP passou despercebido. Aqui as duas metades
    sao varridas, e os COMENTARIOS do codigo ficam de fora — comentario e para
    quem mantem o portugues, nao para quem le a pagina.

    E aviso, nao trava: nome proprio e sigla podem casar por acidente.
    """
    achados = {}

    corpo = html[html.index("<body"):]
    sem_js = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", corpo, flags=re.S)
    for m in MARCAS_PT.finditer(re.sub(r"<[^>]+>", " ", sem_js)):
        achados.setdefault(m.group(0).lower(), 0)
        achados[m.group(0).lower()] += 1

    js = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S))
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)          # comentario de bloco
    js = re.sub(r"(?m)^\s*//.*$", " ", js)                   # comentario de linha
    for m in re.finditer(r"(['\"`])((?:(?!\1)[^\\]|\\.){2,600})\1", js, flags=re.S):
        for w in MARCAS_PT.finditer(m.group(2)):
            achados.setdefault(w.group(0).lower(), 0)
            achados[w.group(0).lower()] += 1

    return sorted(achados.items(), key=lambda kv: -kv[1])


def main():
    conferir = "--conferir" in sys.argv
    print("MAPA-PG  PT -> EN" + ("  (conferencia)" if conferir else ""))
    if not conferir and not os.path.isdir(SAIDA):
        os.makedirs(SAIDA)
    tudo_ok = True
    for pagina in PAGINAS:
        tabela = getattr(T, pagina.replace("-", "_").upper(), None)
        if tabela is None:
            print("  %-16s sem tabela em i18n/traducoes_en.py — PULADA" % (pagina + ".html"))
            continue
        html = io.open(os.path.join(DOCS, pagina + ".html"), encoding="utf-8").read()
        html = aplica(html, tabela, pagina)
        if pagina in PAGINAS_DOCUMENTO:
            html = secoes_de_documento(html, pagina)
        html = estrutura(html, pagina)

        for p in audita(html, pagina):
            raise Falha("%s.html: %s" % (pagina, p))
        resto = sobrou_pt(html)
        if resto:
            print("  ! %s: portugues remanescente — %s"
                  % (pagina, ", ".join("%s(%d)" % (p, n) for p, n in resto[:14])))

        destino = os.path.join(SAIDA, pagina + ".html")
        if conferir:
            atual = io.open(destino, encoding="utf-8").read() if os.path.exists(destino) else None
            ok = atual == html
            tudo_ok = ok and tudo_ok
            print("  en/%-16s %s" % (pagina + ".html", "em dia" if ok else "DESATUALIZADO"))
        else:
            io.open(destino, "w", encoding="utf-8").write(html)
            print("  en/%-16s %6.1f KB · %d trechos" % (pagina + ".html",
                  len(html.encode("utf-8")) / 1024.0, len(tabela)))
    if conferir and not tudo_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
