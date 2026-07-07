# Panduan Deploy ke Vercel — Dashboard Sentimen MyPertamina

## Struktur folder yang sudah disiapkan

```
vercel-deploy/
├── vercel.json              ← konfigurasi routing Vercel
├── requirements.txt         ← dependency Python (versi sudah dikunci)
└── api/
    ├── index.py             ← Flask app (sebelumnya app.py)
    ├── svm_model.pkl
    ├── tfidf_vectorizer.pkl
    ├── mypertamina_clean.csv
    ├── templates/
    │   └── index.html
    └── static/
        ├── css/style.css
        └── js/main.js
```

Kenapa strukturnya begini:
- Vercel Python runtime (`@vercel/python`) hanya mengeksekusi file di dalam folder `api/`.
- Semua file yang dibutuhkan Flask saat runtime (model, csv, template, static) harus berada
  **di dalam** folder `api/` (atau subfolder-nya), karena hanya isi folder tempat file
  entrypoint (`index.py`) berada yang otomatis ikut ter-bundle.
- `app.py` sudah pakai `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` untuk
  menemukan file pkl/csv — ini otomatis tetap benar setelah dipindah ke `api/index.py`,
  jadi **tidak perlu mengubah kode Python sama sekali**.

## Langkah deploy

### 1. Push ke GitHub
```bash
cd vercel-deploy
git init
git add .
git commit -m "Deploy dashboard sentimen ke Vercel"
git branch -M main
git remote add origin https://github.com/USERNAME/mypertamina-dashboard.git
git push -u origin main
```

### 2. Import project di Vercel
1. Buka https://vercel.com/new
2. Pilih repo GitHub kamu
3. **Framework Preset**: pilih "Other" (jangan pilih Flask/Next.js otomatis)
4. Biarkan **Build Command** dan **Output Directory** kosong — `vercel.json` yang mengatur semua
5. Klik **Deploy**

### 3. Tunggu build selesai
Build pertama biasanya 1-3 menit karena harus install pandas + scikit-learn + numpy.

## Hal-hal yang perlu diperhatikan

1. **Versi scikit-learn harus konsisten.** Model `.pkl` kamu dibuat dengan scikit-learn
   tertentu. `requirements.txt` sudah saya isi dengan versi yang stabil dan kompatibel
   (`1.4.2`) — sudah saya tes, `.pkl` kamu ter-load tanpa warning. Kalau nanti kamu retrain
   model dengan versi scikit-learn berbeda, update juga versi di `requirements.txt`.

2. **Cold start akan terasa lambat (3-8 detik)** di request pertama setelah idle, karena
   Vercel harus import pandas/scikit-learn dan load ulang model + hitung ulang semua
   statistik dari CSV setiap kali function "bangun". Ini normal untuk serverless, bukan bug.

3. **Ukuran total dependency mendekati batas.** Flask+pandas+numpy+scikit-learn sekitar
   150-200MB terinstall, masih di bawah limit 250MB Vercel — tapi kalau kamu menambah
   library lain (misal Sastrawi, matplotlib, dll), bisa kena limit. Kode kamu sudah punya
   fallback stemmer kalau Sastrawi tidak ada, jadi **jangan tambahkan Sastrawi ke
   requirements.txt** kecuali benar-benar perlu.

4. **Filesystem read-only.** Semua endpoint kamu sudah hanya membaca file (load pkl/csv),
   tidak ada yang menulis — jadi aman. Kalau nanti menambah fitur baru yang menyimpan file,
   itu harus pakai layanan eksternal (S3, database), bukan menulis ke disk lokal.

5. **URL API tetap sama.** Karena semua route diarahkan ke `api/index.py` lewat
   `vercel.json`, endpoint seperti `/api/predict`, `/api/charts/yearly`, dll akan tetap
   berfungsi persis seperti di lokal.

## Testing lokal sebelum push (opsional tapi disarankan)

```bash
cd vercel-deploy
pip install -r requirements.txt
cd api
python index.py
```
Buka `http://localhost:5000` — kalau ini jalan normal, seharusnya di Vercel juga jalan.
