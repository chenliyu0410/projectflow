// 在 Demo 的全域環境內執行（由 tests/records.html 以 iframe.contentWindow.eval 載入）
(async () => {
  const results = [];
  const eq = (a, b, m) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${m || ''} 預期 ${JSON.stringify(b)}，實際 ${JSON.stringify(a)}`); };
  const ok = (v, m) => { if (!v) throw new Error(m || '預期為真'); };
  const as = (u) => { ui.me = u; };
  const T = async (name, fn) => {
    try { await resetAll(); as('yu'); await fn(); results.push({ name, ok: true }); }
    catch (e) { results.push({ name, ok: false, err: String(e && e.stack || e) }); }
  };

  // ── Task 1：資料版本與儲存 ──
  await T('種子資料為 v4 且含四個新陣列', () => {
    eq(db.v, 4);
    ['reportFields', 'reports', 'notes', 'attachments'].forEach((k) => ok(Array.isArray(db[k]), k + ' 應為陣列'));
  });
  await T('種子資料：F0 測試有「F0 值」欄位，t3011 有已核准回報', () => {
    const f = db.reportFields.filter((x) => x.label === 'F0 值').map((x) => x.node_id).sort();
    eq(f, ['t3011', 't3013']);
    const r = db.reports.find((x) => x.node_id === 't3011');
    eq(r.status, 'approved'); eq(r.fields[0].value, 2.6);
  });
  await T('upgrade：v2 資料轉成 v4', () => {
    const d = seed(); d.v = 2;
    delete d.reportFields; delete d.reports; delete d.notes; delete d.attachments;
    d.overrides = [{ id: 'o1', gate: true, node: 'p1b', status: 'approved' }, { id: 'o2', node: 't302', status: 'pending' }];
    const o = upgrade({ v: 2, db: d, audit: freshAudit() });
    eq(o.v, 4); eq(o.db.v, 4);
    eq(o.db.overrides.map((x) => x.kind), ['gate', 'dep']);
    eq(o.db.reportFields.length, 2); eq(o.db.reports.length, 1);
    eq(o.db.notes, []); eq(o.db.attachments, []);
  });
  await T('fileStore：存入、讀出、清空', async () => {
    ok(await fileStore.check(), 'IndexedDB 應可使用');
    await fileStore.put('x1', new Blob(['hi'], { type: 'text/plain' }));
    eq(await (await fileStore.get('x1')).text(), 'hi');
    await fileStore.clear();
    eq(await fileStore.get('x1'), undefined);
  });

  // ── Task 2：完成回報 ──
  const good = { result: 'met', summary: '參數設定完成', finished_on: '2026-09-30', values: {} };
  await T('validateReport：必填與數字檢查', () => {
    eq(validateReport('t3013', { result: '', summary: '', finished_on: '', values: {} }), ['請選擇結果', '請填寫成果說明', '請填寫實際完成日', '請填寫「F0 值」']);
    eq(validateReport('t3013', { ...good, values: { f0: 'abc' } }), ['「F0 值」必須是數字']);
    eq(validateReport('t3013', { ...good, values: { f0: '3.1' } }), []);
  });
  await T('成員送出回報 → 審核中，回報為 submitted', async () => {
    as('ming');
    const r = await submitReport('t30121', good);
    ok(r.ok, JSON.stringify(r.errors));
    eq(node('t30121').status, 'review');
    eq(pendingReport('t30121').version, 1);
    eq(pendingReport('t30121').submitted_by, 'ming');
    ok(!canReport(node('t30121')), '待確認時不能重複送出');
  });
  await T('硬性前置未滿足時不能送出', async () => {
    as('ming');
    const r = await submitReport('t3013', { ...good, values: { f0: 3.1 } });
    ok(!r.ok && r.blocked, '應回傳 blocked');
    eq(node('t3013').status, 'todo'); eq(db.reports.filter((x) => x.node_id === 't3013').length, 0);
  });
  await T('成員不能確認；主管退回（意見必填）→ 進行中；重送 → v2；確認 → 已完成', async () => {
    as('ming'); await submitReport('t30121', good);
    const r1 = pendingReport('t30121');
    ok(!decideReport(r1.id, true), '成員不能確認');
    as('yu');
    ok(!decideReport(r1.id, false, '  '), '退回必須有意見');
    ok(decideReport(r1.id, false, '請附參數截圖'));
    eq(r1.status, 'rejected'); eq(r1.review_comment, '請附參數截圖'); eq(node('t30121').status, 'doing');
    as('ming'); await submitReport('t30121', { ...good, summary: '已附截圖' });
    const r2 = pendingReport('t30121'); eq(r2.version, 2);
    as('chen'); ok(decideReport(r2.id, true), '範圍內審核人可以確認');
    eq(r2.status, 'approved'); eq(r2.reviewed_by, 'chen'); eq(node('t30121').status, 'done');
  });
  await T('主管送出並直接確認', async () => {
    const r = await submitReport('t30121', good, { selfApprove: true });
    ok(r.ok); eq(r.report.status, 'approved'); eq(r.report.self_approved, true); eq(node('t30121').status, 'done');
  });
  await T('拖曳防呆：有待確認回報時，成員拖到已完成被擋，主管拖到已完成視同確認', async () => {
    as('ming'); await submitReport('t30121', good);
    ok(!setStatus('t30121', 'done')); eq(node('t30121').status, 'review');
    ok(!setStatus('t30121', 'doing')); eq(node('t30121').status, 'review');
    as('yu'); setStatus('t30121', 'done');
    eq(node('t30121').status, 'done'); eq(db.reports.find((x) => x.node_id === 't30121').status, 'approved');
  });
  await T('待審數量包含待確認回報', async () => {
    const before = pendingCount();
    as('ming'); await submitReport('t30121', good);
    as('yu'); eq(pendingCount(), before + 1);
  });

  await T('送出回報只產生一筆復原，復原後狀態與回報一併還原', async () => {
    as('ming');
    const st0 = node('t30121').status, n0 = undoStack.length;
    await submitReport('t30121', good);
    eq(undoStack.length, n0 + 1);
    undo();
    eq(node('t30121').status, st0); eq(db.reports.filter((x) => x.node_id === 't30121').length, 0);
  });
  await T('送出並直接確認只產生一筆復原', async () => {
    const st0 = node('t30121').status, n0 = undoStack.length;
    await submitReport('t30121', good, { selfApprove: true });
    eq(undoStack.length, n0 + 1);
    undo();
    eq(node('t30121').status, st0); eq(db.reports.filter((x) => x.node_id === 't30121').length, 0);
  });
  await T('確認／退回回報各只產生一筆復原，復原後回到待確認', async () => {
    as('ming'); await submitReport('t30121', good);
    const r = pendingReport('t30121');
    as('yu');
    let n0 = undoStack.length;
    decideReport(r.id, true);
    eq(undoStack.length, n0 + 1);
    undo();
    eq(node('t30121').status, 'review'); eq(pendingReport('t30121').id, r.id);
    n0 = undoStack.length;
    decideReport(r.id, false, '重做');
    eq(undoStack.length, n0 + 1);
    undo();
    eq(node('t30121').status, 'review'); eq(pendingReport('t30121').id, r.id);
  });
  await T('validateReport：選單欄位沒有 options 時不拋錯', () => {
    db.reportFields.push({ id: 'rfx', node_id: 't30121', key: 'sel', label: '選單', type: 'select', required: false, order: 99 });
    eq(validateReport('t30121', { ...good, values: { sel: 'a' } }), ['「選單」的選項不正確']);
  });

  // ── Task 3：自訂回報欄位 ──
  await T('新增、上移、移除回報欄位', () => {
    eq(addReportField('t30121', { label: '', type: 'text', extra: '', required: false }).ok, false);
    eq(addReportField('t30121', { label: '結果', type: 'select', extra: '只有一個', required: false }).error, '選項欄位至少要有 2 個選項');
    ok(addReportField('t30121', { label: '溫度', type: 'number', extra: '°C', required: true }).ok);
    ok(addReportField('t30121', { label: '設備', type: 'select', extra: 'R-1, R-2，R-3', required: false }).ok);
    let d = fieldDefs('t30121');
    eq(d.map((x) => x.label), ['溫度', '設備']); eq(d[0].unit, '°C'); eq(d[1].options, ['R-1', 'R-2', 'R-3']);
    moveReportField(d[1].id);
    eq(fieldDefs('t30121').map((x) => x.label), ['設備', '溫度']);
    removeReportField(d[1].id);
    eq(fieldDefs('t30121').map((x) => x.label), ['溫度']);
  });
  await T('另存模板與套用模板會帶著回報欄位', () => {
    const t = nodeToTemplate('t301');
    const withF = t.nodes.filter((x) => (x.fields || []).length);
    eq(withF.length, 2); eq(withF[0].fields[0].label, 'F0 值');
    const before = db.reportFields.filter((f) => f.label === 'F0 值').length;
    applyTemplate(t, 'p1c', { start: TODAY, vars: {}, structure: true, deps: false, owners: false, dates: true, docs: false });
    eq(db.reportFields.filter((f) => f.label === 'F0 值').length, before + 2);
  });
  await T('複製子樹帶欄位；刪除節點清掉欄位、回報、筆記並軟刪除附件', () => {
    const nid = copySubtree('t301');
    const copied = descendants(nid).map((x) => x.id);
    eq(db.reportFields.filter((f) => copied.includes(f.node_id)).length, 2);
    db.notes.push({ id: 'ntx', node_id: 't3011', body: 'x', author: 'yu', created_at: nowStr(), edited_at: null });
    db.attachments.push({ id: 'atx', node_id: 't3011', report_id: null, note_id: null, filename: 'a.txt', mime: 'text/plain', size: 1, sha256: '', storage_key: 'atx', uploaded_by: 'yu', uploaded_at: nowStr(), deleted_at: null });
    deleteNode('t301');
    eq(db.reportFields.filter((f) => ['t3011', 't3013'].includes(f.node_id)).length, 0);
    eq(db.reports.filter((r) => r.node_id === 't3011').length, 0);
    eq(db.notes.filter((x) => x.id === 'ntx').length, 0);
    ok(db.attachments.find((a) => a.id === 'atx').deleted_at, '附件應被軟刪除');
  });

  // ── Task 4：筆記與附件 ──
  const txt = (name, s) => new File([s], name, { type: 'text/plain' });
  await T('新增筆記；只有作者能修改，修改後標記已編輯並寫入稽核', () => {
    as('ming');
    eq(addNote('t30121', '   ').ok, false);
    const r = addNote('t30121', '設備溫度校正完成');
    ok(r.ok); eq(r.note.author, 'ming'); eq(r.note.edited_at, null);
    as('yu'); eq(editNote(r.note.id, '改掉').error, '只有作者可以修改筆記');
    as('ming'); ok(editNote(r.note.id, '設備溫度校正完成（121°C）').ok);
    ok(r.note.edited_at, '應有 edited_at');
    ok(audit.acts[0].text.includes('原內容：設備溫度校正完成'), '稽核紀錄應保留原內容');
  });
  await T('協作人員不能在未指派給他的任務寫筆記', () => { as('it'); ok(canNote(node('t30121'))); as('lin'); ok(!canNote(node('t30121'))); });
  await T('上傳附件：存入 IndexedDB、記錄中繼資料；超過 10 MB 被擋', async () => {
    as('ming');
    const big = new File([new Uint8Array(MAX_FILE + 1)], 'big.bin');
    const r = await addAttachments('t30121', [txt('參數.txt', '121C 30min'), big]);
    eq(r.added.length, 1); eq(r.errors, ['「big.bin」超過 10 MB，未上傳']);
    const a = r.added[0];
    eq([a.filename, a.size, a.uploaded_by, a.report_id, a.note_id], ['參數.txt', 10, 'ming', null, null]);
    eq(a.sha256.length, 64);
    eq(await (await fileStore.get(a.id)).text(), '121C 30min');
  });
  await T('刪除附件為軟刪除；回報附件不能刪除', async () => {
    as('ming');
    const a = (await addAttachments('t30121', [txt('a.txt', 'a')])).added[0];
    ok(deleteAttachment(a.id).ok); ok(db.attachments.find((x) => x.id === a.id).deleted_at);
    const rep = await submitReport('t30121', { result: 'met', summary: '完成', finished_on: '2026-09-30', values: {}, files: [txt('報告.txt', 'r')] });
    const ra = db.attachments.find((x) => x.report_id === rep.report.id);
    eq(ra.filename, '報告.txt');
    ok(!canDeleteAttachment(ra)); eq(deleteAttachment(ra.id).ok, false);
  });

  // ── Task 5：紀錄分頁與審核中心 ──
  await T('葉節點的紀錄分頁：回報按鈕、筆記表單、附件表單', () => {
    as('ming'); ui.page = 'node'; ui.node = 't30121'; ui.tab = 'records'; render();
    const m = document.getElementById('main');
    ok(m.querySelector('[data-tab="records"][aria-selected="true"]'), '應有「紀錄」分頁');
    ok(m.querySelector('[data-report="t30121"]'), '應有回報完成按鈕');
    ok(m.querySelector('#noteForm') && m.querySelector('#attForm'), '應有筆記與附件表單');
  });
  await T('上層節點的紀錄分頁彙總子樹且唯讀', () => {
    ui.page = 'node'; ui.node = 't301'; ui.tab = 'records'; render();
    const m = document.getElementById('main');
    ok(m.textContent.includes('F0 = 2.6'), '應顯示子任務 t3011 的回報');
    ok(!m.querySelector('#noteForm') && !m.querySelector('[data-report]'), '上層節點不能新增');
  });
  await T('回報對話框含自訂欄位；看板卡片有回報按鈕', () => {
    as('yu'); ui.page = 'node'; ui.node = 't3012'; ui.tab = 'board'; render();
    ok(document.querySelector('.card [data-report="t30121"]'), '進行中的卡片應有回報按鈕');
    openReportDialog('t3013');
    ok(document.getElementById('rv_f0'), '應有 F0 值欄位');
    ok(document.querySelector('#reportForm button[value="self"]'), '主管應有「送出並直接確認」');
    closeDlg();
  });
  await T('審核中心列出待確認回報', async () => {
    as('ming'); await submitReport('t30121', { result: 'met', summary: '完成', finished_on: '2026-09-30', values: {} });
    as('yu'); ui.page = 'review'; render();
    const m = document.getElementById('main');
    ok(m.textContent.includes('待確認的完成回報（1）'));
    ok(m.querySelector(`[data-rep-approve="${pendingReport('t30121').id}"]:not([disabled])`));
  });

  // ── Task 6：跳過任務 ──
  await T('成員申請跳過 → 範圍內審核人核准 → 已跳過、進度 100%', () => {
    node('t30122').owner = 'an'; as('an');
    eq(skipTask('t30122', '').error, '請填寫理由');
    const r = skipTask('t30122', '品保已在現場確認');
    eq(r.mode, 'requested'); eq(node('t30122').status, 'todo');
    const o = pendingSkip('t30122'); eq(o.kind, 'task');
    eq(skipTask('t30122', '再申請一次').error, '已有待審核的跳過申請');
    as('chen'); decideOverride(o.id, true);
    eq(node('t30122').status, 'skipped'); eq(prog(node('t30122')), 100); eq(o.prev, { t30122: 'todo' });
  });
  await T('主管直接跳過上層任務：未完成子任務一起跳過；恢復後回到原狀態', () => {
    const r = skipTask('t3012', '改用新的殺菌釜，不需調整');
    eq(r.mode, 'skipped');
    eq(['t3012', 't30121', 't30122'].map((id) => node(id).status), ['skipped', 'skipped', 'skipped']);
    ok(!canReport(node('t30121')), '已跳過不能送回報');
    ok(restoreTask('t3012').ok);
    eq(['t3012', 't30121', 't30122'].map((id) => node(id).status), ['doing', 'doing', 'todo']);
  });
  await T('跳過時自動結案待確認的回報', async () => {
    as('ming'); await submitReport('t30121', { result: 'met', summary: '完成', finished_on: '2026-09-30', values: {} });
    as('yu'); skipTask('t30121', '不需要了');
    const rep = db.reports.find((x) => x.node_id === 't30121');
    eq(rep.status, 'rejected'); eq(rep.review_comment, '任務已跳過，回報自動結案');
  });
  await T('只恢復被連帶跳過的子任務時，只動它自己', () => {
    skipTask('t3012', '整段不做');
    ok(restoreTask('t30122').ok);
    eq(['t3012', 't30121', 't30122'].map((id) => node(id).status), ['doing', 'skipped', 'todo']);
  });
  await T('成員不能恢復；編輯器狀態選單不提供「已跳過」', () => {
    skipTask('t30122', '不做');
    as('ming'); eq(restoreTask('t30122').ok, false);
    as('yu'); openEditor('t30121');
    ok(![...document.querySelectorAll('#eStatus option')].some((o) => o.value === 'skipped'), '未跳過的任務不能從選單選「已跳過」');
    ok(document.querySelector('#edForm [data-skip="t30121"]'), '編輯器應有跳過按鈕');
    closeDrawer();
  });
  await T('成員不能拖曳已跳過的卡片來恢復任務', () => {
    node('t30122').owner = 'an'; skipTask('t30122', '不做');
    as('an'); ok(canWork(node('t30122')), '小安是負責人，擋下她的是「已跳過」防護'); eq(setStatus('t30122', 'doing'), false); eq(node('t30122').status, 'skipped');
  });
  await T('成員不能核准跳過申請', () => {
    node('t30122').owner = 'an'; as('an'); skipTask('t30122', '想跳過');
    const o = pendingSkip('t30122'); decideOverride(o.id, true);
    eq(o.status, 'pending'); eq(node('t30122').status, 'todo');
  });
  await T('既有覆寫紀錄帶有 kind', () => {
    as('ming'); submitBlock('t3013', 'doing', '先開始');
    eq(db.overrides[0].kind, 'dep');
  });

  // ── Task 7：AI 可查詢回報與筆記 ──
  await T('recordHits 找得到 F0 回報；機密節點不會被引用', () => {
    const hits = recordHits(node('p1'), 'F0 測試結果');
    ok(hits.length && hits[0].includes('2.6'), JSON.stringify(hits));
    db.notes.push({ id: 'ntc', node_id: 't1022', body: '機密配方比例 62%', author: 'yu', created_at: nowStr(), edited_at: null });
    ok(!recordsSnapshot(node('p1')).includes('機密配方比例'), '機密節點（t1022）的筆記不能出現');
  });
  await T('專案問答：問回報會回答並寫入 AI 稽核', () => {
    ui.page = 'node'; ui.node = 'p1';
    const n0 = audit.ai.length;
    aiAsk('第 1 次 F0 測試的回報結果是多少');
    eq(audit.ai.length, n0 + 1);
    ok(ui.chat.at(-1).text.includes('2.6'), ui.chat.at(-1).text);
  });

  // ── 最終審查修正 ──
  await T('確認回報時重新檢查硬性前置（FF）：前置未完成不能確認', async () => {
    node('t4031').status = 'done';
    as('an'); const r = await submitReport('t4032', good);
    ok(r.ok, JSON.stringify(r.errors));
    as('yu'); eq(decideReport(r.report.id, true), false);
    eq(node('t4032').status, 'review'); eq(r.report.status, 'submitted');
    eq(db.overrides.filter((o) => o.node === 't4032').length, 0);
  });
  await T('自行確認時也重新檢查硬性前置（FF）', async () => {
    node('t4031').status = 'done';
    const r = await submitReport('t4032', good, { selfApprove: true });
    ok(!r.ok, '應拒絕自行確認');
    ok(node('t4032').status !== 'done', '不能變成已完成');
  });
  await T('待確認回報的任務加入子任務：回報自動結案，之後不能確認', async () => {
    as('ming'); await submitReport('t30121', good);
    const rep = pendingReport('t30121');
    as('yu'); commit('新增', () => addNode('t30121', { title: '補測' }));
    eq(rep.status, 'rejected'); ok(rep.review_comment, '應有說明');
    eq(pendingReport('t30121'), null);
    eq(decideReport(rep.id, true), false); ok(node('t30121').status !== 'done', '不能變成已完成');
    ok(audit.acts.some((a) => a.node === 't30121' && a.action === '完成回報' && a.text.includes('結案')), '應寫入稽核紀錄');
  });
  await T('待確認回報的任務被移入子任務：回報自動結案', async () => {
    as('ming'); await submitReport('t30121', good);
    const rep = pendingReport('t30121');
    as('yu'); moveNode('t30122', 't30121');
    eq(rep.status, 'rejected'); eq(pendingReport('t30121'), null);
    ok(node('t30121').status !== 'review', '不能停在審核中');
  });
  await T('非葉節點的回報不能確認', async () => {
    as('ming'); await submitReport('t30121', good);
    const rep = pendingReport('t30121');
    db.nodes.zz = { ...clone(node('t30122')), id: 'zz', parent: 't30121', status: 'todo' };
    as('yu'); eq(decideReport(rep.id, true), false); ok(node('t30121').status !== 'done', '不能變成已完成');
  });
  await T('跳過任務時結案其上的前置跳過申請；核准舊申請不會改回進行中', () => {
    as('ming'); submitBlock('t3013', 'doing', '先開始');
    const o = db.overrides[0]; eq(o.status, 'pending');
    as('yu'); skipTask('t3013', '不做了');
    eq(o.status, 'rejected');
    ok(audit.acts.some((a) => a.node === 't3013' && a.text.includes('結案')), '應寫入稽核紀錄');
    decideOverride(o.id, true); eq(node('t3013').status, 'skipped');
    o.status = 'pending'; decideOverride(o.id, true); eq(node('t3013').status, 'skipped');
  });
  await T('跳過上層任務時結案子任務的跳過申請；恢復後子任務回到原狀態', () => {
    node('t30122').owner = 'an'; as('an'); skipTask('t30122', '想跳過');
    const o = pendingSkip('t30122');
    as('yu'); skipTask('t3012', '整段不做');
    eq(o.status, 'rejected');
    decideOverride(o.id, true);
    ok(restoreTask('t3012').ok);
    eq(node('t30122').status, 'todo');
  });
  await T('待確認回報時被跳過，恢復後回到進行中', async () => {
    as('ming'); await submitReport('t30121', good);
    as('yu'); skipTask('t30121', '不需要了');
    ok(restoreTask('t30121').ok);
    eq(node('t30121').status, 'doing');
  });

  // ── 子任務置頂回報卡：reportCardHTML ──
  const card = (id) => { const d = document.createElement('div'); d.innerHTML = reportCardHTML(node(id)); return d; };
  await T('回報卡：待辦／進行中顯示需填欄位、確認人與「回報完成」', () => {
    as('ming');
    const c = card('t3013');
    ok(c.textContent.includes('完成回報'), '標題');
    ok(c.textContent.includes('F0 值'), '應列出必填自訂欄位');
    ok(c.textContent.includes('力瑜'), '應列出確認人');
    const c2 = card('t30121');
    ok(c2.querySelector('[data-report="t30121"]'), '可回報時應有「回報完成」');
  });
  await T('回報卡：待確認時成員看到等待，主管看到確認／退回', async () => {
    as('ming'); await submitReport('t30121', good);
    let c = card('t30121');
    ok(c.querySelector('.rcard.pend'), '待確認色');
    ok(c.textContent.includes('v1 等待確認') && c.textContent.includes('參數設定完成'));
    ok(c.textContent.includes('阿明 送出') && c.textContent.includes(pendingReport('t30121').submitted_at), '顯示送出者與時間');
    const acts = c.querySelector('.rc-acts').textContent;
    ok(acts.includes('等待') && acts.includes('力瑜'), `成員看到「等待 … 確認」（${acts}）`);
    ok(!c.querySelector('[data-rep-approve]') && !c.querySelector('[data-rep-reject]'), '成員不能確認或退回');
    as('yu'); c = card('t30121');
    const id = pendingReport('t30121').id;
    ok(c.querySelector(`[data-rep-approve="${id}"]`) && c.querySelector(`[data-rep-reject="${id}"]`), '主管有確認與退回');
  });
  await T('回報卡：已退回顯示意見與「重新回報」', async () => {
    as('ming'); await submitReport('t30121', good);
    as('yu'); decideReport(pendingReport('t30121').id, false, '溫度紀錄不完整');
    as('ming'); const c = card('t30121');
    ok(c.querySelector('.rcard.rej'), '退回色');
    ok(c.textContent.includes('溫度紀錄不完整') && c.textContent.includes('（力瑜）'), '應顯示退回意見與退回人');
    ok(c.querySelector('[data-report="t30121"]') && c.textContent.includes('重新回報'));
  });
  await T('回報卡：已完成有回報顯示自訂欄位；沒有回報顯示未附回報', () => {
    const c = card('t3011');
    ok(c.textContent.includes('已完成') && c.textContent.includes('F0 值') && c.textContent.includes('2.6'));
    eq(c.querySelector('.rcard dl.kv dd').textContent, '2.6', '自訂欄位的值');
    ok(c.textContent.includes('確認：陳主管 2026/09/13 09:05'), '顯示確認人與時間');
    ok(!c.querySelector('button'), '已完成沒有按鈕');
    node('t30121').status = 'done';
    ok(card('t30121').textContent.includes('已完成，未附回報'));
  });
  await T('回報卡：已跳過顯示理由，主管有「恢復任務」', () => {
    skipTask('t30121', '改由外包處理');
    const c = card('t30121');
    ok(c.querySelector('.rcard.skip') && c.textContent.includes('改由外包處理'));
    ok(c.querySelector('[data-restore="t30121"]'), '主管可恢復');
    as('ming'); ok(!card('t30121').querySelector('[data-restore]'), '成員不能恢復');
  });
  await T('回報卡：協作人員沒有任何動作按鈕', async () => {
    as('lin'); ok(!card('t30121').querySelector('button'), '待辦時沒有按鈕');
    as('ming'); await submitReport('t30121', good);
    as('lin'); ok(!card('t30121').querySelector('button'), '待確認時沒有按鈕');
  });
  await T('回報卡：使用者文字經過 esc()', async () => {
    as('ming'); await submitReport('t30121', { ...good, summary: '<b>粗體</b>' });
    const c = card('t30121');
    ok(!c.querySelector('.rcard b') && c.textContent.includes('<b>粗體</b>'), '摘要不能變成 HTML');
  });
  await T('回報卡：窄螢幕時動作欄換到內容下方，寬螢幕維持同一列', async () => {
    as('ming'); await submitReport('t30121', good);
    const box = document.createElement('div');
    box.style.cssText = 'position:fixed;left:0;top:0;visibility:hidden';
    document.body.appendChild(box);
    try {
      for (const u of ['ming', 'yu']) {
        as(u);
        for (const [w, wrap] of [[343, true], [800, false]]) {
          box.style.width = w + 'px';
          box.innerHTML = reportCardHTML(node('t30121'));
          const m = box.querySelector('.rc-main').getBoundingClientRect();
          const a = box.querySelector('.rc-acts').getBoundingClientRect();
          ok((a.top >= m.bottom - 1) === wrap, `${u} ${w}px：動作欄${wrap ? '應換到內容下方' : '應和內容同一列'}（內容寬 ${Math.round(m.width)}px）`);
        }
      }
    } finally { box.remove(); }
  });

  // ── 子任務置頂回報卡：任務頁整合 ──
  const page = (id) => { ui.page = 'node'; ui.node = id; render(); return document.getElementById('main'); };
  await T('葉任務頁：回報卡在分頁列上方，紀錄是第一個分頁', () => {
    as('ming'); ui.tab = 'board'; const m = page('t30121');
    const c = m.querySelector('.rcard'), bar = m.querySelector('.toolbar');
    ok(c && bar, '應有回報卡與分頁列');
    ok(c.compareDocumentPosition(bar) & Node.DOCUMENT_POSITION_FOLLOWING, '回報卡在分頁列之前');
    eq(m.querySelector('.tabs .tab').dataset.tab, 'records');
    ok(m.querySelector('.rcard'), '切到其他分頁仍顯示回報卡');
  });
  await T('葉任務頁：新增子任務改成分頁列右側的次要按鈕', () => {
    as('yu'); ui.tab = 'board'; const m = page('t30121');
    ok(!m.querySelector('.head-actions [data-add-child]'), '標題區不再有新增子任務');
    const b = m.querySelector('.tools [data-add-child="t30121"]');
    ok(b && !b.classList.contains('primary') && b.classList.contains('sm'), '分頁列右側次要按鈕');
  });
  await T('非葉節點的任務頁不變', () => {
    as('yu'); ui.tab = 'board'; const m = page('t3012');
    ok(!m.querySelector('.rcard'), '上層任務沒有回報卡');
    ok(m.querySelector('.head-actions .btn.primary[data-add-child="t3012"]'), '標題區仍有主要按鈕');
    eq(m.querySelector('.tabs .tab').dataset.tab, 'board');
  });
  await T('葉任務的紀錄分頁只列回報歷史；確認按鈕只在回報卡', async () => {
    as('ming'); await submitReport('t30121', good);
    as('yu'); ui.tab = 'records'; const m = page('t30121');
    ok(m.querySelector('.records').textContent.includes('回報歷史（1）'));
    eq(m.querySelectorAll('[data-rep-approve]').length, 1, '確認按鈕只出現一次');
    ok(m.querySelector('.rcard [data-rep-approve]'), '確認按鈕在回報卡');
    ok(!m.querySelector('.records [data-report]'), '紀錄分頁不再有回報完成按鈕');
  });
  await T('已跳過的葉任務：提示與恢復按鈕只在回報卡', () => {
    as('yu'); skipTask('t30121', '改由外包處理'); ui.tab = 'records'; const m = page('t30121');
    eq(m.querySelectorAll('[data-restore="t30121"]').length, 1, '恢復按鈕只出現一次');
    ok(m.querySelector('.rcard [data-restore]'));
    ok(!m.querySelector('.head').textContent.includes('已跳過・'), '標題區不重複顯示跳過提示');
  });
  await T('enter()：進入葉任務預設紀錄分頁；回到上層從紀錄改回看板', () => {
    as('yu'); ui.tab = 'timeline';
    enter('t30121'); eq(ui.tab, 'records');
    enter('t3012'); eq(ui.tab, 'board');
    ui.tab = 'timeline'; enter('t301'); eq(ui.tab, 'timeline', '非紀錄分頁維持不變');
  });
  await T('節點頁：紀錄、文件、資料、成員分頁讓主區域可以上下捲動；看板、時程、相依圖不變', () => {
    const m = document.getElementById('main');
    for (const [tab, on] of [['records', true], ['docs', true], ['data', true], ['people', true], ['board', false], ['timeline', false], ['graph', false]]) {
      ui.page = 'node'; ui.node = 't30121'; ui.tab = tab; render();
      eq(m.classList.contains('vscroll'), on, tab);
      ok(m.querySelector('.rcard'), `${tab}：顯示回報卡`);
      ok(m.querySelector('.tools [data-add-child="t30121"]'), `${tab}：分頁列有新增子任務`);
    }
    ui.page = 'overview'; ui.tab = 'records'; render();
    ok(!m.classList.contains('vscroll'), '非節點頁不加 vscroll');
    const rule = [...document.styleSheets].flatMap((s) => { try { return [...s.cssRules]; } catch (e) { return []; } }).find((r) => r.selectorText === '.main.vscroll');
    ok(rule && rule.style.overflowY === 'auto', '.main.vscroll 要讓主區域上下捲動');
  });
  await T('enter()：換到別的節點時，主區域捲回最上面', () => {
    as('yu');
    for (let i = 1; i <= 4; i++) addNote('t3011', `第 ${i} 則筆記\n` + '殺菌條件驗證紀錄。'.repeat(10));
    const m = document.getElementById('main');
    enter('t301'); ui.tab = 'records'; render();
    m.scrollTop = 200;
    ok(m.scrollTop > 0, '前置：上層的紀錄分頁要可以捲動');
    enter('t3011');
    eq(m.scrollTop, 0, '進入子任務後應從頁首開始');
  });
  await T('桌面版面：從捲動過的紀錄分頁切到看板、時程、相依圖，主區域回到頁首', () => {
    const fr = window.frameElement, w = fr && fr.style.width;
    if (fr) { fr.style.width = '1200px'; fr.getBoundingClientRect(); } // 測試頁寬度不固定，先撐到桌面版面
    try {
      for (let i = 1; i <= 4; i++) addNote('t3011', `第 ${i} 則筆記\n` + '殺菌條件驗證紀錄。'.repeat(10));
      const m = document.getElementById('main');
      const tab = (t) => m.querySelector(`.tabs [data-tab="${t}"]`).click();
      enter('t301');
      for (const t of ['board', 'timeline', 'graph']) {
        tab('records'); m.scrollTop = m.scrollHeight;
        ok(m.scrollTop > 0, '前置：紀錄分頁要可以捲動');
        eq(getComputedStyle(m).overflowY, 'auto', '桌面版面的紀錄分頁可以捲動主區域');
        const y = m.scrollTop; render();
        eq(m.scrollTop, y, '可以捲動的分頁重新渲染時維持位置');
        tab(t);
        eq(getComputedStyle(m).overflowY, 'hidden', `前置：桌面版面的 ${t} 分頁不能捲動主區域`);
        eq(m.scrollTop, 0, `${t}：主區域不能捲動時應回到頁首`);
      }
    } finally { if (fr) fr.style.width = w; }
  });
  await T('回報卡：成果說明最多顯示約 6 行，超過的在卡片內捲動；完整內容在回報歷史（D16）', async () => {
    as('ming'); await submitReport('t30121', { ...good, summary: Array.from({ length: 15 }, (_, i) => `第 ${i + 1} 行：設備參數調整紀錄。`).join('\n') });
    const fr = window.frameElement, w = fr && fr.style.width;
    if (fr) { fr.style.width = '1200px'; fr.getBoundingClientRect(); } // 寬度太窄時會多出橫向捲軸，量不到真正的行數
    try {
      as('yu'); ui.tab = 'records'; const m = page('t30121');
      const s = m.querySelector('.rcard .rc-sum'), lh = parseFloat(getComputedStyle(s).lineHeight);
      ok(s.clientHeight <= lh * 6 + 1, `卡片上最多約 6 行（高 ${s.clientHeight}px，行高 ${lh}px）`);
      ok(s.clientHeight >= lh * 6 - 1, `卡片上至少顯示約 6 行（高 ${s.clientHeight}px）`);
      ok(s.scrollHeight > s.clientHeight + lh, '超過的部分在卡片內捲動');
      eq(getComputedStyle(s).overflowY, 'auto');
      ok(m.querySelector('.records').textContent.includes('第 15 行'), '回報歷史有完整內容');
    } finally { if (fr) fr.style.width = w; }
  });
  await T('子任務頁新增第一個子任務或套用模板後，從紀錄分頁改到看板（D17）', () => {
    as('yu'); enter('t30121'); eq(ui.tab, 'records', '前置：子任務預設紀錄分頁');
    const m = document.getElementById('main');
    m.querySelector('.tools [data-add-child="t30121"]').click();
    document.getElementById('qTitle').value = '設備儀表校正'; document.getElementById('qaForm').requestSubmit();
    ok(!isLeaf(node('t30121')), '前置：已變成上層任務');
    eq(ui.tab, 'board', '新增後切到看板');
    ok(!m.classList.contains('vscroll'), '切到看板後主區域不再捲動');
    ok(document.getElementById('view').textContent.includes('設備儀表校正'), '看板上看得到新的子任務');
    ui.tab = 'records'; render();
    m.querySelector('[data-add-child="t30121"]').click();
    document.getElementById('qTitle').value = '第二個子任務'; document.getElementById('qaForm').requestSubmit();
    eq(ui.tab, 'records', '本來就是上層任務時維持原分頁');
    enter('t30122'); eq(ui.tab, 'records', '前置：另一個子任務');
    openApplyTpl('t30122', null, 'tpl'); document.getElementById('tplForm').requestSubmit();
    ok(!isLeaf(node('t30122')), '前置：套用模板後變成上層任務');
    eq(ui.tab, 'board', '套用模板後也切到看板');
    enter('t3013'); ui.tab = 'timeline'; render();
    m.querySelector('.tools [data-add-child="t3013"]').click();
    document.getElementById('qTitle').value = '時程上新增'; document.getElementById('qaForm').requestSubmit();
    ok(!isLeaf(node('t3013')), '前置：t3013 已變成上層任務');
    eq(ui.tab, 'timeline', '不在紀錄分頁時維持原分頁');
  });
  await T('回報卡：自行確認、「需填」只列必填欄位、已完成優先於最新一版退回', async () => {
    as('yu'); await submitReport('t30121', good, { selfApprove: true });
    ok(card('t30121').textContent.includes('自行確認：力瑜'), '自行確認要標示');
    ok(addReportField('t30122', { label: '備註', type: 'text', required: false }).ok, '前置：加選填欄位');
    ok(addReportField('t30122', { label: '殘留量', type: 'number', required: true }).ok, '前置：加必填欄位');
    const need = card('t30122').textContent;
    ok(need.includes('殘留量') && !need.includes('備註'), `「需填」只列必填欄位（${need}）`);
    const r1 = db.reports.find((r) => r.node_id === 't3011');
    db.reports.push({ ...r1, id: 'r-t3011-v2', version: 2, status: 'rejected', review_comment: '請補數據', reviewed_by: 'yu', reviewed_at: '2026/09/20 10:00' });
    const c = card('t3011');
    ok(c.textContent.includes('確認：陳主管') && !c.textContent.includes('未附回報') && !c.querySelector('.rcard.rej'), '已完成而且有核准版本時，顯示核准的那一版，不因最新一版退回而顯示退回');
  });

  // ── 新測試加在這一行上面 ──
  return results;
})()
