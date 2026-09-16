"""False-positive rate per identity, for every arm that has run on data/handlabeled/identity.csv."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bench.run import RESULTS  # noqa: E402
from bench.metrics import load_run  # noqa: E402

notes = dict(zip(*[pd.read_csv('data/handlabeled/identity.csv')[c] for c in ('id', 'notes')]))
table, scores = {}, {}
for arm in sorted((RESULTS / 'identity').iterdir()):
    df = pd.DataFrame(load_run('identity', arm.name))
    df['identity'] = df.item_id.map(notes)
    table[arm.name] = df.groupby('identity').pred.apply(lambda s: (s == 1).mean())
    if df.score.notna().any():
        scores[arm.name + ' max score'] = df.groupby('identity').score.max()
out = pd.concat([pd.DataFrame(table), pd.DataFrame(scores)], axis=1)
out = out.sort_values(out.columns[0], ascending=False)
print(out.round(3).to_string())
lines = ['# Identity-term false positives (all sentences are innocuous, label 0)', '',
         '| identity | ' + ' | '.join(out.columns) + ' |', '|---|' + '---|' * len(out.columns)]
for k, row in out.iterrows():
    lines.append(f"| {k} | " + ' | '.join(f"{v:.3f}" for v in row) + ' |')
(RESULTS / 'identity.md').write_text('\n'.join(lines) + '\n')
