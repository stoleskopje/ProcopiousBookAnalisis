"""
Statistical analysis and visualizations for the Histos paper.

Computes log-likelihood (G²) for over/under-representation of each group in
each book, relative to the corpus baseline. Generates the per-book heatmap
that is the paper's central figure.
"""
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

u = json.load(open('unified_dataset.json'))

books = [b for b in u['metadata']['books_represented'] if b != 'ANECDOTA']  # Wars only for narrative-geography argument
books_with_anec = u['metadata']['books_represented']
sorted_groups = u['sorted_groups_by_english_count']
words_per_book = u['metadata']['words_per_book']
counts_per_book = u['counts_per_book_english']
total_words = sum(words_per_book[b] for b in books_with_anec)

# ─── 1. Log-likelihood (G²) test for over-representation ──────────────────
# For each (group, book) pair compute G² with continuity:
#   a = count of group in this book
#   b = count of group elsewhere
#   c = words in this book - a (other words in this book)
#   d = words elsewhere - b
# Two-way contingency, signed by sign(observed - expected)

def loglike(a, b, c, d):
    """Dunning's log-likelihood for 2x2 contingency."""
    N = a + b + c + d
    if N == 0 or a == 0 and b == 0:
        return 0.0
    # expected
    e1 = (a + b) * (a + c) / N
    e2 = (a + b) * (b + d) / N
    e3 = (c + d) * (a + c) / N
    e4 = (c + d) * (b + d) / N
    g2 = 0.0
    for obs, exp in [(a, e1), (b, e2), (c, e3), (d, e4)]:
        if obs > 0 and exp > 0:
            g2 += obs * math.log(obs / exp)
    return 2 * g2

# Build matrix: rows = groups, cols = books
top_groups = [g for g in sorted_groups[:20]]

g2_matrix = np.zeros((len(top_groups), len(books_with_anec)))
sign_matrix = np.zeros((len(top_groups), len(books_with_anec)))
share_matrix = np.zeros((len(top_groups), len(books_with_anec)))

for i, g in enumerate(top_groups):
    total_g = u['counts_overall_english'][g]
    for j, b in enumerate(books_with_anec):
        a = counts_per_book[b][g]
        # for word-counts comparison: use scaled per-1000-words rate
        words_b = words_per_book[b]
        words_other = total_words - words_b
        count_other = total_g - a
        # Expected count in this book if uniformly distributed
        expected_in_b = total_g * words_b / total_words
        g2 = loglike(a, count_other, words_b - a, words_other - count_other)
        g2_matrix[i, j] = g2
        sign_matrix[i, j] = 1 if a > expected_in_b else -1
        share_matrix[i, j] = (a / words_b * 1000) if words_b > 0 else 0  # per 1000 words

# Critical G² values (1 df): 3.84 (p<0.05), 6.63 (p<0.01), 10.83 (p<0.001), 15.13 (p<0.0001)
signed_g2 = g2_matrix * sign_matrix

print("LOG-LIKELIHOOD (signed G²) — top 12 groups × books")
print("    + = over-represented relative to corpus baseline")
print("    - = under-represented")
print()
hdr = f"{'Group':<32s} " + " ".join(f"{b:>8s}" for b in books_with_anec)
print(hdr)
print("-" * len(hdr))
for i, g in enumerate(top_groups[:12]):
    row = f"{g:<32s} "
    for j, b in enumerate(books_with_anec):
        v = signed_g2[i, j]
        if abs(v) > 100:
            row += f" {v:+7.0f}*"
        else:
            row += f" {v:+7.1f} "
    print(row)
print()
print("(* = G² > 100, p < 10⁻²³ — extremely strong)")

# ─── 2. The headline chart: per-book RATE heatmap (mentions per 1000 words) ─
# Use rate to control for differing book lengths
fig, ax = plt.subplots(figsize=(11, 8))

# Reorder rows by total count (already in sorted_groups)
display_groups = sorted_groups[:18]
rate_matrix = np.zeros((len(display_groups), len(books_with_anec)))
for i, g in enumerate(display_groups):
    for j, b in enumerate(books_with_anec):
        words_b = words_per_book[b]
        if words_b > 0:
            rate_matrix[i, j] = counts_per_book[b][g] / words_b * 1000

# Log-transform for readability (log1p)
display_matrix = np.log1p(rate_matrix)

im = ax.imshow(display_matrix, cmap='YlOrRd', aspect='auto')

ax.set_xticks(range(len(books_with_anec)))
ax.set_xticklabels([f"Book {b}" if b != 'ANECDOTA' else 'Anecdota' for b in books_with_anec], rotation=0, fontsize=10)
ax.set_yticks(range(len(display_groups)))
ax.set_yticklabels(display_groups, fontsize=10)

# Annotate cells with raw counts
for i in range(len(display_groups)):
    for j in range(len(books_with_anec)):
        raw = counts_per_book[books_with_anec[j]][display_groups[i]]
        if raw > 0:
            text_color = 'white' if display_matrix[i, j] > display_matrix.max() * 0.6 else 'black'
            ax.text(j, i, str(raw), ha='center', va='center', color=text_color, fontsize=9, fontweight='bold')

ax.set_title('Procopius, Wars I–VIII + Anecdota: per-book ethnonym frequency\n(cell label = raw count; cell colour = mentions per 1,000 words, log-scaled)',
             fontsize=12, pad=15)
plt.colorbar(im, ax=ax, label='log(1 + mentions per 1,000 words)', shrink=0.7)
plt.tight_layout()
plt.savefig('figure1_per_book_heatmap.png', dpi=200, bbox_inches='tight')
plt.savefig('figure1_per_book_heatmap.pdf', bbox_inches='tight')
plt.close()
print(f"\n✓ Wrote figure1_per_book_heatmap.png/.pdf")

# ─── 3. The "narrative geography" chart: 5 protagonist peoples vs book ─────
protagonists = ['Persians', 'Vandals', 'Moors (Mauri)', 'Goths (Ostrogoths)', 'Lombards (Longobardi)', 'Lazi']
colors = ['#1f4e79', '#c1272d', '#f4a261', '#2a9d8f', '#7b4f9c', '#264653']
markers = ['o', 's', '^', 'D', 'v', 'P']

fig, ax = plt.subplots(figsize=(11, 6))
x = range(len(books_with_anec))
for p, col, mk in zip(protagonists, colors, markers):
    rates = []
    for b in books_with_anec:
        w = words_per_book[b]
        rates.append(counts_per_book[b][p] / w * 1000 if w > 0 else 0)
    ax.plot(x, rates, marker=mk, linewidth=2, markersize=9, label=p, color=col)

ax.set_xticks(x)
ax.set_xticklabels([f"Bk {b}" if b != 'ANECDOTA' else 'Anec.' for b in books_with_anec], fontsize=11)
ax.set_ylabel('Mentions per 1,000 words', fontsize=11)
ax.set_title('Narrative geography: each protagonist people clusters in the book(s) telling its war',
             fontsize=12, pad=12)
ax.legend(loc='upper left', fontsize=10, frameon=True)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_axisbelow(True)

# Annotate war boundaries
ax.axvspan(-0.4, 1.4, alpha=0.06, color='#1f4e79')   # Persian War
ax.axvspan(1.6, 3.4, alpha=0.06, color='#c1272d')    # Vandalic War
ax.axvspan(3.6, 7.4, alpha=0.06, color='#2a9d8f')    # Gothic War
ax.text(0.5, ax.get_ylim()[1]*0.92, 'Persian War', ha='center', fontsize=10, alpha=0.7, fontweight='bold')
ax.text(2.5, ax.get_ylim()[1]*0.92, 'Vandalic War', ha='center', fontsize=10, alpha=0.7, fontweight='bold')
ax.text(5.5, ax.get_ylim()[1]*0.92, 'Gothic War (and Lazic in VIII)', ha='center', fontsize=10, alpha=0.7, fontweight='bold')

plt.tight_layout()
plt.savefig('figure2_narrative_geography.png', dpi=200, bbox_inches='tight')
plt.savefig('figure2_narrative_geography.pdf', bbox_inches='tight')
plt.close()
print(f"✓ Wrote figure2_narrative_geography.png/.pdf")

# ─── 4. The "absent and emergent" chart: Slavs/Avars/Lombards over the books ───
emergent = ['Sclaveni (Slavs)', 'Antae', 'Avars', 'Lombards (Longobardi)', 'Gepaedes (Gepids)']
ecolors = ['#003366', '#0066cc', '#cc0000', '#7b4f9c', '#996633']

fig, ax = plt.subplots(figsize=(11, 6))
for p, col in zip(emergent, ecolors):
    rates = []
    for b in books_with_anec:
        w = words_per_book[b]
        rates.append(counts_per_book[b][p] / w * 1000 if w > 0 else 0)
    ax.plot(x, rates, marker='o', linewidth=2, markersize=8, label=f"{p} (total {u['counts_overall_english'][p]})", color=col)

ax.set_xticks(x)
ax.set_xticklabels([f"Bk {b}" if b != 'ANECDOTA' else 'Anec.' for b in books_with_anec], fontsize=11)
ax.set_ylabel('Mentions per 1,000 words', fontsize=11)
ax.set_title('The emergent ethnographic horizon of Wars VII–VIII (and the Avar silence)',
             fontsize=12, pad=12)
ax.legend(loc='upper left', fontsize=9, frameon=True)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_axisbelow(True)
# Annotate the Avar zero line
ax.annotate('Avars: 0 across all 447,466 words',
            xy=(7, 0), xytext=(5.5, 0.15),
            fontsize=10, color='#cc0000', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#cc0000', alpha=0.7))
plt.tight_layout()
plt.savefig('figure3_emergent_peoples.png', dpi=200, bbox_inches='tight')
plt.savefig('figure3_emergent_peoples.pdf', bbox_inches='tight')
plt.close()
print(f"✓ Wrote figure3_emergent_peoples.png/.pdf")

# ─── 5. Save the stats matrix for the paper appendix ────────────────────────
stats_out = {
    'top_groups': top_groups,
    'books': books_with_anec,
    'signed_g2': signed_g2.tolist(),
    'rate_per_1000': rate_matrix.tolist(),
    'critical_values': {
        'p<0.05': 3.84,
        'p<0.01': 6.63,
        'p<0.001': 10.83,
        'p<0.0001': 15.13,
    },
    'words_per_book': words_per_book,
}
Path('stats.json').write_text(json.dumps(stats_out, indent=2))
print(f"\n✓ Wrote stats.json")
