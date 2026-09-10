#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mostra o que, na pagina JA GERADA em docs/en/, ainda esta em portugues.

    python3 i18n/pendentes.py comparador

O gerador avisa QUANTAS palavras portuguesas sobraram; este script diz QUAIS
trechos as contem, que e o que se precisa para completar a tabela. Roda sobre o
resultado, nao sobre a fonte — assim mostra exatamente o que o leitor veria.

Cobre os blocos de HTML dentro de template literal do JS, que e onde o texto
costuma se esconder: sao multilinha e nenhum extrator de strings simples os
enxerga.
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARCAS = re.compile(
    r"\b(de|da|do|das|dos|é|são|está|com|para|não|uma|mais|sem|também|já|pelo|"
    r"pela|que|seu|sua|nos|nas|como|ser|foi|entre|sobre|todos|todas|ou)\b", re.I)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pagina = sys.argv[1].replace(".html", "")
    html = io.open(os.path.join(BASE, "docs", "en", pagina + ".html"), encoding="utf-8").read()

    corpo = html[html.index("<body"):]
    sem_js = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", corpo, flags=re.S)
    print("### HTML ESTATICO ###")
    for t in dict.fromkeys(re.split(r"<[^>]+>", sem_js)):
        t = t.strip()
        if len(t) > 2 and MARCAS.search(t):
            print("  |%s|" % t[:300])

    js = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S))
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    js = re.sub(r"(?m)^\s*//.*$", " ", js)
    print("\n### DENTRO DO JAVASCRIPT ###")
    for m in dict.fromkeys(
            m.group(2) for m in re.finditer(r"(['\"`])((?:(?!\1)[^\\]|\\.){2,900})\1", js, flags=re.S)):
        if MARCAS.search(m):
            print("  |%s|" % m.strip()[:500])


if __name__ == "__main__":
    main()
