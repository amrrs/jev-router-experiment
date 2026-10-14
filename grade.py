"""Deterministic scoring plus blinded writing rubric results; no credentials."""
import ast, copy, csv, json, math, os, random, re, statistics, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ARMS=['openai','small','large','routed']
def parse(s):
    return json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',s.strip()))
def content(r):
    return r.get('response',{}).get('choices',[{}])[0].get('message',{}).get('content') or ''
def equal(a,b):
    if isinstance(b,bool) or b is None:return a is b
    if isinstance(b,(float,int)):return type(a) in (int,float) and math.isclose(a,b,rel_tol=0,abs_tol=1e-4)
    if isinstance(b,list):return isinstance(a,list) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    if isinstance(b,dict):return isinstance(a,dict) and a.keys()==b.keys() and all(equal(a[k],v) for k,v in b.items())
    return a==b
def semantic_object(a,b):
    # The original prose did not define exact JSON field names/types for all tasks.
    # Keep raw schema equality separately, and normalize obvious equivalent names
    # and numeric string/fraction notation symmetrically for every model.
    aliases={'hours_to_fill':'hours','makespan':'hours','makespan_hours':'hours','minimum_makespan':'hours','minimum_makespan_hours':'hours','expected_flips':'flips','expected_number_of_flips':'flips','overall_conversion_rate':'conversion_rate','probability_of_disease_given_positive':'probability'}
    if not isinstance(a,dict):return False
    norm={aliases.get(k,k):v for k,v in a.items()}
    for k,v in b.items():
        if type(v) in (int,float) and isinstance(norm.get(k),str):
            try:norm[k]=float(Fraction(norm[k]))
            except (ValueError,ZeroDivisionError):pass
    return equal(norm,b)
def coding(code,cases,no_mutation=False):
    tree=ast.parse(code)
    for n in ast.walk(tree):
        if isinstance(n,(ast.Import,ast.ImportFrom,ast.ClassDef,ast.Global,ast.Nonlocal)):raise ValueError('Disallowed Python construct')
        if isinstance(n,ast.Attribute) and n.attr.startswith('_'):raise ValueError('Disallowed attribute')
        if isinstance(n,ast.Name) and n.id.startswith('__'):raise ValueError('Disallowed name')
    runner='''import json,resource,sys
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
d=json.load(sys.stdin)
allowed={k:__builtins__.__dict__[k] for k in ['len','range','enumerate','zip','sorted','reversed','min','max','sum','abs','round','all','any','list','dict','set','tuple','str','int','float','bool','isinstance','map','filter','ValueError','Exception']}
scope={'__builtins__':allowed}
exec(compile(d['code'],'candidate','exec'),scope,scope)
out=[]
for case in d['cases']:
 x=json.loads(json.dumps(case[0]));before=json.dumps(x,sort_keys=True)
 result=scope['solve'](x)
 out.append({'result':result,'mutated':before!=json.dumps(x,sort_keys=True)})
print(json.dumps(out))
'''
    with tempfile.TemporaryDirectory() as temp:
        p=subprocess.run([sys.executable,'-I','-c',runner],input=json.dumps({'code':code,'cases':cases}),text=True,capture_output=True,timeout=4,cwd=temp,env={})
    if p.returncode:raise ValueError('Candidate execution failed: '+p.stderr[-250:])
    out=json.loads(p.stdout)
    checks=[equal(o['result'],c[1]) and (not no_mutation or not o['mutated']) for o,c in zip(out,cases)]
    return all(checks),checks
def bootstrap(values,seed=41):
    if not values:return [None,None]
    rng=random.Random(seed);means=sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(5000))
    return [means[125],means[4874]]
def main():
    tasks=json.loads((ROOT/'tasks.json').read_text());byid={t['id']:t for t in tasks}
    calls=[json.loads(l) for l in (ROOT/'results/calls.jsonl').read_text().splitlines()]
    routes={(r['meta']['task'],r['meta']['trial']):r for r in calls if r['meta']['kind']=='routing'}
    grades={}
    for r in calls:
        if r['meta']['kind']!='judge':continue
        try:
            g=parse(content(r))['grades']
            for slot,arm in r['meta']['blind_map'].items():grades[(r['meta']['task'],r['meta']['trial'],arm)]=g[slot]
        except Exception:pass
    rows=[]
    for r in calls:
        m=r['meta']
        if m['kind']!='generation' or m['task'] not in byid:continue
        t=byid[m['task']];reason='';passed=False;score=0;checks=[]
        try:
            assert r['status']=='ok','API error'
            obj=parse(content(r))
            if t['tests']:
                passed,checks=coding(obj['code'],t['tests'],'Do not mutate' in t['prompt']);score=float(passed)
            elif t['expected'] is not None:passed=semantic_object(obj,t['expected']) if t['id'].startswith('T') else equal(obj,t['expected']);score=float(passed)
            else:
                g=grades[(t['id'],m['trial'],m['arm'])];checks=g['checks'];reason=g['reason']
                assert len(checks)==len(t['rubric']) and all(type(x) is int and x in (0,1) for x in checks)
                # Word count is executable; override any judge counting error.
                word_count=len(obj['text'].split());lo,hi=map(int,re.search(r'(\d+)-(\d+) words',t['rubric'][0]).groups())
                checks[0]=int(lo<=word_count<=hi)
                score=sum(checks)/len(checks);passed=all(checks)
        except Exception as e:reason=f'{type(e).__name__}: {str(e)[:220]}'
        route=routes.get((t['id'],m['trial']),{}) if m['arm']=='routed' else {}
        ra=route.get('response',{}).get('answers',{}).get('route',{})
        cost=r['cost_usd'];routing_cost=route.get('cost_usd',0) or 0
        upper=r['budget_charge_usd']+route.get('budget_charge_usd',0)
        rows.append(dict(task=t['id'],name=t['name'],category=t['category'],difficulty=t['difficulty'],trial=m['trial'],arm=m['arm'],model=r.get('response',{}).get('model'),passed=bool(passed),score=score,checks=checks,reason=reason,cost_usd=(cost or 0)+routing_cost,cost_upper_usd=upper,reported_cost_usd=cost,routing_cost_usd=routing_cost,latency_s=r['latency_s']+route.get('latency_s',0),generation_latency_s=r['latency_s'],route_choice=ra.get('choice'),route_confidence=ra.get('confidence'),status=r['status'],finish_reason=r.get('response',{}).get('choices',[{}])[0].get('finish_reason'),response=content(r)))
    (ROOT/'results/scored.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (ROOT/'results/scored.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'arms':{},'budget_spend':{p:sum(r['budget_charge_usd'] for r in calls if r['provider']==p) for p in ['openai','nebius','jev']},'total_api_calls':len(calls),'api_errors':sum(r['status']!='ok' for r in calls),'writing_judge':'GPT-5.1 medium; one blinded judge; shared model with baseline; scores exploratory','cost_basis':'Provider-reported token usage x frozen public standard rates; Nebius conservatively no cache discount; excludes taxes','objective_task_count':sum(t['category']!='writing' for t in tasks),'writing_task_count':sum(t['category']=='writing' for t in tasks)}
    for arm in ARMS:
        rr=[r for r in rows if r['arm']==arm];obj=[r for r in rr if r['category']!='writing'];wr=[r for r in rr if r['category']=='writing']
        times=sorted(r['latency_s'] for r in rr)
        taskvalues=[statistics.mean(float(r['passed']) for r in obj if r['task']==t['id']) for t in tasks if t['category']!='writing']
        summary['arms'][arm]={'runs':len(rr),'cost_usd':sum(r['cost_usd'] for r in rr),'cost_upper_usd':sum(r['cost_upper_usd'] for r in rr),'unknown_billed_generations':sum(r['reported_cost_usd'] is None for r in rr),'objective_passes':sum(r['passed'] for r in obj),'objective_runs':len(obj),'objective_pass_rate':statistics.mean(r['passed'] for r in obj),'objective_ci95_task_bootstrap':bootstrap(taskvalues),'writing_mean_score':statistics.mean(r['score'] for r in wr) if wr else None,'writing_full_passes':sum(r['passed'] for r in wr),'writing_runs':len(wr),'latency_median_s':statistics.median(times),'latency_p95_s':times[math.ceil(.95*len(times))-1],'by_difficulty':{d:statistics.mean(r['passed'] for r in obj if r['difficulty']==d) for d in ['easy','medium','hard']},'by_category':{c:statistics.mean(r['passed'] for r in obj if r['category']==c) for c in sorted({r['category'] for r in obj})},'truncated':sum(r['finish_reason']=='length' for r in rr)}
    lookup={(r['task'],r['trial'],r['arm']):r for r in rows}
    # Cluster trials by task, so repeated runs are not mistaken for 72 independent tasks.
    deltas=[]
    for t in tasks:
        if t['category']=='writing':continue
        deltas.append(statistics.mean(int(lookup[(t['id'],i,'routed')]['passed'])-int(lookup[(t['id'],i,'openai')]['passed']) for i in range(3)))
    a=summary['arms'];summary['routed_vs_openai']={'savings_percent':100*(1-a['routed']['cost_usd']/a['openai']['cost_usd']),'conservative_savings_percent':100*(1-a['routed']['cost_upper_usd']/a['openai']['cost_usd']),'savings_bounds_percent':[100*(1-a['routed']['cost_upper_usd']/a['openai']['cost_usd']),100*(1-a['routed']['cost_usd']/a['openai']['cost_upper_usd'])],'objective_delta_pp':100*statistics.mean(deltas),'objective_delta_ci95_pp':[100*x for x in bootstrap(deltas)],'noninferiority_margin_pp':-5,'noninferiority_supported':bootstrap(deltas)[0]>-.05}
    routed=[r for r in rows if r['arm']=='routed'];threshold=json.loads((ROOT/'results/protocol.json').read_text())['routing_policy']['confidence_threshold']
    summary['routing']={'served_models':{model:sum(r['model']==model for r in routed) for model in sorted({r['model'] for r in routed if r['model'] is not None})},'no_generation_response':sum(r['model'] is None for r in routed),'routing_cost_usd':sum(r['routing_cost_usd'] for r in routed),'low_confidence_or_error_calls':sum((r['route_confidence'] or 0)<threshold for r in routed)}
    (ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
