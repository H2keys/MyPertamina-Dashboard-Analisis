"""
==========================================================
  Dashboard Analisis Sentimen MyPertamina
  Backend Flask | SVM + TF-IDF (Data Dinamis dari CSV & PKL)
  -- FIXED: yearly trend, predict confidence, Sastrawi optional --
==========================================================
"""

from flask import Flask, render_template, request, jsonify
import re
import os
import pickle
import pandas as pd
from collections import Counter
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix
)
import numpy as np

# ================================================================
# SASTRAWI — OPSIONAL (fallback ke simple suffix stripping)
# ================================================================
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    _factory = StemmerFactory()
    _sastrawi_stemmer = _factory.create_stemmer()
    SASTRAWI_AVAILABLE = True
    print("✔ Sastrawi stemmer dimuat.")
except ImportError:
    SASTRAWI_AVAILABLE = False
    print("⚠ Sastrawi tidak tersedia, menggunakan simple stemmer pengganti.")


def _simple_stem(word: str) -> str:
    """
    Fallback stemmer ringan untuk Bahasa Indonesia.
    Menghapus imbuhan umum: me-, di-, ber-, ke-, ter-, pe-, -kan, -an, -i, -lah, -kah.
    Tidak seakurat Sastrawi tetapi cukup untuk ekstraksi fitur TF-IDF.
    """
    prefixes = ('memper', 'mempel', 'mempe', 'menge', 'memb', 'memf',
                'memp', 'memv', 'memw', 'meny', 'diper', 'dipel',
                'dipe', 'dinge', 'dibe', 'dise', 'menye', 'meng',
                'meny', 'men', 'mem', 'me', 'ber', 'per', 'ke',
                'ter', 'di', 'se')
    suffixes = ('kan', 'lah', 'kah', 'nya', 'an', 'i')

    w = word
    for p in prefixes:
        if w.startswith(p) and len(w) - len(p) >= 3:
            w = w[len(p):]
            break
    for s in suffixes:
        if w.endswith(s) and len(w) - len(s) >= 3:
            w = w[:-len(s)]
            break
    return w


def stem_text(text: str) -> str:
    if SASTRAWI_AVAILABLE:
        return _sastrawi_stemmer.stem(text)
    # stem kata per kata
    return ' '.join(_simple_stem(w) for w in text.split())


app = Flask(__name__, template_folder='templates', static_folder='static')

# ================================================================
# LOAD DATA DARI FILE CSV & PKL
# ================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_PATH   = os.path.join(BASE_DIR, 'mypertamina_clean.csv')
SVM_PATH   = os.path.join(BASE_DIR, 'svm_model.pkl')
TFIDF_PATH = os.path.join(BASE_DIR, 'tfidf_vectorizer.pkl')

print("Memuat dataset CSV...")
df = pd.read_csv(CSV_PATH)
df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
df['Ulasan_Bersih'] = df['Ulasan_Bersih'].fillna('')

print("Memuat model SVM & TF-IDF Vectorizer...")
with open(SVM_PATH, 'rb') as f:
    MODEL = pickle.load(f)
with open(TFIDF_PATH, 'rb') as f:
    VECTORIZER = pickle.load(f)

# ================================================================
# HITUNG STATISTIK DARI DATA NYATA
# ================================================================

_pos_count  = int((df['Sentimen'] == 'Positif').sum())
_neg_count  = int((df['Sentimen'] == 'Negatif').sum())
_total      = len(df)
_avg_rating = round(float(df['Rating'].mean()), 2)
_vocab_size = len(VECTORIZER.vocabulary_)

# Train/test split (sama seperti saat training: 80/20, random_state=42)
X = df['Ulasan_Bersih']
y = df['Sentimen']
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Evaluasi model pada test set
X_test_tfidf = VECTORIZER.transform(X_test)
y_pred = MODEL.predict(X_test_tfidf)

_accuracy  = round(accuracy_score(y_test, y_pred) * 100, 2)
_precision = round(precision_score(y_test, y_pred, pos_label='Positif') * 100, 2)
_recall    = round(recall_score(y_test, y_pred, pos_label='Positif') * 100, 2)
_f1        = round(f1_score(y_test, y_pred, pos_label='Positif') * 100, 2)
_cm        = confusion_matrix(y_test, y_pred, labels=['Positif', 'Negatif']).tolist()

# Distribusi rating
_rating_dist = df['Rating'].value_counts().sort_index()

# ----------------------------------------------------------------
# Monthly trend
# ----------------------------------------------------------------
df['YearMonth'] = df['Tanggal'].dt.to_period('M')
_monthly = (
    df.groupby(['YearMonth', 'Sentimen'])
      .size()
      .unstack(fill_value=0)
)
for col in ['Positif', 'Negatif']:
    if col not in _monthly.columns:
        _monthly[col] = 0

_month_labels = [
    p.to_timestamp().strftime('%b %y') for p in _monthly.index
]

# ----------------------------------------------------------------
# Yearly trend — agregasi per tahun
# ----------------------------------------------------------------
df['Year'] = df['Tanggal'].dt.year.astype('Int64')   # nullable int agar NaT tidak error

_yearly = (
    df.dropna(subset=['Year'])
      .groupby(['Year', 'Sentimen'])
      .size()
      .unstack(fill_value=0)
)
for col in ['Positif', 'Negatif']:
    if col not in _yearly.columns:
        _yearly[col] = 0

# Pastikan index adalah integer Python biasa (bukan numpy int64/Int64)
_yearly_labels   = [str(int(y)) for y in _yearly.index.tolist()]
_yearly_positif  = [int(v) for v in _yearly['Positif'].tolist()]
_yearly_negatif  = [int(v) for v in _yearly['Negatif'].tolist()]
_yearly_total    = [p + n for p, n in zip(_yearly_positif, _yearly_negatif)]
_yearly_pct_pos  = [
    round(p / t * 100, 1) if t > 0 else 0.0
    for p, t in zip(_yearly_positif, _yearly_total)
]
_yearly_pct_neg  = [
    round(n / t * 100, 1) if t > 0 else 0.0
    for n, t in zip(_yearly_negatif, _yearly_total)
]

# ----------------------------------------------------------------
# Monthly breakdown per tahun (untuk drill-down)
# ----------------------------------------------------------------
_MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']


def _monthly_by_year(year: int) -> dict:
    sub = df[df['Year'] == year].copy()
    sub['Month'] = sub['Tanggal'].dt.month
    grp = (
        sub.groupby(['Month', 'Sentimen'])
           .size()
           .unstack(fill_value=0)
    )
    for col in ['Positif', 'Negatif']:
        if col not in grp.columns:
            grp[col] = 0
    return {
        'labels' : [_MONTH_NAMES[int(m) - 1] for m in grp.index],
        'positif': [int(v) for v in grp['Positif'].tolist()],
        'negatif': [int(v) for v in grp['Negatif'].tolist()],
    }


_yearly_monthly_detail = {
    int(y): _monthly_by_year(int(y))
    for y in _yearly.index.tolist()
}

# ----------------------------------------------------------------
# Top kata per sentimen
# ----------------------------------------------------------------
_STOP = {
    'yang', 'di', 'dan', 'ke', 'dari', 'ini', 'itu', 'untuk', 'dengan', 'pada',
    'saya', 'tidak', 'ada', 'bisa', 'juga', 'sudah', 'lebih', 'sangat', 'tapi',
    'karena', 'jadi', 'buat', 'aja', 'kalo', 'nya', 'pun', 'nih', 'sih', 'lah',
    'dong', 'deh', 'toh', 'kah', 'kan', 'ber', 'banget',
    # Domain specific stopwords yang membuat awan kata tidak bervariasi:
    'aplikasi', 'pertamina', 'mypertamina', 'mau', 'gak', 'udah', 'terus',
    'malah', 'pas', 'bikin', 'lagi', 'baru', 'kalo', 'sama', 'kok', 'saja',
    'pakai', 'banyak', 'orang', 'kalau', 'coba', 'saat', 'biar', 'selalu',
    'padahal', 'terus', 'buka', 'masuk', 'waktu'
}


def _top_words(sentiment: str, n: int = 32) -> list:
    text  = ' '.join(df[df['Sentimen'] == sentiment]['Ulasan_Bersih'])
    words = [w for w in text.split() if len(w) > 2 and w not in _STOP]
    return [[w, c] for w, c in Counter(words).most_common(n)]


_WORDS_POSITIF = _top_words('Positif')
_WORDS_NEGATIF = _top_words('Negatif')

_POS_KW = {w for w, _ in _WORDS_POSITIF[:15]}
_NEG_KW = {w for w, _ in _WORDS_NEGATIF[:15]}

print(f"Data siap: {_total} ulasan | Acc={_accuracy}% | Vocab={_vocab_size}")
print(f"Tahun tersedia: {_yearly_labels}")

# ================================================================
# PREPROCESSING & PREDIKSI
# ================================================================

_NORM_DICT = {
    "apk": "aplikasi", "gk": "tidak",  "bgt": "banget",
    "ga":  "tidak",    "tdk": "tidak",  "dgn": "dengan",
    "yg":  "yang",     "gak": "tidak",  "gpp": "tidak apa",
    "tp":  "tapi",     "krn": "karena", "jd":  "jadi",
    "sy":  "saya",     "sdh": "sudah",  "udh": "sudah",
    "lg":  "lagi",     "sm":  "sama",   "emg": "memang",
    "bngt":"banget",   "aj":  "aja",    "hrs": "harus",
}
_STOPWORDS = {
    'yang', 'di', 'dan', 'ke', 'dari', 'ini', 'itu', 'untuk', 'dengan', 'pada',
}


def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Hapus URL
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # Hapus karakter non-huruf
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = text.lower().strip()
    if not text:
        return ""
    tokens = text.split()
    # Normalisasi singkatan
    tokens = [_NORM_DICT.get(word, word) for word in tokens]
    # Hapus stopword
    tokens = [word for word in tokens if word not in _STOPWORDS and len(word) > 1]
    if not tokens:
        return ""
    # Stemming
    return stem_text(' '.join(tokens))


def _decision_score_to_confidence(raw_score: float) -> float:
    """
    Konversi decision_function score (bisa negatif/positif) ke confidence %.
    Menggunakan sigmoid yang di-clamp ke [50, 99.5].
    Score positif  → prediksi Positif (kelas +1 di SVM binary)
    Score negatif  → prediksi Negatif
    Semakin jauh dari 0, semakin yakin model.
    """
    import math
    # Sigmoid: 1 / (1 + e^-x), lalu re-scale ke [50, 99.5]
    sigmoid = 1.0 / (1.0 + math.exp(-abs(raw_score)))
    conf = 50.0 + sigmoid * 49.5        # range [50, 99.5]
    return round(min(99.5, conf), 1)


def predict_sentiment(text: str) -> dict:
    processed = preprocess_text(text)
    if not processed.strip():
        return {
            'sentiment' : 'Netral / Tidak Dikenali',
            'confidence': 0.0,
            'model_type': 'Teks Kosong Setelah Preprocessing',
        }
    try:
        X_vec = VECTORIZER.transform([processed])
        pred  = MODEL.predict(X_vec)[0]          # string: 'Positif' atau 'Negatif'

        # decision_function: untuk binary SVC mengembalikan array 1D shape (1,)
        # untuk multi-class mengembalikan 2D shape (1, n_classes) — ambil max
        raw_df = MODEL.decision_function(X_vec)
        if hasattr(raw_df, 'ndim') and raw_df.ndim == 2:
            # Multi-class: ambil score kelas yang diprediksi
            class_idx = list(MODEL.classes_).index(pred)
            raw_score = float(raw_df[0][class_idx])
        else:
            raw_score = float(np.array(raw_df).flatten()[0])

        conf = _decision_score_to_confidence(raw_score)

    except Exception as e:
        return {
            'sentiment' : 'ERROR',
            'confidence': 0.0,
            'model_type': f'Error Prediksi: {str(e)[:80]}',
        }

    return {
        'sentiment' : pred,
        'confidence': conf,
        'model_type': f'SVM + TF-IDF ({"Sastrawi" if SASTRAWI_AVAILABLE else "Simple Stemmer"})',
    }


# ================================================================
# ROUTES — API
# ================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/overview')
def api_overview():
    return jsonify({
        'total_scraped'  : _total + 291,
        'total_processed': _total,
        'positif'        : _pos_count,
        'negatif'        : _neg_count,
        'vocab_size'     : _vocab_size,
        'train_size'     : len(X_train),
        'test_size'      : len(X_test),
        'avg_rating'     : _avg_rating,
    })


@app.route('/api/charts/sentiment')
def api_sentiment():
    pct_pos = round(_pos_count / _total * 100, 1)
    pct_neg = round(_neg_count / _total * 100, 1)
    return jsonify({
        'labels'    : ['Positif', 'Negatif'],
        'values'    : [_pos_count, _neg_count],
        'colors'    : ['#2ECC71', '#E74C3C'],
        'percentage': [pct_pos, pct_neg],
    })


@app.route('/api/charts/rating')
def api_rating():
    labels     = [f'{"★" * int(r)} {r}' for r in _rating_dist.index]
    values     = [int(v) for v in _rating_dist.values]
    colors_map = {1: '#E74C3C', 2: '#E67E22', 3: '#F1C40F', 4: '#3498DB', 5: '#2ECC71'}
    colors     = [colors_map.get(int(r), '#95A5A6') for r in _rating_dist.index]
    return jsonify({'labels': labels, 'values': values, 'colors': colors})


@app.route('/api/charts/monthly')
def api_monthly():
    return jsonify({
        'labels'     : _month_labels,
        'positif'    : [int(v) for v in _monthly['Positif'].tolist()],
        'negatif'    : [int(v) for v in _monthly['Negatif'].tolist()],
        'period_keys': [str(p) for p in _monthly.index],   # format: "2025-09"
    })


@app.route('/api/monthly/trending/<year_month>')
def api_monthly_trending(year_month: str):
    """
    Satu ulasan terpopuler dari sentimen dominan bulan tersebut.
    """
    try:
        period = pd.Period(year_month, freq='M')
    except Exception:
        return jsonify({'error': f'Format tidak valid: {year_month}'}), 400

    sub = df[df['YearMonth'] == period]
    if sub.empty:
        return jsonify({'error': f'Tidak ada data untuk {year_month}'}), 404

    pos_count = int((sub['Sentimen'] == 'Positif').sum())
    neg_count = int((sub['Sentimen'] == 'Negatif').sum())
    dominant  = 'Positif' if pos_count >= neg_count else 'Negatif'

    def _top_review(sentiment: str) -> str:
        sub_sent = sub[sub['Sentimen'] == sentiment].dropna(subset=['Ulasan', 'Ulasan_Bersih'])
        if sub_sent.empty:
            return None

        # Hitung probabilitas dari model
        X_tfidf = VECTORIZER.transform(sub_sent['Ulasan_Bersih'])
        d = MODEL.decision_function(X_tfidf)
        p = 1 / (1 + np.exp(-d))

        # Filter confidence > 90%
        if sentiment == 'Positif':
            mask = p >= 0.90
        else:
            mask = p <= 0.10

        valid_rows = sub_sent[mask]
        if valid_rows.empty:
            valid_rows = sub_sent # fallback jika tidak ada yang > 90%

        rows = valid_rows['Ulasan'].str.strip()
        rows = rows[rows.str.len() > 20]
        if rows.empty:
            return None
        
        # 1. Duplikat terbanyak
        counts = rows.str.lower().value_counts()
        if counts.iloc[0] > 1:
            top_lower = counts.index[0]
            return rows[rows.str.lower() == top_lower].iloc[0]
            
        # 2. Review yang paling banyak mengandung kata umum bulan ini
        month_words = ' '.join(valid_rows['Ulasan_Bersih'])
        word_freq   = Counter(w for w in month_words.split() if len(w) > 2 and w not in _STOP)
        if not word_freq:
            return rows.iloc[0]
            
        top_words_set = {w for w, _ in word_freq.most_common(20)}
        best_score, best_review = -1, rows.iloc[0]
        for rev in rows:
            score = sum(1 for w in rev.lower().split() if w in top_words_set)
            if score > best_score:
                best_score, best_review = score, rev
        return best_review

    return jsonify({
        'label'      : period.to_timestamp().strftime('%B %Y'),
        'positif'    : pos_count,
        'negatif'    : neg_count,
        'dominant'   : dominant,
        'top_review' : _top_review(dominant),
    })


@app.route('/api/charts/yearly')
def api_yearly():
    """Tren sentimen per tahun — jumlah & persentase."""
    return jsonify({
        'labels'     : _yearly_labels,
        'positif'    : _yearly_positif,
        'negatif'    : _yearly_negatif,
        'total'      : _yearly_total,
        'pct_positif': _yearly_pct_pos,
        'pct_negatif': _yearly_pct_neg,
    })


@app.route('/api/charts/yearly/<int:year>')
def api_yearly_detail(year: int):
    """Breakdown bulanan untuk tahun tertentu."""
    if year not in _yearly_monthly_detail:
        return jsonify({
            'error'    : f'Tahun {year} tidak tersedia.',
            'available': list(_yearly_monthly_detail.keys()),
        }), 404
    data = dict(_yearly_monthly_detail[year])   # shallow copy agar aman
    data['year'] = year
    return jsonify(data)


@app.route('/api/wordcloud/<sentiment>')
def api_wordcloud(sentiment):
    data = _WORDS_POSITIF if sentiment.lower() == 'positif' else _WORDS_NEGATIF
    return jsonify(data)


@app.route('/api/evaluation')
def api_evaluation():
    return jsonify({
        'accuracy' : _accuracy,
        'precision': _precision,
        'recall'   : _recall,
        'f1'       : _f1,
        'cm'       : _cm,
    })


@app.route('/api/predict', methods=['POST'])
def api_predict():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({'error': 'Tidak ada data yang diterima'}), 400
    text = body.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Teks tidak boleh kosong'}), 400

    result    = predict_sentiment(text)
    processed = preprocess_text(text)
    words     = processed.split() if processed else []

    result.update({
        'processed_text'  : processed,
        'word_count_orig' : len(text.split()),
        'word_count_clean': len(words),
        'matched_positive': list(_POS_KW & set(words)),
        'matched_negative': list(_NEG_KW & set(words)),
    })
    return jsonify(result)


# ================================================================
# ANALYZE URL — Google Play Store scraping + batch prediction
# ================================================================

@app.route('/api/analyze_url', methods=['POST'])
def api_analyze_url():
    """
    Menerima URL Google Play Store, scrape review, dan analisis sentimen batch.
    Body JSON: { "url": "https://play.google.com/store/apps/details?id=com.xxx" }
    """
    try:
        from google_play_scraper import app as gp_app, reviews, Sort
    except ImportError:
        return jsonify({'error': 'Library google-play-scraper tidak tersedia. Jalankan: pip install google-play-scraper'}), 500

    body = request.get_json(silent=True)
    if not body:
        return jsonify({'error': 'Tidak ada data yang diterima'}), 400

    url = body.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL tidak boleh kosong'}), 400

    # ── Ekstrak app_id dari URL ──────────────────────────────────
    import urllib.parse as _up
    try:
        parsed   = _up.urlparse(url)
        app_id   = _up.parse_qs(parsed.query).get('id', [None])[0]
        if not app_id:
            # Coba ekstrak dari path seperti /store/apps/details/id/com.xxx
            parts = [p for p in parsed.path.split('/') if p]
            if 'id' in parts:
                app_id = parts[parts.index('id') + 1]
        if not app_id:
            return jsonify({'error': 'Tidak dapat menemukan app ID dari URL. Pastikan URL mengandung ?id=com.xxx'}), 400
    except Exception as e:
        return jsonify({'error': f'URL tidak valid: {str(e)}'}), 400

    # ── Ambil info aplikasi ──────────────────────────────────────
    try:
        app_info = gp_app(app_id, lang='id', country='id')
    except Exception:
        try:
            app_info = gp_app(app_id, lang='en', country='us')
        except Exception as e:
            return jsonify({'error': f'App tidak ditemukan: {str(e)[:120]}'}), 404

    # ── Scrape reviews (max 200, terbaru) ────────────────────────
    try:
        result_reviews, _ = reviews(
            app_id,
            lang='id', country='id',
            sort=Sort.NEWEST,
            count=200,
        )
    except Exception as e:
        return jsonify({'error': f'Gagal scrape review: {str(e)[:120]}'}), 502

    if not result_reviews:
        return jsonify({'error': 'Tidak ada review yang berhasil diambil dari Play Store.'}), 404

    # ── Analisis sentimen batch ──────────────────────────────────
    analyzed   = []
    pos_count  = 0
    neg_count  = 0
    conf_total = 0.0

    for rev in result_reviews:
        raw_text = (rev.get('content') or '').strip()
        if not raw_text:
            continue

        res       = predict_sentiment(raw_text)
        sentiment = res.get('sentiment', '-')
        conf      = res.get('confidence', 0.0)

        if sentiment == 'Positif':
            pos_count += 1
        elif sentiment == 'Negatif':
            neg_count += 1

        conf_total += conf
        analyzed.append({
            'text'      : raw_text[:300],   # potong agar JSON tidak terlalu besar
            'sentiment' : sentiment,
            'confidence': conf,
            'rating'    : rev.get('score', None),
            'at'        : rev.get('at', None) and str(rev['at'])[:10],
            'userName'  : rev.get('userName', 'Anonim'),
        })

    total     = len(analyzed)
    avg_conf  = round(conf_total / total, 1) if total else 0.0
    pct_pos   = round(pos_count / total * 100, 1) if total else 0.0
    pct_neg   = round(neg_count / total * 100, 1) if total else 0.0

    return jsonify({
        'app_id'        : app_id,
        'app_name'      : app_info.get('title', app_id),
        'app_icon'      : app_info.get('icon', ''),
        'app_developer' : app_info.get('developer', '-'),
        'app_rating'    : app_info.get('score', None),
        'total_scraped' : total,
        'positif'       : pos_count,
        'negatif'       : neg_count,
        'pct_positif'   : pct_pos,
        'pct_negatif'   : pct_neg,
        'avg_confidence': avg_conf,
        'reviews'       : analyzed,
    })


# ================================================================
# ROUTE TAMBAHAN — debug / eksplorasi
# ================================================================

@app.route('/api/dataset/sample')
def api_dataset_sample():
    """Mengembalikan 10 sampel acak dari dataset."""
    sample = df[['Ulasan', 'Sentimen', 'Rating']].sample(10).to_dict(orient='records')
    return jsonify(sample)


@app.route('/api/dataset/stats')
def api_dataset_stats():
    """Ringkasan statistik dataset."""
    return jsonify({
        'total_rows'   : _total,
        'columns'      : df.columns.tolist(),
        'sentimen_dist': df['Sentimen'].value_counts().to_dict(),
        'rating_dist'  : {int(k): int(v) for k, v in df['Rating'].value_counts().sort_index().items()},
        'date_range'   : {
            'min': str(df['Tanggal'].min().date()) if not pd.isnull(df['Tanggal'].min()) else None,
            'max': str(df['Tanggal'].max().date()) if not pd.isnull(df['Tanggal'].max()) else None,
        },
        'years_available': _yearly_labels,
        'stemmer'        : 'Sastrawi' if SASTRAWI_AVAILABLE else 'Simple (fallback)',
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)