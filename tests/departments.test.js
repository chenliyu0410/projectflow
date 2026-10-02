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

  await T('AI 問答：工作量不把未指派任務算成「null」', () => {
    ui.page = 'node'; ui.node = 'p1'; render();
    aiAsk('誰負責最多工作？');
    const t = ui.chat.at(-1).text;
    ok(t.includes('未完成任務分布') && t.includes('阿明'), t);
    ok(!t.includes('null'), '回答不應出現 null：' + t);
  });
  await T('AI 風險分析：工作量最重排除未指派任務', () => {
    ui.page = 'node'; ui.node = 'p1'; render();
    descendants('p1').filter((x) => isLeaf(x) && x.type === 'task' && x.status !== 'done').forEach((x) => { x.owner = null; });
    aiAction('risk');
    const t = ui.chat.at(-1).text;
    ok(t.includes('工作量最重：無'), '全部未指派時應顯示「無」：' + t);
    ok(!t.includes('null'), '回答不應出現 null');
  });
  await T('採購單建立驗收任務：協作部門存 id，模板節點都有負責部門', () => {
    const po = db.ops.pos[0];
    const orig = window.applyTemplate; let tpl = null;
    window.applyTemplate = (t, ...rest) => { tpl = t; return orig(t, ...rest); };
    const btn = document.createElement('button'); btn.type = 'button'; btn.dataset.poTask = po.id; document.body.appendChild(btn);
    try { btn.click(); } finally { window.applyTemplate = orig; btn.remove(); }
    ok(tpl, '應該呼叫 applyTemplate');
    ok(tpl.nodes.every((x) => x.dept === 'd-qa'), '模板根節點與子節點的負責部門都是品保');
    eq(tpl.nodes.filter((x) => x.p === 'r').map((x) => x.dp), [['d-qa'], ['d-qa'], ['d-qa'], ['d-qa']]);
    eq(tpl.nodes[0].dp, []);
    const root = Object.values(db.nodes).find((n) => n.title === `到貨驗收：${po.id}`);
    ok(root, '應該建立驗收任務');
    const subs = kids(root.id);
    eq(subs.length, 4);
    ok(subs.every((n) => JSON.stringify(n.depts) === JSON.stringify(['d-qa'])), '子任務的協作部門應該是 ["d-qa"]');
    ok(subs.every((n) => deptName(n.depts[0]) === '品保'));
  });
  await T('upgrade：模板節點負責部門依序取負責人、第一個協作部門、研發', () => {
    const d = seed(); d.v = 3; delete d.departments;
    Object.values(d.nodes).forEach((n) => { delete n.dept; if (n.owner === null) n.owner = 'yu'; });
    d.templates.forEach((t) => t.nodes.forEach((x) => { delete x.dept; delete x.who; x.dp = []; }));
    const ns = d.templates[0].nodes;
    ns[1].who = 'hua'; ns[1].tag = '檢驗'; ns[1].dp = [];
    ns[2].tag = '採購'; ns[2].dp = ['法規'];
    ns[3].tag = '採購'; ns[3].dp = [];
    const o = upgrade({ v: 3, db: d, audit: freshAudit() });
    const out = o.db.templates[0].nodes;
    eq(out[1].dept, 'd-pur', '有負責人時取負責人的部門');
    eq(out[2].dept, 'd-qa', '沒有負責人時取第一個協作部門');
    eq(out[3].dept, 'd-rd', '都沒有時用研發，不看類別');
  });

  // ── 新測試加在這一行上面 ──
  return results;
})()
