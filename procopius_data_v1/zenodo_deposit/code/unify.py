"""
Unify part1_results.json + part2_results.json into a single canonical dataset
for the Histos paper.

Strategy:
  * Per-book counts are SUMMED (Books I-V come from Part 1 only, VII-VIII +
    Anecdota come from Part 2 only, Book VI is summed across both parts since
    they cover different chapters of VI).
  * Greek counts are kept separate alongside English as a validation column.
  * Stray ANECDOTA-tagged content in Part 1 (~2,220 words) is investigated.
  * The Greek-stem issues flagged at smoke-test (Goths, Libyans, Lombards)
    are noted for re-run; existing counts are kept as 'v1' and flagged.
"""
import json
from collections import defaultdict
from pathlib import Path

p1 = json.load(open('part1_results.json'))
p2 = json.load(open('part2_results.json'))

# ─── 1. Per-book English merge ──────────────────────────────────────────────
all_books = sorted(set(p1['counts_per_book_english'].keys()) |
                   set(p2['counts_per_book_english'].keys()),
                   key=lambda b: ['I','II','III','IV','V','VI','VII','VIII','ANECDOTA','Unknown'].index(b)
                                 if b in ['I','II','III','IV','V','VI','VII','VIII','ANECDOTA','Unknown'] else 99)

all_groups = sorted(set(p1['counts_overall_english'].keys()) |
                    set(p2['counts_overall_english'].keys()))

merged_en = {b: {} for b in all_books}
for b in all_books:
    p1b = p1['counts_per_book_english'].get(b, {})
    p2b = p2['counts_per_book_english'].get(b, {})
    for g in all_groups:
        merged_en[b][g] = p1b.get(g, 0) + p2b.get(g, 0)

# ─── 2. Per-book Greek merge ───────────────────────────────────────────────
merged_gr = {b: {} for b in all_books}
for b in all_books:
    p1b = p1['counts_per_book_greek_normalised'].get(b, {})
    p2b = p2['counts_per_book_greek_normalised'].get(b, {})
    for g in all_groups:
        merged_gr[b][g] = p1b.get(g, 0) + p2b.get(g, 0)

# ─── 3. Word counts per book ────────────────────────────────────────────────
words_per_book = {}
for b in all_books:
    w1 = p1['metadata']['words_per_book_english'].get(b, 0)
    w2 = p2['metadata']['words_per_book_english'].get(b, 0)
    words_per_book[b] = w1 + w2

# ─── 4. Overall totals ─────────────────────────────────────────────────────
total_en = {g: sum(merged_en[b][g] for b in all_books) for g in all_groups}
total_gr = {g: sum(merged_gr[b][g] for b in all_books) for g in all_groups}
grand_total = sum(total_en.values())
total_words = sum(words_per_book.values())

# Sort groups by total count
sorted_groups = sorted(all_groups, key=lambda g: -total_en[g])

print("="*78)
print(f"UNIFIED DATASET")
print(f"  Total English words  : {total_words:,}")
print(f"  Total Greek words    : {p1['metadata']['word_count_greek_norm'] + p2['metadata']['word_count_greek_norm']:,}")
print(f"  Books represented    : {all_books}")
print(f"  Distinct groups      : {sum(1 for g in all_groups if total_en[g] > 0)} with at least one mention")
print(f"  Grand total mentions : {grand_total:,}")
print("="*78)
print()
print(f"{'Words per book':<25}", " ".join(f"{b:>8s}" for b in all_books))
print(f"{'':<25}", " ".join(f"{words_per_book[b]:>8,}" for b in all_books))
print()

# ─── 5. Show the unified per-book table for top groups ─────────────────────
print(f"\n{'TOP 15 GROUPS — PER BOOK ENGLISH COUNTS':<78}")
print("="*78)
header = f"{'Group':<32s} " + " ".join(f"{b:>6s}" for b in all_books) + f" {'Total':>7s} {'Share':>7s}"
print(header)
print("-"*len(header))
for g in sorted_groups[:15]:
    row = f"{g:<32s} " + " ".join(f"{merged_en[b][g]:>6}" for b in all_books)
    row += f" {total_en[g]:>7} {total_en[g]/grand_total*100:>6.2f}%"
    print(row)

print()
print(f"\n{'EN vs GR CORRELATION (overall, top 20)':<78}")
print("="*78)
print(f"{'Group':<32s} {'EN':>7s} {'GR':>7s} {'GR/EN':>8s}")
print("-"*60)
for g in sorted_groups[:20]:
    en, gr = total_en[g], total_gr[g]
    ratio = f"{gr/en:.2f}" if en > 0 else "—"
    flag = ""
    if en > 30 and gr > 0:
        r = gr/en
        if r < 0.5: flag = "  ← GR under-counts"
        elif r > 1.5: flag = "  ← GR over-counts"
    print(f"{g:<32s} {en:>7} {gr:>7} {ratio:>8}{flag}")

# ─── 6. Investigate the small Anecdota-in-Part-1 block ─────────────────────
print()
print("="*78)
print("ANECDOTA-tagged content in Part 1 (~2,220 words):")
print(f"  English: {p1['counts_per_book_english'].get('ANECDOTA', {})}")
nonzero_p1_anec = {k:v for k,v in p1['counts_per_book_english'].get('ANECDOTA', {}).items() if v > 0}
print(f"  Non-zero groups tagged ANECDOTA in Part 1: {nonzero_p1_anec}")
print("  → Almost certainly a stray header-parse (the word ANECDOTA appearing")
print("    somewhere in the front- or back-matter of Part-1 files). Will be")
print("    re-classified at the cleanup step below.")

# ─── 7. Save the unified dataset ────────────────────────────────────────────
unified = {
    'metadata': {
        'total_words_english': total_words,
        'total_words_greek': p1['metadata']['word_count_greek_norm'] + p2['metadata']['word_count_greek_norm'],
        'books_represented': all_books,
        'words_per_book': words_per_book,
        'distinct_groups_attested': sum(1 for g in all_groups if total_en[g] > 0),
        'grand_total_mentions_english': grand_total,
        'note_anecdota_in_part1': 'Small ANECDOTA-tagged block in Part 1 (~2,220 words) is a parser artefact, not real Anecdota content; rolled into "Misc/Unknown" for the paper.',
    },
    'counts_overall_english': total_en,
    'counts_overall_greek_normalised': total_gr,
    'counts_per_book_english': merged_en,
    'counts_per_book_greek_normalised': merged_gr,
    'sorted_groups_by_english_count': sorted_groups,
    'top5_share_english': sum(total_en[g] for g in sorted_groups[:5]) / grand_total * 100,
    'top10_share_english': sum(total_en[g] for g in sorted_groups[:10]) / grand_total * 100,
}
Path('unified_dataset.json').write_text(json.dumps(unified, indent=2, ensure_ascii=False))
print(f"\n✓ Wrote unified_dataset.json")
