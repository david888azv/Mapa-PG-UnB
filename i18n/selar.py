#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carimba, em cada arquivo de i18n/doc_en/, o selo do bloco em portugues que ele traduz.

    python3 i18n/selar.py              # confere e avisa o que esta fora de data
    python3 i18n/selar.py --gravar     # regrava a primeira linha com o selo atual

O selo e o sha256 do trecho em portugues no momento em que a traducao foi feita.
E o que permite ao gerador PARAR quando alguem edita a pagina em portugues sem
rever o ingles — a falha de sempre em site bilingue.

Rodar com --gravar depois de traduzir e o passo normal. Rodar com --gravar SEM
ter revisado o ingles e como desligar o alarme de incendio: o gerador volta a
passar, e a versao inglesa fica mentindo em silencio.
"""
import hashlib
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_EN = os.path.join(BASE, "i18n", "doc_en")


def secoes(pagina):
    html = io.open(os.path.join(BASE, "docs", pagina + ".html"), encoding="utf-8").read()
    for m in re.finditer(r'<div class="section(?: active)?" id="(sec-[\w-]+)">', html):
        ini = m.end()
        prox = html.find('<div class="section', ini)
        fim = prox if prox != -1 else html.find("</div>\n</div>\n<script", ini)
        yield m.group(1), html[ini:fim]


def main():
    gravar = "--gravar" in sys.argv
    paginas = sorted({f.split("__")[0] for f in os.listdir(DOC_EN) if "__" in f})
    for pagina in paginas:
        print(pagina)
        for sec, pt in secoes(pagina):
            caminho = os.path.join(DOC_EN, "%s__%s.html" % (pagina, sec))
            if not os.path.exists(caminho):
                print("  %-18s sem traducao — fica em portugues" % sec)
                continue
            selo = hashlib.sha256(pt.encode("utf-8")).hexdigest()[:16]
            texto = io.open(caminho, encoding="utf-8").read()
            cab, _, corpo = texto.partition("\n")
            atual = cab.replace("<!-- sha:", "").replace("-->", "").strip()
            if atual == selo:
                print("  %-18s em dia" % sec)
            elif gravar:
                io.open(caminho, "w", encoding="utf-8").write("<!-- sha:%s -->\n" % selo + corpo)
                print("  %-18s selo gravado (%s)" % (sec, selo))
            else:
                print("  %-18s DESATUALIZADO (arquivo diz %s, portugues esta em %s)"
                      % (sec, atual or "nada", selo))


if __name__ == "__main__":
    main()
