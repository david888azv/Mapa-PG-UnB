#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera a camada de BOLSAS CAPES do MAPA-PG: docs/dados/bol-<area>.json.

Pedido de funcionalidade do Prof. Marcos D. Pereira, coordenador do PPGBq/UFRJ,
pelo formulário do aplicativo em 13/08/2026: comparar o número de bolsas de cada
programa ao longo dos anos, para enxergar as perdas e os cortes. O painel mostra
produção e corpo docente, e o insumo que sustenta os dois não aparecia em lugar
nenhum.

FONTE
-----
Dados abertos da CAPES, organização "Bolsas e Auxílios", conjunto **Bolsistas dos
Programas da Diretoria de Programas e Bolsas no País (DPB)**, em três blocos que
juntos cobrem **2010 a 2025**. Cada bloco vem partido em três arquivos
(institucionais, qualificação de docentes, estratégicos) e é preciso somar os
três: sozinho, o de institucionais deixa de fora programas inteiros.

O registro é **um por bolsista por ano**, e traz `CD_PROGRAMA_PPG` — a mesma
chave que o resto do MAPA-PG usa. É por isso que esta camada não precisa de
heurística nenhuma para casar com o programa: é o mesmo código.

O QUE É CONTADO
---------------
Três medidas, porque elas respondem a perguntas diferentes e uma sozinha engana:

- **bolsistas** — pessoas distintas com bolsa naquele ano. É o número que a
  coordenação reconhece, mas ele esconde corte no meio do ano.
- **meses de bolsa** (`QT_BOLSA_ANO`) — o total de mensalidades pagas. É a medida
  fiel de perda: quem perde metade do ano continua sendo um bolsista, e aparece
  aqui como seis meses em vez de doze.
- **valor** (`VL_BOLSA_ANO`), em reais NOMINAIS do ano, sem correção nenhuma.

`meses ÷ 12` é a bolsa-equivalente-ano, que é o que se compara entre programas de
tamanhos diferentes.

DECISÕES
--------
1. **Arquivo separado por área**, como a camada de patentes, e não patch nos
   `area-*.json`: o `gerar_dados_completos.py` reescreve aqueles do zero, e um
   patch seria perdido em silêncio no próximo rebuild.
2. **Um arquivo por área com TODOS os anos** — ao contrário das patentes, que são
   por quadriênio. A série anual é justamente o produto aqui, e o arquivo é
   pequeno (dezenas de KB), porque só carrega contagens, nunca o nome de quem
   recebeu a bolsa.
3. **Nome de bolsista NUNCA entra no JSON.** A fonte é nominal, com CPF
   mascarado; o app publica só agregados por programa, ano e nível.
4. **Contagem de pessoa distinta muda de chave conforme o bloco.** Até 2022 os
   arquivos trazem `ID_PESSOA`; de 2023 em diante ele sumiu e resta o CPF
   mascarado. Onde não há `ID_PESSOA`, a chave é o par (documento, nome) — o CPF
   mascarado sozinho colide.
5. **Programa fora do catálogo do app fica de fora**, e o total é reportado: são
   bolsas de programas que nunca foram avaliados ou que sumiram do catálogo, e
   colocá-los numa área exigiria adivinhar.

Uso:
    python3 gerar_bolsas.py --baixar        # baixa os 12 CSVs (~614 MB) e gera
    python3 gerar_bolsas.py                 # usa o que já está em dados_capes/bolsas/
    python3 gerar_bolsas.py --sem-manifest  # não mexe no docs/manifest.json
"""
import argparse
import csv
import glob
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_CAPES = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
FONTE_DIR = os.path.join(DADOS_CAPES, 'bolsas')
DOCS_DIR = os.path.join(REPO, 'docs', 'dados')
MANIFEST = os.path.join(REPO, 'docs', 'manifest.json')
DISCENTES = os.path.join(REPO, 'build', 'cache', 'discentes_por_programa.json')

CKAN = 'https://dadosabertos.capes.gov.br/api/3/action/package_show?id='
PACOTES = [
    '2010-a-2016-bolsistas-dos-programas-da-diretoria-de-programas-e-bolsas-no-pais-dpb',
    '2017-a-2021-bolsistas-dos-programas-da-diretoria-de-programas-e-bolsas-no-pais-dpb',
    '2022-a-2025-bolsistas-dos-programas-da-diretoria-de-programas-e-bolsas-no-pais-dpb',
]

# O que é bolsa de aluno (ou de pós-doutorando) de programa stricto sensu. O
# conjunto da DPB mistura no mesmo arquivo bolsas de iniciação científica, de
# professor da educação básica, de coordenação e de supervisão — nenhuma delas é
# do programa de pós, e somá-las inflaria a série sem que ninguém percebesse.
# A lista saiu da contagem de TODOS os valores distintos de DS_NIVEL na base
# inteira, não de suposição.
NIVEIS = {
    'MESTRADO': 'ME',
    'MESTRADO PROFISSIONAL': 'MP',
    'DOUTORADO': 'DO',
    'DOUTORADO PROFISSIONAL': 'DO',
    'DOUTORADO SANDUÍCHE': 'DO',
    'ESTÁGIO PÓS-DOUTORAL': 'PD',
    'PÓS-DOUTORADO': 'PD',
}


def baixar():
    """Baixa os CSVs dos três blocos para dados_capes/bolsas/."""
    os.makedirs(FONTE_DIR, exist_ok=True)
    for pacote in PACOTES:
        with urllib.request.urlopen(CKAN + pacote, timeout=60) as r:
            d = json.load(r)['result']
        for rec in d['resources']:
            if rec['format'].upper() != 'CSV':
                continue
            destino = os.path.join(FONTE_DIR, os.path.basename(rec['url']))
            if os.path.exists(destino) and os.path.getsize(destino) > 1000:
                print(f'  · já tenho {os.path.basename(destino)}')
                continue
            print(f'  ↓ {os.path.basename(destino)}', flush=True)
            urllib.request.urlretrieve(rec['url'], destino)
    print(f'✓ fonte em {FONTE_DIR}')


def catalogo_areas():
    """{cd_programa: (slug_area, nome_area)} a partir dos area-*.json do app."""
    cd2area = {}
    areas = {}
    for f in sorted(glob.glob(os.path.join(DOCS_DIR, 'area-*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        md = d['metadata']
        areas[md['slug']] = md['area']
        for r in d['data']:
            cd2area[r['cd']] = (md['slug'], md['area'])
    if not cd2area:
        raise SystemExit(f'✗ nenhum area-*.json em {DOCS_DIR}')
    return cd2area, areas


def _abrir(arq):
    """Abre o CSV com a codificação certa — ela MUDA de arquivo para arquivo.

    Onze dos doze vêm em ISO-8859-1 e o de 2025 vem em UTF-8. Ler todos como
    latin-1 não estoura: passa, e transforma 'PÓS-DOUTORADO' em 'PÃS-DOUTORADO',
    que some do mapeamento de níveis em silêncio — foram 3.009 bolsas de
    pós-doutorado perdidas assim na primeira versão.
    """
    for enc in ('utf-8-sig', 'latin-1'):
        try:
            with open(arq, encoding=enc, newline='') as fh:
                fh.read(200000)
            return enc
        except UnicodeDecodeError:
            continue
    return 'latin-1'


def _num(s):
    """Número em QUALQUER dos três formatos que a própria CAPES usa nesta base.

    O mesmo campo `VL_BOLSA_ANO` aparece de três jeitos conforme o bloco:
        2010-2021   13,500.00     vírgula de milhar, ponto decimal
        2022        26.400,00     ponto de milhar, vírgula decimal
        2023-2025   41600.00      sem separador de milhar
    Tratar tudo como o primeiro caso divide o valor de 2022 por mil e ninguém vê:
    a Física da UnB apareceu com R$ 719 em 2022, entre R$ 800 mil e R$ 900 mil nos
    anos vizinhos. A regra que resolve os três casos: o separador que aparece por
    ÚLTIMO é o decimal; o outro é de milhar.
    """
    s = (s or '').strip()
    if not s:
        return 0.0
    ult_p, ult_v = s.rfind('.'), s.rfind(',')
    if ult_p >= 0 and ult_v >= 0:
        dec, mil = ('.', ',') if ult_p > ult_v else (',', '.')
    elif ult_v >= 0:
        # Só vírgula: decimal se tiver 1 ou 2 dígitos depois ('26,4'), senão milhar.
        dec, mil = (',', '.') if len(s) - ult_v - 1 <= 2 else ('.', ',')
    else:
        dec, mil = ('.', ',')
    try:
        return float(s.replace(mil, '').replace(dec, '.'))
    except ValueError:
        return 0.0


def agregar(cd2area):
    """(cd, ano) → {nivel: [bolsistas, meses, valor]}, mais os descartes."""
    arquivos = sorted(glob.glob(os.path.join(FONTE_DIR, '*.csv')))
    if not arquivos:
        raise SystemExit(f'✗ nada em {FONTE_DIR} — rode com --baixar')

    agg = defaultdict(lambda: defaultdict(lambda: [0, 0.0, 0.0]))
    pessoas = defaultdict(set)          # (cd, ano, nivel) → chaves de pessoa
    # Pessoa distinta no PROGRAMA-ANO, não só no nível: quem passa de mestrado a
    # doutorado no mesmo ano tem dois registros, e somar os níveis contaria essa
    # pessoa duas vezes. No país isso infla de 1,4% a 2,3% ao ano; num programa
    # pequeno o efeito é bem maior (Física/UnB em 2025: 49 contra 46 pessoas).
    pessoas_prog = defaultdict(set)     # (cd, ano) → chaves de pessoa
    pessoas_alu = defaultdict(set)      # idem, só mestrado/doutorado
    meses_alu = defaultdict(float)      # meses de bolsa de ALUNO (sem pós-doc)
    valor_alu = defaultdict(float)
    fora = defaultdict(int)             # cd sem área no catálogo → nº de registros
    anos = set()
    niveis_vistos = defaultdict(int)

    for arq in arquivos:
        n = 0
        with open(arq, encoding=_abrir(arq), newline='') as fh:
            for r in csv.DictReader(fh, delimiter=';'):
                cd = (r.get('CD_PROGRAMA_PPG') or '').strip()
                ano = (r.get('AN_REFERENCIA') or '').strip()
                if not cd or not ano.isdigit():
                    continue
                nivel_bruto = (r.get('DS_NIVEL') or '').strip().upper()
                niveis_vistos[nivel_bruto] += 1
                nivel = NIVEIS.get(nivel_bruto)
                if nivel is None:
                    continue                     # bolsa que não é de pós stricto sensu
                if cd not in cd2area:
                    fora[cd] += 1
                    continue
                # Pessoa distinta: ID_PESSOA quando existe; senão (documento, nome),
                # porque o CPF mascarado sozinho colide.
                pid = (r.get('ID_PESSOA') or '').strip()
                if not pid:
                    pid = ((r.get('NR_DOCUMENTO') or '').strip() + '|' +
                           (r.get('NM_BOLSISTA') or '').strip())
                chave = (cd, int(ano), nivel)
                c = agg[(cd, int(ano))][nivel]
                if pid not in pessoas[chave]:
                    pessoas[chave].add(pid)
                    c[0] += 1
                pessoas_prog[(cd, int(ano))].add(pid)
                mes, val = _num(r.get('QT_BOLSA_ANO')), _num(r.get('VL_BOLSA_ANO'))
                c[1] += mes
                c[2] += val
                # Pós-doutorando não é aluno do programa, e misturá-lo com
                # mestrandos e doutorandos estraga qualquer razão por matriculado.
                if nivel != 'PD':
                    pessoas_alu[(cd, int(ano))].add(pid)
                    meses_alu[(cd, int(ano))] += mes
                    valor_alu[(cd, int(ano))] += val
                anos.add(int(ano))
                n += 1
        print(f'  · {os.path.basename(arq):58s} {n:>9,} registros de pós', flush=True)

    distintos = {'todos': {k: len(v) for k, v in pessoas_prog.items()},
                 'alunos': {k: len(v) for k, v in pessoas_alu.items()},
                 'meses_alunos': dict(meses_alu), 'valor_alunos': dict(valor_alu)}
    return agg, sorted(anos), fora, niveis_vistos, distintos


def carregar_discentes():
    """Denominador da razão, vindo do gerar_discentes.py. Ausente, a camada sai
    sem razão nenhuma — melhor não ter o indicador do que tê-lo pela metade."""
    if not os.path.exists(DISCENTES):
        print(f'  ⚠ {DISCENTES} não existe — a camada sai SEM a razão por aluno.\n'
              f'    Rode antes: python3 gerar_discentes.py --baixar', file=sys.stderr)
        return {}, None
    d = json.load(open(DISCENTES, encoding='utf-8'))
    return d.get('data', {}), d.get('anos')


def escrever(agg, anos, cd2area, areas, distintos, tocar_manifest=True):
    disc, anos_disc = carregar_discentes()
    por_area = defaultdict(dict)
    for (cd, ano), niv in agg.items():
        slug = cd2area[cd][0]
        prog = por_area[slug].setdefault(cd, {})
        # Detalhe por nível + totais. O total de PESSOAS não é a soma dos níveis
        # (quem muda de nível no ano entraria duas vezes) e vem do conjunto
        # distinto do programa-ano; meses e valor, sim, são somas.
        tot_m = tot_v = 0
        det = {}
        for k, (b, m, v) in niv.items():
            det[k] = [b, round(m), round(v)]
            tot_m += round(m)
            tot_v += round(v)
        reg = {
            'b': distintos['todos'].get((cd, ano), 0),
            'ba': distintos['alunos'].get((cd, ano), 0),
            'm': tot_m, 'ma': round(distintos['meses_alunos'].get((cd, ano), 0)),
            'v': tot_v, 'va': round(distintos['valor_alunos'].get((cd, ano), 0)),
            'n': det,
        }
        # `al` = denominador: {'ME': [matriculados, ativos], 'DO': [...]}, só nos
        # anos em que o conjunto de discentes existe (vai até 2024).
        alunos = disc.get(cd, {}).get(str(ano))
        if alunos:
            reg['al'] = alunos
        prog[str(ano)] = reg

    escritos, total_kb = 0, 0.0
    resumo = {}
    for slug, progs in sorted(por_area.items()):
        payload = {
            'metadata': {
                'area': areas[slug], 'slug': slug,
                'anos': anos,
                'niveis': {'ME': 'Mestrado', 'MP': 'Mestrado profissional',
                           'DO': 'Doutorado', 'PD': 'Pós-doutorado'},
                'fora_da_conta': 'iniciação científica, iniciação à extensão, professor '
                                 'visitante, supervisão e coordenação — o conjunto da DPB '
                                 'traz essas bolsas nos mesmos arquivos, e elas não são '
                                 'do programa de pós',
                'medidas': {'b': 'pessoas distintas com bolsa no ano (todos os níveis)',
                            'ba': 'idem, só alunos de mestrado e doutorado',
                            'm': 'meses de bolsa pagos no ano',
                            'ma': 'idem, só de alunos',
                            'v': 'valor pago no ano, em reais nominais',
                            'va': 'idem, só de alunos'},
                'contagem': 'A contagem do ano é FLUXO, não foto de um mês: entra quem teve '
                            'bolsa em qualquer parte do ano, e a maioria não teve os 12 meses. '
                            'Meses ÷ 12 dá a bolsa-equivalente-ano, que é o número comparável.',
                'fonte': 'CAPES — Dados Abertos, Bolsistas dos Programas da DPB '
                         '(bolsas no país), blocos 2010-2016, 2017-2021 e 2022-2025',
                'alunos': ({'fonte': 'CAPES — Dados Abertos, Discentes da Pós-Graduação '
                                     'Stricto Sensu', 'anos': anos_disc,
                            'campos': 'al = {nível: [matriculados no fechamento do ano, '
                                      'ativos no ano]}; mestrado e doutorado incluem os '
                                      'profissionais',
                            'razao': 'a razão do painel divide alunos com bolsa por alunos '
                                     'ATIVOS no ano: os dois lados são fluxo do ano'}
                           if anos_disc else None),
                'n_programas': len(progs),
                'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
            },
            'data': progs,
        }
        caminho = os.path.join(DOCS_DIR, f'bol-{slug}.json')
        with open(caminho, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(',', ':'))
        kb = os.path.getsize(caminho) / 1024
        total_kb += kb
        escritos += 1
        resumo[slug] = {'arquivo': f'dados/bol-{slug}.json', 'tamanho_kb': round(kb),
                        'n_programas': len(progs), 'anos': [anos[0], anos[-1]]}

    if tocar_manifest:
        mf = json.load(open(MANIFEST, encoding='utf-8'))
        for a in mf['areas']:
            if a['slug'] in resumo:
                a['bol'] = resumo[a['slug']]
            else:
                a.pop('bol', None)
        mf['bolsas'] = {'fonte': 'CAPES — Bolsistas da DPB (bolsas no país)',
                        'anos': [anos[0], anos[-1]],
                        'atualizado_em': time.strftime('%Y-%m-%d')}
        with open(MANIFEST, 'w', encoding='utf-8') as fh:
            json.dump(mf, fh, ensure_ascii=False, indent=2)
    return escritos, total_kb, resumo


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--baixar', action='store_true', help='baixa os CSVs da CAPES antes')
    ap.add_argument('--sem-manifest', action='store_true', help='não mexe no manifest')
    a = ap.parse_args()
    t0 = time.perf_counter()

    if a.baixar:
        baixar()

    cd2area, areas = catalogo_areas()
    agg, anos, fora, niveis, distintos = agregar(cd2area)
    escritos, kb, resumo = escrever(agg, anos, cd2area, areas, distintos, not a.sem_manifest)

    print(f'\n✓ {escritos} arquivos dados/bol-*.json  ({kb:.0f} KB no total)')
    print(f'  anos cobertos: {anos[0]}–{anos[-1]}')
    print(f'  programas com bolsa e área conhecida: {len({cd for cd, _ in agg})}')
    if fora:
        print(f'  fora do catálogo do app: {len(fora)} programas, '
              f'{sum(fora.values()):,} registros (nunca avaliados ou fora do catálogo)')
    ignorados = {k: v for k, v in niveis.items() if k not in NIVEIS}
    if ignorados:
        top = sorted(ignorados.items(), key=lambda x: -x[1])[:6]
        print('  níveis ignorados (não são de pós stricto sensu): ' +
              ', '.join(f'{k or "(vazio)"} {v:,}' for k, v in top))
    print(f'  {time.perf_counter() - t0:.1f}s')


if __name__ == '__main__':
    main()
