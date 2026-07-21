#!/usr/bin/env python3
"""Gera a camada de PATENTES do MAPA-PG: docs/dados/tec-<area>-<quad>.json.

Entrada (baixada por `baixar_tecnica.py`):
    dados_capes/tec_detalhe_<quad>_patente.csv   detalhe (finalidade, nº, datas, TRL)
    dados_capes/tec_prod_<quad>_patente.csv      tabela-mãe (título 100%, linha de pesquisa)

Saída: um arquivo por (área, quadriênio), com o mesmo slug dos area-*.json:
    - contagem de patentes por programa e por ano
    - a lista das patentes de cada programa (título, descrição, nº, datas, estágio)

DECISÕES DE MODELAGEM
---------------------
1. Arquivo SEPARADO, não patch nos area-*.json. `gerar_dados_completos.py` reescreve
   os area-*.json do zero a cada rebuild; um patch seria silenciosamente perdido.
2. UM ARQUIVO POR QUADRIÊNIO, não um por área com os três dentro: o app carrega só o
   quadriênio que o usuário está vendo (o maior fica em ~700 KB em vez de ~1,8 MB).
3. Placeholder: a CAPES grava '-' para campo não preenchido. Vira '' aqui.
4. DEDUPLICAÇÃO — e ela NÃO é uniforme entre os quadriênios:
     2021-2024  DS_CODIGO_REGISTRO em 95,2% → dedup 'completa'
     2013-2016  CD_REGISTRO em 40,4%        → dedup 'parcial' (o resto não dá p/ deduplicar)
     2017-2020  o campo NÃO EXISTE na base  → dedup 'indisponivel'
   Uma patente com coautoria é declarada por cada programa participante, então:
     - contagem POR PROGRAMA usa os registros como declarados (é o que a CAPES avalia);
     - contagem de ÁREA e NACIONAL só vira "patentes distintas" onde há como deduplicar.
   `metadata.dedup` diz qual dos três casos vale, e o app é obrigado a respeitar:
   em 2017-2020 não existe número de patentes distintas, e inventar um seria mentira.
5. IN_GLOSA = 1 (produção glosada pela CAPES) é descartado, como no pipeline
   bibliográfico.
6. Cobertura declaratória varia MUITO entre quadriênios (descrição 19,6% / 34,9% /
   22,1%; concessão 5,6% / 10,0% / 11,1%). `metadata.cobertura_nacional` carrega os
   percentuais reais para o app exibi-los em vez de números fixos no código.

Uso:
    python3 gerar_tecnica.py                        # todos os quadriênios disponíveis
    python3 gerar_tecnica.py --quadrienio 2021a2024
    python3 gerar_tecnica.py --area quimica biotecnologia
    python3 gerar_tecnica.py --sem-manifest         # não mexe no docs/manifest.json
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.normpath(os.path.join(REPO, '..', 'dados_capes'))
CACHE_DIR = os.path.join(REPO, 'build', 'cache')
DOCS_DIR = os.path.join(REPO, 'docs', 'dados')
MANIFEST = os.path.join(REPO, 'docs', 'manifest.json')

QUAD_ANOS = {'2013a2016': ('2013-2016', range(2013, 2017)),
             '2017a2020': ('2017-2020', range(2017, 2021)),
             '2021a2024': ('2021-2024', range(2021, 2025))}

VAZIO = {'', '-', '--', 'NAO INFORMADO', 'NÃO INFORMADO', 'NAN', 'NONE'}


def limpar(s):
    """Normaliza célula CAPES: strip + placeholder '-' → ''."""
    if not isinstance(s, str):
        return ''
    s = ' '.join(s.split())
    return '' if s.upper() in VAZIO else s


def chave_registro(cod):
    """Chave de deduplicação: só alfanuméricos, maiúsculo.

    'BR 10 2021 024428-3' e 'br102021024428 3' viram a mesma patente. Códigos com
    menos de 6 caracteres úteis são descartados como chave (curtos demais para
    identificar um depósito e colidiriam entre patentes diferentes).
    """
    k = re.sub(r'[^A-Za-z0-9]', '', cod or '').upper()
    return k if len(k) >= 6 else ''


# DS_FINALIDADE é campo livre: a maioria descreve a invenção, mas ~3% dos preenchidos
# trazem apenas a natureza do ativo ("PATENTE DE INVENÇÃO", "REGISTRO DE CULTIVAR").
# Separar os dois evita anunciar como descrição o que é só rótulo de categoria.
_NAT_TOKENS = {
    'PATENTE', 'PATENTES', 'INVENCAO', 'PI', 'MU', 'DI', 'PRIVILEGIO', 'INOVACAO',
    'MODELO', 'UTILIDADE', 'REGISTRO', 'CULTIVAR', 'PROGRAMA', 'COMPUTADOR',
    'SOFTWARE', 'PROPRIEDADE', 'INTELECTUAL', 'DESENHO', 'INDUSTRIAL', 'MARCA',
    'DEPOSITO', 'DEPOSITADA', 'CONCEDIDA', 'PEDIDO', 'DE', 'DO', 'DA', 'E',
}


def eh_natureza(txt):
    """True se DS_FINALIDADE é só o rótulo da categoria do ativo, não uma descrição."""
    s = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode().upper()
    toks = re.sub(r'[^A-Z0-9 ]', ' ', s).split()
    return bool(toks) and len(toks) <= 6 and all(t in _NAT_TOKENS for t in toks)


def load_csv(fp):
    for enc in ('latin-1', 'utf-8-sig', 'utf-8', 'cp1252'):
        try:
            return pd.read_csv(fp, sep=';', encoding=enc, dtype=str, low_memory=False)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f'não consegui decodificar {fp}')


def mapa_areas():
    """cd_programa → slug da área, lido do cache que o app já usa."""
    cd2slug, slugs = {}, []
    for d in sorted(os.listdir(CACHE_DIR)):
        meta_fp = os.path.join(CACHE_DIR, d, 'meta.json')
        if not os.path.exists(meta_fp):
            continue
        slugs.append(d)
        for cd in json.load(open(meta_fp, encoding='utf-8'))['cds']:
            cd2slug[cd] = d
    return cd2slug, slugs


def nome_area(slug):
    fp = os.path.join(DOCS_DIR, f'area-{slug}.json')
    if not os.path.exists(fp):
        return slug
    with open(fp, encoding='utf-8') as fh:
        # o metadata é o primeiro objeto do arquivo; ler só o começo evita
        # carregar 500 KB de dados só para pegar o nome
        head = fh.read(600)
    m = re.search(r'"area":"(.*?)"', head)
    return m.group(1) if m else slug


def carregar(quad):
    det_fp = os.path.join(DATA_DIR, f'tec_detalhe_{quad}_patente.csv')
    prod_fp = os.path.join(DATA_DIR, f'tec_prod_{quad}_patente.csv')
    if not os.path.exists(det_fp):
        return None

    det = load_csv(det_fp).fillna('')
    for c in det.columns:
        det[c] = det[c].map(limpar)
    n_bruto = len(det)
    det = det[det['IN_GLOSA'] != '1']
    n_glosa = n_bruto - len(det)

    # A tabela-mãe leva o título a 100% nos três quadriênios; sozinho, o detalhe dá
    # 42,5% (2013-2016), 77,1% (2017-2020) e 99,2% (2021-2024). Também traz a linha
    # de pesquisa, que o detalhe não tem.
    tit, linha = {}, {}
    if os.path.exists(prod_fp):
        prod = load_csv(prod_fp).fillna('')
        cols = ['ID_ADD_PRODUCAO_INTELECTUAL', 'NM_PRODUCAO']
        tem_lp = 'NM_LINHA_PESQUISA' in prod.columns
        if tem_lp:
            cols.append('NM_LINHA_PESQUISA')
        for r in prod[cols].values:
            pid = limpar(r[0])
            if not pid:
                continue
            tit[pid] = limpar(r[1])
            if tem_lp:
                linha[pid] = limpar(r[2])
    else:
        print(f'  ! sem tabela-mãe ({os.path.basename(prod_fp)}); '
              f'título só do detalhe, sem linha de pesquisa')
    return det, tit, linha, n_glosa


def processar(quad, cd2slug, resumo_max):
    """Lê um quadriênio e devolve (por_area, meta_nacional) ou None se não baixado."""
    carga = carregar(quad)
    if carga is None:
        return None
    det, tit, linha, n_glosa = carga
    quad_label, anos = QUAD_ANOS[quad]
    anos = [str(x) for x in anos]

    print(f'\n══ {quad_label} ══')
    print(f'[1] detalhe: {len(det)} registros ({n_glosa} glosados descartados)')

    det['_slug'] = det['CD_PROGRAMA_IES'].map(cd2slug)
    orfas = int(det['_slug'].isna().sum())
    det = det[det['_slug'].notna()]
    print(f'[2] casadas com área do app: {len(det)} '
          f'({100*len(det)/(len(det)+orfas):.1f}%) — {orfas} órfãs descartadas')

    # 2017-2020 não publica número de registro; 2013-2016 usa CD_REGISTRO.
    col_cod = next((c for c in ('DS_CODIGO_REGISTRO', 'CD_REGISTRO')
                    if c in det.columns), None)

    def col(r, nome):
        return r[nome] if nome and nome in det.columns else ''

    por_area = defaultdict(lambda: defaultdict(list))   # slug → cd → [patente]
    for r in det.to_dict('records'):
        pid = r['ID_ADD_PRODUCAO_INTELECTUAL']
        cod = col(r, col_cod)
        titulo = r.get('NM_TITULO', '') or tit.get(pid, '')
        fin = r.get('DS_FINALIDADE', '')
        natureza = fin if eh_natureza(fin) else ''
        resumo = '' if natureza else fin
        if resumo_max and len(resumo) > resumo_max:
            resumo = resumo[:resumo_max].rsplit(' ', 1)[0] + '…'
        # DT_DEPOSITO cobre registros em que DT_PEDIDO_DEPOSITO está vazio; juntas
        # levam a cobertura de data de 92,4% para 96,3% em 2021-2024.
        deposito = col(r, 'DT_PEDIDO_DEPOSITO') or col(r, 'DT_DEPOSITO')
        ano = r['AN_BASE_PRODUCAO']
        por_area[r['_slug']][r['CD_PROGRAMA_IES']].append({
            'id': pid,
            'ano': ano if ano in anos else '',
            'tit': titulo,
            'res': resumo,
            'nat': natureza,                   # rótulo de categoria, quando é o caso
            'cls': col(r, 'DS_CORRESP_SUBTIPO'),
            'cod': cod,
            'k': chave_registro(cod),          # chave de dedup (vazia = não dedupável)
            'inst': col(r, 'NM_INST_DEPOSITO'),
            'dep': deposito,
            'con': col(r, 'DT_CONCESSAO'),
            'est': col(r, 'DS_ESTAGIO_TECNOLOGIA'),
            'tt': col(r, 'IN_TRANSF_TEC_CONHECIMENTO'),
            'lp': linha.get(pid, ''),
        })

    todos = [p for cds in por_area.values() for v in cds.values() for p in v]
    nac_total = len(todos)
    cobertura = {k: round(100 * sum(1 for p in todos if p[k]) / nac_total, 1)
                 for k in ('tit', 'cod', 'dep', 'con', 'res', 'est')}
    # Distinguir "campo existe e ninguém preencheu" de "campo não existe nesta coleta":
    # 2013-2016 não tem estágio da tecnologia, 2017-2020 não tem número de registro.
    # Sem isso o app mostraria 0%, que sugere desleixo do programa em vez de ausência
    # do campo no formulário da CAPES.
    COLUNA = {'tit': 'NM_TITULO', 'cod': col_cod, 'dep': 'DT_PEDIDO_DEPOSITO',
              'con': 'DT_CONCESSAO', 'res': 'DS_FINALIDADE',
              'est': 'DS_ESTAGIO_TECNOLOGIA'}
    coletado = {k: bool(c) and c in det.columns for k, c in COLUNA.items()}
    coletado['tit'] = True          # sempre há título (detalhe ou tabela-mãe)

    # Regime de deduplicação — determina o que o app pode legitimamente afirmar.
    if col_cod is None:
        dedup = 'indisponivel'
    elif cobertura['cod'] >= 90:
        dedup = 'completa'
    else:
        dedup = 'parcial'

    nac_dist = None
    if dedup != 'indisponivel':
        nac_dist = (len({p['k'] for p in todos if p['k']}) +
                    sum(1 for p in todos if not p['k']))
        print(f'[3] nacional: {nac_total} declarações → {nac_dist} patentes distintas '
              f'(dedup {dedup}, {cobertura["cod"]}% com número de registro)')
    else:
        print(f'[3] nacional: {nac_total} declarações — SEM número de registro nesta '
              f'base, não há como deduplicar coautoria')
    print('[4] cobertura nacional (%): ' +
          ', '.join(f'{k}={v}' for k, v in cobertura.items()))

    meta_nac = {
        'quadrienio': quad_label, 'anos': anos, 'dedup': dedup,
        'n_nacional_declaracoes': nac_total, 'n_nacional_distintas': nac_dist,
        'cobertura_nacional': cobertura, 'campo_coletado': coletado,
    }
    return por_area, meta_nac


def gravar(slug, quad_label, por_area, meta_nac, anos):
    """Grava tec-<slug>-<quad>.json e devolve o resumo da área.

    Área sem nenhuma patente no quadriênio não gera arquivo (nem entra no manifest):
    o app trata a ausência como "nada declarado", que é o fato.
    """
    cds = por_area.get(slug, {})
    if not cds:
        return {'slug': slug, 'arquivo': None, 'n_declaracoes': 0,
                'n_distintas': None, 'n_programas': 0, 'kb': 0.0}
    progs, unicas, sem_cod = {}, set(), 0
    for cd, pats in cds.items():
        pats.sort(key=lambda p: (p['ano'] or '9999', p['tit']))
        por_ano = {y: 0 for y in anos}
        for p in pats:
            if p['ano']:
                por_ano[p['ano']] += 1
            if p['k']:
                unicas.add(p['k'])
            else:
                sem_cod += 1
        progs[cd] = {
            'n': len(pats),
            'ano': por_ano,
            'n_res': sum(1 for p in pats if p['res']),
            'n_cod': sum(1 for p in pats if p['cod']),
            'n_dep': sum(1 for p in pats if p['dep']),
            'n_con': sum(1 for p in pats if p['con']),
            'pat': [{k: v for k, v in p.items() if v and k != 'k'} for p in pats],
        }
    n_dist = None if meta_nac['dedup'] == 'indisponivel' else len(unicas) + sem_cod
    out = {
        'metadata': dict(meta_nac, **{
            'area': nome_area(slug), 'slug': slug, 'subtipo': 'PATENTE',
            'n_programas': len(progs),
            'n_declaracoes': sum(p['n'] for p in progs.values()),
            'n_distintas': n_dist,
            'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
            'fonte': ('CAPES — Detalhes da Produção Intelectual Técnica + '
                      f'Produção Intelectual, {quad_label}'),
        }),
        'programas': progs,
    }
    fp = os.path.join(DOCS_DIR, f'tec-{slug}-{quad_label}.json')
    with open(fp, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    return {'slug': slug, 'arquivo': f'dados/tec-{slug}-{quad_label}.json',
            'n_declaracoes': out['metadata']['n_declaracoes'],
            'n_distintas': n_dist, 'n_programas': len(progs),
            'kb': os.path.getsize(fp) / 1024}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quadrienio', nargs='*', default=sorted(QUAD_ANOS),
                    choices=sorted(QUAD_ANOS),
                    help='padrão: todos os que estiverem baixados')
    ap.add_argument('--area', nargs='*', help='restringe a estes slugs')
    ap.add_argument('--sem-manifest', action='store_true')
    ap.add_argument('--resumo-max', type=int, default=600,
                    help='corte da descrição da patente, em caracteres (0 = sem corte)')
    a = ap.parse_args()

    t0 = time.perf_counter()
    cd2slug, slugs = mapa_areas()
    if a.area:
        desconhecidas = [s for s in a.area if s not in slugs]
        if desconhecidas:
            raise SystemExit(f'ERRO: área(s) fora do cache: {", ".join(desconhecidas)}')
        slugs = a.area
    print(f'══ PATENTES — {len(slugs)} área(s), '
          f'{len(a.quadrienio)} quadriênio(s) pedido(s) ══')
    print(f'[0] cache: {len(cd2slug)} programas mapeados')

    os.makedirs(DOCS_DIR, exist_ok=True)
    por_quad, ausentes = {}, []
    for q in a.quadrienio:
        r = processar(q, cd2slug, a.resumo_max)
        if r is None:
            ausentes.append(q)
            continue
        por_area, meta_nac = r
        quad_label = meta_nac['quadrienio']
        resumos = [gravar(s, quad_label, por_area, meta_nac, meta_nac['anos'])
                   for s in slugs]
        por_quad[quad_label] = (meta_nac, resumos)
        tot_kb = sum(x['kb'] for x in resumos)
        com_pat = sum(1 for x in resumos if x['n_declaracoes'])
        print(f'[5] {len(resumos)} arquivos ({com_pat} áreas com patente), '
              f'{tot_kb/1024:.2f} MB')

    if ausentes:
        print('\n! não baixados (rode baixar_tecnica.py --quadrienio <q>): '
              + ', '.join(ausentes))
    if not por_quad:
        raise SystemExit('ERRO: nenhum quadriênio disponível.')

    if not a.sem_manifest and os.path.exists(MANIFEST):
        with open(MANIFEST, encoding='utf-8') as fh:
            man = json.load(fh)
        # bloco por área: um sub-bloco por quadriênio disponível
        por_slug = defaultdict(dict)
        for quad_label, (_, resumos) in por_quad.items():
            for x in resumos:
                if not x['n_declaracoes']:
                    continue          # área sem patente no quadriênio: nada a listar
                por_slug[x['slug']][quad_label] = {
                    k: x[k] for k in ('arquivo', 'n_declaracoes', 'n_distintas',
                                      'n_programas')}
        for ar in man.get('areas', []):
            if ar['slug'] in por_slug:
                ar['tec'] = {'subtipo': 'PATENTE',
                             'quadrienios': por_slug[ar['slug']]}
            else:
                ar.pop('tec', None)
        man['tecnica'] = {
            'subtipos': ['PATENTE'],
            'quadrienios': {q: {k: m[k] for k in
                                ('dedup', 'n_nacional_declaracoes',
                                 'n_nacional_distintas', 'cobertura_nacional',
                                 'campo_coletado')}
                            for q, (m, _) in sorted(por_quad.items())},
            'atualizado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        with open(MANIFEST, 'w', encoding='utf-8') as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)
        print(f'\n[6] manifest.json: {len(por_slug)} áreas com bloco "tec" '
              f'({len(por_quad)} quadriênios)')

    print(f'\nConcluído em {time.perf_counter()-t0:.1f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
