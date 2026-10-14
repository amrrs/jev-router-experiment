"""Separate diagnostic pilot after first benchmark; never counted as holdout."""
import concurrent.futures,json
import benchmark as b
b.RATES.update(flash=(.14,.28),strong=(.95,4))
PILOT_MODELS={'flash':'deepseek-ai/DeepSeek-V4-Flash-0731','strong':'moonshotai/Kimi-K2.6'}
CASES=[
 ('P1','A $120 item is discounted 25% and then taxed 8%. Return JSON {"total":number}.',{'total':97.2}),
 ('P2','Flip a fair coin until three consecutive heads occur. Return JSON {"expected_flips":number}.',{'expected_flips':14}),
 ('P3','Tasks A=2, B=3, C=5, D=1 hours. C depends on A, D depends on B and C. Two workers. Return JSON {"makespan":number} for minimum duration.',{'makespan':8}),
 ('P4','A: group1 18/20 successes, group2 4/10. B: group1 8/10, group2 14/20. Return JSON {"better_group1":"A or B","better_group2":"A or B","better_overall":"A or B"}.',{'better_group1':'A','better_group2':'B','better_overall':'tie'}),
]
def gen(case,label):
 id,prompt,gold=case
 r=b.call('nebius',{'model':PILOT_MODELS[label],'messages':[{'role':'system','content':b.SYSTEM},{'role':'user','content':prompt}],'max_tokens':6000,'temperature':0},label,{'kind':'calibration','task':id,'label':label,'gold':gold})
 print(id,label,r['status'],b.text(r),r.get('error_body'),flush=True)
def route(case):
 id,prompt,gold=case
 questions={'multistep':{'type':'noul','instructions':'Does solving this request require combining multiple dependent reasoning steps, rather than straightforward extraction or rewriting?'},'algorithmic':{'type':'noul','instructions':'Does this request require mathematical probability, combinatorial optimization, or designing a nontrivial algorithm?'},'route':{'type':'choice','instructions':'Which generation model tier is sufficient to solve this request correctly? Prefer cheap only for direct extraction or simple rewriting. Choose strong for mathematical reasoning or constraint optimization.','criteria':{'cheap':'Direct extraction, simple rewriting, or single-step calculation.','strong':'Probability, multi-step arithmetic, optimization, difficult algorithms or subtle contradictions.'}}}
 r=b.call('jev',{'model':'jev-1.13.0','state':{'request':prompt},'questions':questions},'jev',{'kind':'calibration_route','task':id})
 print(id,'Jev',r['status'],r.get('response',{}).get('answers'),flush=True)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
  fs=[ex.submit(gen,c,l) for c in CASES for l in PILOT_MODELS]+[ex.submit(route,c) for c in CASES]
  for f in concurrent.futures.as_completed(fs):f.result()
