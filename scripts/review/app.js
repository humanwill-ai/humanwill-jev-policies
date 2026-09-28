'use strict';
const DATA = JSON.parse(document.getElementById('reviewData').textContent);
const $ = id => document.getElementById(id);
const fingerprint = DATA.packs.map(p => p.sha256).join(':') + ':' + Object.values(DATA.policies).map(p => p.sha256).join(':') + ':' + DATA.source_catalog_sha256;
const storageKey = 'humanwill.case-review.v1:' + fingerprint;
const allCases = new Map(DATA.packs.flatMap(p => p.cases.map(c => [c.id, {c, p}])));
let state = {reviewer: '', reviews: {}}, packId = 'sources', selectedId = DATA.packs.find(p => p.id === 'sources').cases[0].id;
let storageOK = true;
const labels = {allow: 'Allow', block: 'Block / violation', evaluation_error: 'Evaluation error'};
const statuses = {pending: 'Pending', approved: 'Approved', correction: 'Needs correction'};
const pretty = value => JSON.stringify(value, null, 2);
const now = () => new Date().toISOString();
const pendingCases = () => DATA.packs.filter(p => !p.previously_approved).flatMap(p => p.cases);
const pack = () => DATA.packs.find(p => p.id === packId);
const current = () => allCases.get(selectedId)?.c;
function message(text) { $('message').textContent = text; }
function validateState(candidate) {
  if (!candidate || typeof candidate.reviewer !== 'string' || !candidate.reviews || Array.isArray(candidate.reviews) || typeof candidate.reviews !== 'object') throw Error('Invalid review data.');
  const clean = {reviewer: candidate.reviewer, reviews: {}};
  for (const [id, r] of Object.entries(candidate.reviews)) {
    const entry = allCases.get(id);
    if (!entry || !r || !Object.hasOwn(statuses, r.status) || typeof r.notes !== 'string' || !Object.hasOwn(labels, r.label) || !['', 'not_applicable', 'applicable', 'insufficient_evidence'].includes(r.scope) || typeof r.updated_at !== 'string' || !Number.isFinite(Date.parse(r.updated_at))) throw Error('Invalid or unknown case review: ' + id);
    if (r.status === 'correction' && !r.notes.trim()) throw Error('A correction needs a reason: ' + id);
    if (r.status === 'approved' && (r.label !== entry.c.expected || r.scope !== (entry.c.expected_scope ?? ''))) throw Error('Approval must match the original label and scope: ' + id);
    clean.reviews[id] = {status: r.status, notes: r.notes, label: r.label, scope: r.scope, updated_at: r.updated_at};
  }
  return clean;
}
try { const saved = localStorage.getItem(storageKey) ?? localStorage.getItem('humanwill.case-review.v1:' + DATA.legacy_fingerprint); if (saved) state = validateState(JSON.parse(saved)); }
catch { storageOK = false; message('Saved progress could not be loaded. Use Export review to keep a backup; import a previous export to restore it.'); }
function persist() {
  try { localStorage.setItem(storageKey, JSON.stringify(state)); storageOK = true; }
  catch { storageOK = false; }
  $('storageStatus').textContent = storageOK ? 'Progress saved in this browser. Export before changing browsers or clearing site data.' : 'Browser storage unavailable — export your review before closing.';
}
function review(c) {
  return state.reviews[c.id] ?? {status: allCases.get(c.id).p.previously_approved ? 'approved' : 'pending', notes: '', label: c.expected, scope: c.expected_scope ?? ''};
}
function title(c) { return c.id.replace(/^(holdout-v1-|candidate-v1-|sources-v1-)/, '').replace(/^(sw-|prod-|doc-)/, '').replaceAll('-', ' '); }
function filtered() {
  const query = $('search').value.toLowerCase().trim();
  return pack().cases.filter(c => (!$('policyFilter').value || c.policy_id === $('policyFilter').value) && (!$('statusFilter').value || review(c).status === $('statusFilter').value) && (!query || JSON.stringify(c).toLowerCase().includes(query)));
}
function badge(el, text, kind) { el.textContent = text; el.className = 'badge ' + kind; }
function updateProgress() {
  const counts = {pending: 0, approved: 0, correction: 0};
  pendingCases().forEach(c => counts[review(c).status]++);
  $('progressCount').textContent = counts.approved + ' / ' + pendingCases().length;
  $('progressDetail').textContent = counts.pending + ' pending · ' + counts.correction + ' need correction';
  $('progress').max = pendingCases().length; $('progress').value = counts.approved;
  $('approveRemaining').disabled = pack().previously_approved || !pack().cases.some(c => review(c).status === 'pending');
}
function renderList(cases) {
  $('listCount').textContent = cases.length + ' cases';
  $('caseList').replaceChildren();
  for (const c of cases) {
    const button = document.createElement('button'); button.className = 'case-item'; button.setAttribute('aria-current', String(c.id === selectedId));
    const name = document.createElement('span'); name.className = 'title'; name.textContent = title(c);
    const mini = document.createElement('span'); mini.className = 'mini';
    const label = document.createElement('span'); label.textContent = labels[c.expected];
    const status = document.createElement('span'); status.textContent = statuses[review(c).status];
    mini.append(label, status); button.append(name, mini); button.onclick = () => {selectedId = c.id; render();};
    $('caseList').append(button);
  }
}
function render() {
  updateProgress();
  const cases = filtered();
  if (!cases.some(c => c.id === selectedId)) selectedId = cases[0]?.id ?? null;
  renderList(cases);
  $('tabHoldout').setAttribute('aria-pressed', String(packId === 'holdout'));
  $('tabSources').setAttribute('aria-pressed', String(packId === 'sources'));
  $('tabPrevious').setAttribute('aria-pressed', String(packId === 'previous'));
  $('empty').hidden = !!selectedId; $('casePanel').hidden = !selectedId;
  const index = cases.findIndex(c => c.id === selectedId);
  $('position').textContent = selectedId ? `Case ${index + 1} of ${cases.length} shown · ${pack().title}` : 'No cases shown';
  $('prev').disabled = index <= 0; $('next').disabled = index < 0 || index >= cases.length - 1;
  if (!selectedId) return;
  const c = current(), r = review(c), policy = DATA.policies[c.policy_id];
  $('caseTitle').textContent = title(c); $('caseId').textContent = c.id;
  $('caseMeta').textContent = c.request.stage.replaceAll('_', ' ') + ' / ' + c.policy_id;
  badge($('reviewBadge'), pack().previously_approved && !state.reviews[c.id] ? 'Previously approved' : statuses[r.status], r.status);
  $('event').replaceChildren();
  for (const item of c.request.content) {
    const heading = document.createElement('div'); heading.className = 'subtle'; heading.textContent = [item.kind, item.role, item.name].filter(Boolean).join(' · ');
    const pre = document.createElement('pre');
    pre.textContent = Object.hasOwn(item, 'text') ? (item.text || '(Empty text — see trusted evidence below)') : pretty(item.arguments ?? item);
    $('event').append(heading, pre);
  }
  badge($('expectedBadge'), labels[c.expected], c.expected);
  $('scope').textContent = 'Scope: ' + (c.expected_scope?.replaceAll('_', ' ') ?? 'deterministic; no semantic judgment');
  $('rationale').textContent = c.rationale;
  $('facts').textContent = pretty({trusted_facts: c.trusted_facts, ...(c.source_context ? {source_context: c.source_context} : {}), ...(c.disclosure_context ? {disclosure_context: c.disclosure_context} : {})});
  $('raw').textContent = pretty(c);
  $('policyId').textContent = policy.id + ' · VERSION ' + policy.version;
  $('policyTitle').textContent = policy.title;
  $('policyBody').replaceChildren();
  for (const paragraph of policy.body.split(/\n\s*\n/)) { const p = document.createElement('p'); p.textContent = paragraph.replace(/\n/g, ' '); $('policyBody').append(p); }
  $('policySource').textContent = policy.source;
  $('catalogDetails').hidden = c.policy_id !== 'EVAL-SRC-001';
  $('catalogSource').textContent = DATA.source_catalog;
  $('composition').replaceChildren();
  if (c.expected_composed) {
    const heading = document.createElement('h3'); heading.textContent = 'Combined-policy result: ' + labels[c.expected_composed]; $('composition').append(heading);
    for (const [id, decision] of Object.entries(c.expected_by_policy)) {
      const detail = document.createElement('details'), summary = document.createElement('summary'), text = document.createElement('pre');
      summary.textContent = id + ': ' + labels[decision] + ' — view policy'; text.textContent = DATA.policies[id].source; detail.append(summary, text); $('composition').append(detail);
    }
  }
  if (c.related_case_id) {const p = document.createElement('p'); p.className = 'subtle'; p.textContent = 'Reassesses the workflow from ' + c.related_case_id + ' under the new source policy; its original disclosure-only label is unchanged.'; $('composition').append(p);}
  $('notes').value = r.notes; $('correctedLabel').value = r.label; $('correctedScope').value = r.scope;
  $('historical').textContent = pack().previously_approved ? 'Original owner approval: September 27, 2026' : 'New label awaiting your judgment';
  $('approve').textContent = pack().previously_approved ? 'Reconfirm original result' : 'Approve expected result';
  $('undo').textContent = pack().previously_approved ? 'Restore original approval' : 'Reset this review';
}
function storeReview(c, status, label, scope) {
  state.reviews[c.id] = {status, label, scope, notes: $('notes').value, updated_at: now()}; persist();
}
function record(status) {
  const c = current(); if (!c) return;
  if (status === 'correction' && !$('notes').value.trim()) {message('Add a reason so the proposed correction can be applied accurately.'); $('notes').focus(); return;}
  const before = filtered(); const index = before.findIndex(x => x.id === c.id);
  storeReview(c, status, status === 'approved' ? c.expected : $('correctedLabel').value, status === 'approved' ? (c.expected_scope ?? '') : $('correctedScope').value);
  if ($('autoNext').checked) selectedId = before[index + 1]?.id ?? c.id;
  message(status === 'approved' ? 'Approved ' + c.id + '. Export your review when ready.' : 'Correction recorded for ' + c.id + '. The frozen source case is unchanged.');
  render();
}
$('approve').onclick = () => record('approved'); $('correct').onclick = () => record('correction');
$('notes').oninput = () => {
  const c = current(); if (!c) return; const r = review(c);
  // Removing a correction's explanation returns it to pending until explicitly saved again.
  storeReview(c, r.status === 'correction' && !$('notes').value.trim() ? 'pending' : r.status, r.label, r.scope);
  updateProgress(); renderList(filtered());
};
$('undo').onclick = () => { if (!current()) return; if (!confirm('Reset your review and notes for this case? The original label and any historical approval will be preserved.')) return; delete state.reviews[selectedId]; persist(); message('Original case review state restored.'); render(); };
$('reviewer').value = state.reviewer; $('reviewer').oninput = () => {state.reviewer = $('reviewer').value; persist();};
for (const id of ['search', 'policyFilter', 'statusFilter']) $(id).addEventListener(id === 'search' ? 'input' : 'change', render);
for (const [id, value] of [['tabHoldout', 'holdout'], ['tabSources', 'sources'], ['tabPrevious', 'previous']]) $(id).onclick = () => {packId = value; $('statusFilter').value = ''; $('policyFilter').value = ''; $('search').value = ''; selectedId = null; render();};
function move(delta) {const list = filtered(); selectedId = list[list.findIndex(c => c.id === selectedId) + delta]?.id ?? selectedId; render();}
$('prev').onclick = () => move(-1); $('next').onclick = () => move(1);
$('nextPending').onclick = () => {
  const list = pack().cases; const index = list.findIndex(c => c.id === selectedId);
  const next = [...list.slice(index + 1), ...list.slice(0, index + 1)].find(c => review(c).status === 'pending');
  if (!next) {message('No pending cases in this packet.'); return;}
  $('search').value = ''; $('policyFilter').value = ''; $('statusFilter').value = ''; selectedId = next.id; render();
};
$('approveRemaining').onclick = () => {
  const pending = pack().cases.filter(c => review(c).status === 'pending');
  if (pack().previously_approved || !pending.length || !confirm(`Confirm you have reviewed all ${pending.length} remaining cases in ${pack().title} and accept their ORIGINAL expected results, scopes and any stated combined-policy results. This covers all policies, regardless of filters. Flagged corrections will be preserved.`)) return;
  for (const c of pending) state.reviews[c.id] = {...review(c), status: 'approved', label: c.expected, scope: c.expected_scope ?? '', updated_at: now()};
  persist(); render(); message(pending.length + ' labels approved. Export review to hand off your decisions.');
};
function exportPayload() {
  return {format: 'humanwill.case-review/1', exported_at: now(), fingerprint, ...state,
    packets: DATA.packs.map(p => ({id: p.id, path: p.path, sha256: p.sha256, original_approval_date: p.approval_date,
      cases: p.cases.map(c => ({id: c.id, policy_id: c.policy_id, original_expected: c.expected, original_scope: c.expected_scope, ...(c.expected_composed ? {original_composed: c.expected_composed, original_by_policy: c.expected_by_policy} : {}), ...review(c), provenance: state.reviews[c.id] ? 'local_review' : (p.previously_approved ? 'historical_owner_approval' : 'unreviewed')}))})),
    note: 'Local label review only; no source or evaluation protocol changed. Corrections require adjudication and a versioned dataset before measurement.'};
}
$('export').onclick = () => {
  const blob = new Blob([pretty(exportPayload()) + '\n'], {type: 'application/json'});
  const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'humanwill-case-review-' + new Date().toISOString().slice(0, 10) + '.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  message('Review exported. Keep the JSON file and give it to Codex to record approvals or apply corrections.');
};
$('import').onclick = () => $('importFile').click();
$('importFile').onchange = async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (file.size > 5_000_000) throw Error('Review file is too large.');
    const imported = JSON.parse(await file.text());
    if (imported.format !== 'humanwill.case-review/1' || ![fingerprint, DATA.legacy_fingerprint].includes(imported.fingerprint)) throw Error('This review belongs to different datasets or policies. Nothing was imported.');
    const clean = validateState(imported);
    if (imported.fingerprint === DATA.legacy_fingerprint && Object.keys(clean.reviews).some(id => allCases.get(id).p.id === 'sources')) throw Error('Old-format reviews cannot approve the new source-policy cases.');
    if (!confirm('Replace this browser’s current review with the imported review? Export first if you need to preserve your current progress.')) return;
    state = clean; $('reviewer').value = state.reviewer; persist(); render(); message('Review restored from file.');
  } catch (error) {message(error.message);} finally {event.target.value = '';}
};
$('fingerprints').textContent = DATA.packs.map(p => p.title + '\nSHA-256 ' + p.sha256).join('\n\n');
persist(); render();
