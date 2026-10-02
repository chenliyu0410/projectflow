// 部門模型測試（由 tests/records.html 以 iframe.contentWindow.eval 載入，在 Demo 全域環境內執行）
(async () => {
  const results = [];
  const eq = (a, b, m) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${m || ''} 預期 ${JSON.stringify(b)}，實際 ${JSON.stringify(a)}`); };
  const ok = (v, m) => { if (!v) throw new Error(m || '預期為真'); };
  const as = (u) => { ui.me = u; };
  const T = async (name, fn) => {
    try { await resetAll(); as('yu'); await fn(); results.push({ name, ok: true }); }
    catch (e) { results.push({ name, ok: false, err: String(e && e.stack || e) }); }
  };
  const USERS_ALL = ['yu', 'ming', 'an', 'hua', 'chen', 'lin', 'it'];

  // ── Task 1：部門資料與升級 ──
  await T('種子資料：v4、10 個部門、任務都有負責部門', () => {
    eq(db.v, 4);
    eq(db.departments.map((d) => d.name), ['研發', '製程', '品保', '業務', '生管', '採購', '管理', '資訊', '財務', '製造']);
    eq(dept('d-qa').head, 'chen'); eq(dept('d-pe').head, null);
    const tasks = Object.values(db.nodes).filter((n) => n.type === 'task');
    ok(tasks.every((n) => dept(n.dept)), '每個任務都要有存在的負責部門');
    ok(Object.values(db.nodes).filter((n) => n.type !== 'task').every((n) => n.dept === null), '專案與階段沒有負責部門');
    eq(tasks.filter((n) => n.owner === null).map((n) => n.id).sort(), ['t404', 't504', 't605']);
    ok(tasks.every((n) => n.owner === null || USERS[n.owner].dept === n.dept), '負責人必須屬於負責部門');
  });
  await T('使用者部門與協作部門都存 id', () => {
    eq(USERS.an.dept, 'd-qa'); eq(USERS.lin.dept, 'd-sales'); eq(USERS.it.dept, 'd-it');
    eq(node('t301').depts, ['d-qa']); eq(node('t403').depts, ['d-sales']);
    eq(deptMembers('d-qa'), ['an', 'chen']); eq(deptName('nope'), '—');
    ok(isHead('chen', 'd-qa')); ok(!isHead('an', 'd-qa')); ok(!isHead('yu', null));
  });
  await T('模板節點都有負責部門，協作部門為 id', () => {
    ok(db.templates.every((t) => t.nodes.every((x) => dept(x.dept))), '每個模板節點都要有負責部門');
    eq(db.templates[0].nodes[1].dp, ['d-qa']);
  });
  await T('upgrade：v3 → v4 部門對應', () => {
    const d = seed(); d.v = 3; delete d.departments;
    Object.values(d.nodes).forEach((n) => { delete n.dept; if (n.owner === null) n.owner = 'yu'; });
    d.nodes.t301.depts = ['品保', '法規']; d.nodes.t403.depts = ['行銷']; d.nodes.t503.depts = ['生產', '外星部'];
    d.templates.forEach((t) => t.nodes.forEach((x) => { delete x.dept; x.dp = []; }));
    d.templates[0].nodes[1].dp = ['法規'];
    const au = freshAudit();
    const o = upgrade({ v: 3, db: d, audit: au });
    eq(o.v, 4); eq(o.db.v, 4); eq(o.db.departments.length, 10);
    eq(o.db.nodes.t301.depts, ['d-qa']); eq(o.db.nodes.t403.depts, ['d-sales']); eq(o.db.nodes.t503.depts, ['d-mfg', 'd-rd']);
    eq(o.db.nodes.t301.dept, 'd-pe'); eq(o.db.nodes.t4031.dept, 'd-sales'); eq(o.db.nodes.p1.dept, null);
    eq(o.db.templates[0].nodes[1].dp, ['d-qa']);
    ok(o.db.templates.every((t) => t.nodes.every((x) => x.dept)), '模板節點要補上負責部門');
    ok(au.acts.some((a) => a.text === '部門「外星部」已併入研發'), '要寫入合併的稽核紀錄');
  });
  await T('切換身分選單顯示部門名稱', () => {
    render();
    ok(document.getElementById('meSel').textContent.includes('品保'), '應顯示部門名稱');
    ok(!document.getElementById('meSel').textContent.includes('d-qa'), '不應顯示部門 id');
  });

  // ── 新測試加在這一行上面 ──
  return results;
})()
