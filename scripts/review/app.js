'use strict';
const DATA = JSON.parse(document.getElementById('reviewData').textContent);
const $ = id => document.getElementById(id);
const fingerprint = DATA.packs.map(p => p.sha256).join(':') + ':' + Object.values(DATA.policies).map(p => p.sha256).join(':') + ':' + DATA.source_catalog_sha256;
const storageKey = 'humanwill.case-review.v1:' + fingerprint;
const allCases = new Map(DATA.packs.flatMap(p => p.cases.map(c => [c.id, {c, p}])));
const releaseScope = new Map(DATA.release_scope.cases.map(c => [c.id, c]));
let state = {reviewer: '', reviews: {}, archived_reviews: {}, owner_removals_revision: DATA.owner_removals_revision}, packId = 'holdout', selectedId = 'holdout-v1-sw-download-dependency';
let storageOK = true, lastRemovedId = null;
const labels = {allow: 'Allow', block: 'Block / violation', evaluation_error: 'Evaluation error'};
const statuses = {pending: 'Pending', approved: 'Approved', correction: 'Needs correction', removed: 'Removed'};
const pretty = value => JSON.stringify(value, null, 2);
const now = () => new Date().toISOString();
const pendingCases = () => DATA.packs.filter(p => !p.previously_approved).flatMap(p => p.cases);
const pack = () => DATA.packs.find(p => p.id === packId);
const current = () => allCases.get(selectedId)?.c;
const expectedLabel = c => c.review_expected ?? c.expected;
const expectedScope = c => c.review_scope ?? c.expected_scope ?? '';
const legacyFingerprints = [DATA.previous_fingerprint, DATA.legacy_fingerprint];
function message(text) { $('message').textContent = text; }
function validateRows(rows, historical = false) {
  if (!rows || Array.isArray(rows) || typeof rows !== 'object') throw Error('Invalid review records.');
  const clean = {};
  for (const [id, r] of Object.entries(rows)) {
    const c = historical ? DATA.original_labels[id] : allCases.get(id)?.c;
    if (!c || !r || !Object.hasOwn(statuses, r.status) || typeof r.notes !== 'string' || !Object.hasOwn(labels, r.label) || !['', 'not_applicable', 'applicable', 'insufficient_evidence'].includes(r.scope) || typeof r.updated_at !== 'string' || !Number.isFinite(Date.parse(r.updated_at))) throw Error('Invalid or unknown case review: ' + id);
    if (r.status === 'correction' && !r.notes.trim()) throw Error('A correction needs a reason: ' + id);
    if (r.status === 'approved' && (r.label !== expectedLabel(c) || r.scope !== expectedScope(c))) throw Error('Approval must match the reviewed label and scope: ' + id);
    clean[id] = {status: r.status, notes: r.notes, label: r.label, scope: r.scope, updated_at: r.updated_at};
    if (r.status === 'removed') {
      if (!['pending', 'approved', 'correction'].includes(r.previous_status)) throw Error('Invalid restoration state: ' + id);
      if (r.previous_status === 'approved' && (r.label !== expectedLabel(c) || r.scope !== expectedScope(c))) throw Error('Invalid removed approval: ' + id);
      if (r.previous_status === 'correction' && !r.notes.trim()) throw Error('Removed correction needs its reason: ' + id);
      clean[id].previous_status = r.previous_status;
      if (r.removal_reason !== undefined) {if (typeof r.removal_reason !== 'string') throw Error('Invalid removal reason: ' + id); clean[id].removal_reason = r.removal_reason;}
    }
  }
  return clean;
}
function validateState(candidate, legacy = false, applyOwnerRemovals = false) {
  if (!candidate || typeof candidate.reviewer !== 'string') throw Error('Invalid review data.');
  let reviews = candidate.reviews, archived = candidate.archived_reviews ?? {};
  if (legacy) {
    if (!reviews || Array.isArray(reviews) || typeof reviews !== 'object') throw Error('Invalid review records.');
    reviews = {...reviews}; archived = {...archived};
    for (const id of Object.keys(reviews)) if (Object.hasOwn(DATA.original_labels, id)) {archived[id] = reviews[id]; delete reviews[id];}
  }
  const clean = {reviewer: candidate.reviewer, reviews: validateRows(reviews), archived_reviews: validateRows(archived, true)};
  if (applyOwnerRemovals) for (const [id, removal] of Object.entries(DATA.default_removed)) {
    const prior = clean.reviews[id];
    if (prior && prior.status !== 'removed') clean.reviews[id] = {...prior, status: 'removed', previous_status: prior.status, removal_reason: removal.reason, updated_at: removal.removed_at};
  }
  if (candidate.owner_removals_revision !== DATA.owner_removals_revision) {
    for (const [id, removal] of Object.entries(DATA.active_removals ?? {})) {
      const prior = clean.reviews[id];
      if (prior && prior.status !== 'removed') clean.reviews[id] = {...prior, status: 'removed', previous_status: prior.status, removal_reason: removal.reason, updated_at: removal.removed_at};
    }
  }
  clean.owner_removals_revision = DATA.owner_removals_revision;
  return clean;
}
try {
  const saved = localStorage.getItem(storageKey);
  if (saved) state = validateState(JSON.parse(saved));
  else for (const oldFingerprint of [DATA.compatible_fingerprint, ...legacyFingerprints]) {
    const old = localStorage.getItem('humanwill.case-review.v1:' + oldFingerprint);
    if (old) {state = validateState(JSON.parse(old), legacyFingerprints.includes(oldFingerprint), true); message(oldFingerprint === DATA.compatible_fingerprint ? 'Saved reviews retained. The vague Git-fetch case is removed from active review.' : 'Unchanged reviews restored; original single-policy reviews retained as history.'); break;}
  }
} catch { storageOK = false; message('Saved progress could not be loaded. Use Export review to keep a backup; import a previous export to restore it.'); }
function persist() {
  try { localStorage.setItem(storageKey, JSON.stringify(state)); storageOK = true; }
  catch { storageOK = false; }
  $('storageStatus').textContent = storageOK ? 'Progress saved in this browser. Export before changing browsers or clearing site data.' : 'Browser storage unavailable — export your review before closing.';
}
function review(c) {
  if (state.reviews[c.id]) return state.reviews[c.id];
  if (DATA.default_removed[c.id]) return {status: 'removed', previous_status: 'pending', notes: DATA.default_removed[c.id].reason, label: expectedLabel(c), scope: expectedScope(c), updated_at: DATA.default_removed[c.id].removed_at};
  return {status: (allCases.get(c.id).p.previously_approved || DATA.recorded_approvals?.includes(c.id)) ? 'approved' : 'pending', notes: '', label: expectedLabel(c), scope: expectedScope(c), ...(DATA.recorded_approvals?.includes(c.id) ? {updated_at: DATA.recorded_approval_at} : {})};
}
function title(c) { return c.id.replace(/^(holdout-v1-|candidate-v1-|sources-v1-)/, '').replace(/^(sw-|prod-|doc-)/, '').replaceAll('-', ' '); }
function filtered() {
  const query = $('search').value.toLowerCase().trim();
  return pack().cases.filter(c => (!$('releaseScopeFilter').value || releaseScope.get(c.id)?.suite === $('releaseScopeFilter').value) && (!$('policyFilter').value || (c.policy_id === $('policyFilter').value || c.also_policy_ids?.includes($('policyFilter').value))) && ($('statusFilter').value ? review(c).status === $('statusFilter').value : review(c).status !== 'removed') && (!query || JSON.stringify(c).toLowerCase().includes(query)));
}
function badge(el, text, kind) { el.textContent = text; el.className = 'badge ' + kind; }
function updateProgress() {
  const counts = {pending: 0, approved: 0, correction: 0, removed: 0};
  pendingCases().forEach(c => counts[review(c).status]++);
  $('progressCount').textContent = counts.approved + ' / ' + (pendingCases().length - counts.removed);
  $('progressDetail').textContent = counts.pending + ' pending · ' + counts.correction + ' need correction · ' + [...allCases.values()].filter(({c}) => review(c).status === 'removed').length + ' removed';
  $('progress').max = Math.max(1, pendingCases().length - counts.removed); $('progress').value = counts.approved;
  $('tabHoldout').firstChild.textContent = 'Updated ' + DATA.packs[0].cases.filter(c => review(c).status !== 'removed').length + ' ';
  $('tabPrevious').firstChild.textContent = 'Previously approved · ' + DATA.packs.find(p => p.id === 'previous').cases.filter(c => review(c).status !== 'removed').length + ' ';
  $('tabSources').firstChild.textContent = 'Approved sources · ' + DATA.packs.find(p => p.id === 'sources').cases.filter(c => review(c).status !== 'removed').length + ' ';
  $('approveRemaining').disabled = pack().previously_approved || !pack().cases.some(c => review(c).status === 'pending');
}
function renderList(cases) {
  $('listCount').textContent = cases.length + ' cases';
  $('caseList').replaceChildren();
  for (const c of cases) {
    const button = document.createElement('button'); button.className = 'case-item'; button.setAttribute('aria-current', String(c.id === selectedId));
    const name = document.createElement('span'); name.className = 'title'; name.textContent = title(c);
    const mini = document.createElement('span'); mini.className = 'mini';
    const label = document.createElement('span'); label.textContent = labels[expectedLabel(c)];
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
  const c = current(), r = review(c), policy = DATA.policies[c.review_policy_id ?? c.policy_id];
  $('caseTitle').textContent = title(c); $('caseId').textContent = c.id;
  const cohort = releaseScope.get(c.id);
  $('releaseScopeLabel').textContent = cohort ? (cohort.suite === 'generic_policy' ? 'Generic policy suite. ' : 'Advanced command diagnostic — retained outside first-release acceptance. ') + DATA.release_scope.reason_definitions[cohort.reason] : 'Historically removed case; outside both current suites.';
  $('caseMeta').textContent = c.request.stage.replaceAll('_', ' ') + ' / ' + [c.policy_id, ...(c.also_policy_ids ?? [])].join(' + ');
  badge($('reviewBadge'), pack().previously_approved && !state.reviews[c.id] ? 'Previously approved' : statuses[r.status], r.status);
  $('event').replaceChildren();
  for (const item of c.request.content) {
    const heading = document.createElement('div'); heading.className = 'subtle'; heading.textContent = [item.kind, item.role, item.name].filter(Boolean).join(' · ');
    const pre = document.createElement('pre');
    pre.textContent = Object.hasOwn(item, 'text') ? (item.text || '(Empty text — see trusted evidence below)') : pretty(item.arguments ?? item);
    $('event').append(heading, pre);
  }
  const context = DATA.question_contexts?.[c.id];
  $('contextPanel').hidden = !context;
  $('contextSummary').replaceChildren();
  $('questionContext').textContent = context ? pretty(context) : '';
  if (context) {
    const add = text => {const p = document.createElement('p'); p.textContent = text; $('contextSummary').append(p);};
    add(context.assessment_point);
    for (const tool of context.tool_contracts ?? []) add(tool.name + ': ' + tool.contract);
    for (const fact of context.resource_observations ?? []) add(fact.resource + ': ' + (fact.availability ? fact.availability + '. ' : '') + fact.description);
    const source = context.software_origin_resolution;
    if (source) {
      add('Software-origin lookup: ' + source.status + '. ' + source.resources.length + ' resource(s) recorded. This does not state whether a source is approved.');
      for (const resource of source.resources) add([resource.kind, resource.operation, resource.endpoint, resource.package].filter(Boolean).join(' · '));
    }
  }
  $('scopeQuestions').replaceChildren();
  for (const pid of [c.policy_id, ...(c.also_policy_ids ?? [])]) {
    const heading = document.createElement('h4'), p = document.createElement('p');
    heading.textContent = pid;
    p.textContent = DATA.scope_questions?.[pid]?.[c.request.stage] ?? 'Deterministic policy: no semantic question is sent to Jev.';
    $('scopeQuestions').append(heading, p);
  }
  badge($('expectedBadge'), labels[expectedLabel(c)], expectedLabel(c));
  $('scope').textContent = c.review_revision ? 'Combined result · source scope: ' + c.review_scope.replaceAll('_', ' ') : 'Scope: ' + (c.expected_scope?.replaceAll('_', ' ') ?? 'deterministic; no semantic judgment');
  $('rationale').textContent = c.rationale;
  $('facts').textContent = pretty({trusted_facts: c.trusted_facts, ...(c.source_context ? {source_context: c.source_context} : {}), ...(c.disclosure_context ? {disclosure_context: c.disclosure_context} : {})});
  $('raw').textContent = pretty(c);
  $('policyId').textContent = policy.id + ' · VERSION ' + policy.version;
  $('policyTitle').textContent = policy.title;
  $('policyBody').replaceChildren();
  for (const paragraph of policy.body.split(/\n\s*\n/)) { const p = document.createElement('p'); p.textContent = paragraph.replace(/\n/g, ' '); $('policyBody').append(p); }
  $('policySource').textContent = policy.source;
  $('catalogDetails').hidden = c.policy_id !== 'EVAL-SRC-001' && !c.also_policy_ids?.includes('EVAL-SRC-001');
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
  $('historical').textContent = pack().previously_approved ? 'Original owner approval: September 27, 2026' : (DATA.recorded_approvals?.includes(c.id) ? 'Owner approval recorded: September 28, 2026' : c.review_revision ? 'Revised review: original policy + source policy' : 'New label awaiting your judgment');
  $('archivedReview').hidden = !state.archived_reviews[c.id];
  $('archivedReviewText').textContent = state.archived_reviews[c.id] ? pretty({original_policy_only: DATA.original_labels[c.id], previous_review: state.archived_reviews[c.id]}) : '';
  $('approve').textContent = pack().previously_approved ? 'Reconfirm original result' : 'Approve expected result';
  $('undo').textContent = pack().previously_approved ? 'Restore original approval' : 'Reset this review';
  $('removeCase').textContent = r.status === 'removed' ? 'Restore to review' : 'Remove from review';
  for (const id of ['approve', 'correct', 'undo', 'correctedLabel', 'correctedScope', 'notes']) $(id).disabled = r.status === 'removed';
}
function storeReview(c, status, label, scope) {
  state.reviews[c.id] = {...review(c), status, label, scope, notes: $('notes').value, updated_at: now()}; persist();
}
function record(status) {
  const c = current(); if (!c || review(c).status === 'removed') return;
  if (status === 'correction' && !$('notes').value.trim()) {message('Add a reason so the proposed correction can be applied accurately.'); $('notes').focus(); return;}
  const before = filtered(); const index = before.findIndex(x => x.id === c.id);
  storeReview(c, status, status === 'approved' ? expectedLabel(c) : $('correctedLabel').value, status === 'approved' ? expectedScope(c) : $('correctedScope').value);
  if ($('autoNext').checked) selectedId = before[index + 1]?.id ?? c.id;
  message(status === 'approved' ? 'Approved ' + c.id + '. Export your review when ready.' : 'Correction recorded for ' + c.id + '. The frozen source case is unchanged.');
  render();
}
function restoreRemoved(id) {
  const c = allCases.get(id)?.c; if (!c) return;
  const r = review(c); if (r.status !== 'removed') return;
  const {previous_status, removal_reason, ...restored} = r;
  state.reviews[id] = {...restored, status: previous_status ?? 'pending', updated_at: now()};
  packId = allCases.get(id).p.id;
  $('statusFilter').value = ''; $('search').value = ''; $('policyFilter').value = ''; $('releaseScopeFilter').value = '';
  selectedId = id; lastRemovedId = null; $('undoRemove').hidden = true;
  persist(); render(); message('Restored ' + id + ' to review.');
}
$('removeCase').onclick = () => {
  const c = current(); if (!c) return;
  const r = review(c); if (r.status === 'removed') {restoreRemoved(c.id); return;}
  state.reviews[c.id] = {...r, status: 'removed', previous_status: r.status, removal_reason: $('notes').value, notes: $('notes').value, updated_at: now()};
  lastRemovedId = c.id; $('undoRemove').hidden = false;
  persist(); render(); message('Removed ' + c.id + '. Undo now, or select Removed in the status filter to restore it later. Export review to apply this removal to the project.');
};
$('undoRemove').onclick = () => restoreRemoved(lastRemovedId);
$('approve').onclick = () => record('approved'); $('correct').onclick = () => record('correction');
$('notes').oninput = () => {
  const c = current(); if (!c) return; const r = review(c);
  // Removing a correction's explanation returns it to pending until explicitly saved again.
  storeReview(c, r.status === 'correction' && !$('notes').value.trim() ? 'pending' : r.status, r.label, r.scope);
  updateProgress(); renderList(filtered());
};
$('undo').onclick = () => { if (!current()) return; if (!confirm('Reset your review and notes for this case? The original label and any historical approval will be preserved.')) return; delete state.reviews[selectedId]; persist(); message('Original case review state restored.'); render(); };
$('reviewer').value = state.reviewer; $('reviewer').oninput = () => {state.reviewer = $('reviewer').value; persist();};
for (const id of ['search', 'policyFilter', 'statusFilter', 'releaseScopeFilter']) $(id).addEventListener(id === 'search' ? 'input' : 'change', render);
for (const [id, value] of [['tabHoldout', 'holdout'], ['tabSources', 'sources'], ['tabPrevious', 'previous']]) $(id).onclick = () => {packId = value; $('releaseScopeFilter').value = ''; $('statusFilter').value = ''; $('policyFilter').value = ''; $('search').value = ''; selectedId = null; render();};
function move(delta) {const list = filtered(); selectedId = list[list.findIndex(c => c.id === selectedId) + delta]?.id ?? selectedId; render();}
$('prev').onclick = () => move(-1); $('next').onclick = () => move(1);
$('nextPending').onclick = () => {
  const list = pack().cases; const index = list.findIndex(c => c.id === selectedId);
  const next = [...list.slice(index + 1), ...list.slice(0, index + 1)].find(c => review(c).status === 'pending');
  if (!next) {message('No pending cases in this packet.'); return;}
  $('search').value = ''; $('policyFilter').value = ''; $('statusFilter').value = ''; $('releaseScopeFilter').value = ''; selectedId = next.id; render();
};
$('approveRemaining').onclick = () => {
  const pending = pack().cases.filter(c => review(c).status === 'pending');
  if (pack().previously_approved || !pending.length || !confirm(`Confirm you have reviewed all ${pending.length} remaining cases in ${pack().title} and accept their ORIGINAL expected results, scopes and any stated combined-policy results. This covers all policies, regardless of filters. Flagged corrections will be preserved.`)) return;
  for (const c of pending) state.reviews[c.id] = {...review(c), status: 'approved', label: expectedLabel(c), scope: expectedScope(c), updated_at: now()};
  persist(); render(); message(pending.length + ' labels approved. Export review to hand off your decisions.');
};
function exportPayload() {
  return {format: 'humanwill.case-review/1', exported_at: now(), fingerprint, ...state,
    context_preview: {sha256: DATA.question_context_sha256, status: 'live_evaluated_once', approval_scope: 'Recorded approvals refer to original labels; the added context is a separate experiment.'},
    release_scope: {version: DATA.release_scope.version, sha256: DATA.release_scope_sha256, note: 'Retrospective capability grouping; cases and labels retained, not new accuracy evidence.'},
    reviews: {...Object.fromEntries((DATA.recorded_approvals ?? []).filter(id => !allCases.get(id).p.previously_approved).map(id => [id, review(allCases.get(id).c)])), ...state.reviews},
    removals: [...allCases.values()].filter(({c}) => review(c).status === 'removed').map(({c, p}) => ({id: c.id, packet: p.id, reason: review(c).removal_reason ?? review(c).notes, removed_at: review(c).updated_at, authority: DATA.default_removed[c.id]?.removed_at === review(c).updated_at ? (DATA.default_removed[c.id].authority ?? 'owner_instruction') : 'local_review'})),
    packets: DATA.packs.map(p => ({id: p.id, path: p.path, sha256: p.sha256, active_case_count: p.cases.filter(c => review(c).status !== 'removed').length, original_approval_date: p.approval_date,
      cases: p.cases.map(c => ({id: c.id, policy_id: c.policy_id, original_expected: c.expected, original_scope: c.expected_scope, reviewed_expected: expectedLabel(c), reviewed_scope: expectedScope(c), review_revision: c.review_revision ?? null, ...(c.expected_composed ? {original_composed: c.expected_composed, original_by_policy: c.expected_by_policy} : {}), ...review(c), provenance: state.reviews[c.id] ? 'local_review' : (p.previously_approved ? 'historical_owner_approval' : DATA.recorded_approvals?.includes(c.id) ? 'recorded_owner_approval' : 'unreviewed')}))})),
    note: 'Local review decisions and explicit removals. Removed cases are excluded from the active review denominator, never counted as approvals. Apply exported changes to the project before evaluation; historical evidence is retained.'};
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
    if (imported.format !== 'humanwill.case-review/1' || ![fingerprint, DATA.compatible_fingerprint, ...legacyFingerprints].includes(imported.fingerprint)) throw Error('This review belongs to different datasets or policies. Nothing was imported.');
    const legacy = legacyFingerprints.includes(imported.fingerprint);
    const clean = validateState(imported, legacy, imported.fingerprint !== fingerprint);
    if (imported.fingerprint === DATA.legacy_fingerprint && Object.keys(clean.reviews).some(id => allCases.get(id).p.id === 'sources')) throw Error('Old-format reviews cannot approve the new source-policy cases.');
    if (!confirm('Replace this browser’s current review with the imported review? Export first if you need to preserve your current progress.')) return;
    state = clean; $('reviewer').value = state.reviewer; persist(); render(); message(legacy ? 'Imported unchanged reviews; original 100-case reviews retained as history. Revised 100-case approvals remain pending.' : 'Review restored from file.');
  } catch (error) {message(error.message);} finally {event.target.value = '';}
};
$('fingerprints').textContent = DATA.packs.map(p => p.title + '\nSHA-256 ' + p.sha256).join('\n\n');
persist(); render();
