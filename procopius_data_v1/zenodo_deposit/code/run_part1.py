"""
run_part1.py  —  Procopius frequency analysis, Part 1 (pages 1–10, Wars I–VI)
================================================================================
Paste this entire file into the OTHER project (the one that contains pages-1
through pages-10 of the Loeb Procopius corpus) and run it.

It is fully self-contained: standard library only, no external dependencies.
Output:
    /home/claude/part1_results.json          — all counts, per-book, English+Greek
    /home/claude/validation_sample_part1.csv — 100 random matches for manual check

Pipeline (identical methodology to the earlier Part 1 report, extended):
    1. Decode 10 page-files as UTF-8 (errors='replace')
    2. OCR-normalise: soft hyphens, control chars, zero-width, line-end hyphens
    3. Parse Loeb running headers ('HISTORY OF THE WARS, I. xv. 7') to tag
       each paragraph with its Book number
    4. Split paragraphs; classify each as English / Greek / Index
    5. Count English ethnonym surface-forms, overall AND per Book
    6. Count Greek ethnonym stems on the Greek paragraphs (validation)
    7. Sample 100 random matches with context for manual precision check
================================================================================
"""

import re
import json
import csv
import random
import unicodedata
from pathlib import Path
from collections import defaultdict

# ─── Configuration ─────────────────────────────────────────────────────────────
SRC_DIR  = Path('/mnt/project')
OUT_JSON = '/home/claude/part1_results.json'
OUT_CSV  = '/home/claude/validation_sample_part1.csv'
PART_NUMBER = 1
EXPECTED_FILES = 10            # pages 1–10
SEED = 20260521                # reproducible validation sample

random.seed(SEED)

# ─── 1. Locate the 10 page-files robustly ────────────────────────────────────
# Try several known naming patterns
CANDIDATE_PATTERNS = [
    'ProcopiusCombinedreduced-pages-{}.pdf',
    'ProcopiusCombinedreducedpages{}.pdf',
    'ProcopiusCombinedreduced-pages-{}.PDF',
    'pages-{}.pdf',
    'page-{}.pdf',
]

raw_parts, files_used, files_missing = [], [], []
for i in range(1, EXPECTED_FILES + 1):
    found = None
    for pat in CANDIDATE_PATTERNS:
        candidate = SRC_DIR / pat.format(i)
        if candidate.exists():
            found = candidate
            break
    if found is None:
        # last-resort glob
        matches = list(SRC_DIR.glob(f'*pages*{i}*.pdf')) + list(SRC_DIR.glob(f'*page*{i}*.pdf'))
        # filter so we don't match '11' when looking for '1'
        matches = [m for m in matches if re.search(rf'(?<!\d){i}(?!\d)', m.name)]
        if matches:
            found = matches[0]
    if found is None:
        files_missing.append(i)
        continue
    raw_parts.append(found.read_bytes().decode('utf-8', errors='replace'))
    files_used.append(found.name)

raw = '\n'.join(raw_parts)
print(f"Files found    : {len(files_used)} / {EXPECTED_FILES}")
for f in files_used: print(f"  ✓ {f}")
if files_missing:
    print(f"Files MISSING  : {files_missing}")
    print("Halting — re-name/locate files and re-run.")
    raise SystemExit(1)

print(f"Raw chars      : {len(raw):,}")

# ─── 2. OCR normalisation ─────────────────────────────────────────────────────
cleaned = raw
cleaned = cleaned.replace('\u00ad', '')         # soft hyphen
cleaned = cleaned.replace('\u0002', '')         # control char
for zw in ('\u200b', '\u200c', '\u200d'):
    cleaned = cleaned.replace(zw, '')
cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
cleaned = re.sub(r'(\w)-\n(\w)', r'\1\2', cleaned)

# ─── 3. Parse running headers for per-book tagging ─────────────────────────────
HEADER_WARS     = re.compile(r'HISTORY OF THE WARS,\s*([IVX]+)\.\s*[ivxlcdm]+', re.IGNORECASE)
HEADER_ANECDOTA = re.compile(r'\bANECDOTA\s+[ivxlcdm]+', re.IGNORECASE)

book_markers = []   # (position, book_label)
for m in HEADER_WARS.finditer(cleaned):
    book_markers.append((m.start(), m.group(1).upper()))
for m in HEADER_ANECDOTA.finditer(cleaned):
    book_markers.append((m.start(), 'ANECDOTA'))
book_markers.sort()

def book_for_position(pos):
    if not book_markers:
        return 'Unknown'
    current = book_markers[0][1]
    for mpos, blabel in book_markers:
        if mpos <= pos:
            current = blabel
        else:
            break
    return current

books_seen = sorted({b for _, b in book_markers})
print(f"Book markers   : {len(book_markers)} (books: {books_seen})")

# ─── 4. Paragraph splitting + classification ─────────────────────────────────
GREEK_RANGES = [(0x0370, 0x03FF), (0x1F00, 0x1FFF)]
def greek_share(p):
    letters = [c for c in p if c.isalpha()]
    if not letters: return 0.0
    g = sum(1 for c in letters
            if any(lo <= ord(c) <= hi for lo, hi in GREEK_RANGES))
    return g / len(letters)

REF_RE = re.compile(r'\b[IVXLCDM]+\.\s*[ivxlcdm]+\.\s*\d+\b')
def idx_share(p):
    toks = p.split()
    return len(REF_RE.findall(p)) / max(len(toks), 1)

para_records, cursor = [], 0
for para in re.split(r'\n\s*\n', cleaned):
    pos = cleaned.find(para, cursor)
    if pos < 0: pos = cursor
    cursor = pos + len(para)
    gs = greek_share(para); ix = idx_share(para)
    if gs > 0.05: cls = 'greek'
    elif ix > 0.03: cls = 'index'
    else: cls = 'english'
    para_records.append({'text': para, 'pos': pos,
                         'book': book_for_position(pos), 'class': cls})

eng_paras   = [p for p in para_records if p['class'] == 'english']
greek_paras = [p for p in para_records if p['class'] == 'greek']
idx_paras   = [p for p in para_records if p['class'] == 'index']
print(f"Paragraphs     : {len(para_records)} (eng={len(eng_paras)}, greek={len(greek_paras)}, index={len(idx_paras)})")

# ─── 5. English ethnonym counting (overall + per book) ──────────────────────
GROUPS_EN = {
    "Romans":                            ["Roman", "Romans"],
    "Persians":                          ["Persian", "Persians", "Medes", "Median"],
    "Goths (Ostrogoths)":                ["Goth", "Goths", "Gothic"],
    "Vandals":                           ["Vandal", "Vandals"],
    "Moors (Mauri)":                     ["Moor", "Moors", "Moorish"],
    "Huns (generic)":                    ["Hun", "Huns", "Hunnic"],
    "Armenians":                         ["Armenian", "Armenians"],
    "Lazi":                              ["Lazi"],
    "Christians":                        ["Christian", "Christians"],
    "Libyans":                           ["Libyan", "Libyans"],
    "Saracens (Arabs)":                  ["Saracen", "Saracens"],
    "Massagetae":                        ["Massagetae", "Massagete"],
    "Visigoths":                         ["Visigoths"],
    "Eruli (Heruli)":                    ["Eruli", "Erulian", "Heruli"],
    "Germans (= Franks per Procopius)":  ["Germans"],
    "Ephthalitae (White Huns)":          ["Ephthalitae"],
    "Franks":                            ["Franks", "Germani"],
    "Neapolitans":                       ["Neapolitans"],
    "Greeks (Hellenes)":                 ["Greek", "Greeks"],
    "Isaurians":                         ["Isaurian", "Isaurians"],
    "Italians":                          ["Italians"],
    "Homeritae (Himyarites)":            ["Homeritae", "Homerite"],
    "Iberians (Caucasian)":              ["Iberian", "Iberians"],
    "Jews / Hebrews":                    ["Jew", "Jews", "Hebrew", "Hebrews"],
    "Aethiopians":                       ["Aethiopian", "Aethiopians"],
    "Carthaginians":                     ["Carthaginians"],
    "Arians":                            ["Arian", "Arians"],
    "Alani (Alans)":                     ["Alani"],
    "Burgundians":                       ["Burgundians"],
    "Colchians":                         ["Colchian", "Colchians"],
    "Persarmenians":                     ["Persarmenian", "Persarmenians"],
    "Arborychi (Armorici)":              ["Arborychi", "Armorici"],
    "Tzani":                             ["Tzani"],
    "Beroeans":                          ["Beroeans"],
    "Taurians":                          ["Taurians"],
    "Blemyes":                           ["Blemyes"],
    "Thuringians":                       ["Thuringian", "Thuringians"],
    "Nobatae":                           ["Nobatae"],
    "Suevi (Suebi)":                     ["Suevi"],
    "Sabiri":                            ["Sabiri"],
    "Alamani (Alemanni)":                ["Alamani"],
    "Antae":                             ["Antae"],
    "Sclaveni (Slavs)":                  ["Sclaveni"],
    # Groups we expect to be absent here — verify
    "Avars":                             ["Avar", "Avars"],
    "Lombards (Longobardi)":             ["Lombard", "Lombards", "Longobardi"],
    "Samaritans":                        ["Samaritan", "Samaritans"],
    "Gepaedes (Gepids)":                 ["Gepaedes", "Gepid", "Gepids"],
}

def count_in(text, forms):
    detail, total = {}, 0
    for f in forms:
        n = len(re.findall(r'\b' + re.escape(f) + r'\b', text))
        if n > 0:
            detail[f] = n; total += n
    return total, detail

corpus_overall = '\n\n'.join(p['text'] for p in eng_paras)
by_book = defaultdict(list)
for p in eng_paras:
    by_book[p['book']].append(p['text'])
corpora_by_book = {b: '\n\n'.join(ps) for b, ps in by_book.items()}

en_counts_overall, en_forms_overall = {}, {}
for g, forms in GROUPS_EN.items():
    total, detail = count_in(corpus_overall, forms)
    en_counts_overall[g] = total
    en_forms_overall[g]  = detail

en_counts_per_book = {b: {} for b in corpora_by_book}
for b, text in corpora_by_book.items():
    for g, forms in GROUPS_EN.items():
        total, _ = count_in(text, forms)
        en_counts_per_book[b][g] = total

word_count_overall   = len(re.findall(r'\b\w+\b', corpus_overall))
words_per_book       = {b: len(re.findall(r'\b\w+\b', t)) for b, t in corpora_by_book.items()}

print(f"English words  : {word_count_overall:,}")
print(f"Per-book words : {words_per_book}")

# ─── 6. Greek pipeline (validation) ───────────────────────────────────────────
def normalize_greek(text):
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower()

# Stems are in *post-normalisation* form (no breathings, no accents, lowercase)
GROUPS_GR = {
    "Romans":                  [r"\bρωμαι\w*"],
    "Persians":                [r"\bπερσ\w*", r"\bμηδ\w*"],
    "Goths (Ostrogoths)":      [r"\bγοτθ\w*"],
    "Vandals":                 [r"\bβανδιλ\w*", r"\bβανδηλ\w*"],
    "Moors (Mauri)":           [r"\bμαυρουσ\w*"],
    "Huns (generic)":          [r"\bουνν\w*"],
    "Armenians":               [r"\bαρμενι\w*"],
    "Lazi":                    [r"\bλαζ(?:ο|ω|οι|ων|ους|οις)\w*"],
    "Christians":              [r"\bχριστιαν\w*"],
    "Saracens (Arabs)":        [r"\bσαρακην\w*"],
    "Massagetae":              [r"\bμασσαγετ\w*"],
    "Eruli (Heruli)":          [r"\bερουλ\w*"],
    "Franks":                  [r"\bφραγγ\w*", r"\bγερμαν\w*"],
    "Ephthalitae (White Huns)":[r"\bεφθαλιτ\w*"],
    "Sclaveni (Slavs)":        [r"\bσκλαβην\w*"],
    "Antae":                   [r"\bαντ(?:αι|ων|αις|ας)\b"],
    "Avars":                   [r"\bαβαρ(?:ος|οι|ων|οις|ους|ε)\b"],
    "Lombards (Longobardi)":   [r"\bλογγιβαρδ\w*", r"\bλογγοβαρδ\w*"],
    "Samaritans":              [r"\bσαμαρ(?:ειτ|ιτ)\w*"],
    "Gepaedes (Gepids)":       [r"\bγηπαιδ\w*", r"\bγεπιδ\w*"],
    "Isaurians":               [r"\bισαυρ\w*"],
    "Iberians (Caucasian)":    [r"\bιβηρ\w*"],
    "Greeks (Hellenes)":       [r"\bελλην\w*"],
    "Aethiopians":             [r"\bαιθιοπ\w*"],
    "Libyans":                 [r"\bλιβυ\w*"],
    "Visigoths":               [r"\bουισιγοτθ\w*", r"\bβισιγοτθ\w*"],
}

gr_corpus_norm = normalize_greek('\n\n'.join(p['text'] for p in greek_paras))
gr_corpus_words = len(re.findall(r'\w+', gr_corpus_norm))

gr_counts_overall = {}
for g, patterns in GROUPS_GR.items():
    total = sum(len(re.findall(p, gr_corpus_norm)) for p in patterns)
    gr_counts_overall[g] = total

# Per-book Greek (using nearest English running header for each Greek paragraph)
gr_by_book = defaultdict(list)
for p in greek_paras:
    gr_by_book[p['book']].append(p['text'])
gr_corpora_by_book = {b: normalize_greek('\n\n'.join(ps)) for b, ps in gr_by_book.items()}

gr_counts_per_book = {b: {} for b in gr_corpora_by_book}
for b, text in gr_corpora_by_book.items():
    for g, patterns in GROUPS_GR.items():
        gr_counts_per_book[b][g] = sum(len(re.findall(p, text)) for p in patterns)

print(f"Greek words    : {gr_corpus_words:,}")

# ─── 7. Validation sample (100 random English hits with context + book) ────
all_hits = []
for g, forms in GROUPS_EN.items():
    for f in forms:
        for m in re.finditer(r'\b' + re.escape(f) + r'\b', corpus_overall):
            all_hits.append({'group': g, 'form': f, 'pos': m.start()})

# Map cleaned-corpus positions back to original-text positions (approximate)
random.shuffle(all_hits)
sample = all_hits[:100]
for h in sample:
    p = h['pos']
    ctx = corpus_overall[max(0, p-80) : p+100].replace('\n', ' ').strip()
    # Find the paragraph for the book tag
    for para in eng_paras:
        # crude: search for context start in para
        if h['form'] in para['text']:
            h['book'] = para['book']
            break
    else:
        h['book'] = 'Unknown'
    h['context'] = ctx
    h['correct'] = ''   # to be filled by human

with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['group','form','book','context','correct'])
    w.writeheader()
    for h in sample:
        w.writerow({k: h.get(k, '') for k in ['group','form','book','context','correct']})

# ─── 8. Save JSON ─────────────────────────────────────────────────────────────
out = {
    'part': PART_NUMBER,
    'metadata': {
        'files_used': files_used,
        'files_missing': files_missing,
        'word_count_english': word_count_overall,
        'word_count_greek_norm': gr_corpus_words,
        'words_per_book_english': words_per_book,
        'paragraphs_total': len(para_records),
        'paragraphs_english': len(eng_paras),
        'paragraphs_greek': len(greek_paras),
        'paragraphs_index': len(idx_paras),
        'books_detected': books_seen,
        'seed': SEED,
    },
    'counts_overall_english': en_counts_overall,
    'counts_per_book_english': en_counts_per_book,
    'form_breakdown_english': en_forms_overall,
    'counts_overall_greek_normalised': gr_counts_overall,
    'counts_per_book_greek_normalised': gr_counts_per_book,
    'group_definitions_english': GROUPS_EN,
    'group_patterns_greek_normalised': {g: pats for g, pats in GROUPS_GR.items()},
}
Path(OUT_JSON).write_text(json.dumps(out, indent=2, ensure_ascii=False))
print(f"\n✓ Wrote {OUT_JSON}")
print(f"✓ Wrote {OUT_CSV}  (100-row validation sample)")
print(f"\nTOP 10 ENGLISH COUNTS (Part 1):")
for g, n in sorted(en_counts_overall.items(), key=lambda kv:-kv[1])[:10]:
    print(f"  {g:<35s} {n:>5}")
print(f"\nTOP 10 GREEK COUNTS (validation, normalised):")
for g, n in sorted(gr_counts_overall.items(), key=lambda kv:-kv[1])[:10]:
    print(f"  {g:<35s} {n:>5}")
