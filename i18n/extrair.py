#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lista o que, numa pagina de docs/, e candidato a traducao.

    python3 i18n/extrair.py comparador

Nao traduz nada: so separa o joio do trigo para quem vai escrever a tabela em
traducoes_en.py. Sai em duas secoes — o texto visivel do HTML e as strings
literais do JavaScript que tem cara de rotulo (com espaco ou acento). A decisao
do que e rotulo e do que e DADO (nome de instituicao, sigla, chave de objeto)
continua sendo humana; e justamente por isso que existe uma tabela explicita.
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pagina = sys.argv[1].replace(".html", "")
    s = io.open(os.path.join(BASE, "docs", pagina + ".html"), encoding="utf-8").read()

    corpo = s[s.index("<body"):]
    sem_js = re.sub(r"<script.*?</script>|<style.*?</style>", " ", corpo, flags=re.S)
    frags = [t.strip() for t in re.split(r"<[^>]+>", sem_js)]
    frags = [f for f in dict.fromkeys(frags) if len(f) > 1 and not re.fullmatch(r"[\W\d]+", f)]
    print("### TEXTO VISIVEL (%d) ###" % len(frags))
    for f in frags:
        print("  |%s|" % f)

    print("\n### ATRIBUTOS ###")
    for m in dict.fromkeys(re.findall(r'(?:placeholder|aria-label|title|alt)="([^"]{2,})"', sem_js)):
        print("  |%s|" % m)

    js = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", s, flags=re.S))
    vistos = []
    for m in re.finditer(r"(['\"`])((?:(?!\1)[^\\\n]|\\.){3,220})\1", js):
        lit = m.group(2)
        if lit in vistos:
            continue
        if not (" " in lit or re.search(r"[áàâãéêíóôõúçÁÉÍÓÚÂÊÔÃÕÇ]", lit)):
            continue
        if lit.startswith(("http", "./", "../", "#", "data:")):
            continue
        if re.fullmatch(r"[\s\d.,%/:;+\-()]+", lit):
            continue
        if re.match(r"^[a-z-]+\s*:\s*[#\d]", lit) or "px;" in lit or "flex" in lit[:12]:
            continue          # bloco de CSS inline, nao rotulo
        vistos.append(lit)
    print("\n### STRINGS DO JS (%d) ###" % len(vistos))
    for lit in vistos:
        print("  |%s|" % lit)

if __name__ == "__main__":
    main()
