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
  await T('種子資料：v5、10 個部門、任務都有負責部門', () => {
    eq(db.v, 5);
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
  await T('upgrade：v3 → v5 部門對應', () => {
    const d = seed(); d.v = 3; delete d.departments;
    Object.values(d.nodes).forEach((n) => { delete n.dept; if (n.owner === null) n.owner = 'yu'; });
    d.nodes.t301.depts = ['品保', '法規']; d.nodes.t403.depts = ['行銷']; d.nodes.t503.depts = ['生產', '外星部'];
    d.templates.forEach((t) => t.nodes.forEach((x) => { delete x.dept; x.dp = []; }));
    d.templates[0].nodes[1].dp = ['法規'];
    const au = freshAudit();
    const o = upgrade({ v: 3, db: d, audit: au });
    eq(o.v, 5); eq(o.db.v, 5); eq(o.db.departments.length, 10); eq(o.db.workflows.length, 2);
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
  await T('採購單建立驗收任務：協作部門存 id，新任務的負責部門都是品保', () => {
    const po = db.ops.pos[0];
    const btn = document.createElement('button'); btn.type = 'button'; btn.dataset.poTask = po.id; document.body.appendChild(btn);
    try { btn.click(); } finally { btn.remove(); }
    const root = Object.values(db.nodes).find((n) => n.title === `到貨驗收：${po.id}`);
    ok(root, '應該建立驗收任務');
    eq(root.dept, 'd-qa', '驗收任務的負責部門');
    eq(root.depts, []);
    const subs = kids(root.id);
    eq(subs.length, 4);
    ok(subs.every((n) => n.dept === 'd-qa'), '子任務的負責部門應該是品保：' + subs.map((n) => n.dept).join(','));
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

  // ── Task 4：部門管理 ──
  await T('部門管理只限系統管理員', () => {
    as('yu'); eq(addDept('品管').error, '只有系統管理員可以管理部門');
    eq(deleteDept('d-fin').ok, false);
  });
  await T('新增部門：名稱必填、不可重複', () => {
    as('it');
    eq(addDept('  ').error, '請填寫部門名稱');
    eq(addDept('研發').error, '已有同名部門');
    const r = addDept('倉儲'); ok(r.ok); eq(dept(r.id).name, '倉儲'); eq(dept(r.id).head, null);
  });
  await T('修改部門：主管必須是部門成員、名稱不可重複', () => {
    as('it');
    eq(updateDept('d-qa', { name: '品保', head: 'ming' }).error, '主管必須是部門成員');
    eq(updateDept('d-qa', { name: '研發', head: null }).error, '已有同名部門');
    ok(updateDept('d-qa', { name: '品質保證', head: 'an' }).ok);
    eq(deptName('d-qa'), '品質保證'); eq(dept('d-qa').head, 'an');
  });
  await T('刪除部門：有任務或人員時拒絕；空部門可以刪除且可復原', () => {
    as('it');
    const u = deptUsage('d-qa');
    eq(u.users, 2); ok(u.tasks > 0);
    eq(deleteDept('d-qa').error, `部門還有 ${u.tasks} 件任務、2 位人員，請先移轉`);
    ok(deleteDept('d-fin').ok); eq(dept('d-fin'), null);
    undo(); ok(dept('d-fin'), '復原後部門回來');
  });
  await T('部門面板：管理員有編輯按鈕，其他人唯讀；標示未設主管', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'people';
    as('it'); render();
    ok(document.querySelector('[data-dept-add]'), '管理員看得到新增部門');
    ok(document.querySelector('[data-dept-edit="d-qa"]'));
    as('ming'); render();
    ok(!document.querySelector('[data-dept-add]'), '成員看不到新增部門');
    ok(document.getElementById('main').textContent.includes('未設主管'));
  });

  // ── Task 4 修正輪 1 ──
  // Task 5 移除了「我部門被指派的」群組（spec §5.3），部門名稱改由看板卡片與任務頁標題的 whoHTML 顯示，所以這個測試改檢查這兩處
  await T('XSS：部門改名後，看板卡片與任務頁標題不會把部門名稱當成 HTML', () => {
    as('it');
    const evil = '<img src=x onerror="window.__xss=1">';
    try {
      ok(updateDept('d-qa', { name: evil, head: 'chen' }).ok);
      ui.page = 'node'; ui.node = 'p1d'; ui.tab = 'board'; render();
      const card = document.querySelector('[data-id="t404"]');
      ok(card, '看板上有 t404 的卡片');
      eq(card.querySelectorAll('img').length, 0, '卡片上不應該出現 img 元素');
      ok(card.textContent.includes('<img'), '卡片要顯示部門名稱的原字串');
      ui.node = 't404'; render();
      const main = document.getElementById('main');
      eq(main.querySelectorAll('img').length, 0, '任務頁標題裡不應該出現 img 元素');
      ok(main.textContent.includes('<img'), '任務頁標題要顯示部門名稱的原字串');
      // 已指派的分支：負責人名稱旁的部門名稱
      node('t404').owner = 'an'; ui.node = 'p1d'; render();
      const card2 = document.querySelector('[data-id="t404"]');
      ok(card2.querySelector('.who').textContent.includes('小安'), '卡片顯示負責人');
      eq(card2.querySelectorAll('img').length, 0, '已指派的卡片上不應該出現 img 元素');
      ok(card2.querySelector('.who').textContent.includes('<img'), '已指派的卡片要顯示部門名稱的原字串');
      ui.node = 't404'; render();
      eq(document.getElementById('main').querySelectorAll('img').length, 0, '已指派的任務頁標題不應該出現 img 元素');
      ok(document.querySelector('.meta').textContent.includes('<img'), '已指派的任務頁標題要顯示部門名稱的原字串');
      // 任務對話框的負責部門下拉
      openEditor('t404');
      eq($('drawer').querySelectorAll('img').length, 0, '對話框裡不應該出現 img 元素');
      ok([...$('eDept').options].find((o) => o.value === 'd-qa').text.includes('<img'), '負責部門選項要顯示部門名稱的原字串');
      closeDrawer();
      ok(window.__xss === undefined, '不應執行部門名稱裡的腳本');
    } finally { delete window.__xss; }
  });
  await T('部門管理：新增、修改、刪除成功後都寫稽核紀錄', () => {
    as('it');
    const r = addDept('倉儲'); ok(r.ok);
    eq(audit.acts[0].action, '部門'); ok(audit.acts[0].text.includes('倉儲'), audit.acts[0].text);
    ok(updateDept(r.id, { name: '倉庫', head: null }).ok);
    eq(audit.acts[0].action, '部門'); ok(audit.acts[0].text.includes('倉儲') && audit.acts[0].text.includes('倉庫'), audit.acts[0].text);
    ok(deleteDept(r.id).ok);
    eq(audit.acts[0].action, '部門'); ok(audit.acts[0].text.includes('倉庫'), audit.acts[0].text);
  });
  await T('修改部門：非管理員被拒且名稱不變；管理員可以清除主管', () => {
    as('yu');
    eq(updateDept('d-qa', { name: 'x', head: null }).error, '只有系統管理員可以管理部門');
    eq(deptName('d-qa'), '品保'); eq(dept('d-qa').head, 'chen');
    as('it');
    ok(updateDept('d-qa', { name: '品保', head: null }).ok);
    eq(dept('d-qa').head, null);
  });
  await T('刪除部門：只被協作部門、只被模板、只有人員時，分別拒絕', () => {
    as('it');
    eq(deptUsage('d-fin'), { tasks: 0, users: 0 }, '財務一開始沒有任何引用');
    eq(deptUsage('d-it'), { tasks: 0, users: 1 }, '資訊只有人員（資訊室）');
    node('t301').depts.push('d-fin');
    eq(deptUsage('d-fin'), { tasks: 1, users: 0 });
    eq(deleteDept('d-fin').error, '部門還有 1 件任務、0 位人員，請先移轉');
    node('t301').depts.pop();
    const tn = db.templates[0].nodes[1];
    tn.dp.push('d-fin');
    eq(deleteDept('d-fin').error, '部門還有 1 件任務、0 位人員，請先移轉');
    tn.dp.pop();
    const old = tn.dept; tn.dept = 'd-fin';
    eq(deleteDept('d-fin').error, '部門還有 1 件任務、0 位人員，請先移轉');
    tn.dept = old;
    eq(deleteDept('d-it').error, '部門還有 0 件任務、1 位人員，請先移轉');
    ok(dept('d-fin') && dept('d-it'), '被拒絕時部門都還在');
    ok(deleteDept('d-fin').ok, '引用都移除後可以刪除');
  });
  await T('部門面板：成員看不到編輯與刪除按鈕，管理員看得到刪除', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'people';
    as('ming'); render();
    eq(document.querySelectorAll('[data-dept-edit]').length, 0);
    eq(document.querySelectorAll('[data-dept-del]').length, 0);
    as('it'); render();
    ok(document.querySelector('[data-dept-del="d-fin"]'), '管理員看得到財務的刪除按鈕');
  });

  // ── Task 5：負責部門與負責人 ──
  await T('addNode：預設上層任務的部門；負責人不在部門時為未指派', () => {
    as('yu'); const a = commit('t', () => addNode('t3012', { title: 'A' }));
    eq(node(a).dept, 'd-pe'); eq(node(a).owner, null);
    as('ming'); const b = commit('t', () => addNode('t3012', { title: 'B' }));
    eq(node(b).owner, 'ming');
    as('yu'); const c = commit('t', () => addNode('p1a', { title: 'C' }));
    eq(node(c).dept, 'd-rd'); eq(node(c).owner, 'yu');
    const d = commit('t', () => addNode('p1a', { title: 'D', dept: 'd-qa', owner: 'ming' }));
    eq(node(d).owner, null, '負責人不屬於部門時清空');
  });
  await T('任務對話框：負責人只列出部門成員；換部門會清空不屬於新部門的負責人', () => {
    as('yu'); openEditor('t404');
    eq([...$('eOwner').options].map((o) => o.value), ['', 'an', 'chen']);
    closeDrawer();
    openEditor('t30121');
    $('eDept').value = 'd-qa'; $('eDept').dispatchEvent(new Event('change', { bubbles: true }));
    eq($('eOwner').value, '');
    $('eOwner').value = 'an'; saveEditor('t30121');
    eq(node('t30121').dept, 'd-qa'); eq(node('t30121').owner, 'an');
  });
  await T('任務對話框：部門主管可以指派但不能改部門', () => {
    as('chen'); openEditor('t404');
    ok($('eDept').disabled, '部門欄停用'); ok(!$('eOwner').disabled, '負責人欄可用');
    $('eOwner').value = 'an'; saveEditor('t404');
    eq(node('t404').owner, 'an');
  });
  await T('看板：未指派卡片顯示「未指派・部門」', () => {
    as('yu'); ui.page = 'node'; ui.node = 'p1d'; ui.tab = 'board'; render();
    ok(document.querySelector('[data-id="t404"]').textContent.includes('未指派・品保'));
  });
  await T('我的任務：部門主管有「待我指派」，成員沒有', () => {
    as('chen'); ui.page = 'mytasks'; render();
    const m = document.getElementById('main');
    ok(m.textContent.includes('待我指派（1）'), m.textContent.slice(0, 200));
    ok(m.querySelector('[data-edit="t404"]'), '有指派按鈕');
    ok(!m.textContent.includes('被指派的'), '移除部門被指派的群組');
    as('an'); render();
    ok(!document.getElementById('main').textContent.includes('待我指派'));
  });
  await T('總覽：部門負載依負責部門統計，未指派不算進人員負載', () => {
    as('yu'); ui.page = 'overview'; render();
    const m = document.getElementById('main').textContent;
    ok(m.includes('製造'), '列出所有部門'); ok(!m.includes('null'), '不應出現 null');
  });

  // ── Task 5 修正輪 1 ──
  await T('F1 ERP 同步：證照到期任務的負責人是阿華、部門是採購，異動文字與事實一致', () => {
    as('yu'); erpSync();
    const c = Object.values(db.nodes).find((n) => n.certFor);
    ok(c, '應該建立證照更新任務');
    eq([c.dept, c.owner], ['d-pur', 'hua']);
    ok(audit.acts.some((a) => a.action === 'ERP 同步' && a.text.includes('已自動建立更新任務給阿華')), '異動文字要寫給阿華');
  });
  await T('F1 配方改版重做任務：保留原任務的負責人與部門', () => {
    as('yu'); ui.page = 'ops'; ui.opsTab = 'formulas'; render();
    const boxes = [...document.querySelectorAll('.impact')];
    boxes.forEach((b) => { b.checked = ['t301', 't403'].includes(b.value); });
    ok(boxes.filter((b) => b.checked).length === 2, '影響分析要列出 t301 與 t403');
    document.querySelector('[data-impact]').click();
    const redo = (src) => Object.values(db.nodes).find((n) => n.title === `【配方 v4 重做】${node(src).title}`);
    ok(redo('t301') && redo('t403'), '要建立兩個重做任務');
    eq([redo('t301').dept, redo('t301').owner], ['d-pe', 'ming']);
    eq([redo('t403').dept, redo('t403').owner], ['d-qa', 'an']);
  });
  await T('F1 會議記錄建立待辦：待辦的負責人與部門照負責人', () => {
    as('yu'); ui.page = 'node'; ui.node = 'p1d'; ui.tab = 'board'; render();
    runMinutes('待辦：阿華 10/20 前確認供應商證照\n待辦：小安 10/22 前補測試報告');
    runAIAction(ui.chat.length - 1, 0);
    $('minParent').value = 'p1d';
    $('minConfirm').requestSubmit();
    const t = (title) => Object.values(db.nodes).find((n) => n.title === title);
    ok(t('確認供應商證照') && t('補測試報告'), '兩項待辦都要建立');
    eq([t('確認供應商證照').parent, t('確認供應商證照').dept, t('確認供應商證照').owner], ['p1d', 'd-pur', 'hua']);
    eq([t('補測試報告').dept, t('補測試報告').owner], ['d-qa', 'an']);
  });
  await T('F2 儲存任務：沒有 can(dept)／can(assign) 時，欄位被改也不會改部門或負責人', () => {
    as('ming'); openEditor('t30121');
    $('eDept').disabled = false; $('eDept').value = 'd-qa'; $('eOwner').disabled = false; $('eOwner').value = '';
    saveEditor('t30121'); closeDrawer();
    eq([node('t30121').dept, node('t30121').owner], ['d-pe', 'ming'], '成員不能改部門與負責人');
    as('chen'); openEditor('t404');
    $('eDept').disabled = false; $('eDept').value = 'd-pe'; $('eOwner').value = 'an';
    saveEditor('t404'); closeDrawer();
    eq([node('t404').dept, node('t404').owner], ['d-qa', 'an'], '部門主管可以指派，但不能改部門');
  });
  await T('F3 快速新增：預設負責人是自己（階段負責人不在部門時）；繼續新增會保留未指派', () => {
    as('ming'); ui.page = 'node'; ui.node = 'p1d'; ui.tab = 'board'; render();
    openQuickAdd('p1d'); eq($('qWho').value, 'ming', '阿明在階段底下新增，預設是自己'); closeDlg();
    as('yu'); openQuickAdd('t404'); eq($('qWho').value, '', '未指派的品保任務底下，力瑜不屬於品保，預設未指派'); closeDlg();
    openQuickAdd('p1d'); eq($('qWho').value, 'yu');
    $('qTitle').value = 'F3 測試'; $('qWho').value = '';
    document.getElementById('qaForm').requestSubmit([...document.querySelectorAll('#qaForm button[type="submit"]')].find((b) => b.value === 'more'));
    eq(node(Object.keys(db.nodes).find((id) => node(id).title === 'F3 測試')).owner, null);
    eq($('qWho').value, '', '建立並繼續新增：保留未指派');
    closeDlg();
  });
  await T('F5 未指派的任務底下新增第一個子任務：提示寫「未指派・部門」而不是「—」', () => {
    as('yu'); openQuickAdd('t404');
    const note = document.querySelector('#qaForm .note').textContent;
    ok(note.includes('負責人仍是') && note.includes('未指派・品保'), note);
    ok(!note.includes('仍是 —'), note);
    closeDlg();
  });

  // ── Task 6：時間軸收合與部門篩選 ──
  const tlRowIds = () => [...document.querySelectorAll('#tl .tl-row[data-row]')].map((r) => r.dataset.row);
  await T('時間軸：專案預設只顯示階段列', () => {
    as('yu'); ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline'; render();
    eq(tlRowIds(), ['p1a', 'p1b', 'p1c', 'p1d', 'p1e']);
  });
  await T('時間軸：點階段展開，可同時展開多個', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline'; render();
    document.querySelector('[data-twist="p1c"]').click();
    document.querySelector('[data-twist="p1d"]').click();
    const ids = tlRowIds();
    ok(ids.includes('t301') && ids.includes('t401'), ids.join(','));
    ok(!ids.includes('t101'), '未展開的階段不顯示工作');
  });
  await T('時間軸：部門篩選只影響工作列，階段列保持完整', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline';
    ['p1a', 'p1b', 'p1c', 'p1d', 'p1e'].forEach((p) => { ui.expanded['t' + p] = true; });
    render();
    document.querySelector('[data-tl-dept="d-qa"]').click();
    const ids = tlRowIds();
    ['p1a', 'p1b', 'p1c', 'p1d', 'p1e'].forEach((p) => ok(ids.includes(p), '階段列 ' + p));
    const tasks = ids.map(node).filter((x) => x.type === 'task');
    ok(tasks.length > 0, '應有品保的工作');
    ok(tasks.every((x) => x.dept === 'd-qa' || descendants(x.id).some((d) => d.dept === 'd-qa')), tasks.map((x) => x.id).join(','));
    ok(ids.includes('t404'), '品保的未指派工作（專案負責人看得到）');
    ok(!ids.includes('t102'), '研發的工作（沒有品保子任務）被篩掉');
    ok(document.querySelector('[data-tl-dept="d-qa"][aria-pressed="true"]'));
  });
  await T('時間軸：篩選後作為路徑的上層任務以淡色顯示', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline'; ui.expanded.tp1c = true; ui.expanded.tt301 = true; ui.expanded.tt3012 = true; ui.tlDept = 'd-qa'; render();
    ok(document.querySelector('#tl .tl-row.dim[data-row="t301"]'), 't301 是製程的任務，因子任務 t30122 屬於品保而以淡色路徑出現');
    ok(!document.querySelector('#tl .tl-row.dim[data-row="t30122"]'), '符合篩選的任務不淡化');
  });
  await T('時間軸：沒有階段的專案不收合，篩選直接套用', () => {
    ui.page = 'node'; ui.node = 'p4'; ui.tab = 'timeline'; ui.tlDept = 'd-pur'; render();
    const ids = tlRowIds();
    ok(ids.includes('t801') && ids.includes('t802'), ids.join(','));
    ui.tlDept = 'd-fin'; render();
    eq(tlRowIds(), []);
  });
  await T('時間軸篩選狀態不寫入資料、不進復原紀錄', () => {
    const before = undoStack.length;
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline'; render();
    document.querySelector('[data-tl-dept="d-qa"]').click();
    eq(undoStack.length, before); ok(!('tlDept' in db));
  });
  // ── Task 7：範本 ──
  await T('套用模板：任務帶負責部門；未勾預設負責人時全部未指派', () => {
    as('yu');
    const t = db.templates.find((x) => x.id === 'tp1');
    const res = commit('套用', () => applyTemplate(t, 'p1d', { start: '2026-10-01', vars: { 產品名: 'X' }, structure: true, deps: true, owners: false, dates: true, docs: false }));
    const made = [node(res.root), ...descendants(res.root)];
    ok(made.every((x) => x.owner === null), '全部未指派');
    eq(node(res.root).dept, 'd-qa');
    eq(made.find((x) => x.title === '選定檢驗單位並詢價').dept, 'd-pur');
  });
  await T('另存為模板會帶入負責部門', () => {
    const t = nodeToTemplate('t301');
    eq(t.nodes[0].dept, 'd-pe'); ok(t.nodes.every((x) => x.dept));
  });
  await T('依範本建立專案：任務依範本帶部門且未指派', () => {
    eq(PHASE_TEMPLATE[2][3][0], ['殺菌條件驗證（F0 值）', 'd-pe']);
  });
  await T('模板庫預覽顯示負責部門', () => {
    ui.page = 'templates'; render();
    ok(document.getElementById('main').textContent.includes('採購負責'));
  });

  // ── 整體修正 ──
  await T('未指派的負責人顯示「未指派」，不出現「—」；改為未指派的稽核不寫「已通知」', () => {
    as('yu'); ui.page = 'node'; ui.node = 't404'; ui.tab = 'people'; render();
    const dd = [...document.querySelectorAll('#main dt')].find((x) => x.textContent === '負責人').nextElementSibling;
    ok(dd.textContent.includes('未指派'), dd.textContent); ok(!dd.textContent.includes('—'), dd.textContent);
    ui.node = 'p1e'; ui.tab = 'timeline'; render();
    const bar = document.querySelector('[data-bar="t504"]');
    ok(!bar.textContent.includes('—') && !bar.title.includes('—'), bar.textContent + '｜' + bar.title);
    const line = publicSnapshot(node('p1')).split('\n').find((l) => l.includes('量產製程參數確認'));
    ok(line.endsWith('｜未指派'), line);
    openEditor('t30121'); $('eOwner').value = ''; saveEditor('t30121');
    eq(node('t30121').owner, null);
    ok(audit.acts[0].text.includes('負責人改為 未指派') && !audit.acts[0].text.includes('已通知'), audit.acts[0].text);
  });
  await T('看板卡片的「名字・部門」不換行', () => {
    as('yu'); ui.page = 'node'; ui.node = 'p1d'; ui.tab = 'board'; render();
    const nm = document.querySelector('[data-id="t403"] .who .whonm');
    ok(nm, '名字和部門包在同一個 span'); ok(nm.textContent.includes('・'), nm.textContent);
    eq(getComputedStyle(nm).whiteSpace, 'nowrap');
  });
  await T('權限表「修改時程」和 D23 一致', () => {
    as('yu'); ui.page = 'node'; ui.node = 'p1'; ui.tab = 'people'; render();
    const row = [...document.querySelectorAll('#main .tbl tbody tr')].find((tr) => tr.cells[0].textContent === '修改時程');
    const col = (k) => row.cells[1 + Object.keys(ROLES).indexOf(k)].textContent;
    ok(col('reviewer') !== '✅' && col('reviewer').includes('自己負責'), col('reviewer'));
    eq(col('collab'), '自己負責');
  });
  await T('回報對話框：select 欄位沒有 options 也能打開', () => {
    db.reportFields.push({ id: 'rf-nox', node_id: 't30121', key: 'nox', label: '無選項', type: 'select', unit: '', required: false, order: 1 });
    as('ming'); openReportDialog('t30121');
    ok($('rv_nox') && $('rv_nox').tagName === 'SELECT', '應有 select 欄位');
    closeDlg();
  });

  // ── 新測試加在這一行上面 ──
  return results;
})()
