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

  // ── 新測試加在這一行上面 ──
  return results;
})()
