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
    ok(see('an', 't3012'), '看得到上層任務'); ok(see('an', 'p1'), '看得到專案'); ok(see('an', 'p1a'), '看得到同專案的其他階段'); ok(see('an', 'p1e'), '看得到自己沒有任務的階段');
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
    ok(document.querySelector('[data-id="t302"]'), '看板應出現自己負責的任務');
  });

  // ── Task 2 修正輪 1 ──
  await T('單一規則：只靠「範圍內審核人」看得到（陳主管與 t302）', () => {
    eq(who('t302'), ['yu', 'ming', 'chen', 'it']);
  });
  await T('單一規則：只靠「協作部門主管」看得到（協作部門含採購的任務，spec §7.3）', () => {
    ok(!see('hua', 't302'), '協作部門沒有採購時，採購主管看不到');
    node('t302').depts = ['d-pur'];
    ok(see('hua', 't302'), '協作部門含採購時，採購主管看得到');
  });
  await T('單一規則：只靠「協作人員」看得到（小林與 t402）', () => {
    ok(see('lin', 't402'));
  });
  await T('單一規則：只靠「負責部門主管」看得到已指派的任務（陳主管與 t101）', () => {
    ok(see('chen', 't101'));
  });
  await T('側欄不列出看不到的專案；停在看不到的專案時重導到第一個看得到的專案', () => {
    as('lin'); ui.page = 'node'; ui.node = 'p1'; render();
    ok(document.querySelector('#projectList [data-enter="p1"]'), '側欄要有看得到的 p1');
    ok(!document.querySelector('#projectList [data-enter="p2"]'), '側欄不應列出看不到的 p2');
    ui.node = 'p2'; render();
    eq(ui.node, 'p1');
  });
  await T('路徑：下層任務只因上層規則看得到時，不會讓中間的未指派任務顯示（D20）', () => {
    db.nodes['t-x'] = { ...clone(node('t30122')), id: 't-x', parent: 't3012', owner: null, dept: 'd-qa', collabs: [], depts: [] };
    db.nodes['t-x1'] = { ...clone(node('t30122')), id: 't-x1', parent: 't-x', owner: 'an', dept: 'd-qa', collabs: [], depts: [] };
    // ming 負責 t3012：看得到已指派的 D（上層規則），看不到未指派的 N（spec §4.1 字面）
    eq(see('ming', 't-x1'), true); eq(see('ming', 't-x'), false);
    // 小安負責 D：路徑上的 N 看得到
    eq(see('an', 't-x'), true);
  });
  const noProject = () => { Object.values(db.nodes).filter((n) => n.type === 'task').forEach((n) => { n.owner = 'yu'; n.collabs = []; n.depts = []; }); as('an'); };
  await T('一個專案都看不到：節點頁顯示空狀態，不帶到別人的專案（D21）', () => {
    noProject();
    eq(projects().filter(visible).length, 0);
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'board'; render();
    const txt = document.getElementById('main').textContent;
    ok(txt.includes('目前沒有你看得到的專案'), '主區域應顯示空狀態：' + txt.slice(0, 80));
    ok(!txt.includes(node('p1').title), '不應顯示 p1 的標題');
    ok(!document.getElementById('aiScope').textContent.includes(node('p1').title), 'AI 範圍不應帶到別人的專案');
    ok(!document.querySelector('#projectList [data-enter]'), '側欄不列出專案');
    ['overview', 'mytasks', 'review'].forEach((pg) => { ui.page = pg; render(); });
  });
  await T('一個專案都看不到：AI 副手問答不出錯、不帶到別人的專案（D21）', () => {
    noProject();
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'board'; render();
    aiAsk('這個專案的風險？');
    let last = ui.chat.at(-1);
    ok(last && !last.user && last.text.includes('目前沒有你看得到的專案'), '節點頁應回覆沒有可看的專案：' + JSON.stringify(last));
    ui.page = 'overview'; render();
    aiAsk('這個專案的風險？');
    last = ui.chat.at(-1);
    ok(last && !last.user && last.text.includes('目前沒有你看得到的專案'), '總覽應回覆沒有可看的專案：' + JSON.stringify(last));
    ok(!JSON.stringify(ui.chat).includes(node('p1').title), '回覆不應帶到 p1 的標題');
    aiAction('risk');
  });
  await T('一個專案都看不到：確認建立待辦不出錯，也不開對話框（D21）', () => {
    noProject();
    closeDlg();
    const items = [{ title: '測試待辦', owner: 'an', due: '2026-10-05' }];
    ui.page = 'node'; ui.node = 'p1'; render();
    openMinutesConfirm(items, () => {});
    ok(!document.getElementById('dlg').open, '節點頁不應開啟對話框');
    ui.page = 'overview'; render();
    openMinutesConfirm(items, () => {});
    ok(!document.getElementById('dlg').open, '總覽不應開啟對話框');
  });

  // ── Task 3：操作權限 ──
  const w = (u, id) => { as(u); return canWork(node(id)); };
  await T('canWork：負責人、部門主管、專案負責人、系統管理員', () => {
    ok(w('ming', 't30121')); ok(w('yu', 't30121')); ok(w('it', 't30121'));
    ok(!w('chen', 't30121'), '審核人不是負責人也不是部門主管');
    node('t30122').owner = 'an';
    ok(w('an', 't30122'), '負責人'); ok(w('chen', 't30122'), '部門主管');
    ok(!w('lin', 't403'), '協作人員不能操作');
    ok(w('chen', 't404'), '主管可以操作未指派任務'); ok(!w('an', 't404'), '同部門成員不能操作未指派任務');
  });
  await T('協作人員可以寫筆記，但不能送回報、不能改狀態', () => {
    as('lin');
    ok(canNote(node('t403')), '協作人員可以寫筆記');
    ok(!canReport(node('t4032')));
    eq(setStatus('t4032', 'doing'), false);
    // 葉任務 t402：lin 是協作人員，同一個節點上可以寫筆記、不能回報、不能改狀態
    const t = node('t402');
    ok(t.collabs.includes('lin') && t.owner !== 'lin' && isLeaf(t), 't402 是 lin 協作的葉任務');
    ok(canNote(t), '協作人員可以寫筆記'); ok(!canReport(t), '協作人員不能送回報'); ok(!canWork(t));
    eq(setStatus('t402', 'doing'), false); eq(t.status, 'todo', '狀態不變');
    ok(addNote('t402', '協作人員的筆記').ok);
  });
  await T('指派負責人與改負責部門的權限', () => {
    as('chen'); ok(can('assign', node('t404')), '部門主管可以指派'); ok(!can('dept', node('t404')), '部門主管不能改部門');
    as('an'); ok(!can('assign', node('t404')));
    as('yu'); ok(can('assign', node('t504'))); ok(can('dept', node('t504')));
    as('ming'); ok(!can('assign', node('t30121')), '負責人不能自己改派');
    as('chen'); ok(!can('assign', node('t30121')), '別的部門的主管不能指派');
    ok(!can('assign', node('p1')), '專案不是任務');
  });
  await T('修改時程：成員只能改自己負責或自己主管部門的任務', () => {
    as('ming'); ok(can('schedule', node('t30121'))); ok(!can('schedule', node('t30122')));
    as('hua'); ok(can('schedule', node('t8024')));
  });
  await T('權限表顯示「指派負責人」', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'people'; render();
    const txt = document.getElementById('main').textContent;
    ok(txt.includes('指派負責人')); ok(txt.includes('部門主管'), '權限表要寫「部門主管」');
    ok(!txt.includes('undefined'), '權限表不應出現 undefined');
  });
  await T('can(\'edit\', 任務) 等於 canWork', () => {
    as('chen'); ok(!can('edit', node('t30121')), '審核人不是負責人也不是主管，不能編輯');
    as('an'); ok(!can('edit', node('t404')), '同部門成員不能編輯未指派任務');
    as('ming'); ok(can('edit', node('t30121')), '負責人可以編輯');
    as('chen'); ok(can('edit', node('t404')), '部門主管可以編輯未指派任務');
    as('chen'); ok(can('edit', node('p1c')), '階段維持原本的規則');
  });
  await T('協作部門主管：不能操作，但可以寫筆記（含附檔）', async () => {
    node('t30121').depts = ['d-pur'];
    ok(!w('hua', 't30121'), '協作部門主管不能操作'); ok(!canReport(node('t30121')));
    ok(canNote(node('t30121')), '協作部門主管可以寫筆記');
    const r = addNote('t30121', '採購的筆記'); ok(r.ok, JSON.stringify(r));
    const res = await addAttachments('t30121', [new File(['x'], 'x.txt', { type: 'text/plain' })], { noteId: r.note.id });
    ok(res.ok, '協作部門主管的筆記附件：' + JSON.stringify(res.errors)); eq(res.added[0].note_id, r.note.id);
  });
  await T('協作人員的筆記附件：掛在筆記上；任務附件仍被拒；筆記必須屬於同一個任務', async () => {
    const f = () => new File(['a'], 'a.txt', { type: 'text/plain' });
    as('lin');
    const r = addNote('t402', '附檔筆記'); ok(r.ok, JSON.stringify(r));
    const res = await addAttachments('t402', [f()], { noteId: r.note.id });
    ok(res.ok, '協作人員的筆記附件：' + JSON.stringify(res.errors));
    eq(res.added.length, 1); eq(res.added[0].note_id, r.note.id); eq(res.added[0].node_id, 't402'); eq(res.added[0].uploaded_by, 'lin');
    eq(db.attachments.filter((a) => a.note_id === r.note.id).length, 1, '附件要掛在這則筆記上');
    const bad = await addAttachments('t402', [f()]);
    eq(bad.ok, false); eq(bad.added.length, 0); eq(bad.errors, ['你的角色無權上傳附件']);
    as('yu'); const other = addNote('t30121', '別的任務的筆記'); ok(other.ok); as('lin');
    eq((await addAttachments('t402', [f()], { noteId: other.note.id })).ok, false, '別的任務的筆記不能掛附件');
    eq((await addAttachments('t402', [f()], { noteId: 'nt-nope' })).ok, false, '不存在的筆記不能掛附件');
    eq(db.attachments.length, 1, '只有第一個附件被存下來');
  });
  await T('修改時程（D23）：任務跟 canWork，階段與專案照舊', () => {
    as('chen');
    ok(!can('schedule', node('t30121')), '審核人不能改別人任務的時程');
    ok(can('schedule', node('t404')), '部門主管可以改未指派任務的時程');
    ok(can('schedule', node('p1c')), '審核人可以改階段時程');
    ok(can('schedule', node('p1')), '審核人可以改專案時程');
    as('yu'); ok(can('schedule', node('t30121'))); ok(can('schedule', node('p1c')));
    as('it'); ok(can('schedule', node('t30121')));
    as('an'); ok(!can('schedule', node('p1c')), 'member 不是階段負責人，不能改');
    as('ming'); node('p1c').owner = 'ming'; ok(can('schedule', node('p1c')), 'member 負責的階段可以改時程');
    as('hua'); node('t8024').owner = null; ok(can('schedule', node('t8024')), '部門主管可以改自己部門未指派任務的時程');
    ok(!can('schedule', node('t30121')), '採購主管不能改製程任務');
    as('lin'); ok(!can('schedule', node('t402')), '協作人員不能改時程');
  });
  await T('審核人不能用對話框或時間軸拖曳修改別人任務的時程（D23）', () => {
    as('chen');
    const s0 = node('t30121').start, e0 = node('t30121').end;
    applySchedule('t30121', 'm', 1);
    eq([node('t30121').start, node('t30121').end], [s0, e0], '審核人拖曳不能改時程');
    openEditor('t30121');
    ok(document.getElementById('eStart').disabled, '開始日停用'); ok(document.getElementById('eEnd').disabled, '結束日停用');
    ok(document.getElementById('eLock').disabled, '鎖定停用');
    ok(document.getElementById('edForm').textContent.includes('你的角色無權編輯此節點'), '要有唯讀提示');
    closeDrawer();
    as('ming'); applySchedule('t30121', 'm', 1);
    ok(node('t30121').start !== s0, '負責人拖曳可以改時程');
    openEditor('t30121');
    ok(!document.getElementById('eStart').disabled && !document.getElementById('eEnd').disabled, '負責人的日期可以改');
    closeDrawer();
  });
  await T('範圍內的審核人可以寫筆記；範圍外不行；唯讀一律不行（D24）', () => {
    as('chen');
    ok(canNote(node('t30121')), '範圍內審核人（殺菌與保存）可以寫筆記');
    ok(addNote('t30121', '審核人的筆記').ok);
    const t = node('t102');
    ok(!inReviewerScope(t) && !t.collabs.includes('chen') && !isHead('chen', t.dept) && !t.depts.some((d) => isHead('chen', d)) && t.owner !== 'chen', 't102 與 chen 無關');
    ok(!canNote(t), '範圍外、不是協作人員或主管的審核人不能寫筆記');
    eq(addNote('t102', 'x').ok, false);
    const bak = USERS.lin.role; USERS.lin.role = 'readonly';
    try { as('lin'); ok(node('t402').collabs.includes('lin')); ok(!canNote(node('t402')), '唯讀不能寫筆記'); eq(addNote('t402', 'x').ok, false); }
    finally { USERS.lin.role = bak; }
  });

  // ── 新測試加在這一行上面 ──
  return results;
})()
