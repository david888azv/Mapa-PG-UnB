#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sela `VERSION_DATA` de docs/index.html com a data do CHANGELOG.

A tela de abertura mostra "v<VERSION> — <mês> <ano>". A versão sempre foi
interpolada (`${VERSION}`), mas o mês era texto escrito à mão ao lado dela: ficou
em "Julho 2026" enquanto a versão andou sozinha até a 5.8.3. Um rótulo que o
release não toca é um rótulo que envelhece em silêncio.

Agora a página guarda só a data ISO (`VERSION_DATA`) e formata o mês pelo locale
(`LOCALE_APP`), de modo que docs/ e docs/en/ saem do mesmo campo. Este script põe
nesse campo a data do cabeçalho da versão atual no CHANGELOG — que passa a ser a
fonte única.

    python3 build/selar_versao_data.py            # sela; imprime o que mudou
    python3 build/selar_versao_data.py --conferir # só confere (sai 1 se defasado)

Rode ao publicar uma versão, depois de escrever o cabeçalho dela no CHANGELOG, e
antes de `gerar_ingles.py`.
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(BASE, 'docs', 'index.html')
CHANGELOG = os.path.join(BASE, 'CHANGELOG.md')


def versao_do_app(html):
    m = re.search(r"const VERSION = '([^']+)';", html)
    if not m:
        raise SystemExit('nao achei `const VERSION` em docs/index.html')
    return m.group(1)


def data_no_changelog(versao):
    txt = open(CHANGELOG, encoding='utf-8').read()
    # cabecalho: "## v5.8.4 — titulo qualquer (2026-09-17)"
    m = re.search(r'^## v%s\b.*?\((\d{4}-\d{2}-\d{2})\)\s*$' % re.escape(versao),
                  txt, flags=re.M)
    if not m:
        raise SystemExit('CHANGELOG.md nao tem cabecalho datado para a v%s.\n'
                         'Escreva o cabecalho da versao antes de selar.' % versao)
    return m.group(1)


def main():
    conferir = '--conferir' in sys.argv
    html = open(INDEX, encoding='utf-8').read()
    versao = versao_do_app(html)
    data = data_no_changelog(versao)

    m = re.search(r"const VERSION_DATA = '([^']*)';", html)
    if not m:
        raise SystemExit('nao achei `const VERSION_DATA` em docs/index.html')
    atual = m.group(1)

    if atual == data:
        print('em dia: v%s — VERSION_DATA = %s' % (versao, data))
        return 0
    if conferir:
        print('DEFASADO: v%s tem %s no CHANGELOG e %s na pagina' % (versao, data, atual))
        return 1

    html = html.replace("const VERSION_DATA = '%s';" % atual,
                        "const VERSION_DATA = '%s';" % data, 1)
    open(INDEX, 'w', encoding='utf-8').write(html)
    print('selado: v%s — %s (era %s). Rode gerar_ingles.py para docs/en/.'
          % (versao, data, atual))
    return 0


if __name__ == '__main__':
    sys.exit(main())
