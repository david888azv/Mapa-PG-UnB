#!/usr/bin/env python3
"""
Gera 27 stubs de redirecionamento docs/ies/<sigla>/index.html → /?ies=SIGLA,
dando uma URL limpa e indexável por universidade de referência
(ex.: /ies/ufmg/ abre o app com a UFMG destacada) sem duplicar o app.

Fonte da lista: docs/registry_ies.json (as 27 IFES).

SEO — o app cobre as 49 Áreas de Avaliação da CAPES (taxonomia 2017-2020) desde 16/07/2026.
Até então eram 42: o catálogo era derivado da pegada da UnB (gerar_registry.py montava
`areas_capes` iterando sobre os programas dela), e as 7 áreas em que a UnB não atua sumiam
do app — foi o que fez usuários de SC não acharem, p.ex., ENGENHARIA QUÍMICA da UFSC
(ENGENHARIAS II). Se este número mudar, conferir `docs/registry.json.areas_capes` antes de
escrever: prometer cobertura sem conferir foi exatamente o erro anterior.
"""
import json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, 'docs')
REG = os.path.join(DOCS, 'registry_ies.json')
SITE = 'https://david888azv.github.io/Mapa-PG-UnB/'

ifes = json.load(open(REG, encoding='utf-8'))['ifes']

TPL = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MAPA-PG — {rot} ({uf}) como referência | Pós-graduação CAPES</title>
<meta name="description" content="MAPA-PG com a {nome} ({rot}) como referência: compare a produção e os indicadores dos programas de pós-graduação da {rot} com seus pares nacionais, sempre dentro da mesma Área de Avaliação da CAPES, nas 49 áreas e ao longo de três quadriênios (2013–2024). Gratuito, com dados públicos da CAPES.">
<link rel="canonical" href="{site}?ies={sigla}">
<meta name="robots" content="index,follow">
<meta http-equiv="refresh" content="0; url=../../index.html?ies={sigla}">
<script>location.replace('../../index.html?ies={sigla}' + location.hash);</script>
</head>
<body>
<p>Redirecionando para o <strong>MAPA-PG</strong> com a <strong>{nome} ({rot})</strong> como referência…</p>
<p>Se não for redirecionado, <a href="../../index.html?ies={sigla}">clique aqui</a>.</p>
</body>
</html>
"""

n = 0
urls = []
for i in ifes:
    sigla = i['sigla']
    rot = 'UnB' if sigla == 'UNB' else sigla
    d = os.path.join(DOCS, 'ies', sigla.lower())
    os.makedirs(d, exist_ok=True)
    html = TPL.format(rot=rot, uf=i['uf'], nome=i['nome'], sigla=sigla, site=SITE)
    with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(html)
    urls.append(f"{SITE}ies/{sigla.lower()}/")
    n += 1

print(f'✓ {n} stubs em docs/ies/<sigla>/index.html')
print(f'  (as URLs /ies/<sigla>/ entram no sitemap via build/gerar_sitemap.py)')
