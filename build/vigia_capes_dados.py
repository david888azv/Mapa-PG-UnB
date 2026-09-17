#!/usr/bin/env python3
"""Vigia semanal do portal de Dados Abertos da CAPES para o MAPA-PG.

Em 16/09/2026 o portal ainda estava no conjunto "2021 a 2024" (última alteração
em 12-15/12/2025) e a produção de 2025 não existia. Pelo calendário observado, o
ano N sai entre novembro e dezembro de N+1, e o ano 2025 deve abrir um conjunto
novo "2025 a 2028". Este vigia existe para ninguém ter de ficar conferindo à mão.

Acompanha, pela API CKAN, os conjuntos que o app consome:
  - todos os da pós-graduação stricto sensu (COLSUCUP: produção, autor, detalhes,
    programas, cursos, discentes, docentes, projetos, teses);
  - bolsistas da DPB (denominador/numerador das bolsas).

Avisa quando aparece conjunto novo, quando um conjunto muda de data de alteração
ou quando surge recurso novo/alterado. A primeira execução só grava a linha de
base e sai calada. "nada novo" é o caso comum e sai calado no cron.

Uso:
  python3 vigia_capes_dados.py            # compara e imprime
  python3 vigia_capes_dados.py --email    # idem, e manda e-mail se houver novidade
"""
import json
import os
import smtplib
import ssl
import sys
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

API = "https://dadosabertos.capes.gov.br/api/3/action"
AQUI = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(AQUI, "vigia_capes_estado.json")
LOG = os.path.join(AQUI, "vigia_capes.log")
DESTINO = os.environ.get("CAPES_AVISO_PARA") or os.environ.get("SMTP_FROM", "contato@daciencia.org")

# Buscas cuja união cobre o que o app usa. "stricto sensu" pega os COLSUCUP;
# "bolsistas" pega o da DPB. Filtra-se depois por palavras no nome.
BUSCAS = ["stricto sensu", "colsucup", "pos-graduacao", "bolsistas"]
RELEVANTE = ("stricto-sensu", "pos-graduacao", "producao-intelectual",
             "teses-e-dissertacoes", "diretoria-de-programas-e-bolsas")


def com_tentativas(f, *a, **k):
    # Os servidores do governo derrubam conexão de vez em quando (visto em 16/09/2026
    # nos dois portais ao mesmo tempo); três tentativas espaçadas bastam.
    import time
    for n in range(3):
        try:
            return f(*a, **k)
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            if isinstance(e, urllib.error.HTTPError) or n == 2:
                raise
            time.sleep(10 * (n + 1))


def api(acao, **params):
    url = "%s/%s?%s" % (API, acao, urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={"User-Agent": "mapa-pg-vigia/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    if not d.get("success"):
        raise RuntimeError("API CAPES falhou em %s" % acao)
    return d["result"]


def instantaneo():
    pacotes = {}
    for q in BUSCAS:
        inicio = 0
        while True:
            res = com_tentativas(api, "package_search", q=q, rows=100, start=inicio)
            for p in res["results"]:
                if not any(k in p["name"] for k in RELEVANTE):
                    continue
                pacotes[p["name"]] = {
                    "modificado": p["metadata_modified"],
                    "recursos": sorted({
                        "%s|%s" % (r["name"], (r.get("last_modified") or r.get("created") or "")[:10])
                        for r in p.get("resources", [])
                    }),
                }
            inicio += 100
            if inicio >= res["count"]:
                break
    if not pacotes:
        raise RuntimeError("nenhum conjunto relevante retornado — API mudou?")
    return pacotes


def compara(antes, agora):
    linhas = []
    for nome in sorted(set(agora) - set(antes)):
        destaque = "  <<< QUADRIÊNIO NOVO" if "2025" in nome else ""
        linhas.append("CONJUNTO NOVO: %s%s" % (nome, destaque))
        linhas.append("  https://dadosabertos.capes.gov.br/dataset/%s" % nome)
        for r in agora[nome]["recursos"]:
            linhas.append("    + %s" % r.replace("|", "  (") + ")")
    for nome in sorted(set(antes) & set(agora)):
        a, b = antes[nome], agora[nome]
        novos = sorted(set(b["recursos"]) - set(a["recursos"]))
        if a["modificado"] != b["modificado"] or novos:
            linhas.append("CONJUNTO ALTERADO: %s (%s -> %s)" % (nome, a["modificado"][:10], b["modificado"][:10]))
            linhas.append("  https://dadosabertos.capes.gov.br/dataset/%s" % nome)
            for r in novos:
                linhas.append("    + %s" % r.replace("|", "  (") + ")")
    for nome in sorted(set(antes) - set(agora)):
        linhas.append("CONJUNTO SUMIU DA BUSCA: %s" % nome)
    return linhas


def manda_email(texto):
    faltando = [k for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS") if not os.environ.get(k)]
    if faltando:
        print("[aviso] e-mail NÃO enviado — falta %s no ambiente." % ", ".join(faltando))
        return False
    msg = EmailMessage()
    msg["From"] = os.environ.get("SMTP_FROM", "contato@daciencia.org")
    msg["To"] = DESTINO
    msg["Subject"] = "MAPA-PG: novidade nos dados abertos da CAPES"
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="daciencia.org")
    msg.set_content(texto)
    s = smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")))
    s.starttls(context=ssl.create_default_context())
    s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
    s.send_message(msg)
    s.quit()
    print("[ok] aviso enviado para %s" % DESTINO)
    return True


def registra(texto):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (datetime.now().isoformat(timespec="seconds"), texto))


def main():
    agora = instantaneo()
    if not os.path.exists(ESTADO):
        with open(ESTADO, "w", encoding="utf-8") as f:
            json.dump(agora, f, ensure_ascii=False, indent=1)
        registra("linha de base gravada: %d conjuntos" % len(agora))
        print("nada novo (linha de base gravada: %d conjuntos)" % len(agora))
        return
    with open(ESTADO, encoding="utf-8") as f:
        antes = json.load(f)
    linhas = compara(antes, agora)
    if not linhas:
        registra("nada novo (%d conjuntos)" % len(agora))
        print("nada novo")
        return
    texto = ("Mudanças no portal de Dados Abertos da CAPES desde a última verificação:\n\n"
             + "\n".join(linhas)
             + "\n\nPróximo passo: baixar para coleta-capes/dados_capes/ e ajustar os scripts de "
               "mapa-pg-multi/build/ ao novo conjunto/quadriênio.\n")
    print(texto)
    registra("NOVIDADE: %d linhas" % len(linhas))
    enviado = "--email" in sys.argv and manda_email(texto)
    # Só avança a linha de base se o aviso saiu (ou se não foi pedido e-mail),
    # para uma falha de SMTP não engolir a novidade.
    if enviado or "--email" not in sys.argv:
        with open(ESTADO, "w", encoding="utf-8") as f:
            json.dump(agora, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
