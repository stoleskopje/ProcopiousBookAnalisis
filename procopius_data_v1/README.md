# Procopius Frequency Analysis — Data and Code

**A whole-corpus frequency analysis of ethnonyms in Procopius of Caesarea's *History of the Wars* and the opening of the *Anecdota* (Loeb edition, ed. Dewing 1914–1940)**

This deposit accompanies the article *Counting Procopius's Peoples: Quantitative Ethnography and the Narrative Geography of the* Wars, submitted to *Greek, Roman, and Byzantine Studies*.

---

## Contents

```
data/                                  ← derived datasets, computed counts, statistics
  unified_dataset.json                 canonical merged per-book counts (English + Greek)
  part1_results.json                   raw output of run_part1.py (Wars I–VI, ~212,179 words)
  part2_results.json                   raw output of run_part2.py (Wars VI–VIII + Anecdota, ~235,287 words)
  stats.json                           per-(group, book) log-likelihood G² matrix
  validation_sample_part1.csv          100 randomly-sampled matches with ±150 char context (Part 1)
  validation_sample_part2.csv          100 randomly-sampled matches with ±150 char context (Part 2)

code/                                  ← analytical pipeline (Python 3, standard library + matplotlib)
  run_part1.py                         OCR-cleaning, paragraph classification, per-book counting for Part 1
  run_part2.py                         same, for Part 2 (different file-name range)
  unify.py                             merges part1_results.json and part2_results.json into unified_dataset.json
  analyse.py                           computes G² statistics and generates the three figures

figures/                               ← published figures (PNG + PDF)
  figure1_per_book_heatmap.{png,pdf}   per-book frequency heatmap (eighteen most-cited groups)
  figure2_narrative_geography.{png,pdf} protagonist-people line chart by book
  figure3_emergent_peoples.{png,pdf}    emergent Danubian peoples and the Avar silence
```

---

## Summary of results

The pipeline counts mentions of 46 ethnic, civic, and religious groups across 447,466 words of running English narrative in Books I–VIII of the *Wars* and the opening of the *Anecdota*, plus 270,734 words of Greek validation on the Loeb facing pages. It produces:

- **5,318 individual mentions** of 46 distinct groups, attributed to specific books via parsing of the Loeb running headers.
- **Per-(group, book) log-likelihood G² values** showing that each protagonist people is significantly over-represented (G² > 100, p < 10⁻²³) in precisely the books that narrate its war: Persians in I–II, Vandals in III–IV, Moors in IV, Goths in V–VIII, Lazi in VIII.
- **A validation pipeline** on the Greek facing pages: high-frequency groups agree with the English at Greek/English ratios of 0.86 for Romans, 1.00 for Persians, 0.96 for Lazi, 0.88 for Armenians, and 0.82 for the generic Huns.

The full analytical argument is in the paper.

---

## How to reproduce

The pipeline is deterministic and uses only Python's standard library plus `matplotlib` for plotting. You need:

- Python 3.8 or later
- `matplotlib` (any recent version)
- A copy of the Loeb Procopius edition (Dewing 1914–1940), digitised as plain-text page-files. The deposit does NOT include the corpus text itself; see "Corpus access" below.

### To re-run from scratch on your own corpus copy

1. Place your OCR'd Loeb page-files in two directories — pages 1–10 for Part 1 (Wars I–VI), and pages 11–20 for Part 2 (Wars VI–VIII + Anecdota). The files should be named in the convention `ProcopiusCombinedreduced-pages-1.pdf`, `…-2.pdf`, etc., even if the file content is plain text. (The pipeline reads them as text regardless of extension.)
2. Edit the `BASE_DIR` constant in `run_part1.py` and `run_part2.py` to point to your file locations.
3. Run `python run_part1.py` — this produces `part1_results.json` and `validation_sample_part1.csv`.
4. Run `python run_part2.py` — this produces `part2_results.json` and `validation_sample_part2.csv`.
5. Run `python unify.py` — this merges both into `unified_dataset.json`.
6. Run `python analyse.py` — this produces `stats.json` and the three figure files.

Total runtime on a 2020-era laptop: under 30 seconds end-to-end.

### To verify the deposited results without re-running

Open `data/unified_dataset.json` and `data/stats.json`. These are the canonical outputs cited in the paper. Per-book counts for any group at any book can be extracted directly. The 200 validation rows in the two CSVs can be independently graded against the original Loeb text by anyone with access to it.

---

## Corpus access

The underlying text is the Loeb Classical Library edition of Procopius:

> H. B. Dewing, trans., *Procopius*, 7 vols., Loeb Classical Library (London: Heinemann; Cambridge, Mass.: Harvard University Press, 1914–1940).

Volumes 1–6 (the *Wars* and the *Secret History*, 1914–1935) are in the public domain in the United States and many other jurisdictions, and digitised copies are freely available through the Internet Archive, Wikisource, and several university repositories. Volume 7 (*Buildings*, 1940, translated by Dewing with Glanville Downey) is not used in the present analysis.

The Greek text consulted in parallel is the Loeb facing pages, identical with:

> J. Haury and G. Wirth, edd., *Procopii Caesariensis Opera Omnia*, 4 vols. (Leipzig: Teubner, 1962–1964).

Anyone wishing to reproduce the analysis with the identical input files used here can obtain a digitised Loeb volume from the sources above and run the pipeline on its OCR output. The pipeline's normalisation steps (described in `run_part1.py`) handle typical OCR artefacts: soft hyphens, control characters, zero-width characters, and end-of-line hyphenations.

---

## Validation

The two `validation_sample_*.csv` files each contain 100 randomly-sampled positive matches from the corresponding pipeline run. Each row has five columns:

- `group` — the ethnonym category (e.g., "Persians", "Sclaveni (Slavs)")
- `form` — the specific surface form matched (e.g., "Persians", "Sclavenes")
- `book` — the book of the *Wars* (I–VIII) or "ANECDOTA"
- `context` — approximately 150 characters of surrounding text from the Loeb (sufficient for unambiguous identification, well within fair-use bounds)
- `correct` — empty in the deposit; for the reader to fill in as True / False / borderline against the original Loeb text

The `correct` column in the published version of the deposit (this one) is left empty so that any independent verifier can grade the sample themselves without bias from the author's grading.

---

## License

The dataset (`*.json`, `*.csv`), code (`*.py`), and figures (`figure*.png`, `figure*.pdf`) in this deposit are released under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license. You may share and adapt them for any purpose, including commercial, provided you give appropriate credit, link to the license, and indicate if changes were made.

The short context snippets in the validation CSVs are taken from the Dewing Loeb translation (1914–1935), which is in the public domain in the United States.

---

## AI-assistance disclosure

In accordance with current journal practice on the use of generative AI in scholarly work:

> The analytical pipeline (the Python code in `code/`) and the prose of the accompanying paper were drafted with the assistance of a generative AI assistant (Claude, Anthropic). All counts, statistical tests, and figures were generated by the deterministic Python pipeline; the AI assistant's role was code drafting, code review, and editorial discussion. The author made all methodological choices (corpus selection, surface-form lists, book-tagging strategy, statistical test selection, validation procedure), all interpretive judgements, and all decisions about what to include and what to leave out. The author is responsible for all interpretations and conclusions and has manually verified the relevant counts against the original Loeb text through the 200-row validation sample.

This disclosure also appears in §2.7 of the accompanying paper.

---

## Citation

If you use this dataset or code in your own research, please cite both the deposit and the article:

> [Author]. (2026). *Procopius Frequency Analysis: Data and Code* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

> [Author]. (forthcoming). "Counting Procopius's Peoples: Quantitative Ethnography and the Narrative Geography of the *Wars*." *Greek, Roman, and Byzantine Studies*.

A machine-readable `CITATION.cff` is included in this deposit.

---

## Contact

For questions, corrections, or collaboration enquiries, please contact the author at [email].

If you find an error in the dataset or pipeline, please open an issue at the GitHub mirror of this deposit (if available) or contact the author directly. Corrections will be incorporated into versioned updates of the Zenodo record.
