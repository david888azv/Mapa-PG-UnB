#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera docs/sitemap.xml e docs/robots.txt a partir de manifest.json + registry.json.

URLs incluidas:
  - home                                   prioridade 1.0
  - 1 por Area CAPES  (?area=<slug>)       prioridade 0.8   (42)
  - 1 por curso UnB   (?area=<slug>&curso=<sufixo>)  0.6    (94)

Reexecute apos atualizar areas/cursos:
    python3 build/gerar_sitemap.py
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "..", "docs")
SITE = "https://david888azv.github.io/Mapa-PG-UnB/"


def main():
    manifest = json.load(open(os.path.join(DOCS, "manifest.json"), encoding="utf-8"))
    registry = json.load(open(os.path.join(DOCS, "registry.json"), encoding="utf-8"))
    lastmod = (manifest.get("atualizado_em") or manifest.get("gerado_em") or "")[:10]

    urls = [(SITE, "1.0")]
    for a in manifest["areas"]:
        urls.append((SITE + "?area=" + a["slug"], "0.8"))
    for p in registry["programas_unb"]:
        urls.append((SITE + "?area=" + p["slug_area"] + "&curso=" + p["sufixo"], "0.6"))

    def esc(s):
        return s.replace("&", "&amp;")

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lm = ("<lastmod>%s</lastmod>" % lastmod) if lastmod else ""
    for loc, prio in urls:
        out.append("  <url><loc>%s</loc>%s<changefreq>monthly</changefreq>"
                   "<priority>%s</priority></url>" % (esc(loc), lm, prio))
    out.append("</urlset>")
    open(os.path.join(DOCS, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(out) + "\n")

    robots = ("User-agent: *\n"
              "Allow: /\n\n"
              "Sitemap: %ssitemap.xml\n" % SITE)
    open(os.path.join(DOCS, "robots.txt"), "w", encoding="utf-8").write(robots)

    print("sitemap.xml: %d URLs (1 home + %d areas + %d cursos)" %
          (len(urls), len(manifest["areas"]), len(registry["programas_unb"])))
    print("robots.txt: OK  | lastmod=%s" % (lastmod or "(sem data)"))


if __name__ == "__main__":
    main()
