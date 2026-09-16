"""When you only have ONE small labelled set (no disjoint train split), estimate the own:* arm
honestly with 5-fold cross-validation.   python scripts/own_cv.py --sample surge-1k"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sklearn.model_selection import StratifiedKFold, cross_val_predict  # noqa: E402
from sklearn.metrics import precision_recall_fscore_support, accuracy_score  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import make_pipeline, make_union  # noqa: E402
from bench.data import load_sample  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('--sample', required=True); a = ap.parse_args()
df = load_sample(a.sample)
pipe = make_pipeline(make_union(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                                TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)),
                     LogisticRegression(C=4, max_iter=2000, class_weight="balanced"))
X, y = df.text.to_numpy(dtype=object), df.label.to_numpy(dtype=int)
pred = cross_val_predict(pipe, X, y,
                         cv=StratifiedKFold(5, shuffle=True, random_state=20261012))
p, r, f, _ = precision_recall_fscore_support(y, pred, average='binary')
print(f"own (5-fold CV on {len(df)} labels): P={p:.3f} R={r:.3f} F1={f:.3f} acc={accuracy_score(y, pred):.3f}")
