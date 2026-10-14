# Jev + Nebius router experiment

Compare GPT-5.1 medium with open models hosted by Nebius, directly and through Jev routing. This repository contains experiment code, synthetic tasks, recorded protocols, scored results, and charts.

![Jev chooses between DeepSeek V4 Flash and Kimi K2.6](assets/jev-nebius-routing.png)

Jev makes typed routing decisions. The selected Nebius-hosted model generates the answer. Routed measurements include both stages' cost and latency.

## Recorded results

The completed structured-text experiment contains 30 prompts, three attempts per prompt, and four arms. These full results include classification, extraction, source lookup, and policy tasks.

| System | Success / 90 attempts | Estimated token cost |
| --- | --- | --- |
| GPT-5.1 medium | 87/90 (96.7%) | $0.06518–$0.13123 |
| Fixed DeepSeek V4 Flash 0731 | 84/90 (93.3%) | $0.00387–$0.00621 |
| Fixed Kimi K2.6 | 90/90 (100%) | $0.08916 |
| Jev → Nebius open models | 83/90 (92.2%) | $0.01175–$0.01433 |

Conservative estimated savings against GPT-5.1: **78.0%**. The success gap was −4.4 percentage points, with a task-cluster bootstrap interval of [−10.0, 0.0]. This does **not** establish noninferiority under the exploratory five-point margin.

A post-hoc subset removing the entire classification category contains 21 extraction, source-lookup, and policy tasks:

| System | Success / 63 attempts | Estimated token cost |
| --- | --- | --- |
| GPT-5.1 medium | 63/63 (100%) | $0.04752 |
| Fixed DeepSeek V4 Flash 0731 | 63/63 (100%) | $0.00263 |
| Fixed Kimi K2.6 | 63/63 (100%) | $0.06598 |
| Jev → Nebius open models | 62/63 (98.4%) | $0.00982–$0.01239 |

The selected cohort shows **73.9% conservative estimated savings**, but is exploratory, not a fresh holdout. Its routed failure was a timeout. Fixed Flash was cheaper and passed all attempts here, so these results do not demonstrate an incremental benefit from Jev over a fixed cheap model.

Ranges include maximum reserved charges for unknown-billed timeouts. These are public-rate token estimates, not reconciled invoices or total business costs. Rates and versions were recorded on **14 October 2026**. See [pricing sources](research/pricing-sources.json), [full summary](core/results/summary.json), and [focused-cohort calculations](results/focused-cohort.json).

## Routing policy

Jev sees only the incoming prompt and model descriptions—not difficulty labels, answer keys, grading checks, or generated answers. It answers three questions:

1. Does the request require multiple dependent reasoning steps?
2. Does it require probability, combinatorial optimization, or a nontrivial algorithm?
3. Which generator tier is sufficient?

The revised policy selects Kimi when the algorithmic signal is at least 0.75, the multistep signal is at least 0.90, Jev selects the stronger tier, confidence is below 0.50, or routing fails. Otherwise it selects Flash. These thresholds are application policy, not correctness guarantees. See [validation/run.py](validation/run.py) and the [recorded core protocol](core/results/protocol.json).

## Repository layout

| Path | Contents |
| --- | --- |
| `benchmark.py` | HTTP harness, credential loading, budgets, routing, generation, and writing evaluation |
| `build_tasks.py`, `tasks.json` | Original broad Qwen discovery workload |
| `validation/` | Fresh broad workload using the revised model portfolio and routing policy |
| `core/` | Completed 30-task structured-text exploration |
| `confirmation/` | Fresh follow-up tasks and code; execution was interrupted and is incomplete |
| `grade.py` | Objective grading, restricted Python evaluation, writing scores, task-cluster bootstrap |
| `pilot.py` | Diagnostic calibration, not held-out quality evidence |
| `make_figures.py` | Offline chart generation |
| `results/`, `*/results/` | Protocols, scored CSV/JSON, and summaries |
| `figures/`, `assets/` | Charts and the supplied routing illustration |

Three experiments completed. Incomplete confirmation results are not used for outcome claims. Blog drafts, publishing code, raw provider payloads, browser previews, local budget state, and credential files are excluded.

## Setup

Use Python 3.9 or newer on macOS or Linux. The HTTP harness uses the standard library. Only chart generation needs matplotlib:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Set `OPENAI_API_KEY`, `NEBIUS_API_KEY`, and `JEV_API_KEY` in your shell environment. No keys are included. The original local workflow also supports `~/openai.env`, `~/jev.env`, and `~/Documents/nebius.env`. Environment variables take precedence.

## Running experiments

**The smoke, run, and judge commands send paid API requests.** Offline grading and figure generation do not.

Original discovery:

```sh
python3 benchmark.py smoke
python3 benchmark.py run
python3 benchmark.py judge
python3 grade.py
```

Revised broad validation:

```sh
python3 validation/run.py run
python3 validation/run.py judge
python3 validation/grade.py
```

Structured-text exploration:

```sh
python3 core/run.py run
python3 core/grade.py
```

Task-generation scripts reproduce the checked-in JSON datasets. Protocols check prompt hashes and routing policies before resuming. Calls use a recorded shuffle seed and four HTTP workers. Failed generations remain in the denominator and are not automatically retried.

Raw `calls.jsonl` files are generated locally and ignored by Git. A fresh clone has published scored results but no resumable raw-call ledger; running a benchmark starts new calls. Offline regrading requires a locally generated ledger. Archive any existing protocol, ledger, and scored results together before independent reruns.

Harness caps are $10 OpenAI, $2 Nebius, and $0.10 Jev. Cross-process reservations currently preserve $1 of OpenAI headroom. Unknown-billed failures retain their maximum reservation. Limits cover this harness, not unrelated account activity or taxes.

Generate full structured-text charts offline:

```sh
.venv/bin/python make_figures.py
```

## Method and limitations

- Structured-text success requires valid JSON, exact fields, matching reference values, and numeric tolerance 0.0001. Timeouts count as failures.
- Original discovery prompts did not always specify exact JSON fields/types. `semantic_object` records symmetric normalization for those discovery results. Later workloads use strict grading.
- Writing scores are separate from objective success. They use a blinded GPT-5.1 evaluator and executable word counting. Incomplete evaluator outputs were retained and rerun with a larger output budget; these costs remain included.
- Python code is checked against finite cases using restricted builtins, AST checks, CPU/wall-time limits, an isolated directory, and no credential environment. This is not a general-purpose security sandbox; macOS rejected memory resource limits.
- One diagnostic pilot prompt had inconsistent tie labels and supports no quality claim.
- Difficulty labels are author judgments. Bootstrap samples cluster all repeats by task. Three attempts do not create three independent task types.
- Generation messages are identical across arms, but sampling and reasoning behavior differ. This is a practical system comparison, not an equal-compute study.
- Synthetic workloads are small and do not establish production reliability, broad model equivalence, or total business savings.

## API references

- [Jev API](https://docs.typesafe.ai/api)
- [Jev models and pricing](https://docs.typesafe.ai/models)
- [Nebius Token Factory](https://docs.tokenfactory.nebius.com/quickstart)
- [GPT-5.1](https://developers.openai.com/api/docs/models/gpt-5.1)
- [OpenAI pricing](https://developers.openai.com/api/docs/pricing)
