import json,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo/'validation'))
import run as configured
b=configured.b
b.ROOT=Path(__file__).resolve().parent
b.LEDGER=b.ROOT/'results/calls.jsonl'
prior=[]
for directory in ['results','validation/results','core/results']:
 path=repo/directory/'calls.jsonl'
 if path.exists():prior += [json.loads(l) for l in path.read_text().splitlines()]
b.SPENT={p:sum(r['budget_charge_usd'] for r in prior+b.records() if r['provider']==p) for p in b.CAPS}
b.SCORING_DESCRIPTION='Final fresh confirmation set:30 source-grounded structured-text tasks,10 extraction,10 source_lookup,10 policy;10 easy,10 medium,10 hard. Exact JSON field names and gold-value equality; numeric tolerance1e-4. No subjective judge or semantic normalization. All30tasks retained. Three repeats,four arms. Cluster bootstrap by task,5000samples. Five-point exploratory quality margin fixed before calls. Reuse revised router and generator models from validation with no retuning. Workload narrowed after core exploration showed label-description ambiguity in classification; classification excluded from this final workload. Development results remain published.'
if __name__=='__main__':b.main()
