"""HTML UI for the IDS Global API.

Single-page app served at GET /. It calls POST /predict (multipart) which
returns JSON. All CSS/JS is inlined so the UI works behind ngrok with no
extra static-file routing.

Server-side templating uses simple ``str.replace`` instead of Jinja2 so we
don't need an extra dependency.
"""

from __future__ import annotations

from typing import List


def render_index(
    model_options: List[str],
    feature_count: int,
    feature_preview: List[str],
    class_names: List[str],
) -> str:
    """Build the HTML page with server-side data baked in."""

    options_html = "\n".join(
        f'              <option value="{m}">{m}</option>' for m in model_options
    ) or '              <option value="" disabled>No models found</option>'

    classes_html = "".join(
        f'<span class="class-chip class-{i}">{name}</span>'
        for i, name in enumerate(class_names)
    )

    preview_html = ", ".join(feature_preview[:8])
    if len(feature_preview) > 8:
        preview_html += ", &hellip;"

    return _PAGE.replace("{{OPTIONS}}", options_html) \
        .replace("{{FEATURE_COUNT}}", str(feature_count)) \
        .replace("{{FEATURE_PREVIEW}}", preview_html) \
        .replace("{{CLASS_CHIPS}}", classes_html) \
        .replace("{{CLASS_NAMES_JSON}}", _json_dumps(class_names)) \
        .replace("{{FEATURE_COLS_JSON}}", _json_dumps(feature_preview))


def _json_dumps(value) -> str:
    import json

    return json.dumps(value)


_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>IDS Model Tester</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>&#128737;</text></svg>" />
  <style>
    :root {
      --primary: #4f46e5;
      --primary-hover: #4338ca;
      --primary-soft: #eef2ff;
      --bg-start: #e0e7ff;
      --bg-end: #fae8ff;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --border: #c7d2fe;
      --border-light: #e2e8f0;
      --text: #1e293b;
      --text-light: #64748b;
      --text-mute: #94a3b8;
      --radius: 14px;
      --radius-sm: 8px;
      --shadow: 0 10px 25px -5px rgba(79,70,229,.15), 0 8px 10px -6px rgba(79,70,229,.1);

      --c-benign: #10b981;
      --c-bot:    #f97316;
      --c-ddos:   #ef4444;
      --c-dos:    #f43f5e;
      --c-prob:   #eab308;
      --c-other:  #6366f1;
    }

    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      padding: 32px 20px 80px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: linear-gradient(135deg, var(--bg-start) 0%, var(--bg-end) 100%);
      color: var(--text);
      line-height: 1.5;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      background: var(--surface);
      padding: 36px;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      border-top: 5px solid var(--primary);
    }

    header { text-align: center; margin-bottom: 28px; }
    h1 {
      margin: 0 0 6px;
      font-size: 1.9rem;
      font-weight: 700;
      color: var(--primary);
      letter-spacing: -0.02em;
    }
    .subtitle { color: var(--text-light); font-size: .98rem; }
    .class-row { margin-top: 14px; display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; }
    .class-chip {
      font-size: .72rem;
      padding: 3px 10px;
      border-radius: 999px;
      background: var(--primary-soft);
      color: var(--primary);
      font-weight: 600;
      letter-spacing: .03em;
    }
    .class-chip.class-0 { background: #d1fae5; color: #065f46; }
    .class-chip.class-1 { background: #fed7aa; color: #9a3412; }
    .class-chip.class-2 { background: #fee2e2; color: #991b1b; }
    .class-chip.class-3 { background: #ffe4e6; color: #9f1239; }
    .class-chip.class-4 { background: #fef3c7; color: #92400e; }

    .layout-grid {
      display: grid;
      grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
      gap: 32px;
    }
    @media (max-width: 880px) {
      .layout-grid { grid-template-columns: 1fr; }
      .container { padding: 24px; }
    }

    section.card {
      background: var(--surface-soft);
      padding: 22px;
      border-radius: var(--radius);
      border: 1px solid var(--border-light);
    }
    section.card h2 {
      margin: 0 0 16px;
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    section.card h2 .badge {
      font-size: .68rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--primary);
      color: #fff;
      letter-spacing: .04em;
    }

    .form-group { margin-bottom: 18px; }
    label {
      display: block;
      font-weight: 600;
      margin-bottom: 6px;
      font-size: .92rem;
    }

    select, textarea {
      width: 100%;
      padding: 11px 12px;
      border: 2px solid var(--border);
      border-radius: var(--radius-sm);
      background: #fff;
      font-family: inherit;
      font-size: .94rem;
      color: var(--text);
      transition: border-color .15s, box-shadow .15s;
    }
    select:focus, textarea:focus, .file-drop:focus-within {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(79,70,229,.15);
    }
    textarea { resize: vertical; min-height: 110px; font-family: ui-monospace, "Cascadia Mono", Menlo, Consolas, monospace; font-size: .88rem; }

    .file-drop {
      position: relative;
      border: 2px dashed var(--border);
      border-radius: var(--radius-sm);
      padding: 22px 16px;
      text-align: center;
      background: #fff;
      transition: border-color .15s, background .15s;
      cursor: pointer;
    }
    .file-drop:hover, .file-drop.drag { border-color: var(--primary); background: var(--primary-soft); }
    .file-drop input[type=file] {
      position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
    }
    .file-drop .file-icon { font-size: 1.6rem; }
    .file-drop .file-text { font-weight: 600; color: var(--text); margin-top: 4px; }
    .file-drop .file-hint { font-size: .8rem; color: var(--text-light); margin-top: 2px; }
    .file-drop.has-file { border-style: solid; border-color: var(--primary); background: var(--primary-soft); }
    .file-drop.has-file .file-text { color: var(--primary); }

    .divider {
      display: flex; align-items: center; text-align: center;
      margin: 18px 0; color: var(--text-mute);
      font-size: .78rem; font-weight: 700; letter-spacing: .12em;
    }
    .divider::before, .divider::after {
      content: ''; flex: 1; border-bottom: 1px dashed var(--border);
    }
    .divider:not(:empty)::before { margin-right: 14px; }
    .divider:not(:empty)::after  { margin-left: 14px; }

    .hint {
      font-size: .82rem;
      color: var(--text-light);
      margin-top: 8px;
      background: #fff;
      padding: 10px 12px;
      border-radius: var(--radius-sm);
      border-left: 3px solid var(--primary);
    }
    code {
      background: #e2e8f0;
      padding: 1px 6px;
      border-radius: 4px;
      color: #be185d;
      font-weight: 600;
      font-family: ui-monospace, "Cascadia Mono", Menlo, Consolas, monospace;
      font-size: .82rem;
    }

    .btn-row { display: flex; gap: 10px; margin-top: 6px; }
    button {
      flex: 1;
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 13px 20px;
      font-size: 1rem;
      font-weight: 600;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: background .15s, transform .05s;
    }
    button:hover:not(:disabled) { background: var(--primary-hover); }
    button:active:not(:disabled) { transform: translateY(1px); }
    button:disabled { background: var(--text-mute); cursor: not-allowed; }
    button.btn-ghost {
      flex: 0 0 auto;
      background: transparent;
      color: var(--text-light);
      border: 2px solid var(--border-light);
      padding: 11px 16px;
    }
    button.btn-ghost:hover:not(:disabled) { background: var(--surface-soft); border-color: var(--primary); color: var(--primary); }

    /* ---------- Results ---------- */
    #results { min-height: 320px; display: flex; flex-direction: column; gap: 14px; }
    .placeholder {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: var(--text-light);
      text-align: center;
      padding: 30px 20px;
      border: 2px dashed var(--border-light);
      border-radius: var(--radius);
      background: #fff;
    }
    .placeholder .ph-icon { font-size: 2.6rem; margin-bottom: 10px; }
    .placeholder h3 { margin: 0 0 6px; color: var(--text); font-size: 1.05rem; }
    .placeholder p  { margin: 0; font-size: .92rem; }

    .spinner {
      display: inline-block; width: 38px; height: 38px;
      border: 4px solid var(--primary-soft);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin .9s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .error {
      background: #fef2f2;
      border-left: 4px solid #dc2626;
      color: #991b1b;
      padding: 14px 16px;
      border-radius: var(--radius-sm);
      font-size: .92rem;
    }
    .error strong { color: #7f1d1d; }
    .error pre { margin: 8px 0 0; font-size: .8rem; color: #991b1b; white-space: pre-wrap; }

    .pred-card {
      background: #fff;
      border: 1px solid var(--border-light);
      border-radius: var(--radius);
      padding: 20px;
    }
    .pred-card .pred-head {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      margin-bottom: 14px;
    }
    .pred-card .pred-title {
      font-size: .82rem; color: var(--text-light); font-weight: 600;
      text-transform: uppercase; letter-spacing: .08em;
    }
    .pred-badge {
      display: inline-block;
      padding: 6px 14px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 1rem;
      color: #fff;
      background: var(--c-other);
    }
    .pred-badge.c-Benign { background: var(--c-benign); }
    .pred-badge.c-Bot    { background: var(--c-bot); }
    .pred-badge.c-DDoS   { background: var(--c-ddos); }
    .pred-badge.c-Dos    { background: var(--c-dos); }
    .pred-badge.c-Prob   { background: var(--c-prob); color: #1e293b; }

    .conf-line {
      display: flex; align-items: center; justify-content: space-between;
      font-size: .9rem; margin-bottom: 6px;
    }
    .conf-line .conf-val { font-weight: 700; color: var(--text); }
    .conf-bar {
      height: 8px; background: var(--surface-soft); border-radius: 999px; overflow: hidden;
      border: 1px solid var(--border-light);
    }
    .conf-fill {
      height: 100%; background: linear-gradient(90deg, var(--primary), #a855f7);
      transition: width .4s ease;
    }
    .pred-card.bg-Benign .conf-fill { background: linear-gradient(90deg, var(--c-benign), #34d399); }
    .pred-card.bg-Bot    .conf-fill { background: linear-gradient(90deg, var(--c-bot),    #fb923c); }
    .pred-card.bg-DDoS   .conf-fill { background: linear-gradient(90deg, var(--c-ddos),   #f87171); }
    .pred-card.bg-Dos    .conf-fill { background: linear-gradient(90deg, var(--c-dos),    #fb7185); }
    .pred-card.bg-Prob   .conf-fill { background: linear-gradient(90deg, var(--c-prob),   #fde047); }

    .topk { margin-top: 16px; }
    .topk h4 {
      margin: 0 0 8px;
      font-size: .8rem; color: var(--text-light); font-weight: 700;
      letter-spacing: .08em; text-transform: uppercase;
    }
    .topk-row {
      display: grid; grid-template-columns: 22px 1fr 60px;
      align-items: center; gap: 10px;
      font-size: .88rem; padding: 4px 0;
    }
    .topk-row .rank { color: var(--text-mute); font-weight: 700; font-size: .78rem; text-align: right; }
    .topk-bar { background: var(--surface-soft); height: 8px; border-radius: 999px; overflow: hidden; border: 1px solid var(--border-light); }
    .topk-fill { height: 100%; background: var(--primary); }
    .topk-row .pct { font-variant-numeric: tabular-nums; color: var(--text); font-weight: 600; text-align: right; }

    .topk-row .label-wrap { display: flex; align-items: center; gap: 8px; }
    .topk-row .label-name { font-weight: 600; color: var(--text); }

    /* ---------- Batch results ---------- */
    .batch-summary {
      background: #fff;
      border: 1px solid var(--border-light);
      border-radius: var(--radius);
      padding: 18px;
    }
    .batch-summary h3 { margin: 0 0 12px; font-size: 1rem; }
    .summary-row {
      display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;
    }
    .summary-pill {
      flex: 1 1 100px;
      background: var(--surface-soft);
      border-radius: var(--radius-sm);
      padding: 10px 12px;
      border: 1px solid var(--border-light);
    }
    .summary-pill .name { font-size: .72rem; color: var(--text-light); text-transform: uppercase; letter-spacing: .06em; font-weight: 700; }
    .summary-pill .count { font-size: 1.4rem; font-weight: 700; }
    .summary-pill.c-Benign { background: #ecfdf5; border-color: #a7f3d0; }
    .summary-pill.c-Benign .count { color: var(--c-benign); }
    .summary-pill.c-Bot    { background: #fff7ed; border-color: #fed7aa; }
    .summary-pill.c-Bot    .count { color: var(--c-bot); }
    .summary-pill.c-DDoS   { background: #fef2f2; border-color: #fecaca; }
    .summary-pill.c-DDoS   .count { color: var(--c-ddos); }
    .summary-pill.c-Dos    { background: #fff1f2; border-color: #fecdd3; }
    .summary-pill.c-Dos    .count { color: var(--c-dos); }
    .summary-pill.c-Prob   { background: #fefce8; border-color: #fde68a; }
    .summary-pill.c-Prob   .count { color: var(--c-prob); }

    .stack-bar {
      display: flex; height: 12px; border-radius: 999px; overflow: hidden;
      border: 1px solid var(--border-light); background: var(--surface-soft);
    }
    .stack-seg { height: 100%; }
    .stack-seg.c-Benign { background: var(--c-benign); }
    .stack-seg.c-Bot    { background: var(--c-bot); }
    .stack-seg.c-DDoS   { background: var(--c-ddos); }
    .stack-seg.c-Dos    { background: var(--c-dos); }
    .stack-seg.c-Prob   { background: var(--c-prob); }

    .table-wrap {
      max-height: 360px; overflow: auto;
      border: 1px solid var(--border-light); border-radius: var(--radius-sm);
      background: #fff;
    }
    table.batch {
      width: 100%; border-collapse: collapse; font-size: .86rem;
    }
    table.batch th, table.batch td {
      padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border-light);
      font-variant-numeric: tabular-nums;
    }
    table.batch th {
      background: var(--surface-soft);
      font-weight: 700; color: var(--text-light);
      text-transform: uppercase; font-size: .72rem; letter-spacing: .06em;
      position: sticky; top: 0;
    }
    table.batch tr:last-child td { border-bottom: none; }
    table.batch td.idx { color: var(--text-mute); width: 60px; }
    table.batch td .mini-bar {
      display: inline-block; width: 60px; height: 6px;
      background: var(--surface-soft); border-radius: 999px; overflow: hidden;
      vertical-align: middle; margin-left: 8px; border: 1px solid var(--border-light);
    }
    table.batch td .mini-fill { height: 100%; background: var(--primary); }
    table.batch td .row-badge {
      display: inline-block; padding: 2px 10px; border-radius: 999px;
      font-size: .78rem; font-weight: 600; color: #fff; background: var(--c-other);
    }
    table.batch td .row-badge.c-Benign { background: var(--c-benign); }
    table.batch td .row-badge.c-Bot    { background: var(--c-bot); }
    table.batch td .row-badge.c-DDoS   { background: var(--c-ddos); }
    table.batch td .row-badge.c-Dos    { background: var(--c-dos); }
    table.batch td .row-badge.c-Prob   { background: var(--c-prob); color: #1e293b; }

    footer.meta {
      margin-top: 28px;
      text-align: center;
      color: var(--text-light);
      font-size: .82rem;
    }
    footer.meta a { color: var(--primary); text-decoration: none; }
    footer.meta a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Intrusion Detection System</h1>
      <div class="subtitle">SDN-IoT network flow classifier &middot; choose a model, paste features or upload a CSV.</div>
      <div class="class-row">{{CLASS_CHIPS}}</div>
    </header>

    <div class="layout-grid">
      <!-- ================= INPUT ================= -->
      <section class="card">
        <h2>Input <span class="badge">Step 1</span></h2>

        <div class="form-group">
          <label for="model">Model</label>
          <select id="model">
{{OPTIONS}}
          </select>
        </div>

        <div class="form-group">
          <label>Upload CSV</label>
          <div class="file-drop" id="drop">
            <input type="file" id="csvfile" accept=".csv,text/csv" />
            <div class="file-icon">&#128206;</div>
            <div class="file-text" id="file-text">Drop a CSV here or click to browse</div>
            <div class="file-hint" id="file-hint">Must contain the {{FEATURE_COUNT}} feature columns. Up to 200 rows.</div>
          </div>
        </div>

        <div class="divider">or paste</div>

        <div class="form-group">
          <label for="features">Comma-separated feature values</label>
          <textarea id="features" placeholder="0.0, 1.2, 3.4, ... ({{FEATURE_COUNT}} numbers, in the same order the model was trained on)"></textarea>
          <div class="hint">
            Need exactly <code>{{FEATURE_COUNT}}</code> numbers, in this order:<br/>
            <code>{{FEATURE_PREVIEW}}</code>
          </div>
        </div>

        <div class="btn-row">
          <button id="btn-predict" type="button">Run Prediction</button>
          <button id="btn-clear" type="button" class="btn-ghost" title="Clear inputs and results">Reset</button>
        </div>
      </section>

      <!-- ================= RESULTS ================= -->
      <section class="card">
        <h2>Results <span class="badge">Step 2</span></h2>
        <div id="results">
          <div class="placeholder">
            <div class="ph-icon">&#129504;</div>
            <h3>Awaiting input</h3>
            <p>Pick a model, then upload a CSV or paste feature values to see the prediction.</p>
          </div>
        </div>
      </section>
    </div>

    <footer class="meta">
      <a href="/docs" target="_blank" rel="noopener">API Docs</a>
      &middot; <a href="/models" target="_blank" rel="noopener">Models JSON</a>
    </footer>
  </div>

  <script>
    const CLASS_NAMES = {{CLASS_NAMES_JSON}};
    const FEATURE_COLS = {{FEATURE_COLS_JSON}};
    const $ = (id) => document.getElementById(id);

    function fmtPct(p) {
      if (typeof p !== 'number' || Number.isNaN(p)) return '-';
      return (p * 100).toFixed(2) + '%';
    }
    function classOf(label) {
      return label && CLASS_NAMES.includes(label) ? label : 'other';
    }
    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[c]));
    }

    // ---------- File drag/drop ----------
    const drop = $('drop');
    const fileInput = $('csvfile');
    const fileText = $('file-text');
    const fileHint = $('file-hint');

    fileInput.addEventListener('change', () => updateFileLabel());
    ['dragenter', 'dragover'].forEach(ev =>
      drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach(ev =>
      drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('drag'); }));
    drop.addEventListener('drop', (e) => {
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) {
        const dt = new DataTransfer(); dt.items.add(f); fileInput.files = dt.files;
        updateFileLabel();
      }
    });
    function updateFileLabel() {
      const f = fileInput.files[0];
      if (f) {
        drop.classList.add('has-file');
        fileText.innerHTML = '&#128196; ' + escapeHtml(f.name);
        fileHint.textContent = (f.size / 1024).toFixed(1) + ' KB - ready';
      } else {
        drop.classList.remove('has-file');
        fileText.textContent = 'Drop a CSV here or click to browse';
        fileHint.textContent = 'Must contain the ' + FEATURE_COLS.length + ' feature columns. Up to 200 rows.';
      }
    }

    // ---------- Reset ----------
    $('btn-clear').addEventListener('click', () => {
      fileInput.value = '';
      updateFileLabel();
      $('features').value = '';
      $('results').innerHTML = `
        <div class="placeholder">
          <div class="ph-icon">&#129504;</div>
          <h3>Awaiting input</h3>
          <p>Pick a model, then upload a CSV or paste feature values to see the prediction.</p>
        </div>`;
    });

    // ---------- Prediction ----------
    $('btn-predict').addEventListener('click', runPrediction);

    function setLoading() {
      $('results').innerHTML = `
        <div class="placeholder">
          <div class="spinner"></div>
          <h3 style="margin-top:14px;">Running prediction...</h3>
          <p>The first call after server start can take a moment as the model loads into memory.</p>
        </div>`;
    }
    function setError(msg, detail) {
      const detailHtml = detail ? `<pre>${escapeHtml(JSON.stringify(detail, null, 2))}</pre>` : '';
      $('results').innerHTML = `<div class="error"><strong>Error:</strong> ${escapeHtml(msg)}${detailHtml}</div>`;
    }

    async function runPrediction() {
      const btn = $('btn-predict');
      const model = $('model').value;
      const file = fileInput.files[0];
      const features = $('features').value.trim();

      if (!model) { setError('No model selected.'); return; }
      if (!file && !features) {
        setError('Provide either a CSV file or comma-separated feature values.');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Predicting...';
      setLoading();

      const form = new FormData();
      form.append('model_id', model);
      form.append('top_k', '5');
      if (file) form.append('file', file);
      else      form.append('features', features);

      try {
        const resp = await fetch('/predict', { method: 'POST', body: form });
        const data = await resp.json();
        if (!resp.ok) {
          setError(data.detail?.message || data.detail || data.error || 'Prediction failed.', data);
          return;
        }
        renderResult(data);
      } catch (e) {
        setError('Network error: ' + (e.message || e));
      } finally {
        btn.disabled = false;
        btn.textContent = 'Run Prediction';
      }
    }

    // ---------- Renderers ----------
    function renderResult(data) {
      const preds = data.predictions || [];
      if (preds.length === 0) {
        setError('No predictions returned.');
        return;
      }
      if (preds.length === 1) {
        $('results').innerHTML = renderSingle(preds[0], data.model_id);
      } else {
        $('results').innerHTML = renderBatch(preds, data.model_id, data.num_rows);
      }
    }

    function renderSingle(p, modelId) {
      const label = p.pred_label || (p.pred_class_id != null ? ('Class ' + p.pred_class_id) : 'Unknown');
      const cls   = classOf(label);
      const probs = p.proba || [];
      const top   = (p.top_k && p.top_k.length ? p.top_k :
                     probs.map((v, i) => ({ index: i, label: CLASS_NAMES[i] || ('Class ' + i), prob: v }))
                          .sort((a, b) => b.prob - a.prob).slice(0, 5));
      const conf  = top[0] ? top[0].prob : 0;

      const topkHtml = top.map((t, i) => {
        const rowCls = classOf(t.label);
        return `
          <div class="topk-row">
            <span class="rank">#${i + 1}</span>
            <div>
              <div class="label-wrap">
                <span class="row-badge c-${escapeHtml(rowCls)}">${escapeHtml(t.label || '?')}</span>
              </div>
              <div class="topk-bar" style="margin-top:6px;">
                <div class="topk-fill" style="width:${(t.prob * 100).toFixed(1)}%"></div>
              </div>
            </div>
            <span class="pct">${fmtPct(t.prob)}</span>
          </div>`;
      }).join('');

      return `
        <div class="pred-card bg-${escapeHtml(cls)}">
          <div class="pred-head">
            <div>
              <div class="pred-title">Prediction</div>
              <div style="margin-top:4px;"><span class="pred-badge c-${escapeHtml(cls)}">${escapeHtml(label)}</span></div>
            </div>
            <div style="text-align:right; font-size:.8rem; color:var(--text-light);">
              <div>model</div>
              <div style="font-weight:600; color:var(--text); word-break:break-all;">${escapeHtml(modelId || '-')}</div>
            </div>
          </div>
          <div class="conf-line">
            <span>Confidence</span>
            <span class="conf-val">${fmtPct(conf)}</span>
          </div>
          <div class="conf-bar"><div class="conf-fill" style="width:${(conf * 100).toFixed(1)}%"></div></div>
          <div class="topk">
            <h4>Top ${top.length}</h4>
            ${topkHtml}
          </div>
        </div>`;
    }

    function renderBatch(preds, modelId, numRows) {
      const counts = {};
      CLASS_NAMES.forEach(c => counts[c] = 0);
      preds.forEach(p => {
        const lbl = p.pred_label || ('Class ' + p.pred_class_id);
        counts[lbl] = (counts[lbl] || 0) + 1;
      });

      const total = preds.length;
      const pillsHtml = Object.entries(counts).map(([name, n]) => `
        <div class="summary-pill c-${escapeHtml(classOf(name))}">
          <div class="name">${escapeHtml(name)}</div>
          <div class="count">${n}</div>
        </div>`).join('');

      const stackHtml = Object.entries(counts).filter(([, n]) => n > 0).map(([name, n]) => {
        const w = (n / total) * 100;
        return `<div class="stack-seg c-${escapeHtml(classOf(name))}" style="width:${w}%" title="${escapeHtml(name)}: ${n}"></div>`;
      }).join('');

      const rowsHtml = preds.slice(0, 200).map((p, i) => {
        const lbl = p.pred_label || ('Class ' + p.pred_class_id);
        const cls = classOf(lbl);
        const probs = p.proba || [];
        const conf  = probs.length ? Math.max.apply(null, probs) : 0;
        return `
          <tr>
            <td class="idx">${i + 1}</td>
            <td><span class="row-badge c-${escapeHtml(cls)}">${escapeHtml(lbl)}</span></td>
            <td>${fmtPct(conf)}<span class="mini-bar"><span class="mini-fill" style="width:${(conf * 100).toFixed(1)}%"></span></span></td>
          </tr>`;
      }).join('');

      const moreNote = preds.length > 200
        ? `<tr><td colspan="3" style="text-align:center; color:var(--text-light); font-style:italic;">... ${preds.length - 200} more rows hidden</td></tr>`
        : '';

      return `
        <div class="batch-summary">
          <h3>Batch summary &middot; ${total} ${total === 1 ? 'row' : 'rows'} &middot; <span style="color:var(--text-light); font-weight:400;">${escapeHtml(modelId || '-')}</span></h3>
          <div class="summary-row">${pillsHtml}</div>
          <div class="stack-bar">${stackHtml}</div>
        </div>
        <div class="table-wrap">
          <table class="batch">
            <thead><tr><th>#</th><th>Predicted class</th><th>Confidence</th></tr></thead>
            <tbody>${rowsHtml}${moreNote}</tbody>
          </table>
        </div>`;
    }
  </script>
</body>
</html>
"""
