'use strict';
const $ = (s) => document.querySelector(s);
const escapeHTML = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json = (v) => escapeHTML(JSON.stringify(v, null, 2));
const badge = (v) => `<span class="badge ${escapeHTML(v.toLowerCase().replaceAll(' ', '-'))}">${escapeHTML(v)}</span>`;
const money = (t) => t.amount == null ? 'Unknown amount' : `${Number(t.amount).toLocaleString(undefined, {maximumFractionDigits: 2})} ${t.currency || '?'}`;
const date = (v) => new Date(v).toLocaleString();
let samples = [], activeReport = null, historyOffset = 0;
const historyLimit = 20;
async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    let message = data.detail || 'Request failed';
    if (Array.isArray(message)) message = message.map(d => `${d.loc.slice(1).join('.')}: ${d.msg}`).join('; ');
    throw new Error(message);
  }
  return data;
}
function showError(error) {
  $('#alert').textContent = error.message || String(error);
  $('#alert').classList.remove('hidden');
}
function clearError() { $('#alert').classList.add('hidden'); }
function go() {
  const page = location.hash.slice(1) || 'dashboard';
  const valid = ['dashboard','details','policies','history'].includes(page) ? page : 'dashboard';
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('hidden', p.id !== valid));
  document.querySelectorAll('[data-nav]').forEach(p => p.classList.toggle('active', p.dataset.nav === valid));
  $('#breadcrumb').textContent = ({dashboard:'Dashboard', details:'Verification details', policies:'Policy knowledge base', history:'Audit history'})[valid];
  clearError();
  if (valid === 'history') loadHistory().catch(showError);
  if (valid === 'policies') loadPolicies().catch(showError);
}
window.addEventListener('hashchange', go);
async function refreshStatus() {
  const s = await api('/api/system/status');
  const stats = s.statistics;
  $('#stat-total').textContent = Object.values(stats).reduce((a,b) => a+b, 0);
  $('#stat-pass').textContent = stats.PASS || 0;
  $('#stat-flag').textContent = stats.FLAGGED || 0;
  $('#stat-review').textContent = (stats['NEEDS INFORMATION'] || 0) + (stats['REVIEW REQUIRED'] || 0);
  $('#system-status').innerHTML = `<div class="system-row"><span>Database</span><strong>${escapeHTML(s.database)}</strong></div><div class="system-row"><span>Orchestration</span><strong>${s.llm_configured ? 'LLM configured' : 'Workflow Mode'}</strong></div><div class="system-row"><span>Retrieval</span><strong>${escapeHTML(s.retrieval_mode)}</strong></div><div class="system-row"><span>Knowledge base</span><strong>${s.policy_count} policies · ${s.chunk_count} chunks</strong></div><div class="system-note">${escapeHTML(s.retrieval_warning || 'Local semantic model operational. Vectors cached on disk.')}${!s.llm_configured ? '<br>No LLM key required for deterministic verification.' : `<br>${escapeHTML(s.llm_status)}`}</div>`;
}
function populate(sample) {
  const form = $('#transaction-form');
  form.reset();
  for (const [key, value] of Object.entries(sample)) {
    if (key === 'documents') {
      form.querySelectorAll('[name="document"]').forEach(input => { input.checked = (value || []).includes(input.value); input.disabled = value === null; });
      $('#documents-unknown').checked = value === null;
    } else if (form.elements.namedItem(key)) form.elements.namedItem(key).value = value == null ? '' : String(value);
  }
}
$('#sample').addEventListener('change', () => {
  const sample = samples.find(s => s.id === $('#sample').value);
  if (sample) populate(sample.transaction);
});
$('#documents-unknown').addEventListener('change', () => {
  document.querySelectorAll('[name="document"]').forEach(c => { c.disabled = $('#documents-unknown').checked; });
});
$('#transaction-form').addEventListener('submit', async (event) => {
  event.preventDefault(); clearError();
  const form = new FormData(event.target), transaction = {};
  for (const key of ['sender_name','recipient_name','sender_country','recipient_country','amount','currency','purpose','sender_kyc','recipient_verified','customer_type']) {
    const value = form.get(key);
    transaction[key] = value === '' ? null : ['sender_kyc','recipient_verified'].includes(key) ? value === 'true' : value;
  }
  transaction.documents = $('#documents-unknown').checked ? null : form.getAll('document');
  $('#verify-button').disabled = true;
  $('#verify-button').textContent = 'Investigating…';
  $('#verify-progress').classList.remove('hidden');
  try {
    const report = await api('/api/transactions/verify', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(transaction)});
    renderReport(report); location.hash = 'details';
    await refreshStatus(); window.scrollTo({top:0, behavior:'smooth'});
  } catch (error) { showError(error); }
  finally { $('#verify-button').disabled = false; $('#verify-button').innerHTML = 'Verify Transaction <span>→</span>'; $('#verify-progress').classList.add('hidden'); }
});
function condition(c) {
  if (!c) return 'Always';
  if (c.all) return c.all.map(condition).join(' AND ');
  if (c.any) return c.any.map(condition).join(' OR ');
  if (c.not) return `NOT (${condition(c.not)})`;
  const op = ({eq:'=',ne:'≠',gt:'>',gte:'≥',lt:'<',lte:'≤',in:'is one of',not_in:'is not one of',contains_all:'includes',known:'is known'})[c.operator] || c.operator;
  return `${c.field.replaceAll('_',' ')} ${op}${c.operator === 'known' ? '' : ' '+JSON.stringify(c.value)}`;
}
function evidenceHTML(p) {
  return `<article class="evidence-card"><div class="evidence-header"><strong>${escapeHTML(p.policy_id)}</strong><span>Cosine similarity ${Number(p.score).toFixed(3)}</span></div><div class="report-meta">${escapeHTML(p.source_filename)}${p.page ? ` · Page ${p.page}` : ''} · ${escapeHTML(p.chunk_id)}</div><details><summary>Read retrieved passage</summary><blockquote>${escapeHTML(p.text)}</blockquote></details></article>`;
}
function renderReport(r) {
  activeReport = r;
  $('#download-report').classList.remove('hidden');
  const checks = r.rule_results;
  const rows = checks.map(x => `<tr><td class="report-rule-desc"><strong>${escapeHTML(x.rule_id)}</strong><small>${escapeHTML(x.description)}</small></td><td><code>${json(x.actual_value)}</code></td><td>${escapeHTML(condition(x.expected_condition))}<small>${escapeHTML(x.explanation)}</small>${x.exception ? `<details><summary>Applicability & exception</summary><p>Applies: ${escapeHTML(condition(x.applicability))}</p><p>Exception: ${escapeHTML(condition(x.exception))} (${escapeHTML(x.exception_reference)})</p></details>` : ''}</td><td>${badge(x.result)}</td><td><code>${escapeHTML(x.policy_reference)}</code></td></tr>`).join('');
  const t = r.transaction;
  $('#report-content').innerHTML = `<div class="report-banner"><div><div class="eyebrow">ADVISORY ASSESSMENT</div>${badge(r.assessment)}<h2>${escapeHTML(money(t))} <span class="report-meta">${escapeHTML(t.sender_country || '?')} → ${escapeHTML(t.recipient_country || '?')}</span></h2><p>${escapeHTML(r.summary)}</p><div class="report-meta">Report ${escapeHTML(r.id)} · ${escapeHTML(date(r.timestamp))}</div><div class="report-meta">Transaction ${escapeHTML(r.transaction_id)}</div></div><div><span class="tag">${escapeHTML(r.execution_mode)}</span><p>${escapeHTML(r.mode_reason)}</p><span class="tag">${escapeHTML(r.retrieval_mode)}</span></div></div>
    <div class="report-grid"><article class="panel"><div class="panel-heading"><h2>Recommended next steps</h2></div><div class="content-pad"><ul>${r.next_steps.map(s => `<li>${escapeHTML(s)}</li>`).join('')}</ul><h3>Missing mandatory information</h3><p class="rules-note">${r.missing_information.length ? escapeHTML(r.missing_information.join(', ')) : 'No mandatory transaction fields are unknown.'}</p>${r.ai_explanation ? `<h3>Agent evidence highlights</h3><p class="rules-note">${escapeHTML(r.ai_explanation.label)}</p><ul>${r.ai_explanation.highlights.map(x => `<li>${escapeHTML(x)}</li>`).join('')}</ul><p class="rules-note">Citations: ${escapeHTML(r.ai_explanation.citation_ids.join(', '))}</p>` : ''}</div></article><article class="panel"><div class="panel-heading"><h2>Transaction snapshot</h2></div><div class="content-pad"><dl class="transaction-facts">${Object.entries(t).map(([k,v]) => `<dt>${escapeHTML(k.replaceAll('_',' '))}</dt><dd>${escapeHTML(v === null ? 'Unknown' : Array.isArray(v) ? v.join(', ') || 'None supplied' : v)}</dd>`).join('')}</dl></div></article></div>
    <article class="panel"><div class="panel-heading"><div><h2>Deterministic rule evaluation</h2><p>All ${checks.length} rules considered, including those outside retrieved passages.</p></div></div><div class="table-wrap"><table><thead><tr><th>Rule</th><th>Actual value</th><th>Requirement</th><th>Result</th><th>Policy reference</th></tr></thead><tbody>${rows}</tbody></table></div></article>
    <div class="section-heading"><div><h2>Retrieved policy evidence</h2><p>Actual source passages. Retrieval supports explanation; it does not select mandatory checks.</p></div><span class="tag">${r.evidence.length} passages</span></div>
    <details class="rules-note"><summary>Documents searched (${r.documents_searched.length})</summary><p>${escapeHTML(r.documents_searched.join(', '))}</p></details>${r.evidence.map(evidenceHTML).join('')}
    <div class="section-heading"><div><h2>Recorded execution</h2><p>Observable tool operations, in execution order. Expand to inspect inputs and outputs.</p></div><span class="tag">${r.trace.length} operations</span></div><article class="panel">${r.trace.map(s => `<details class="trace-item"><summary><span class="trace-number">${s.order}</span><span><strong>${escapeHTML(s.tool_name)}</strong><small>${escapeHTML(s.output_summary)} · ${escapeHTML(s.origin)} · ${s.duration_ms} ms</small></span>${badge(s.state)}</summary><h3>Inputs</h3><pre>${json(s.inputs)}</pre><h3>Output</h3><pre>${json(s.output)}</pre></details>`).join('')}</article>
    <details class="evidence-card"><summary>Policy version snapshot (${r.policy_versions.length})</summary><pre class="code">${json(r.policy_versions)}</pre></details>`;
}
$('#download-report').addEventListener('click', () => {
  if (!activeReport) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(activeReport,null,2)], {type:'application/json'}));
  const a = document.createElement('a'); a.href = url; a.download = `policyguard-${activeReport.id}.json`; a.click(); URL.revokeObjectURL(url);
});
async function loadPolicies() {
  const policies = await api('/api/policies');
  $('#policy-count').textContent = `${policies.length} source documents`;
  $('#policy-list').innerHTML = policies.map(p => `<article class="panel policy-card"><span class="tag">${escapeHTML(p.policy_id)}</span><h2>${escapeHTML(p.name)}</h2><p>${escapeHTML(p.description.slice(0,180))}${p.description.length > 180 ? '…' : ''}</p><div class="policy-meta"><span>v${escapeHTML(p.version)}</span><span>· ${p.chunks} chunks</span><span>· ${p.associated_rule_ids.length} rules</span><span>· ${escapeHTML(p.indexing_status)}</span></div><button class="button secondary" data-policy="${escapeHTML(p.policy_id)}">Read policy & rules ↗</button></article>`).join('');
}
$('#policy-list').addEventListener('click', async (event) => {
  const button = event.target.closest('[data-policy]'); if (!button) return;
  try {
    const p = await api('/api/policies/'+encodeURIComponent(button.dataset.policy));
    $('#policy-detail').innerHTML = `<article class="panel policy-detail-panel"><div class="detail-head"><h2>${escapeHTML(p.name)}</h2><button class="button secondary" id="close-policy">Close ×</button></div><p class="rules-note">${escapeHTML(p.policy_id)} · v${escapeHTML(p.version)} · Effective ${escapeHTML(p.effective_date || 'not specified')} · ${escapeHTML(p.source_document)}</p>${!p.enforceable ? '<p class="warning-text">Untrusted uploaded reference. No executable rules activated.</p>' : ''}<div class="source-text">${escapeHTML(p.policy_text)}</div><h3>Structured rule definitions (${p.rules.length})</h3><pre class="code">${json(p.rules)}</pre></article>`;
    $('#close-policy').addEventListener('click', () => { $('#policy-detail').innerHTML = ''; });
    $('#policy-detail').scrollIntoView({behavior:'smooth'});
  } catch(error) { showError(error); }
});
$('#search-form').addEventListener('submit', async (event) => {
  event.preventDefault(); clearError(); const button = event.target.querySelector('button'); button.disabled = true;
  try {
    const r = await api('/api/policies/search', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:$('#policy-query').value,top_k:5})});
    $('#search-results').innerHTML = `<div class="section-heading"><h2>Retrieved passages</h2><span class="tag">${escapeHTML(r.mode)}</span></div>${r.warning ? `<p class="warning-text">${escapeHTML(r.warning)}</p>` : ''}${r.passages.map(evidenceHTML).join('')}<div class="section-heading"><h2>All policy documents</h2></div>`;
  } catch(error) { showError(error); } finally { button.disabled = false; }
});
$('#upload-form').addEventListener('submit', async (event) => {
  event.preventDefault(); clearError(); const file = $('#policy-file').files[0];
  if (!file) return;
  if (file.size > 5*1024*1024) { showError(new Error('Maximum upload size is 5 MiB.')); return; }
  const form = new FormData(); form.append('file',file);
  $('#upload-button').disabled = true; $('#upload-status').textContent = 'Extracting text and indexing on the backend…';
  try {
    const p = await api('/api/policies/upload', {method:'POST',body:form});
    $('#upload-status').textContent = `${p.name}\nProcessing: ${p.processing_status} · Index: ${p.indexing_status}\n${p.chunks} chunks indexed. No rules activated.`;
    await Promise.all([loadPolicies(),refreshStatus()]); event.target.reset();
  } catch(error) { $('#upload-status').textContent = 'Processing failed. Document was not added.'; showError(error); }
  finally { $('#upload-button').disabled = false; }
});
async function loadHistory() {
  const filter = $('#history-filter').value;
  const query = new URLSearchParams({limit:historyLimit,offset:historyOffset});
  if (filter) query.set('assessment',filter);
  const items = await api('/api/verifications?'+query);
  $('#history-table').innerHTML = items.length ? `<div class="table-wrap"><table><thead><tr><th>Transaction / Report</th><th>Route</th><th>Amount</th><th>Assessment</th><th>Mode</th><th>Recorded</th></tr></thead><tbody>${items.map(r => `<tr><td><button class="history-link" data-report="${escapeHTML(r.id)}">${escapeHTML(r.transaction.sender_name || 'Unknown sender')} → ${escapeHTML(r.transaction.recipient_name || 'Unknown recipient')}</button><small>${escapeHTML(r.id.slice(0,8))}</small></td><td>${escapeHTML(r.transaction.sender_country || '?')} → ${escapeHTML(r.transaction.recipient_country || '?')}</td><td>${escapeHTML(money(r.transaction))}</td><td>${badge(r.assessment)}</td><td>${escapeHTML(r.execution_mode)}</td><td>${escapeHTML(date(r.timestamp))}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty-state"><h2>No assessments here yet.</h2><p>Verify a demo transaction to create an audit record, or change the filter.</p></div>';
  $('#history-prev').disabled = historyOffset === 0;
  $('#history-next').disabled = items.length < historyLimit;
  $('#history-page').textContent = `Page ${historyOffset/historyLimit+1} · ${items.length} records`;
}
$('#history-table').addEventListener('click',async (event) => {
  const button = event.target.closest('[data-report]'); if (!button) return;
  try { renderReport(await api('/api/verifications/'+encodeURIComponent(button.dataset.report))); location.hash = 'details'; window.scrollTo(0,0); } catch(error) { showError(error); }
});
$('#history-filter').addEventListener('change', () => { historyOffset = 0; loadHistory().catch(showError); });
$('#refresh-history').addEventListener('click', () => loadHistory().catch(showError));
$('#history-prev').addEventListener('click', () => { historyOffset = Math.max(0,historyOffset-historyLimit); loadHistory().catch(showError); });
$('#history-next').addEventListener('click', () => { historyOffset += historyLimit; loadHistory().catch(showError); });
async function init() {
  const countries = {IN:'India',SG:'Singapore',US:'United States',GB:'United Kingdom',DE:'Germany',AU:'Australia',CA:'Canada',AE:'United Arab Emirates',JP:'Japan',KP:'North Korea (fictional restriction)',IR:'Iran (fictional restriction)',SY:'Syria (fictional restriction)',BR:'Brazil (unsupported demo corridor)'};
  document.querySelectorAll('.country').forEach(select => { for (const [code,name] of Object.entries(countries)) { const o = document.createElement('option'); o.value=code; o.textContent=`${name} · ${code}`; select.append(o); } });
  go();
  try {
    const results = await Promise.all([api('/api/transactions/samples'),refreshStatus()]); samples=results[0];
    samples.forEach(s => { const o=document.createElement('option'); o.value=s.id; o.textContent=s.label; $('#sample').append(o); });
    $('#sample').value=samples[0].id; populate(samples[0].transaction);
  } catch(error) { showError(error); }
}
init();
