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

  // ── Task 2：可見性 ──
  const see = (u, id) => { as(u); return visible(node(id)); };
  const who = (id) => USERS_ALL.filter((u) => see(u, id));
  await T('未指派任務：只有部門主管、專案負責人、系統管理員看得到', () => {
    eq(who('t404'), ['yu', 'chen', 'it']);
  });
  await T('未指派且部門沒有主管：只有專案負責人與系統管理員', () => {
    eq(who('t504'), ['yu', 'it']);
  });
  await T('已指派：負責人、部門主管、協作人員、協作部門主管、範圍內審核人', () => {
    eq(who('t30121'), ['yu', 'ming', 'chen', 'it']);
    eq(who('t403'), ['yu', 'an', 'chen', 'lin', 'it']);
    eq(who('t802'), ['yu', 'hua', 'chen', 'it']);
  });
  await T('同部門成員看不到已指派給別人的任務', () => {
    eq(see('an', 't30122'), false);
  });
  await T('路徑：負責子任務的人看得到上層與專案的所有階段；負責上層的人看得到子任務', () => {
    node('t30122').owner = 'an';
    ok(see('an', 't3012'), '看得到上層任務'); ok(see('an', 'p1'), '看得到專案'); ok(see('an', 'p1a'), '看得到同專案的其他階段');
    ok(!see('an', 't3013'), '看不到旁支任務');
    ok(see('ming', 't30122'), '負責上層任務的人看得到子任務');
  });
  await T('未指派的子任務：負責上層任務的人也看不到', () => {
    db.nodes['t-un'] = { ...clone(node('t30122')), id: 't-un', owner: null, dept: 'd-pe', collabs: [], depts: [] };
    eq(see('ming', 't-un'), false); eq(see('yu', 't-un'), true);
  });
  await T('唯讀角色看得到全部；看不到任何任務的專案不顯示', () => {
    ok(seeNode(node('t504'), { id: 'x', role: 'readonly', dept: 'd-it' }));
    eq(see('lin', 'p2'), false);
  });
  await T('拿掉「顯示全部任務」開關', () => {
    as('ming'); ui.page = 'node'; ui.node = 'p1'; ui.tab = 'board'; render();
    ok(!document.getElementById('showAllChk'), '不應有顯示全部開關');
    ok(!document.querySelector('[data-id="t404"]'), '看板不應出現看不到的任務');
  });

  // ── 新測試加在這一行上面 ──
  return results;
})()
