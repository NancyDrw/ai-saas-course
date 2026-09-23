# AI Prompt Optimization Notes

## What changed

Lesson 9 sent every credit operation to Gemini, including date, type, amount and
category. The lesson 10 prompt is now isolated in `app/prompts.py` and sends a
compact ledger summary instead:

- count of operations;
- total credits added, spent and remaining;
- exact expense totals grouped by category.

The model still receives every fact it needs for an analysis, but no longer sees
repeated dates or individual operations. The backend continues to reject an AI
response if it names an unknown expense category or returns an amount that does
not equal the ledger total for that category.

## Prompt contract

The prompt defines the model role, task, Ukrainian response language, available
facts and output fields: `summary`, `top_expense_categories`, `risks`, and
`advice`.

It explicitly forbids inventing sums, categories, dates or facts. When there
are too few data points, the model must state that in `summary` and leave
unsupported lists empty.

## Token estimate

Token counts were measured with `tiktoken` and `cl100k_base`. Gemini has a
different tokenizer, so these are comparative estimates rather than Gemini
billing figures.

| Scenario | Lesson 9 prompt | Optimized prompt | Reduction |
| --- | ---: | ---: | ---: |
| Typical ledger: 3 operations | 473 | 334 | 139 (29.4%) |
| Larger ledger: 30 operations | 1175 | 349 | 826 (70.3%) |

Run the comparison again with:

```bash
python -m app.check_prompt_tokens
```

## Tested scenarios

- A regular ledger with one credit addition and repeated `AI-сесія` expenses:
  the prompt contains correct totals and the aggregated category amount.
- An empty ledger: the prompt says that there are zero operations and no
  expenses, without adding unsupported facts.

Run the focused checks with:

```bash
python -m unittest app.test_prompts
```
