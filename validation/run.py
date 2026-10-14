"""Validation runner: revised policy fixed before fresh tasks are executed."""
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import benchmark as b
b.ROOT=Path(__file__).resolve().parent
b.LEDGER=b.ROOT/'results/calls.jsonl'
b.MODELS={'openai':'gpt-5.1-2025-11-13','small':'deepseek-ai/DeepSeek-V4-Flash-0731','large':'moonshotai/Kimi-K2.6'}
b.RATES={'openai':(1.25,10),'small':(.14,.28),'large':(.95,4),'jev':(.042,0)}
b.GENERATION_CONFIG={'openai':{'reasoning_effort':'medium','max_completion_tokens':6000,'service_tier':'default'},'nebius':{'temperature':0,'max_tokens':6000}}
b.QUALITY_MARGIN_PP=-5
b.SCORING_DESCRIPTION='24 objective tasks: exact JSON fields and gold-value equality; numeric tolerance 1e-4. Code: all supplied tests pass and interval insertion input remains unmodified. Six writing tasks: blinded GPT-5.1 medium rubric checks plus executable word limits. Cluster bootstrap by task with 5000 resamples. Five-point exploratory noninferiority margin fixed before validation calls.'
# Aggregate original experiment, calibration, and validation spending.
original_path=b.ROOT.parent/'results/calls.jsonl'
original=[json.loads(l) for l in original_path.read_text().splitlines()] if original_path.exists() else []
b.SPENT={p:sum(r['budget_charge_usd'] for r in original+b.records() if r['provider']==p) for p in b.CAPS}
b.POLICY={'model':'jev-1.13.0','routing_rule':'large if algorithmic>=0.75 OR multistep>=0.90 OR route choice strong OR route confidence<0.50; else small','confidence_threshold':.50,'fallback':'large','questions':{'multistep':{'type':'noul','instructions':'Does solving this request require combining multiple dependent reasoning steps, rather than straightforward extraction or rewriting?'},'algorithmic':{'type':'noul','instructions':'Does this request require mathematical probability, combinatorial optimization, or designing a nontrivial algorithm?'},'route':{'type':'choice','instructions':'Which generation model tier is sufficient to solve this request correctly? Prefer cheap for direct extraction, routine calculations, or simple writing. Choose strong for probability, constraint optimization, nontrivial algorithms or subtle conflicting evidence.','criteria':{'cheap':'DeepSeek V4 Flash 0731, inexpensive capable open reasoning model ($0.14/$0.28 per million input/output). Sufficient for routine tasks.','strong':'Kimi K2.6, larger open reasoning model ($0.95/$4 per million input/output). Prefer for demanding reasoning, complex algorithms and subtle evidence.'}}}}
def route(task,trial):
 r=b.call('jev',{'model':b.POLICY['model'],'state':{'request':task['prompt']},'questions':b.POLICY['questions']},'jev',{'kind':'routing','task':task['id'],'trial':trial,'arm':'routed'})
 a=r.get('response',{}).get('answers',{});c=a.get('route',{})
 if r['status']!='ok' or c.get('choice') not in ['cheap','strong']:return 'large','routing_error'
 if a.get('algorithmic',{}).get('noul',0)>=.75 or a.get('multistep',{}).get('noul',0)>=.90:return 'large','complexity_gate'
 if c.get('confidence',0)<.50:return 'large','low_confidence'
 return ('large' if c['choice']=='strong' else 'small'),'choice'
b.route=route
def generation(task,trial,arm,label):
 body={'model':b.MODELS[label],'messages':[{'role':'system','content':b.SYSTEM},{'role':'user','content':task['prompt']}]}
 if label=='openai':body.update(reasoning_effort='medium',max_completion_tokens=6000,service_tier='default',store=False)
 else:body.update(temperature=0,max_tokens=6000)
 return b.call('openai' if label=='openai' else 'nebius',body,label,{'kind':'generation','task':task['id'],'trial':trial,'arm':arm})
b.generation=generation
if __name__=='__main__':b.main()
