# Triage key-gated aspect-extraction eval

model: google/gemini-2.5-flash
base labels (3): ['billing charge', 'checkout crash', 'slow sync']
base canonical anchors: ['bill', 'charge', 'checkout', 'crash', 'slow', 'sync']

| metric | value | bound | pass |
|---|---|---|---|
| planted-aspect recall | 1.00 | >= 0.7 | PASS |
| paraphrase jaccard (min) | 0.86 | >= 0.6 | PASS |

contract: contracts/aspect-extraction-stability.yaml (threshold 0.6)
