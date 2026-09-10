#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abre cada pagina de docs/en/ num Chromium de verdade e reprova se algo quebrou.

    python3 testar_ingles.py

Existe por um motivo concreto: a primeira geracao da versao inglesa saiu com a
pagina INTEIRA morta, e nem o gerador nem o olho pegaram. A traducao de
`'% Mestres (pad)'` virou `'% w/ master's (std)'` — a apostrofe fechou a string
JS de aspas simples, o script todo virou erro de sintaxe e a tela ficou so com o
HTML estatico, com cara de "quase certo". Nenhuma inspecao de texto acha isso;
so executar acha.

O que se confere em cada pagina:
  • nenhum erro de JavaScript (a armadilha acima);
  • nenhuma requisicao 404 — o <base href="../"> esta mandando dados, icones e
    Chart.js para o lugar certo;
  • a pagina montou (tem texto de verdade, nao so o esqueleto);
  • o alternador PT|EN aponta para a pagina irma em portugues.

O beacon do Web Analytics e BLOQUEADO no teste, para nao contar acesso de
localhost no painel.
"""
import os
import sys
import threading
import http.server
import socketserver
import functools

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
PAGINAS = ["index", "help-doc"]
PORTA = 0          # 0 = o sistema escolhe uma porta livre


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("playwright nao instalado: pip install playwright && playwright install chromium")

    class Silencioso(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", PORTA),
                                 functools.partial(Silencioso, directory=DOCS))
    porta = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    reprovadas = []
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        for pagina in PAGINAS:
            destino = os.path.join(DOCS, "en", pagina + ".html")
            if not os.path.exists(destino):
                print("  %-18s (nao gerada ainda)" % (pagina + ".html"))
                continue
            pg = navegador.new_page(viewport={"width": 1400, "height": 900})
            pg.route("**/beacon.min.js", lambda r: r.abort())
            erros, ruins = [], []
            pg.on("pageerror", lambda e: erros.append(str(e)[:160]))
            pg.on("response", lambda r: ruins.append("%d %s" % (r.status, r.url))
                  if r.status >= 400 and "beacon" not in r.url else None)
            pg.goto("http://127.0.0.1:%d/en/%s.html" % (porta, pagina), wait_until="networkidle")
            pg.wait_for_timeout(1500)

            texto = pg.evaluate("document.body.innerText.trim().length")
            volta = pg.evaluate("""(()=>{const a=document.querySelector('.langsel a');
                return a ? a.getAttribute('href') : null})()""")
            problemas = []
            if erros:
                problemas.append("erro JS: %s" % erros[0])
            if ruins:
                problemas.append("requisicao %s" % ruins[0])
            if texto < 300:
                problemas.append("pagina praticamente vazia (%d chars)" % texto)
            if not volta or not volta.startswith("../"):
                problemas.append("alternador nao volta para o portugues (href=%r)" % volta)

            print("  %-18s %s" % (pagina + ".html",
                                  "ok (%d chars)" % texto if not problemas else "FALHOU"))
            for p in problemas:
                print("       %s" % p)
            if problemas:
                reprovadas.append(pagina)
            pg.close()
        navegador.close()
    srv.shutdown()

    if reprovadas:
        raise SystemExit("\nreprovadas: %s" % ", ".join(reprovadas))
    print("\ntodas as paginas em ingles passaram")


if __name__ == "__main__":
    sys.exit(main())
