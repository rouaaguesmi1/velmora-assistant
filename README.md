# Velmora : Help-Center Assistant & Evaluation Harness

An extractive question-answering system built over 30 help-center articles, with a reproducible evaluation harness for measuring retrieval quality, answer correctness, and abstention behaviour.

**Constraints:** Python 3 standard library only. No external dependencies, API keys, accounts, network access, or randomness.

## 1. Getting Started

### Run the evaluation

```bash
python -m evaluation.run_eval
```

Prints the evaluation summary and generates the output files in `results/`.

### Run the tests

```bash
python -m unittest discover -s tests -t .
```

**Test suite:** 22 tests.

### Configuration

```bash
python -m evaluation.run_eval --threshold 0.30
```

Available options:

| Argument | Description |
|---|---|
| `--threshold` | Abstention coverage threshold |
| `--kb` | Knowledge-base directory |
| `--eval` | Evaluation dataset |
| `--out` | Output directory |
| `--review` | Manual-review file |

The evaluation pipeline is deterministic. Two consecutive runs produce byte-identical output files.

The provided files in `data/kb/` and `data/eval.jsonl` remain unmodified.

## 2. Architecture

The assistant follows a simple extractive pipeline:

**BM25 retrieval → Abstention check → Sentence selection → Citation → Evaluation**

| Component | Implementation | Rationale |
|---|---|---|
| Retrieval | BM25 over article titles (2× weight) and body text, with lightweight suffix stemming and stop-word filtering. | Efficient lexical retrieval without external dependencies. |
| Abstention | Refuses when the top article covers less than 30% of the question's IDF weight. | Normalizes retrieval evidence across questions of different lengths. |
| Answer generation | Extracts the two best-matching sentences from the top article. | Keeps answers grounded in the source material rather than generating new claims. |
| Citations | Includes article ID and last-updated date. | Makes answers traceable to the knowledge base. |
| Contradiction handling | Detects conflicting numerical values for the same unit within the same category. Displays both answers, newest first, with dates. | Avoids silently treating the newest article as authoritative when exceptions may exist. |
| Evaluation | Deterministic keyword-based judge using `answer_keywords` from the evaluation dataset. | Provides a lightweight, reproducible correctness check. |

### Abstention strategy

Raw BM25 scores are influenced by question length. Instead, the assistant measures the proportion of the question's IDF weight covered by the top article.

A threshold of `0.30` was selected from the evaluation results.

Words absent from the knowledge base contribute to the question's information weight but cannot be matched, reducing coverage and increasing the likelihood of abstention.

### Contradiction handling

When articles within the same category contain different figures for the same unit, the assistant:

1. Identifies the conflicting values.
2. Retrieves the corresponding sentences.
3. Displays both answers, newest first.
4. Includes the dates and article citations.
5. Explicitly indicates that the help center contains inconsistent information.

The publication date determines display order, not correctness. This distinction matters for exceptions such as Q04.

Detection is intentionally limited to numerical contradictions. See [NOTE.md](NOTE.md) for details.

## 3. Evaluation Results

**Dataset:** 40 questions (35 answerable, 5 unanswerable).

**Default threshold:** `0.30`

| Metric | Result |
|---|---:|
| Recall@1 | 80.0% |
| Recall@3 | 88.6% |
| Recall@5 | 91.4% |
| Correct answers | 28/35 (80.0%) |
| Confident incorrect answers | 1/35 |
| Incorrect abstentions | 6/35 |
| Correctly refused unanswerable questions | 5/5 |

Recall@k measures whether at least one relevant source article appears in the top k retrieved articles.

### Threshold cross-validation

Five-fold cross-validation was also performed to examine threshold stability.

| Metric | Result |
|---|---:|
| Correct answers | 27/35 |
| Confident incorrect answers | 1 |
| Incorrect abstentions | 7 |
| Correctly refused unanswerable questions | 5/5 |

Thresholds between `0.30` and `0.55` produced identical results on the full evaluation set. The default remains `0.30`, the lowest threshold on that plateau.

Cross-validation evaluates threshold stability only; it does not eliminate the effects of tuning other system components on the same dataset.

## 4. Additional Evaluation

Beyond the core requirements, several optional checks were implemented.

- **Threshold analysis:** Compares different abstention thresholds to understand the accuracy–coverage trade-off.
- **Contradiction detection:** Identifies conflicting numerical information across articles.
- **Judge validation:** Compares the automated keyword judge against a manual review.
- **Cross-validation:** Examines the stability of threshold selection across five folds.
- **Retrieval experiments:** Tests alternative sentence-based reranking. The experiment reduced correct answers from 27 to 24, so it was discarded.

### Judge validation

A manual review of 29 answered questions was conducted using `data/manual_review.csv`.

- Agreement between automated judge and manual review: 29/29.
- Answers considered correct after review: 28/29.
- Incorrect answer identified: Q08.

This agreement is not independent validation: the manual review used the same answer keywords as a reference, which introduces some evaluation bias.

## 5. Limitations and Known Issues

### Evaluation bias

All 40 questions influenced development decisions, including threshold selection, sentence weighting, and contradiction-detection rules.

Consequently, reported results should not be interpreted as independent estimates of generalisation performance.

### Abstention limitations

All five unanswerable questions were correctly refused, but this is a small sample.

Their coverage scores overlap with those of answerable questions that were incorrectly refused. A larger and independently collected evaluation set is needed to establish a reliable threshold.

### Incorrect source selection

Extractive answering prevents the system from generating unsupported text, but it does not guarantee that the retrieved sentences are relevant.

Q08 demonstrates this limitation: the assistant confidently extracts information from the wrong article.

### Contradiction detection

The current implementation detects only numerical conflicts involving the same unit and category.

It cannot reliably identify:
- Contradictions expressed in words.
- Exceptions that require contextual interpretation.
- Conflicts involving different units or categories.

The newest-first ordering can also place an exception before the general policy.

### Keyword judge

The keyword-based judge is deterministic but cannot fully evaluate semantic correctness.

For example, an answer may contain all required keywords while omitting important context or exceptions.

## 6. Next Steps

Given another development day, I would prioritise:

1. **Independent evaluation:** Introduce questions written by someone else, including more unanswerable and unusually phrased questions.
2. **Human validation:** Have two reviewers independently assess the automated judge.
3. **Answer verification:** Check whether selected sentences actually answer the question, rather than relying exclusively on retrieval scores.
4. **Retrieval comparison:** Evaluate embedding-based retrieval against BM25, particularly for vocabulary gaps.
5. **Knowledge-base quality:** Resolve known inconsistencies, including KB-07, and explicitly mark exceptional policies such as the sale terms.

## 7. Manual Review

The evaluation generates `results/review_template.csv`, containing:

- Question ID.
- Generated answer.
- Automated judge verdict.
- Empty `human_correct` field.

To perform a review:

1. Open `results/review_template.csv`.
2. Fill `human_correct` with `y` or `n`, indicating whether the answer is correct and useful to a customer.
3. Save the completed file as `data/manual_review.csv`.
4. Run the evaluation again.

The harness reports agreement between the automated judge and human review, along with the proportion of answers considered correct.

## 8. Project Structure

```text
velmora/
├── velmora/
│   ├── text.py
│   ├── kb.py
│   ├── bm25.py
│   └── assistant.py
│
├── evaluation/
│   ├── metrics.py
│   └── run_eval.py
│
├── tests/
│   ├── test_metrics.py
│   └── test_assistant.py
│
├── data/
│   ├── kb/
│   ├── eval.jsonl
│   └── manual_review.csv
│
├── results/
│   ├── results.jsonl
│   ├── review_template.csv
│   └── summary_stdout.txt
│
├── FAILURES.md
├── NOTE.md
└── README.md
```

## 9. Design Principles

The implementation prioritises:

- **Grounded answers:** Every response is extracted from the provided knowledge base.
- **Controlled abstention:** The assistant can refuse when retrieval evidence is insufficient.
- **Traceability:** Answers include source article identifiers and update dates.
- **Transparency:** Numerical conflicts are surfaced rather than silently resolved.
- **Reproducibility:** No randomness, external services, or runtime dependencies.
- **Measurability:** Retrieval, correctness, abstention, and evaluation limitations are explicitly reported.

The objective is not to maximise the number of answered questions. It is to provide useful answers while making uncertainty, source conflicts, and evaluation weaknesses measurable.
