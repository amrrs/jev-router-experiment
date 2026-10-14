"""Fresh focused holdout. Uses the revised validation policy without tuning."""
import json,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo/'validation'))
import run as configured
b=configured.b
b.ROOT=Path(__file__).resolve().parent
b.LEDGER=b.ROOT/'results/calls.jsonl'
prior=[]
for directory in ['results','validation/results']:
 path=repo/directory/'calls.jsonl'
 if path.exists():prior += [json.loads(l) for l in path.read_text().splitlines()]
b.SPENT={p:sum(r['budget_charge_usd'] for r in prior+b.records() if r['provider']==p) for p in b.CAPS}
b.SCORING_DESCRIPTION='30 structured-text tasks: exact JSON field names and gold-value equality; tolerance 1e-4 for numeric values. 10 easy,10 medium,10 hard. Domain chosen from original discovery extraction results, not validation results. No writing judge. Cluster bootstrap by task,5000 resamples. Five-point exploratory margin fixed before core execution. Three repeats and four arms. Revised policy from validation reused without adaptation.'
if __name__=='__main__':b.main()
