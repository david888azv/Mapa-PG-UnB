#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gráfico nacional dos programas em QUEDA CRÍTICA (classe VERMELHO).
Reusa a classificação de investiga_nacional.py (sinal limpo de artigos brutos).

Painel A — trajetórias INDEXADAS (base 2017-20 = 100): mediana nacional (estável)
           vs. o leque dos programas vermelhos colapsando no período 2021-24.
Painel B — nº de programas vermelhos por área CAPES (onde se concentram).

Saída: saida/quedas_criticas_nacional.png
"""
import os, json
from statistics import mean, median
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from investiga_nacional import CACHE, carregar_meta_programas, montar
from investiga_quedas import ANOS, BASE, REC, MLABEL, SUF

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, 'saida')
YRS = list(range(2017, 2025))   # foco no período comparável


def main():
    A = json.load(open(os.path.join(CACHE, 'art_total_ano.json'), encoding='utf-8'))
    art, names, ies = A['art'], A['names'], A['ies']
    roster = json.load(open(os.path.join(CACHE, 'roster_ano.json'), encoding='utf-8'))
    meta = carregar_meta_programas()
    progs = montar(art, names, ies, roster, meta)

    def indice(p):
        b = mean(p['serie'][y] for y in BASE)
        return [(p['serie'][y] / b * 100) if b > 0 else None for y in YRS]

    reds = [p for p in progs if p['classe'] == 'VERMELHO']
    nao_estr = [p for p in progs if p['classe'] != 'ESTRUTURAL' and mean(p['serie'][y] for y in BASE) > 0]

    # mediana nacional do índice por ano
    med = []
    for j, y in enumerate(YRS):
        vals = [indice(p)[j] for p in nao_estr if indice(p)[j] is not None]
        med.append(median(vals) if vals else None)

    fig = plt.figure(figsize=(15, 6.8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.65, 1], wspace=0.22)
    axA = fig.add_subplot(gs[0]); axB = fig.add_subplot(gs[1])

    # ---- Painel A
    for p in reds:
        axA.plot(YRS, indice(p), color='#E74C3C', lw=0.7, alpha=0.13, zorder=2)
    axA.plot([], [], color='#E74C3C', lw=1.5, alpha=0.6,
             label=f'{len(reds)} programas em queda crítica (cada linha = 1 programa)')
    axA.plot(YRS, med, color='#1E8449', lw=3.5, marker='o', zorder=5,
             label='Mediana nacional (todos os programas)')
    axA.axhline(100, color='#999999', ls=':', lw=1, zorder=1)
    axA.axvspan(2020.5, 2024.5, color='#FADBD8', alpha=0.45, zorder=0)
    axA.text(2022.5, axA.get_ylim()[1] * 0.97, '2021-2024\n(coleta em andamento)',
             ha='center', va='top', fontsize=9, color='#922B21')
    axA.set_ylim(0, 200)
    axA.set_xticks(YRS); axA.set_xlabel('Ano-base')
    axA.set_ylabel('Produção indexada (média 2017-2020 = 100)')
    axA.set_title('A) Trajetória: mediana nacional estável × programas em queda crítica',
                  fontsize=11, fontweight='bold')
    axA.grid(alpha=0.3); axA.legend(fontsize=9, loc='upper left', framealpha=0.95)

    # ---- Painel B
    by_area = Counter(p['area'] for p in reds)
    top = by_area.most_common(14)[::-1]
    labels = [a if len(a) <= 30 else a[:29] + '…' for a, _ in top]
    vals = [n for _, n in top]
    ypos = range(len(top))
    axB.barh(list(ypos), vals, color='#C0392B', alpha=0.85)
    axB.set_yticks(list(ypos)); axB.set_yticklabels(labels, fontsize=8)
    for i, v in enumerate(vals):
        axB.text(v + 0.1, i, str(v), va='center', fontsize=8, color='#7B241C')
    axB.set_xlabel('Nº de programas em queda crítica')
    axB.set_title(f'B) Onde estão os {len(reds)} críticos (por área CAPES)',
                  fontsize=11, fontweight='bold')
    axB.grid(axis='x', alpha=0.3)

    fig.suptitle(f'BRASIL — programas de pós-graduação {MLABEL.upper()} em queda crítica de produção (2021-2024)\n'
                 'dados brutos CAPES · sinal limpo (artigos distintos) · recálculo mapa-pg-multi/pip',
                 fontsize=12.5, fontweight='bold')
    fig.subplots_adjust(top=0.86, bottom=0.10, left=0.06, right=0.985)
    out = os.path.join(SAIDA, f'quedas_criticas_nacional{SUF}.png')
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f'{len(reds)} vermelhos | salvo: {out}')
    print('Top áreas:', by_area.most_common(6))


if __name__ == '__main__':
    main()
