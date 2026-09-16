"""Experiment 7: build data/handlabeled/obfuscation.csv from the toxic items of a base sample
where the naive word list fires, by transforming EVERY word-list match. Labels stay 1 by
construction (the meaning does not change), so no hand-labelling is needed.

    python scripts/make_obfuscation.py --base balanced-2k
"""
import argparse, hashlib, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bench.arms import RegexArm  # noqa: E402

L33T = str.maketrans({'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '$', 't': '7', 'u': 'v'})
CYR = str.maketrans({'a': 'а', 'e': 'е', 'o': 'о', 'i': 'і', 'c': 'с', 'p': 'р', 'x': 'х', 'k': 'к'})


def build(base_name: str) -> pd.DataFrame:
    rx = RegexArm()
    p = Path('data/handlabeled') / f'{base_name}.csv'
    if not p.exists():
        p = Path('data/samples') / f'{base_name}.csv'
    df = pd.read_csv(p)
    base = [t for t in df[df.label == 1].text if rx.pattern.search(t)]

    def glue(t):
        # remove the whitespace around each match: "you fuck ing" -> "youfucking"
        spans = [m.span() for m in rx.pattern.finditer(t)]
        out, last = [], 0
        for s, e in spans:
            out.append(t[last:s].rstrip()); out.append(t[s:e]); last = e
            while last < len(t) and t[last].isspace():
                last += 1
        out.append(t[last:])
        return ''.join(out)

    transforms = {
        'original': lambda t: t,
        'l33t': lambda t: rx.pattern.sub(lambda m: m.group(0).translate(L33T), t),
        'spaced': lambda t: rx.pattern.sub(lambda m: ' '.join(m.group(0)), t),
        'homoglyph': lambda t: rx.pattern.sub(lambda m: m.group(0).translate(CYR), t),
        'asterisk': lambda t: rx.pattern.sub(lambda m: m.group(0)[0] + '*' * (len(m.group(0)) - 2) + m.group(0)[-1], t),
        'concatenated': glue,
    }
    rows = []
    for t in base:
        for kind, f in transforms.items():
            v = f(t)
            rows.append({'id': hashlib.sha1((kind + v).encode()).hexdigest()[:12], 'text': v, 'label': 1, 'notes': kind})
    return pd.DataFrame(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--base', default='balanced-2k'); a = ap.parse_args()
    out = build(a.base); out.to_csv('data/handlabeled/obfuscation.csv', index=False)
    print(f"{len(out)} rows ({out.notes.nunique()} variants x {len(out)//out.notes.nunique()} items) -> data/handlabeled/obfuscation.csv")
