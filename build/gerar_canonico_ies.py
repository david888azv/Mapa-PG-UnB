#!/usr/bin/env python3
"""
Gera build/ies_canonico.json — tabela de canonicalizacao de siglas de IES.

PARA QUE SERVE. Desde que a sigla passou a ser resolvida POR QUADRIENIO
(ver mapear_programas em gerar_dados_completos.py), cada registro carrega o
rotulo da sua epoca. Isso e historicamente correto e cobra um preco: a mesma
instituicao aparece no filtro de IES sob dois nomes (FUFPI e UFPI, UFT e UFNT),
e quem escolhe o rotulo atual nao ve os quadrienios anteriores.

CRITERIO. CD_ENTIDADE_CAPES e o identificador estavel da instituicao — a sigla
e so o rotulo daquele ano. Duas siglas com o mesmo CD_ENTIDADE_CAPES sao a
mesma instituicao. A sigla CANONICA e a usada no ano mais recente.

COLISAO. Cinco siglas sao usadas por DUAS entidades diferentes (UVA, FVC, IPA,
ESPM, FG — homonimos reais, nao renomeacoes). Para essas, canonicalizar por
sigla fundiria instituicoes distintas: elas entram em 'colisoes' e ficam FORA
de 'canonico'. Quem consumir a tabela deve, nesses casos, desambiguar pelo
CD_ENTIDADE_CAPES do registro, ou nao canonicalizar.

Uso:
    python3 gerar_canonico_ies.py            # gera + relatorio
    python3 gerar_canonico_ies.py --dry-run  # so relatorio
"""
import csv, glob, json, os, argparse, time
from collections import defaultdict

csv.field_size_limit(10 ** 9)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
DOCS_DIR = os.path.join(REPO, 'docs')
# Fica em build/, nao em docs/: e insumo do build, nao artefato publicado —
# o app nunca o baixa, os aliases ja viajam dentro de cada area-*.json.
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ies_canonico.json')


def ler(fp):
    for enc in ('latin-1', 'utf-8-sig', 'utf-8', 'cp1252'):
        try:
            with open(fp, encoding=enc, errors='strict', newline='') as fh:
                return list(csv.DictReader(fh, delimiter=';'))
        except UnicodeDecodeError:
            continue
    return []


def coletar():
    """CD_ENTIDADE_CAPES -> {ano: {(sigla, uf, nome)}}"""
    ent = defaultdict(lambda: defaultdict(set))
    for fp in sorted(glob.glob(os.path.join(DATA_DIR, 'programas_*.csv'))):
        for r in ler(fp):
            ce = (r.get('CD_ENTIDADE_CAPES') or '').strip()
            sg = (r.get('SG_ENTIDADE_ENSINO') or '').strip()
            if not ce or not sg:
                continue
            ent[ce][int(float(r['AN_BASE']))].add((
                sg,
                (r.get('SG_UF_PROGRAMA') or '').strip(),
                (r.get('NM_ENTIDADE_ENSINO') or '').strip(),
            ))
    return ent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    ent = coletar()

    # sigla canonica de cada entidade = a do ano mais recente.
    # Ano com duas siglas para a MESMA entidade e raro; desempata pela ordem
    # alfabetica, so para ser deterministico (nao muda de execucao p/ execucao).
    canon_ent, hist = {}, defaultdict(lambda: defaultdict(set))
    for ce, por_ano in ent.items():
        for an, trios in por_ano.items():
            for sg, uf, nome in trios:
                hist[ce][sg].add(an)
        ultimo = max(por_ano)
        sg, uf, nome = sorted(por_ano[ultimo])[0]
        canon_ent[ce] = {'sigla': sg, 'uf': uf, 'nome': nome}

    # sigla -> entidades que a usaram (colisao = sigla de duas instituicoes)
    sig2ent = defaultdict(set)
    for ce in hist:
        for sg in hist[ce]:
            sig2ent[sg].add(ce)
    colisoes = {sg: sorted(es) for sg, es in sig2ent.items() if len(es) > 1}

    # Duas exclusoes, nao uma:
    #   (a) a sigla legada colide      — mapea-la escolheria uma entidade a esmo;
    #   (b) o ALVO colide              — mapear para ela FUNDE instituicoes.
    # (b) e o caso da UVA: a entidade 22004017 usou 'UVA-CE' ate 2023 e 'UVA' em
    # 2024, e 'UVA' ja era a Veiga de Almeida (31030017). Canonicalizar
    # UVA-CE -> UVA juntaria a estadual do Ceara com a privada do Rio. A
    # ambiguidade foi criada pela propria CAPES em 2024; a tabela nao pode
    # resolve-la sozinha, entao expoe o caso em 'alvo_ambiguo'.
    canonico, alvo_ambiguo = {}, {}
    for ce, info in canon_ent.items():
        for sg in hist[ce]:
            if sg == info['sigla'] or sg in colisoes:
                continue
            reg = {**info, 'cd_entidade': ce, 'anos': sorted(hist[ce][sg])}
            (alvo_ambiguo if info['sigla'] in colisoes else canonico)[sg] = reg

    out = {
        'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
        'criterio': 'CD_ENTIDADE_CAPES; sigla canonica = a do ano mais recente',
        'n_entidades': len(ent),
        'n_aliases': len(canonico),
        'canonico': dict(sorted(canonico.items())),
        'colisoes': colisoes,
        'alvo_ambiguo': dict(sorted(alvo_ambiguo.items())),
        'por_entidade': {ce: {**canon_ent[ce],
                              'siglas': {sg: sorted(ans) for sg, ans in hist[ce].items()}}
                         for ce in sorted(canon_ent)},
    }

    print('entidades CAPES        : %d' % len(ent))
    print('aliases (sigla legada) : %d' % len(canonico))
    print('colisoes (nao mapeadas): %d  %s' % (len(colisoes), sorted(colisoes)))
    print('alvo ambiguo (fora)    : %d  %s' % (len(alvo_ambiguo),
          ['%s->%s' % (k, v['sigla']) for k, v in sorted(alvo_ambiguo.items())]))

    # cobertura: siglas do app sem nenhum registro em 2021-2024
    legado = defaultdict(set)
    for fp in glob.glob(os.path.join(DOCS_DIR, 'dados', 'area-*.json')):
        for r in json.load(open(fp, encoding='utf-8'))['data']:
            legado[r['sigla']].add(r['quad'])
    so_antigas = {s for s, q in legado.items() if '2021-2024' not in q}
    cobertas = {s for s in so_antigas if s in canonico}
    print('\nsiglas no app          : %d' % len(legado))
    print('  sem registro em 21-24: %d' % len(so_antigas))
    print('  com alias canonico   : %d' % len(cobertas))
    print('  sem alias            : %d  (instituicao que so existiu ate 2020, '
          'ou colisao)' % (len(so_antigas) - len(cobertas)))

    print('\n--- amostra de aliases ---')
    for sg in sorted(cobertas)[:12]:
        print('  %-18s -> %-14s %s' % (sg, canonico[sg]['sigla'], canonico[sg]['nome'][:44]))

    if a.dry_run:
        print('\n[dry-run] nada gravado.')
        return
    with open(OUT_PATH, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    print('\n✓ %s (%.0f KB)' % (OUT_PATH, os.path.getsize(OUT_PATH) / 1024))


if __name__ == '__main__':
    main()
