// 與既有測試共用 Demo iframe，逐項重建隔離資料。
(async () => {
  const results = [];
  const eq = (a,b,m) => { if(JSON.stringify(a)!==JSON.stringify(b)) throw new Error(`${m||''} 預期 ${JSON.stringify(b)}，實際 ${JSON.stringify(a)}`); };
  const ok = (v,m) => { if(!v) throw new Error(m||'預期為真'); };
  const T = async (name,fn) => { try { await resetAll(); ui.me='yu'; await fn(); results.push({name,ok:true}); } catch(e) { results.push({name,ok:false,err:String(e.stack||e)}); } };
  function makeLegacyPayload(version) {
    const d=seed(); d.v=version; d.nodes.p1.title=`保留 v${version} 節點`;
    if(version<5) delete d.workflows;
    if(version<4) { delete d.departments; Object.values(d.nodes).forEach(n=>delete n.dept); d.templates.forEach(t=>t.nodes.forEach(n=>delete n.dept)); }
    if(version<3) { delete d.reportFields; delete d.reports; delete d.notes; delete d.attachments; d.overrides.forEach(x=>delete x.kind); }
    return {v:version,db:d,audit:freshAudit(),me:'yu'};
  }
  await T('W6：v6 容器固定包含五家公司',()=>{
    const p=seedPortfolio(); eq(p.v,6); eq(p.activeCompanyId,'petfood');
    eq(Object.keys(p.companies).sort(),['construction','electronics','events','petfood','software']);
    eq(p.companies.petfood.me,'yu'); eq(p.companies.petfood.db.v,6);
  });
  await T('W6：v5 升級完整保留毛研資料與舊附件鍵',()=>{
    const d=seed(); d.v=5; d.nodes.p1.title='人類保留節點';
    d.attachments.push({id:'legacy-file',node_id:'p1',report_id:null,note_id:null,filename:'舊附件.pdf',mime:'application/pdf',size:12,sha256:'',storage_key:'legacy-file',uploaded_by:'yu',uploaded_at:'2026/10/08 08:00',deleted_at:null});
    const a=freshAudit(); a.acts.unshift({at:'2026/10/08 08:00',actor:'yu',node:'p1',action:'測試',text:'保留稽核'});
    const p=upgrade({v:5,db:d,audit:a,me:'lin'});
    eq(p.v,6); eq(p.companies.petfood.db.nodes.p1.title,'人類保留節點');
    eq(p.companies.petfood.db.attachments.find(a=>a.id==='legacy-file').storage_key,'legacy-file');
    eq(p.companies.petfood.audit.acts[0].text,'保留稽核'); eq(p.companies.petfood.me,'lin'); eq(p.companies.electronics.id,'electronics');
  });
  await T('W6：部分損壞 v6 只修補壞公司',()=>{
    const p=seedPortfolio(); p.companies.petfood.db.nodes.p1.title='不可被蓋掉';
    p.companies.events=null; delete p.companies.software; p.activeCompanyId='missing';
    const repaired=[]; const fixed=upgrade(p,repaired);
    eq(fixed.companies.petfood.db.nodes.p1.title,'不可被蓋掉'); eq(fixed.companies.events.id,'events');
    eq(fixed.companies.software.id,'software'); eq(fixed.activeCompanyId,'petfood'); eq(repaired.sort(),['events','software']);
    [c=>delete c.db.ops.formulas,c=>c.users.ming=null].forEach(corrupt=>{
      const damaged=seedPortfolio(); damaged.companies.events.audit.acts.push({text:'其他公司保留'});
      corrupt(damaged.companies.petfood); const ids=[]; const repaired=upgrade(damaged,ids);
      eq(ids,['petfood']); ok(Array.isArray(repaired.companies.petfood.db.ops.formulas));
      ok(repaired.companies.petfood.users.ming); eq(repaired.companies.events.audit.acts.at(-1).text,'其他公司保留');
    });
  });
  await T('W6：v2 到 v4 都能逐版升到 v6',()=>{
    [2,3,4].forEach(v=>{ const p=upgrade(makeLegacyPayload(v)); eq(p.v,6); eq(p.companies.petfood.db.nodes.p1.title,`保留 v${v} 節點`); eq(p.companies.petfood.me,'yu'); });
  });
  await T('W6：公司選擇器位於身分選擇器上方',()=>{
    render(); const c=$('companySel'),m=$('meSel'); ok(c&&m); ok(c.compareDocumentPosition(m)&Node.DOCUMENT_POSITION_FOLLOWING);
    eq([...c.options].map(x=>x.textContent),['毛研食品｜寵物食品製造','峰曜科技｜電子產品製造','光點企劃｜活動行銷','雲序軟體｜SaaS 軟體服務','築衡工程｜營建工程']);
  });
  await T('W6：切換公司使用目標預設負責人並清空暫態 UI',async()=>{
    ui.page='ops'; ui.node='p1'; ui.connect={from:'p1'}; ui.opsTab='po'; ui.chat=[{text:'舊公司'}];
    undoStack.push({label:'舊公司',snap:JSON.stringify(db)});
    $('askInput').value='舊公司提問'; toast('舊公司通知');
    window._pq=setTimeout(()=>openDlg('舊公司搜尋結果'),20);
    ok(switchCompany('electronics').ok); eq(company.id,'electronics'); eq(me().id,'el-lin');
    eq(ui.page,'overview'); eq(ui.node,projects().find(visible)?.id||null); eq(ui.connect,null); eq(ui.chat.length,0); eq(undoStack.length,0);
    await new Promise(resolve=>setTimeout(resolve,40));
    eq($('askInput').value,'');eq($('toasts').children.length,0);ok(!$('dlg').open);
  });
  await T('W6：公司資料來回切換會持久化且不互改',()=>{
    projects()[0].title='毛研自訂名稱'; save(); switchCompany('electronics');
    const other=projects()[0]?.title; switchCompany('petfood'); eq(projects()[0].title,'毛研自訂名稱'); ok(other!=='毛研自訂名稱');
    ui.me='lin';save();load();eq(ui.me,'lin');eq(company.id,'petfood');eq(projects()[0].title,'毛研自訂名稱');
    switchCompany('electronics');switchCompany('petfood');eq(ui.me,'yu');
  });
  await T('W6：持久化失敗時公司切換完全不生效',()=>{
    ui.page='ops';ui.node='p1';undoStack.push({label:'保留',snap:JSON.stringify(db)});
    const before=JSON.stringify({portfolio,ui,undoStack,db,audit});const set=Storage.prototype.setItem;
    try { Storage.prototype.setItem=function(){throw new Error('quota');}; ok(!switchCompany('electronics').ok); }
    finally { Storage.prototype.setItem=set; }
    eq(JSON.stringify({portfolio,ui,undoStack,db,audit}),before);eq(company.id,'petfood');
  });
  await T('W6：五家公司符合專案與工作流最低量且角色完整',()=>{
    Object.values(seedPortfolio().companies).forEach(c=>{ const roots=Object.values(c.db.nodes).filter(n=>n.type==='project');ok(roots.length>=2,c.id);if(c.id!=='petfood')eq(roots.length,2);
      eq(c.db.workflows.length,2);const roles=new Set(Object.values(c.users).map(u=>u.role));['owner','reviewer','member','collab','admin'].forEach(r=>ok(roles.has(r),c.id+r));ok(c.db.departments.length>=9);
    });
  });
  await T('W6：各產業主專案含關卡、前置、報告、註記、稽核與營運連結',()=>{
    Object.values(seedPortfolio().companies).forEach(c=>{const ns=Object.values(c.db.nodes);ok(ns.some(n=>n.type==='project'));ok(Object.keys(c.db.gates).length,c.id+'關卡');ok(c.db.deps.length,c.id+'前置');
      ok(c.db.reports.some(r=>c.db.nodes[r.node_id]),c.id+'報告');ok(c.db.notes.some(r=>c.db.nodes[r.node_id]),c.id+'註記');ok(ns.some(n=>n.links?.length),c.id+'連結');ok(c.audit.acts.length,c.id+'稽核');
      if(c.id!=='petfood') {ok(c.db.deps.some(d=>d.cond?.kind==='ops'),c.id+'營運條件');c.db.deps.forEach(d=>ok(c.db.nodes[d.to]&&(!d.from||c.db.nodes[d.from])));}
    });
  });
  await T('W6：非毛研公司不引用毛研成員',()=>{
    const p=seedPortfolio();const ids=Object.keys(p.companies.petfood.users);
    COMPANY_ORDER.slice(1).forEach(id=>{const c=p.companies[id];ids.forEach(uid=>ok(!JSON.stringify(c.db.nodes).includes(`"${uid}"`),id+uid));Object.values(c.db.nodes).forEach(n=>ok(!n.owner||c.users[n.owner]));});
  });
  await T('W6：四個新產業部門名稱正確',()=>{
    const p=seedPortfolio();const expected={electronics:['產品企劃','硬體研發','工業設計','採購','品保','製造','認證','業務','資訊','財務'],events:['策略企劃','創意','客戶服務','活動製作','媒體','公關','採購','財務','資訊'],software:['產品','前端','後端','品質保證','DevOps','資安','客戶成功','業務','資訊'],construction:['專案管理','設計','機電','採購','工務','品管','職安','財務','行政','資訊']};
    Object.entries(expected).forEach(([id,names])=>eq(p.companies[id].db.departments.map(d=>d.name),names,id));
  });
  await T('W6：五家公司種子標題與營運連結有效',()=>{
    const p=seedPortfolio();const expected={petfood:['成貓主食罐・鮪魚雞肉','高齡犬關節保健罐','筆電新機種專流'],electronics:['AstraBook AI 筆電 NPI','65W 充電器降本','筆電 NPI 專流'],events:['夏季新品發表會','年度經銷商大會','活動執行專流'],software:['企業 SSO 上線','通知中心改版','版本發佈專流'],construction:['總部辦公室裝修','空調主機汰換','裝修工程專流']};
    Object.entries(expected).forEach(([id,[main,secondary,wf]])=>{const c=p.companies[id],ns=Object.values(c.db.nodes);ok(ns.some(n=>n.title===main),id+main);ok(ns.some(n=>n.title===secondary),id+secondary);ok(c.db.workflows.some(w=>w.name===wf));
      ns.flatMap(n=>n.links||[]).forEach(l=>{const list=id==='petfood'?c.db.ops[{supplier:'suppliers',formula:'formulas',po:'pos',wo:'wos'}[l.t]]:c.db.ops.records[l.t];ok(list?.some(r=>r.id===l.id),id+l.id);});
    });
  });
  await T('W6：四個新產業各有六個正確營運模組',()=>{
    const labels={electronics:['供應商','零件','BOM','採購單','試產批次','驗證項目'],events:['供應商','場地','預算','採購','場次','交付物'],software:['需求','版本','缺陷','環境','部署','事件'],construction:['承包商','材料','合約','工單','查驗','變更單']};
    Object.entries(labels).forEach(([id,names])=>{switchCompany(id);eq(OPS_CONFIG.modules.map(m=>m.label),names);ok(OPS_CONFIG.modules.every(m=>m.columns?.every(c=>c.key&&c.label&&c.type)));});
  });
  await T('W6：通用營運頁跳脫文字並容忍未知資料',()=>{
    switchCompany('software');const r=db.ops.records.requirement[0];r.title='<img src=x onerror=alert(1)>';ui.opsTab='requirement';
    const html=pageOps();ok(html.includes('&lt;img'));ok(!html.includes('<img src=x'));eq(opsRecords('missing'),[]);eq(opsRecord('requirement','missing'),null);
    ui.opsSel='missing';ok(pageOps().includes('找不到營運記錄'));
    ui.opsTab='missing';ok(pageOps().includes('需求'));
    const u=ui.me;ui.me='sw-an';ok(!pageOps().includes('120,000'));ui.me=u;
    OPS_CONFIG.modules.push(null,{id:'bad',label:'損壞'});ui.opsTab='bad';ok(pageOps().includes('目前沒有營運資料'));
    ok(linkCard({t:'missing',id:'<壞連結>'},projects()[0]).includes('&lt;壞連結&gt;'));
  });
  await T('W6：通用營運條件由狀態推進解除',()=>{
    switchCompany('software');const cond={kind:'ops',module:'deployment',id:'SW-DEP-PROD',field:'status',need:'已完成',label:'正式環境部署'};
    ok(!condMet(cond));const snapshot=JSON.stringify(db);ui.me='sw-an';ok(!advanceOpsRecord('deployment','SW-DEP-PROD').ok);eq(JSON.stringify(db),snapshot);ui.me='sw-yi';
    let steps=0;while(!condMet(cond)&&steps<6){advanceOpsRecord('deployment','SW-DEP-PROD');steps++;}ok(steps<6);ok(condMet(cond));ok(audit.acts.some(x=>x.text.includes('SW-DEP-PROD')));
    const saved=JSON.parse(localStorage.getItem(KEY));ok(saved.companies.software.audit.acts.some(x=>x.text.includes('SW-DEP-PROD')));eq(opsRecord('deployment','SW-DEP-PROD').status,'已完成');
    const before=JSON.stringify(db);poNext('PO-2604');woNext('WO-T2603');erpSync();eq(JSON.stringify(db),before);
  });
  await T('W6：毛研食品仍使用完整配方採購工單追溯頁',()=>{
    switchCompany('petfood');const html=pageOps();['配方','採購','工單','追溯'].forEach(text=>ok(html.includes(text)));
    ['suppliers','materials','formulas','pos','wos','trace','erp'].forEach(tab=>{ui.opsTab=tab;const h=pageOps();ok(h.length>100);ok(!/undefined|NaN/.test(h));});
  });
  await T('W6：新附件鍵含公司前綴且舊毛研鍵仍可讀',async()=>{
    eq(attachmentStorageKey('new-file'),'petfood:new-file');await fileStore.put('legacy-file',new Blob(['old']));
    eq(await (await attachmentBlob({id:'legacy-file',storage_key:'legacy-file'})).text(),'old');
    eq(await (await attachmentBlob({id:'legacy-file'})).text(),'old');
    switchCompany('software');eq(attachmentStorageKey('new-file'),'software:new-file');eq(await attachmentBlob({id:'legacy-file'}),undefined);
    eq(await attachmentBlob({id:'legacy-file',storage_key:'legacy-file'}),undefined);
  });
  await T('W6：相同附件 ID 在不同公司使用不同 blob',async()=>{
    db.seq=2000;const a=await addAttachments('t3013',[new File(['petfood'],'same.txt')]);ok(a.ok);eq(a.added[0].storage_key,'petfood:at2001');
    switchCompany('software');db.seq=2000;const n=Object.values(db.nodes).find(n=>n.type==='task');
    const b=await addAttachments(n.id,[new File(['software'],'same.txt')]);ok(b.ok);eq(b.added[0].id,a.added[0].id);eq(b.added[0].storage_key,'software:at2001');
    eq(await (await attachmentBlob(b.added[0])).text(),'software');eq(await attachmentBlob(a.added[0]),undefined);
    switchCompany('petfood');eq(await (await attachmentBlob(db.attachments[0])).text(),'petfood');
    const count=db.attachments.length;
    const pending=addAttachments('t3013',[new File(['不可跨公司'],'pending.txt')]);switchCompany('software');
    const result=await pending;ok(!result.ok,'切換後應中止未完成上傳');eq(db.attachments.length,1);switchCompany('petfood');eq(db.attachments.length,count);
    const reporting=submitReport('t30121',{result:'met',summary:'毛研不可跨公司回報',finished_on:'2026-09-30',values:{},files:[new File(['report'],'report.txt')]});
    switchCompany('software');const unchanged=JSON.stringify({db,audit,chat:ui.chat,undoStack});
    const report=await reporting;ok(!report.ok);eq(JSON.stringify({db,audit,chat:ui.chat,undoStack}),unchanged);
  });
  await T('W6：重設目前公司不改其他公司或其附件',async()=>{
    projects()[0].title='待重設毛研';const a=await addAttachments('t3013',[new File(['petfood'],'pf.txt')]);save();
    await fileStore.put('legacy-delete',new Blob(['old']));db.attachments.push({...a.added[0],id:'legacy-delete',storage_key:'legacy-delete'});save();
    switchCompany('software');projects()[0].title='保留雲序';const n=Object.values(db.nodes).find(n=>n.type==='task');const b=await addAttachments(n.id,[new File(['software'],'sw.txt')]);save();
    const other=JSON.stringify(activeCompanySnapshot());switchCompany('petfood');openResetCompany();ok($('dlg').textContent.includes('毛研食品'));ok($('dlg').textContent.includes('其他四家公司'));
    ok((await resetActiveCompany()).ok);eq(await fileStore.get(a.added[0].storage_key),undefined);eq(await fileStore.get('legacy-delete'),undefined);
    eq(JSON.stringify(portfolio.companies.software),other);switchCompany('software');eq(projects()[0].title,'保留雲序');eq(await (await attachmentBlob(b.added[0])).text(),'software');
  });
  await T('W6：重設持久化失敗不改資料也不刪附件',async()=>{
    switchCompany('software');projects()[0].title='不可遺失';const n=Object.values(db.nodes).find(n=>n.type==='task');const up=await addAttachments(n.id,[new File(['keep'],'keep.txt')]);save();
    const before=JSON.stringify({portfolio,db,ui,audit,undoStack});ok(!(await resetActiveCompany(()=>false)).ok);eq(JSON.stringify({portfolio,db,ui,audit,undoStack}),before);
    eq(await (await attachmentBlob(up.added[0])).text(),'keep');
  });
  // ── 新測試加在這一行上面 ──
  return results;
})()
