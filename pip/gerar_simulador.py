#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador preditivo (HTML5 interativo) — incentivo à produção e transição de nota.

Gera saida/simulador_pip.html (self-contained, Chart.js inline). Três simuladores:
  1) Nota 3 -> 4 (manual): auxílio R$, artigos/pesq/ano e % de adesão.
  2) Nota 4 -> 5 (manual): idem.
  3) Otimizador: fixa só o auxílio R$ e busca, por programa, a adesão mínima
     (com até AMAX art/pesq/ano viáveis) que leva o programa à mediana nacional;
     informa quando é inviável para adesão entre 5 e 100%.

Modelo: incremento médio do programa = A · (adesão%); nova produção = atual +
incremento; "transita" se nova produção >= mediana nacional da nota seguinte.
Orçamento/ano = auxílio × pesquisadores aderentes (dos programas abaixo da mediana).
Fator de impacto é desconsiderado nesta simulação (a pedido).

Dados (produção art/permanente/ano 2017-2020 e nº de permanentes) vêm do build_pip.
"""
import os
import json

import build_pip as B

SAIDA = B.SAIDA
DOCS = os.path.dirname(B.DADOS)
CHARTJS = os.path.join(DOCS, 'chart.umd.min.js')
AMAX = 2.0   # máx. de artigos/pesquisador/ano considerados viáveis pelo otimizador


def coletar():
    progs, area_de, areas = B.carregar()
    ref, _ = B.media_referencia(progs, area_de)
    stats = B.stats_por_nota(progs)
    linhas = B.analisar(progs, area_de, ref)
    ativo = lambda l: (l['situacao'] == 'EM FUNCIONAMENTO'
                       and 'fallback' not in l['baseline'] and l['ma_atual'] is not None)

    def coorte(nota):
        return [{'nome': l['programa'], 'area': l['area'],
                 'ma': round(l['ma_atual'], 2), 'n': l['n_perm'] or 0}
                for l in linhas if l['nota'] == nota and ativo(l)]

    return {'med4': stats[4]['nac']['mediana'], 'med5': stats[5]['nac']['mediana'],
            'n3': coorte(3), 'n4': coorte(4)}


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;color:#222;background:#f5f7fa;line-height:1.5;
     max-width:1060px;margin:0 auto;padding:14px 18px 60px}
h1{font-size:22px;color:#1A2A3A;margin-bottom:2px}
h2{font-size:17px;color:#1F618D;border-bottom:2px solid #AED6F1;padding-bottom:3px;margin:8px 0 10px}
.sub{color:#666;font-size:12.5px}.meta{color:#777;font-size:11px;margin-bottom:8px}
.card{background:#fff;border-radius:10px;box-shadow:0 1px 6px rgba(0,0,0,.08);padding:16px 18px;margin:16px 0}
.model{background:#EAF2F8;border-left:4px solid #2E86C1;padding:10px 14px;border-radius:6px;font-size:12.5px;margin:10px 0}
.inputs{display:flex;flex-wrap:wrap;gap:14px;margin:12px 0}
.fld{display:flex;flex-direction:column;font-size:12px;color:#444}
.fld label{font-weight:600;margin-bottom:3px}
.fld input{width:160px;padding:7px 8px;border:1px solid #bbb;border-radius:6px;font-size:14px}
.fld .hint{color:#888;font-size:10.5px;margin-top:2px}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0}
.kpi{flex:1;min-width:150px;background:#F8F9FA;border-left:4px solid #5DADE2;border-radius:6px;padding:8px 12px}
.kpi.big{border-left-color:#27AE60}.kpi.bud{border-left-color:#E67E22}
.kpi .v{font-size:21px;font-weight:800;color:#1A2A3A}.kpi .l{font-size:11px;color:#666;text-transform:uppercase}
.chartbox{position:relative;height:340px;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:12px;margin-top:8px}
th{background:#2C3E50;color:#fff;padding:5px 7px;text-align:center;position:sticky;top:0}
td{border:1px solid #ddd;padding:3px 7px;text-align:center}
td.l{text-align:left}
tr.ok td{background:#E9F7EF}tr.bad td{background:#FDEDEC}
.tbl-wrap{max-height:360px;overflow:auto;border:1px solid #eee;border-radius:6px;margin-top:8px}
.tag{display:inline-block;font-weight:700}.tag.g{color:#1E8449}.tag.r{color:#C0392B}
"""

# JS: __DATA__ e __AMAX__ substituídos; sem f-string p/ evitar escapar chaves.
JS = r"""
const SIM = __DATA__;
const AMAX = __AMAX__;
const nf = new Intl.NumberFormat('pt-BR');
const brl = x => 'R$ ' + nf.format(Math.round(x));
const f1 = x => (x===null||x===undefined||isNaN(x)) ? '—' : x.toFixed(1).replace('.', ',');
const vL = { id:'vL', afterDraw(c){ const o=(c.options.plugins&&c.options.plugins.vL)||{};
  (o.lines||[]).forEach(L=>{ const x=c.scales.x,a=c.chartArea, x0=x.getPixelForValue(L.value),ctx=c.ctx;
    ctx.save();ctx.beginPath();ctx.moveTo(x0,a.top);ctx.lineTo(x0,a.bottom);ctx.lineWidth=1.6;
    ctx.strokeStyle=L.color;ctx.setLineDash(L.dash||[6,4]);ctx.stroke();ctx.restore();});}};
Chart.register(vL);

const charts = {};
function barChart(id, med){
  charts[id] = new Chart(document.getElementById(id), {
    type:'bar',
    data:{ labels:[], datasets:[
      { label:'Produção atual', data:[], backgroundColor:'#AEB6BF' },
      { label:'Após incentivo', data:[], backgroundColor:[] } ] },
    options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
      scales:{ x:{ title:{display:true,text:'art/permanente/ano'} } },
      plugins:{ legend:{position:'top'},
        vL:{ lines:[{value:med,color:'#C0392B',dash:[6,4]}] },
        tooltip:{ callbacks:{ label:it=> it.dataset.label+': '+f1(it.parsed.x) } } } }
  });
}
function updBar(id, labels, atual, novo, med){
  const ch=charts[id]; ch.data.labels=labels;
  ch.data.datasets[0].data=atual; ch.data.datasets[1].data=novo;
  ch.data.datasets[1].backgroundColor=novo.map((v,i)=> v>=med ? '#27AE60' : '#5DADE2');
  ch.options.plugins.vL.lines=[{value:med,color:'#C0392B',dash:[6,4]}];
  ch.update();
}

function num(id){ return parseFloat(document.getElementById(id).value); }
function clamp(v,a,b){ return Math.max(a, Math.min(b, v)); }

// ---- Simulador manual (nota N -> N+1) ----
function manual(simId, cohort, med){
  const X = clamp(num(simId+'X')||0, 1000, 3000);
  const A = Math.max(0, num(simId+'A')||0);
  const p = clamp(num(simId+'P')||0, 5, 100);
  const progs = SIM[cohort];
  const below = progs.filter(o=> o.ma < med);
  const jaAcima = progs.length - below.length;
  let trans=0, budget=0, rows='';
  const labs=[], at=[], nv=[];
  below.slice().sort((a,b)=>a.ma-b.ma).forEach(o=>{
    const inc = A*(p/100), novo = o.ma + inc, ok = novo >= med;
    if(ok) trans++;
    const adh = Math.round(o.n*(p/100)); budget += X*adh;
    labs.push(o.nome.length>34?o.nome.slice(0,34):o.nome); at.push(+o.ma.toFixed(2)); nv.push(+novo.toFixed(2));
    rows += '<tr class="'+(ok?'ok':'')+'"><td class="l">'+o.nome+'</td><td>'+o.n+'</td><td>'+f1(o.ma)+
      '</td><td>'+f1(novo)+'</td><td>'+f1(med)+'</td><td>'+adh+'</td><td>'+(ok?'<span class="tag g">✓ atinge</span>':'—')+'</td></tr>';
  });
  document.getElementById(simId+'K1').textContent = trans;
  document.getElementById(simId+'K2').textContent = below.length;
  document.getElementById(simId+'K3').textContent = brl(budget);
  document.getElementById(simId+'note').textContent =
    progs.length+' programas no total · '+jaAcima+' já ≥ mediana · '+below.length+' abaixo · incremento aplicado = '+
    f1(A*(p/100))+' art/pesq/ano (A '+f1(A)+' × adesão '+f1(p)+'%).';
  document.getElementById(simId+'rows').innerHTML = rows ||
    '<tr><td colspan="7">Todos os programas já estão na mediana.</td></tr>';
  updBar(simId+'Chart', labs, at, nv, med);
}

// ---- Otimizador (fixa auxílio; busca adesão mínima por programa) ----
function otim(){
  const X = clamp(num('o3X')||0, 1000, 3000);
  let html='';
  [['n3', SIM.med4, '3 → 4'], ['n4', SIM.med5, '4 → 5']].forEach(([coh, med, lbl])=>{
    const progs = SIM[coh];
    const below = progs.filter(o=> o.ma < med);
    let feas=0, infeas=0, budget=0, rows='';
    below.slice().sort((a,b)=>a.ma-b.ma).forEach(o=>{
      const gap = med - o.ma;                 // produção média a adicionar
      if(gap > AMAX){                          // nem a 100% de adesão com AMAX alcança
        infeas++;
        rows += '<tr class="bad"><td class="l">'+o.nome+'</td><td>'+f1(o.ma)+'</td><td>'+f1(gap)+
          '</td><td colspan="3"><span class="tag r">não alcança</span> (precisaria de '+f1(gap)+
          ' art/pesq a 100% de adesão; acima do viável de '+f1(AMAX)+')</td></tr>';
        return;
      }
      const pOpt = Math.max(5, 100*gap/AMAX);  // adesão mínima (%) usando A=AMAX
      const aOpt = gap/(pOpt/100);             // artigos/pesq exatos p/ essa adesão (<= AMAX)
      const adh = Math.round(o.n*pOpt/100);
      const cost = X*adh; budget += cost; feas++;
      rows += '<tr class="ok"><td class="l">'+o.nome+'</td><td>'+f1(o.ma)+'</td><td>'+f1(gap)+
        '</td><td>'+f1(aOpt)+'</td><td>'+f1(pOpt)+'%</td><td>'+brl(cost)+'</td></tr>';
    });
    html += '<h3 style="margin:14px 0 4px;color:#2C3E50">Nota '+lbl+' — alvo mediana '+f1(med)+
      ' · '+feas+' viáveis · '+infeas+' inviáveis · orçamento '+brl(budget)+'/ano</h3>'+
      '<div class="tbl-wrap"><table><tr><th>Programa</th><th>Produção</th><th>Falta (art/pesq)</th>'+
      '<th>Art/pesq ótimo</th><th>Adesão ótima</th><th>Custo/ano</th></tr>'+
      (rows||'<tr><td colspan="6">Todos já ≥ mediana.</td></tr>')+'</table></div>';
  });
  document.getElementById('o3X_eff').textContent = brl(clamp(num('o3X')||0,1000,3000));
  document.getElementById('o3out').innerHTML = html;
}

window.addEventListener('DOMContentLoaded', ()=>{
  barChart('s3Chart', SIM.med4);
  barChart('s4Chart', SIM.med5);
  ['s3X','s3A','s3P'].forEach(id=>document.getElementById(id).addEventListener('input', ()=>manual('s3','n3',SIM.med4)));
  ['s4X','s4A','s4P'].forEach(id=>document.getElementById(id).addEventListener('input', ()=>manual('s4','n4',SIM.med5)));
  document.getElementById('o3X').addEventListener('input', otim);
  manual('s3','n3',SIM.med4); manual('s4','n4',SIM.med5); otim();
});
"""


def manual_card(sid, titulo, alvo_txt):
    return f"""
<div class="card">
<h2>{titulo}</h2>
<p class="sub">{alvo_txt}</p>
<div class="inputs">
  <div class="fld"><label>Auxílio (R$/pesquisador/ano)</label>
    <input id="{sid}X" type="number" min="1000" max="3000" step="50" value="1000">
    <span class="hint">entre R$ 1.000 e R$ 3.000</span></div>
  <div class="fld"><label>Artigos/pesquisador/ano (A)</label>
    <input id="{sid}A" type="number" min="0" max="10" step="0.1" value="2.0">
    <span class="hint">produção extra de quem adere (1 casa decimal)</span></div>
  <div class="fld"><label>Adesão do programa (%)</label>
    <input id="{sid}P" type="number" min="5" max="100" step="0.1" value="50.0">
    <span class="hint">de 5,0 a 100,0%</span></div>
</div>
<div class="kpis">
  <div class="kpi big"><div class="v" id="{sid}K1">0</div><div class="l">Programas que atingem a mediana</div></div>
  <div class="kpi"><div class="v" id="{sid}K2">0</div><div class="l">Programas abaixo da mediana</div></div>
  <div class="kpi bud"><div class="v" id="{sid}K3">R$ 0</div><div class="l">Orçamento por ano</div></div>
</div>
<p class="meta" id="{sid}note"></p>
<div class="chartbox"><canvas id="{sid}Chart"></canvas></div>
<div class="tbl-wrap"><table>
<tr><th>Programa</th><th>Perm.</th><th>Produção atual</th><th>Após incentivo</th><th>Mediana nac.</th><th>Aderentes</th><th>Atinge?</th></tr>
<tbody id="{sid}rows"></tbody></table></div>
</div>"""


def build_html(data):
    chartjs = open(CHARTJS, encoding='utf-8').read()
    js = JS.replace('__DATA__', json.dumps(data, ensure_ascii=False)).replace('__AMAX__', repr(AMAX))
    body = f"""
<h1>Simulador preditivo — incentivo à produção e transição de nota (UnB)</h1>
<p class="sub">Quantos programas mudariam de nota com um auxílio por pesquisador, comparando com a mediana nacional</p>
<p class="meta">Prof. Titular David Lima Azevedo — GDAI / Núcleo de Estrutura da Matéria / Instituto de Física — UnB ·
Sistema MAPA-PG · produção art/permanente/ano (2017-2020). <b>Fator de impacto desconsiderado nesta simulação.</b></p>

<div class="model"><b>Modelo.</b> Incremento médio do programa = <b>A × (adesão%)</b>, onde A = artigos/pesquisador/ano
de quem adere. Nova produção = atual + incremento. Um programa <b>atinge</b> a meta se a nova produção alcança a
<b>mediana nacional</b> dos programas da nota seguinte (Nota 4 = {data['med4']:.2f} · Nota 5 = {data['med5']:.2f} art/pesq/ano,
substitua a vírgula por ponto mentalmente). Orçamento/ano = auxílio × pesquisadores aderentes dos programas abaixo da mediana.</div>

{manual_card('s3', '1) Simulador Nota 3 → 4 (manual)', f"Alvo: mediana nacional da nota 4 = {data['med4']:.2f} art/pesq/ano. {len(data['n3'])} programas nota 3 acadêmicos da UnB.")}
{manual_card('s4', '2) Simulador Nota 4 → 5 (manual)', f"Alvo: mediana nacional da nota 5 = {data['med5']:.2f} art/pesq/ano. {len(data['n4'])} programas nota 4 acadêmicos da UnB.")}

<div class="card">
<h2>3) Otimizador — fixa o auxílio e busca a solução ótima</h2>
<p class="sub">Informe apenas o auxílio. Para cada programa, busca-se a <b>adesão mínima</b> (e os artigos/pesquisador
correspondentes, até {AMAX:.1f}/ano) que levam o programa à mediana nacional, ao <b>menor orçamento</b>. Se nem a 100%
de adesão alcançar, o programa é marcado <b>inviável</b> por produção (o salto dependerá de infraestrutura/impacto).</p>
<div class="inputs">
  <div class="fld"><label>Auxílio (R$/pesquisador/ano)</label>
    <input id="o3X" type="number" min="1000" max="3000" step="50" value="1000">
    <span class="hint">entre R$ 1.000 e R$ 3.000 · efetivo: <b id="o3X_eff">R$ 1.000</b></span></div>
</div>
<div id="o3out"></div>
</div>
"""
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'<title>Simulador preditivo — MAPA-PG (UnB)</title>'
            f'<style>{CSS}</style></head><body>{body}'
            f'<script>{chartjs}</script><script>{js}</script></body></html>')


def main():
    data = coletar()
    os.makedirs(SAIDA, exist_ok=True)
    out = os.path.join(SAIDA, 'simulador_pip.html')
    open(out, 'w', encoding='utf-8').write(build_html(data))
    print('Simulador HTML5:', out, f"({os.path.getsize(out)/1024:.0f} KB)")
    print(f"  nota 3: {len(data['n3'])} programas | nota 4: {len(data['n4'])} programas")
    print(f"  medianas alvo: nota4={data['med4']} nota5={data['med5']} | AMAX={AMAX}")


if __name__ == '__main__':
    main()
