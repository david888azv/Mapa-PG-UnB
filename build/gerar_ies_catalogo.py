#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o catálogo COMPLETO de instituições para o seletor de referência do app
===========================================================================
Antes, a referência só podia ser uma de 27 IFES (`registry_ies.json`, 391 KB no
shell). Agora o usuário busca por sigla ou nome — "FIO CRUZ" acha as 7 unidades
da FIOCRUZ — entre TODAS as instituições com programa avaliado.

SAÍDAS
------
`docs/ies_index.json`  (~110 KB)  índice enxuto de busca: sigla, nome, UF,
    nº de programas, áreas em que atua, apelidos de busca e o arquivo da IES.
    Substitui `registry_ies.json` no precache — o shell FICA MENOR cobrindo 18×
    mais instituições.
`docs/dados/ies-<slug>.json`  (~2 KB cada)  a lista de programas daquela
    instituição, buscada só quando ela é escolhida. Mesmo shape que
    `registry_ies.por_ies[X]` + os campos do `ifes[]`, para `buildRegistryForRef()`
    no app mudar o mínimo.

DECISÕES
--------
• **Nome de arquivo por slug** (`slug_ies` em ies_core): há sigla com espaço,
  acento e barra ('UFPB-JOÃO PESSOA', 'FIOCRUZ-NESC/CPQAM', 'FIOCRUZ-EGS
  BRASÍLIA'), que não vai crua para uma URL. Colisão aborta o build.
  Vai em `docs/dados/` e NÃO em `docs/ies/<sigla>/`, que já é das landings de SEO.
• **As 27 IFES seguem privilegiadas**: entram em `destaque` (atalhos visíveis no
  painel, sem precisar buscar), mantêm o nome editorial e a agregação de campi.
• **Campus agregado não vira entrada separada.** UFPB-AREIA, UFPB-JOÃO PESSOA,
  UFPB-RIO TINTO, UFSC-BLUMENAU e UFS-ITABAIANA são entidades próprias já
  contidas em UFPB/UFSC/UFS; listá-las de novo faria duas opções com programas
  sobrepostos. Elas entram como APELIDO DE BUSCA da instituição-mãe, então
  procurar "blumenau" ou "itabaiana" continua achando.
• Instituição sem nenhum programa fora de desativação não entra (não haveria o
  que comparar).
• **Programa aprovado e ainda sem nota entra em campo separado**
  (`programas_sem_nota` no arquivo da IES, `nsn` no índice), nunca em
  `programas`. A regra de comparação não muda — sem nota ele continua fora de
  médias, rankings e gráficos —, mas deixa de ser invisível: antes o programa
  não existia em lugar nenhum do app e isso se lia como programa inexistente.
  Ver `sem_nota.py`.

A regra de quais programas são de cada instituição está em `ies_core.py`,
compartilhada com `gerar_registry_ies.py`.
"""
import json
import os
import sys
import time
from collections import defaultdict

import ies_core as C
import sem_nota as SN
from gerar_registry_ies import IFES, entidades_das_ifes

INDEX_PATH = os.path.join(C.REPO, 'docs', 'ies_index.json')
DADOS_DIR = os.path.join(C.REPO, 'docs', 'dados')


def construir():
    por_entidade, ent_de_sigla, canon_de_sigla = C.carregar_canonico()
    registros, siglas_vistas = C.varrer_areas()

    ents_27 = entidades_das_ifes(ent_de_sigla)
    ents_das_27 = {e for es in ents_27.values() for e in es}

    def canon(s):
        return canon_de_sigla.get(s, s)

    canonicas = {canon(s) for s in siglas_vistas}
    # campus de uma das 27: contido na mãe, não vira entrada própria
    absorvidas = sorted(k for k in canonicas
                        if ent_de_sigla.get(k) in ents_das_27 and k not in IFES)

    # sigla_ies → (uf, nome, siglas CAPES, apelidos de busca)
    perfil = {}
    for k in IFES:
        siglas = C.siglas_de_entidades(ents_27[k], por_entidade)
        apelidos = sorted(set(siglas) - {k})
        # nome dos campi agregados entra na busca ("blumenau", "itabaiana")
        for e in ents_27[k]:
            nm = por_entidade[e].get('nome') or ''
            if nm:
                apelidos.append(nm)
        perfil[k] = (IFES[k][0], IFES[k][1], siglas, sorted(set(apelidos)))

    for k in sorted(canonicas - set(IFES) - set(absorvidas)):
        ent = ent_de_sigla.get(k)
        if ent is None:
            print(f'⚠ {k}: sem entidade em ies_canonico.json — usando só a própria sigla',
                  file=sys.stderr)
            perfil[k] = ('', k, [k], [])
            continue
        info = por_entidade[ent]
        siglas = C.siglas_de_entidades({ent}, por_entidade)
        perfil[k] = (info.get('uf', ''), info.get('nome') or k, siglas,
                     sorted(set(siglas) - {k}))

    siglas_de = {k: set(v[2]) for k, v in perfil.items()}
    por_ies = C.programas_por_ies(registros, siglas_de, C.sufixos_unb())

    # ── programas aprovados e ainda SEM NOTA ────────────────────────────
    # Não entram em `programas` (o app compara por nota e não teria onde
    # colocá-los); entram numa lista à parte, para a instituição poder dizer que
    # existem. Ver `sem_nota.py` e o caso da UFG em Geociências.
    var2ies = {v: k for k, vs in siglas_de.items() for v in vs}
    sem_por_ies = defaultdict(list)
    sem_orfaos = []
    for p in SN.coletar():
        ies = var2ies.get(p['sigla'])
        if ies is None:
            sem_orfaos.append(p)
            continue
        sem_por_ies[ies].append({k: v for k, v in p.items() if k != 'conceito_bruto'})

    # ── instituição que SÓ tem programa sem nota ────────────────────────
    # Ela não aparece nos `area-*.json` — não tem programa avaliado —, então não
    # existia em `perfil` e caía fora do seletor inteiro. É a situação de quem
    # acabou de ter o primeiro programa aprovado: procurar a instituição pelo
    # nome não achava nada, e não achar nada se lê como "não está no sistema".
    # Entra com `programas` vazio; a cascata da v5.6.0 já sabe montar as áreas a
    # partir dos programas sem nota, e nenhuma média muda, porque não há nota.
    novas = []
    for p in sem_orfaos:
        k = canon(p['sigla'])
        if k in perfil:            # renomeação: a canônica já está no seletor
            sem_por_ies[k].append({x: v for x, v in p.items() if x != 'conceito_bruto'})
            continue
        if k not in perfil:
            ent = ent_de_sigla.get(p['sigla'])
            if ent is None:
                print(f'⚠ {p["sigla"]}: sem entidade em ies_canonico.json — '
                      f'programa sem nota fica fora do seletor', file=sys.stderr)
                continue
            info = por_entidade[ent]
            siglas = C.siglas_de_entidades({ent}, por_entidade)
            perfil[k] = (info.get('uf', ''), info.get('nome') or k, siglas,
                         sorted(set(siglas) - {k}))
            por_ies[k] = {'grandes_areas': {}, 'programas': []}
            novas.append(k)
        sem_por_ies[k].append({x: v for x, v in p.items() if x != 'conceito_bruto'})
    novas = sorted(set(novas))

    # Sem programa NENHUM — nem com nota, nem aprovado sem nota → fora do seletor
    vazias = sorted(k for k in perfil
                    if not por_ies[k]['programas'] and not sem_por_ies.get(k))
    for k in vazias:
        del perfil[k]
        del por_ies[k]
        sem_por_ies.pop(k, None)

    # slug único
    slugs = {}
    for k in perfil:
        s = C.slug_ies(k)
        if s in slugs:
            sys.exit(f'✗ colisão de slug {s!r}: {slugs[s]!r} e {k!r}')
        slugs[s] = k

    return perfil, por_ies, slugs, absorvidas, vazias, sem_por_ies, novas


def main():
    t0 = time.perf_counter()
    perfil, por_ies, slugs, absorvidas, vazias, sem_por_ies, novas = construir()
    slug_de = {v: k for k, v in slugs.items()}

    # ── um arquivo por instituição ──
    escritos = 0
    tam_total = 0
    for k in sorted(perfil):
        uf, nome, siglas, _ap = perfil[k]
        p = por_ies[k]
        payload = {
            'sigla': k, 'nome': nome, 'uf': uf, 'siglas_capes': siglas,
            'grandes_areas': p['grandes_areas'], 'programas': p['programas'],
        }
        if sem_por_ies.get(k):
            payload['programas_sem_nota'] = sem_por_ies[k]
        caminho = os.path.join(DADOS_DIR, f'ies-{slug_de[k]}.json')
        with open(caminho, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(',', ':'))
        tam_total += os.path.getsize(caminho)
        escritos += 1

    # ── índice de busca ──
    lista = []
    for k in sorted(perfil, key=lambda x: (-len(por_ies[x]['programas']), x)):
        uf, nome, _siglas, apelidos = perfil[k]
        areas = sorted({pr['slug_area'] for pr in por_ies[k]['programas']})
        e = {'s': k, 'n': nome, 'uf': uf,
             'np': len(por_ies[k]['programas']), 'ar': areas,
             'f': f'dados/ies-{slug_de[k]}.json'}
        if sem_por_ies.get(k):
            e['nsn'] = len(sem_por_ies[k])   # aprovados sem nota, fora da comparação
        if apelidos:
            e['al'] = apelidos
        lista.append(e)

    index = {
        'gerado_em': time.strftime('%Y-%m-%d %H:%M:%S'),
        'padrao': 'UNB',
        'n_ies': len(lista),
        'destaque': [i['sigla'] for i in
                     sorted(({'sigla': k, 'uf': IFES[k][0]} for k in IFES if k in perfil),
                            key=lambda x: x['uf'])],
        'ies': lista,
    }
    with open(INDEX_PATH, 'w', encoding='utf-8') as fh:
        json.dump(index, fh, ensure_ascii=False, separators=(',', ':'))

    n_prog = len({pr['cd_programa'] for k in por_ies for pr in por_ies[k]['programas']})
    print(f'✓ {INDEX_PATH}  ({os.path.getsize(INDEX_PATH)/1024:.0f} KB)')
    print(f'  instituições no seletor: {len(lista)}  (destaque: {len(index["destaque"])})')
    print(f'  programas distintos cobertos: {n_prog}')
    print(f'✓ {escritos} arquivos dados/ies-*.json  ({tam_total/1024:.0f} KB no total, '
          f'média {tam_total/escritos/1024:.1f} KB)')
    if absorvidas:
        print(f'  campi agregados à sede (apelido de busca, sem entrada própria): '
              f'{len(absorvidas)} — {absorvidas}')
    if vazias:
        print(f'  fora do seletor por não ter programa ativo: {len(vazias)} — {vazias[:6]}')
    n_sem = sum(len(v) for v in sem_por_ies.values())
    print(f'  programas aprovados e ainda SEM NOTA: {n_sem} em {len(sem_por_ies)} instituições '
          f'(listados à parte, fora de médias e rankings)')
    if novas:
        print(f'  instituições que entraram SÓ por programa sem nota: {len(novas)} — {novas}')
    print(f'  {time.perf_counter()-t0:.1f}s')


if __name__ == '__main__':
    main()
