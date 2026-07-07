// ================================================================
// main.js — Dashboard Sentimen MyPertamina
// Extracted from templates/index.html
// ================================================================

// ── HELPERS ──
const fmt    = n => n?.toLocaleString('id-ID') ?? '-';
const fmtPct = n => n != null ? n + '%' : '-';

// ── CHART.JS DEFAULTS ──
Chart.defaults.font  = { family: 'Inter, sans-serif', size: 12 };
Chart.defaults.color = '#60657A';

// ── NAV DATE ──
document.getElementById('navDate').textContent =
    new Date().toLocaleDateString('id-ID', { year: 'numeric', month: 'long', day: 'numeric' });

// ================================================================
// OVERVIEW
// ================================================================
fetch('/api/overview').then(r => r.json()).then(d => {
    document.getElementById('statTotal').textContent  = fmt(d.total_processed);
    document.getElementById('statPos').textContent    = fmt(d.positif);
    document.getElementById('statNeg').textContent    = fmt(d.negatif);
    document.getElementById('statRating').textContent = d.avg_rating ?? '-';
    const t = d.total_processed;
    document.getElementById('statPosPct').textContent = t ? `${(d.positif/t*100).toFixed(1)}% dari total` : '';
    document.getElementById('statNegPct').textContent = t ? `${(d.negatif/t*100).toFixed(1)}% dari total` : '';
    document.getElementById('trainSize').textContent  = fmt(d.train_size);
    document.getElementById('testSize').textContent   = fmt(d.test_size);
    document.getElementById('vocabSize').textContent  = fmt(d.vocab_size);
});

// ================================================================
// EVALUASI
// ================================================================
fetch('/api/evaluation').then(r => r.json()).then(d => {
    document.getElementById('evalAcc').textContent  = fmtPct(d.accuracy);
    document.getElementById('evalPrec').textContent = fmtPct(d.precision);
    document.getElementById('evalRec').textContent  = fmtPct(d.recall);
    document.getElementById('evalF1').textContent   = fmtPct(d.f1);

    const [[tp, fn], [fp, tn]] = d.cm;
    document.getElementById('cmTotal').textContent = fmt(tp + fn + fp + tn);
    document.getElementById('cmTP').innerHTML = `${fmt(tp)}<small>True Positive</small>`;
    document.getElementById('cmFN').innerHTML = `${fmt(fn)}<small>False Negative</small>`;
    document.getElementById('cmFP').innerHTML = `${fmt(fp)}<small>False Positive</small>`;
    document.getElementById('cmTN').innerHTML = `${fmt(tn)}<small>True Negative</small>`;
});

// ================================================================
// DISTRIBUSI SENTIMEN (doughnut)
// ================================================================
fetch('/api/charts/sentiment').then(r => r.json()).then(d => {
    new Chart(document.getElementById('sentimentChart'), {
        type: 'doughnut',
        data: {
            labels: d.labels.map((l, i) => `${l} (${d.percentage[i]}%)`),
            datasets: [{
                data: d.values,
                backgroundColor: d.colors,
                borderWidth: 0,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true } },
                tooltip: { callbacks: { label: ctx => ` ${fmt(ctx.raw)} ulasan` } }
            }
        }
    });
});

// ================================================================
// DISTRIBUSI RATING (bar)
// ================================================================
fetch('/api/charts/rating').then(r => r.json()).then(d => {
    new Chart(document.getElementById('ratingChart'), {
        type: 'bar',
        data: {
            labels: d.labels,
            datasets: [{
                label: 'Jumlah Ulasan',
                data: d.values,
                backgroundColor: d.colors,
                borderRadius: 6,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#E4E6ED' }, ticks: { callback: v => fmt(v) } },
                x: { grid: { display: false } }
            }
        }
    });
});

// ================================================================
// TREN BULANAN (line) + TRENDING REVIEWS
// ================================================================
let _monthlyPeriodKeys = [];   // ["2025-09", "2025-10", ...]
let _trendingCache     = {};   // cache per period key
let _trendHoverTimer   = null;
let _activeTrendKey    = null;
let _activeTrendTab    = 'pos';

fetch('/api/charts/monthly').then(r => r.json()).then(d => {
    _monthlyPeriodKeys = d.period_keys || [];

    new Chart(document.getElementById('monthlyChart'), {
        type: 'line',
        data: {
            labels: d.labels,
            datasets: [
                {
                    label: 'Positif',
                    data: d.positif,
                    borderColor: '#0FA958',
                    backgroundColor: 'rgba(15,169,88,.08)',
                    fill: true,
                    tension: .4,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointHoverBackgroundColor: '#0FA958',
                    borderWidth: 2.5,
                },
                {
                    label: 'Negatif',
                    data: d.negatif,
                    borderColor: '#E8001D',
                    backgroundColor: 'rgba(232,0,29,.07)',
                    fill: true,
                    tension: .4,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointHoverBackgroundColor: '#E8001D',
                    borderWidth: 2.5,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top', labels: { usePointStyle: true, padding: 16 } },
                tooltip: {
                    backgroundColor: '#0E1117',
                    titleColor: '#FFFFFF',
                    bodyColor: '#E4E6ED',
                    borderColor: '#60657A',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    titleFont: { size: 13, weight: '700', family: 'Inter, sans-serif' },
                    bodyFont: { size: 12, family: 'Inter, sans-serif' },
                    displayColors: true,
                    boxWidth: 12,
                    boxHeight: 12,
                    boxPadding: 4,
                    callbacks: {
                        title: (items) => items[0]?.label ?? '',
                        label: (ctx) => {
                            const icon = ctx.datasetIndex === 0 ? '▲' : '▼';
                            return `  ${icon} ${ctx.dataset.label}: ${fmt(ctx.raw)} ulasan`;
                        },
                        afterBody: (items) => {
                            const total = items.reduce((s, i) => s + (i.raw ?? 0), 0);
                            return [``, `  Total: ${fmt(total)} ulasan`];
                        }
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#E4E6ED' } },
                x: { grid: { display: false } }
            },
            onHover: (_evt, activeEls) => {
                if (!activeEls || activeEls.length === 0) return;
                const idx = activeEls[0].index;
                const key = _monthlyPeriodKeys[idx];
                if (!key || key === _activeTrendKey) return;
                // Debounce: tunggu 300ms sebelum fetch
                clearTimeout(_trendHoverTimer);
                _trendHoverTimer = setTimeout(() => loadTrending(key), 300);
            }
        }
    });
});

// ── Trending Reviews Helpers ──────────────────────────────────────

function loadTrending(periodKey) {
    if (_activeTrendKey === periodKey) return;
    _activeTrendKey = periodKey;

    if (_trendingCache[periodKey]) {
        renderTrending(_trendingCache[periodKey]);
        return;
    }

    _setTrendingState('loading');

    fetch(`/api/monthly/trending/${periodKey}`)
        .then(r => r.json())
        .then(data => {
            _trendingCache[periodKey] = data;
            renderTrending(data);
        })
        .catch(() => _setTrendingState('hint'));
}

function renderTrending(data) {
    if (data.error) { _setTrendingState('hint'); return; }

    // Sembunyikan hint & loading, tampilkan konten
    document.getElementById('trendingHint').style.display    = 'none';
    document.getElementById('trendingLoading').style.display = 'none';
    document.getElementById('trendingContent').style.display = 'block';

    // Label bulan + status dominan
    const isPos = data.dominant === 'Positif';
    const domIcon  = isPos ? '📈' : '📉';
    const domColor = isPos ? 'var(--green)' : 'var(--red)';
    document.getElementById('trendingMonthLabel').innerHTML =
        `<i class="bi bi-fire" style="color:var(--red)"></i>
         Ulasan Tren Bulan <strong>${data.label}</strong>
         &nbsp;·&nbsp;
         <span style="color:${domColor}">${domIcon} Dominan ${data.dominant}</span>`;

    // Ambil elemen single box
    const boxBox    = document.getElementById('tqBoxSingle');
    const boxIcon   = document.getElementById('tqIconSingle');
    const boxTitle  = document.getElementById('tqHeaderTitle');
    const boxText   = document.getElementById('tqSentenceSingle');
    const boxFooter = document.getElementById('tqFooterSingle');

    // Atur class box (warna hijau/merah)
    boxBox.className = 'tq-box ' + (isPos ? 'tq-pos' : 'tq-neg');

    // Atur icon & title
    boxIcon.className = isPos ? 'bi bi-hand-thumbs-up-fill' : 'bi bi-hand-thumbs-down-fill';
    boxTitle.textContent = isPos ? 'Ulasan Positif Terpopuler' : 'Ulasan Negatif Terpopuler';

    // Atur teks & footer
    if (data.top_review) {
        boxText.textContent = data.top_review;
        const count = isPos ? data.positif : data.negatif;
        boxFooter.textContent = `Mewakili ${fmt(count)} ulasan ${data.dominant.toLowerCase()} bulan ini`;
    } else {
        boxText.textContent = `Tidak ada ulasan ${data.dominant.toLowerCase()} bulan ini.`;
        boxFooter.textContent = '';
    }
}

function _setTrendingState(state) {
    document.getElementById('trendingHint').style.display    = state === 'hint'    ? 'flex'  : 'none';
    document.getElementById('trendingLoading').style.display = state === 'loading' ? 'flex'  : 'none';
    document.getElementById('trendingContent').style.display = state === 'loaded'  ? 'block' : 'none';
}

function _escHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}



// ================================================================
// TREN TAHUNAN
// ================================================================
let yearlyData             = null;
let yearlyDetailChartInst  = null;
let yearlyOverviewChartInst = null;
let activeYear             = null;

fetch('/api/charts/yearly').then(r => r.json()).then(d => {
    yearlyData = d;

    // Buat pill per tahun
    const pillsCont = document.getElementById('yearPills');
    const allPill   = document.createElement('button');
    allPill.className   = 'year-pill active';
    allPill.textContent = 'Semua Tahun';
    allPill.dataset.year = 'all';
    allPill.onclick = () => showYearlyOverview();
    pillsCont.appendChild(allPill);

    d.labels.forEach(yr => {
        const btn = document.createElement('button');
        btn.className   = 'year-pill';
        btn.textContent = yr;
        btn.dataset.year = yr;
        btn.onclick = () => showYearlyDetail(parseInt(yr));
        pillsCont.appendChild(btn);
    });

    // Default tampilkan overview semua tahun
    showYearlyOverview();
});

function setActivePill(yearVal) {
    document.querySelectorAll('.year-pill').forEach(b => {
        b.classList.toggle('active', b.dataset.year === String(yearVal));
    });
}

function renderYearlySummary(year) {
    const cont = document.getElementById('yearlySummary');
    if (!year || year === 'all') {
        const totalPos = yearlyData.positif.reduce((a, b) => a + b, 0);
        const totalNeg = yearlyData.negatif.reduce((a, b) => a + b, 0);
        const total    = totalPos + totalNeg;
        cont.innerHTML = `
            <div class="ys-card">
                <div class="ys-label">Total Ulasan</div>
                <div class="ys-value" style="color:var(--ink)">${fmt(total)}</div>
                <div class="ys-bar"><div class="ys-bar-fill" style="width:100%;background:var(--ink)"></div></div>
            </div>
            <div class="ys-card">
                <div class="ys-label">Total Positif</div>
                <div class="ys-value" style="color:var(--green)">${fmt(totalPos)}</div>
                <div class="ys-bar"><div class="ys-bar-fill" style="width:${(totalPos/total*100).toFixed(1)}%;background:var(--green)"></div></div>
            </div>
            <div class="ys-card">
                <div class="ys-label">Total Negatif</div>
                <div class="ys-value" style="color:var(--red)">${fmt(totalNeg)}</div>
                <div class="ys-bar"><div class="ys-bar-fill" style="width:${(totalNeg/total*100).toFixed(1)}%;background:var(--red)"></div></div>
            </div>`;
        return;
    }
    const idx = yearlyData.labels.indexOf(String(year));
    if (idx < 0) return;
    const pos   = yearlyData.positif[idx];
    const neg   = yearlyData.negatif[idx];
    const total = pos + neg;
    cont.innerHTML = `
        <div class="ys-card">
            <div class="ys-label">Total Ulasan ${year}</div>
            <div class="ys-value" style="color:var(--ink)">${fmt(total)}</div>
            <div class="ys-bar"><div class="ys-bar-fill" style="width:100%;background:var(--ink)"></div></div>
        </div>
        <div class="ys-card">
            <div class="ys-label">Positif ${year}</div>
            <div class="ys-value" style="color:var(--green)">${fmt(pos)} <span style="font-size:13px;font-weight:500">(${yearlyData.pct_positif[idx]}%)</span></div>
            <div class="ys-bar"><div class="ys-bar-fill" style="width:${yearlyData.pct_positif[idx]}%;background:var(--green)"></div></div>
        </div>
        <div class="ys-card">
            <div class="ys-label">Negatif ${year}</div>
            <div class="ys-value" style="color:var(--red)">${fmt(neg)} <span style="font-size:13px;font-weight:500">(${yearlyData.pct_negatif[idx]}%)</span></div>
            <div class="ys-bar"><div class="ys-bar-fill" style="width:${yearlyData.pct_negatif[idx]}%;background:var(--red)"></div></div>
        </div>`;
}

function showYearlyOverview() {
    setActivePill('all');
    activeYear = 'all';
    renderYearlySummary('all');

    document.getElementById('yearlyOverviewWrap').style.display = '';
    document.getElementById('yearlyDetailWrap').style.display   = 'none';

    if (yearlyOverviewChartInst) { yearlyOverviewChartInst.destroy(); }

    yearlyOverviewChartInst = new Chart(document.getElementById('yearlyOverviewChart'), {
        type: 'bar',
        data: {
            labels: yearlyData.labels,
            datasets: [
                {
                    label: 'Positif',
                    data: yearlyData.positif,
                    backgroundColor: 'rgba(15,169,88,.85)',
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Negatif',
                    data: yearlyData.negatif,
                    backgroundColor: 'rgba(232,0,29,.8)',
                    borderRadius: 6,
                    borderSkipped: false,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index' },
            plugins: {
                legend: { position: 'top', labels: { usePointStyle: true, padding: 16 } },
                tooltip: {
                    callbacks: {
                        afterBody: (items) => {
                            const total = items.reduce((s, i) => s + i.raw, 0);
                            return [`Total: ${fmt(total)}`];
                        }
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#E4E6ED' }, ticks: { callback: v => fmt(v) } },
                x: { grid: { display: false } }
            }
        }
    });
}

function showYearlyDetail(year) {
    setActivePill(year);
    activeYear = year;
    renderYearlySummary(year);

    fetch(`/api/charts/yearly/${year}`).then(r => r.json()).then(d => {
        document.getElementById('yearlyOverviewWrap').style.display = 'none';
        document.getElementById('yearlyDetailWrap').style.display   = '';

        if (yearlyDetailChartInst) { yearlyDetailChartInst.destroy(); }

        yearlyDetailChartInst = new Chart(document.getElementById('yearlyDetailChart'), {
            type: 'bar',
            data: {
                labels: d.labels,
                datasets: [
                    {
                        label: `Positif ${year}`,
                        data: d.positif,
                        backgroundColor: 'rgba(15,169,88,.85)',
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                    {
                        label: `Negatif ${year}`,
                        data: d.negatif,
                        backgroundColor: 'rgba(232,0,29,.8)',
                        borderRadius: 6,
                        borderSkipped: false,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index' },
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true, padding: 16 } },
                    title: {
                        display: true,
                        text: `Breakdown Bulanan — Tahun ${year}`,
                        font: { size: 13, weight: '600' },
                        color: '#0E1117',
                        padding: { bottom: 12 },
                    }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#E4E6ED' }, ticks: { callback: v => fmt(v) } },
                    x: { grid: { display: false } }
                }
            }
        });
    });
}

// ================================================================
// WORD CLOUD
// ================================================================
let wcActive = 'positif';

function loadWordCloud(sentiment) {
    wcActive = sentiment;
    document.getElementById('wcTabPos').className = 'wc-tab' + (sentiment === 'positif' ? ' active-pos' : '');
    document.getElementById('wcTabNeg').className = 'wc-tab' + (sentiment === 'negatif' ? ' active-neg' : '');

    fetch(`/api/wordcloud/${sentiment}`).then(r => r.json()).then(data => {
        const canvas = document.getElementById('wordCloudCanvas');
        const ctx    = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        canvas.width  = canvas.offsetWidth;
        canvas.height = 300;

        WordCloud(canvas, {
            list: data,
            gridSize: Math.round(14 * canvas.width / 1024),
            weightFactor: sentiment === 'positif' ? 0.38 : 0.42,
            fontFamily: 'Inter, sans-serif',
            color: (word, weight) => sentiment === 'positif'
                ? (weight > 200 ? '#0FA958' : '#20C997')
                : (weight > 200 ? '#E8001D' : '#E65C00'),
            backgroundColor: '#F5F6FA',
            rotateRatio: 0.25,
        });
    });
}

window.addEventListener('load', () => loadWordCloud('positif'));

// ================================================================
// PREDIKSI
// ================================================================
const TEMPLATES = {
    positif: [
        "Aplikasi sangat membantu buat cek poin dan tukar voucher.",
        "Mantap, scan barcode cepat banget pas antri di SPBU.",
        "Untuk pertama kali pakai, tetap bintang 5!",
        "Sering dapet promo cashback pakai aplikasi ini.",
        "Sangat memudahkan tanpa harus bawa uang cash.",
        "Fitur pembayaran digital sangat praktis dan aman.",
    ],
    negatif: [
        "ribet banget dah, bingung saya cara mau daftar",
        "Aplikasi sering error force close sendiri pas mau bayar.",
        "Loadingnya lama banget, bikin antrian panjang di pom.",
        "Susah login padahal password dan nomor sudah benar.",
        "Gagal terus pas mau isi saldo, sudah coba berkali-kali.",
        "Bug di halaman utama, tampilan berantakan sejak update.",
    ]
};

let tplTexts = ['', '', '', ''];

function refreshTpl() {
    const sp = [...TEMPLATES.positif].sort(() => Math.random() - .5);
    const sn = [...TEMPLATES.negatif].sort(() => Math.random() - .5);
    tplTexts = [sp[0], sp[1], sn[0], sn[1]];
    const short = t => t.length > 22 ? t.slice(0, 22) + '…' : t;
    [0, 1, 2, 3].forEach(i => {
        const el = document.getElementById(`tpl${i}`);
        el.textContent = `"${short(tplTexts[i])}"`;
        el.title = tplTexts[i];
    });
}

function setTpl(i) {
    document.getElementById('inputText').value = tplTexts[i];
    document.getElementById('predResult').style.display = 'none';
    predictSentiment();
}

function setTemplate(t) {
    document.getElementById('inputText').value = t;
    document.getElementById('predResult').style.display = 'none';
}

refreshTpl();

function predictSentiment() {
    const text = document.getElementById('inputText').value.trim();
    if (!text) return;

    const btn = document.getElementById('btnPredict');
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Memproses…';
    btn.disabled  = true;

    fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    })
    .then(async r => {
        if (!r.ok) {
            const err = await r.text();
            console.error("Server Error:", err);
            throw new Error(err);
        }
        return r.json();
    })
    .then(data => {
        if (data.error) {
            alert("Error dari server: " + data.error);
            return;
        }

        const isPos = data.sentiment === 'Positif';
        const isNeg = data.sentiment === 'Negatif';

        const box    = document.getElementById('predResult');
        const header = document.getElementById('resultHeader');
        const sent   = document.getElementById('resSentiment');
        const conf   = document.getElementById('resConf');

        box.style.display = 'block';
        box.className     = 'result-box' + (isPos ? ' pos' : isNeg ? ' neg' : '');
        header.className  = 'result-header' + (isPos ? ' pos' : isNeg ? ' neg' : '');

        sent.innerHTML = isPos
            ? `<i class="bi bi-emoji-smile-fill"></i> Positif`
            : isNeg
            ? `<i class="bi bi-emoji-frown-fill"></i> Negatif`
            : `<i class="bi bi-question-circle"></i> ${data.sentiment}`;
        sent.className = 'result-sentiment' + (isPos ? ' pos' : isNeg ? ' neg' : '');

        conf.textContent = data.confidence + '%';
        conf.className   = 'result-conf' + (isPos ? ' pos' : isNeg ? ' neg' : '');

        document.getElementById('resModel').textContent   = data.model_type;
        document.getElementById('resWcOrig').textContent  = data.word_count_orig;
        document.getElementById('resWcClean').textContent = data.word_count_clean;
        document.getElementById('resClean').textContent   = data.processed_text || '(teks kosong setelah preprocessing)';

        box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    })
    .catch(err => {
        alert('Terjadi kesalahan saat memproses data. Silakan cek terminal Flask.');
        console.error(err);
    })
    .finally(() => {
        btn.innerHTML = '<i class="bi bi-lightning-fill"></i> Prediksi Sekarang';
        btn.disabled  = false;
    });
}

// Enter + Ctrl untuk prediksi
document.getElementById('inputText').addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.ctrlKey) predictSentiment();
});
