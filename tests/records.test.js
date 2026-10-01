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
  await T('種子資料為 v3 且含四個新陣列', () => {
    eq(db.v, 3);
    ['reportFields', 'reports', 'notes', 'attachments'].forEach((k) => ok(Array.isArray(db[k]), k + ' 應為陣列'));
  });
  await T('種子資料：F0 測試有「F0 值」欄位，t3011 有已核准回報', () => {
    const f = db.reportFields.filter((x) => x.label === 'F0 值').map((x) => x.node_id).sort();
    eq(f, ['t3011', 't3013']);
    const r = db.reports.find((x) => x.node_id === 't3011');
    eq(r.status, 'approved'); eq(r.fields[0].value, 2.6);
  });
  await T('upgrade：v2 資料轉成 v3', () => {
    const d = seed(); d.v = 2;
    delete d.reportFields; delete d.reports; delete d.notes; delete d.attachments;
    d.overrides = [{ id: 'o1', gate: true, node: 'p1b', status: 'approved' }, { id: 'o2', node: 't302', status: 'pending' }];
    const o = upgrade({ v: 2, db: d, audit: freshAudit() });
    eq(o.v, 3); eq(o.db.v, 3);
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

  // ── 新測試加在這一行上面 ──
  return results;
})()
