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
  // ── 新測試加在這一行上面 ──
  return results;
})()
