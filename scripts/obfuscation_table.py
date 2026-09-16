"""Recall per transform on data/handlabeled/obfuscation.csv, for every arm that has run on it."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bench.run import RESULTS  # noqa: E402
from bench.metrics import load_run  # noqa: E402

notes = dict(zip(*[pd.read_csv('data/handlabeled/obfuscation.csv')[c] for c in ('id', 'notes')]))
table = {}
for arm in sorted((RESULTS / 'obfuscation').iterdir()):
    df = pd.DataFrame(load_run('obfuscation', arm.name))
    df['kind'] = df.item_id.map(notes)
    table[arm.name] = df.groupby('kind').pred.apply(lambda s: (s == 1).mean())
out = pd.DataFrame(table).reindex(['original', 'l33t', 'spaced', 'homoglyph', 'asterisk', 'concatenated'])
pct = (out * 100).round(1)
print(pct.to_string())
md = ['# Recall (%) per transform', '', '| transform | ' + ' | '.join(pct.columns) + ' |', '|---|' + '---|' * len(pct.columns)]
md += [f"| {k} | " + ' | '.join(f"{v:.1f}" for v in row) + ' |' for k, row in pct.iterrows()]
(RESULTS / 'obfuscation.md').write_text('\n'.join(md) + '\n')
