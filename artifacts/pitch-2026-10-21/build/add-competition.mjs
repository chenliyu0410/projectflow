import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';

// Input is the 19-slide screenshot deck from git commit 15d25fa.
const ROOT='C:/Users/User/Desktop/專流/artifacts/pitch-2026-10-21';
const SKILL='C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.22136/skills/presentations';
const PY='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const SOURCE=path.join(ROOT,'build/source-before-competition.pptx');
const revision=process.argv[2]||'focus-1';
const p=await PresentationFile.importPptx(await FileBlob.load(SOURCE));
const original=[...p.slides.items];
if(original.length!==19)throw new Error('Expected 19 input slides');
await p.inspect({select:'$.slides[*]',include:['id','index','layout','elements.id','elements.kind','elements.text'],fileName:path.join(ROOT,'build/competition-input-inspection.ndjson')});
const C={bg:'#071B2B',ink:'#112D3D',muted:'#A5BBC8',white:'#F5F8FA',teal:'#51D8C6',gold:'#F4C16D',paper:'#F4F6F4',gray:'#526975'};
const FONT='Microsoft JhengHei';
const sources=[
 {id:1,product:'Notion',title:'Relations & rollups',url:'https://www.notion.com/help/relations-and-rollups',claim:'資料庫之間可建立關聯與彙總。'},
 {id:2,product:'Notion',title:'Sub-items & dependencies',url:'https://www.notion.com/help/tasks-and-dependencies',claim:'支援子任務、相依與日期自動調整。'},
 {id:3,product:'Asana',title:'Approvals',url:'https://help.asana.com/s/article/approvals',claim:'核准任務可同意、要求修改或拒絕。可用方案需確認。'},
 {id:4,product:'monday.com',title:'The Connect Boards Column',url:'https://support.monday.com/hc/en-us/articles/360000635139-The-Connect-Boards-Column',claim:'連結不同看板項目，並用鏡像欄位顯示關聯資料。'},
 {id:5,product:'Odoo',title:'Manufacturing product configuration（20.0）',url:'https://www.odoo.com/documentation/20.0/applications/inventory_and_mrp/manufacturing/management/configure_manufacturing_product.html',claim:'製造模組有BOM及批號／序號設定。'},
 {id:6,product:'Odoo',title:'Pricing / hosting options',url:'https://www.odoo.com/pricing',claim:'官方方案說明包括Odoo Online、Odoo.sh與On-premise。未引用價格，也不假設所有方案均支援自管。'},
 {id:7,product:'Odoo',title:'Allocation report（20.0）',url:'https://www.odoo.com/documentation/20.0/applications/inventory_and_mrp/manufacturing/workflows/allocation.html',claim:'採購／製造單與收貨入庫可用於滿足需求配置。'}
];
const sourceNotes=sources.map(s=>`[${s.id}] ${s.product} ${s.title}\n${s.url}\n已核對內容：${s.claim}`).join('\n\n');
const provenance={verifiedOn:'2026-10-21',method:'官方文件與搜尋索引核對，非付費帳號橫向實測。Odoo部分頁面直接讀取逾時，採官方網域搜尋摘錄，不引用未讀到的細節。',sources,localEvidence:['README.md §2 功能總覽','README.md §8 後續路線圖','screenshots/provenance.json'],boundaries:['比較情境是分析判斷，不是完整功能或效能排名。','導入、追查與成本優勢是待驗證假設。','自管部署不是獨家能力。','沒有ERP／AD串接、正式AI資料整合或正式安全部署完成的主張。']};
await fs.writeFile(path.join(ROOT,'competition-sources.json'),JSON.stringify(provenance,null,2)+'\n');
function text(s,str,x,y,w,h,size=28,color=C.white,bold=false,name=str){
 const sh=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=str;sh.text.style={typeface:FONT,fontSize:size,color,bold,autoFit:'none',wrap:'square',insets:0,verticalAlignment:'top'};return sh;
}
function slide(title,tag,note,light=false){
 const s=p.slides.add();s.background.fill=light?C.paper:C.bg;
 text(s,tag,64,34,1152,30,18,light?C.gray:C.muted);
 text(s,title,64,86,1152,105,44,light?C.ink:C.white,true);
 s.speakerNotes.text=note+'\n\n比較基準：2026-10-21。正式版現況：README.md §2／§8，程式基準15d25fa。比較結論是依已查官方文件與現有專流展示作出的定位分析，未完成競品實機橫向評測。能力可能依方案、版本、設定與外掛而異。\n\n'+sourceNotes;
 return s;
}
function table(s,rows,{left=64,width=1152,top=210,height=360,widths=[210,470,472],size=23,light=false}={}){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left,top,width,height,columnWidths:widths,values:rows});
 t.borders.assign({fill:light?'#D3DEDF':'#355064',width:1,style:'solid'});
 for(let r=0;r<rows.length;r++){
  t.rows[r].height=r===0?58:(height-58)/(rows.length-1);
  for(let c=0;c<rows[0].length;c++){
   const cell=t.getCell(r,c);cell.fill=r===0?'#123747':(light?C.paper:'#0A2232');
   cell.text.style={typeface:FONT,fontSize:r===0?22:size,color:r===0?C.teal:(light?C.ink:C.white),bold:r===0,verticalAlignment:'middle',insets:14,autoFit:'none'};
  }
 }return t;
}
const additions=[];
{
 const s=slide('選專流，把研發交付的規則與證據管起來','為什麼選專流',
 '建議講約40秒。專流放在主視覺，先給選用結論：如果企業正在處理跨部門研發、試作與新品導入，需要把回報確認、前置規則及相關文件採購放在同一個工作脈絡，專流值得優先試用。Notion、Asana與monday.com亦有關聯、核准與工作流能力，也有模板及自動化，不能宣稱必須從零打造。這裡比較的是現有產品提供的工作起點，不是斷言其他產品做不到。專流已有研發任務、完成回報、閘門、模板與營運關聯，可用現有展示路徑對照企業需求，再調整規則。是否減少導入工時仍需實測。Odoo已有製造與營運管理功能；完整ERP需求不以專流取代。',true);
 text(s,'市售產品的可用能力',64,204,410,42,25,C.gray,true);
 table(s,[['產品','代表能力'],['Notion','資料庫關聯與相依'],['Asana','核准與要求修改'],['monday.com','跨看板連結與鏡像'],['Odoo','採購、庫存與製造']],{left:64,width:410,widths:[150,260],top:258,height:290,size:20,light:true});
 text(s,'官方依據 [1–7]\n完整來源見第 23 頁',64,566,410,60,20,C.gray);
 s.shapes.add({geometry:'rect',name:'ProjectFlow focal panel',position:{left:506,top:200,width:710,height:407},fill:'#123D48',line:{fill:'none',width:0}});
 text(s,'專流 ProjectFlow',538,229,646,62,46,C.teal,true);
 text(s,'為研發交付準備好的流程起點',538,300,646,48,30,C.white,true);
 const pairs=[['交付有依據','回報、審核、閘門與例外紀錄'],['追查有脈絡','任務串文件版本與採購紀錄'],['流程能沿用','工作流模板帶到下一個專案']];
 for(const [i,r] of pairs.entries()){
  const y=365+i*57;text(s,r[0],538,y,205,40,27,C.teal,true);text(s,r[1],754,y,430,42,24,C.white);
 }
 text(s,'優先試用：跨部門研發、試作與新品導入',538,551,646,40,24,C.gold,true);
 text(s,'競品亦可搭建相關流程；本頁比較選用起點，非獨家功能排名。',64,634,1152,35,20,C.gray);
 additions.push(s);
}
{
 const s=slide('專流把主管的三個追問，變成可執行流程','選用理由與現有能力',
 '建議講約45秒。用主管的具體管理情境說明三個選用理由。第一，執行者說完成之後，主管能看回報內容再確認或退回，配合前置、閘門及例外紀錄；不能說所有任務都強制審核或全自動放行，實際規則仍需設定，條件型前置目前由管理者確認。第二，任務已有文件版本及採購等營運關聯，不必在本次展示另建一套關聯模型；但與既有ERP的同步仍未完成。第三，正式版已有15套產業工作流、模板另存套用及版本，可把做法帶到下一案；這不是說競品沒有模板。主張是專流提供可直接演示與調整的研發交付起點，並非宣稱零設定或已量測導入更快。證據請連回第10頁回報、第12至13頁版本與採購，模板依README正式功能總覽。');
 const t=table(s,[['主管最怕的事','專流已有的流程','主管拿到的管理依據'],['任務說完成了，\n卻沒人確認能交付','回報送審與退回\n前置、閘門與覆寫留痕','查得到誰確認、依據為何\n讓例外放行有紀錄'],['規格或包材變動，\n相關紀錄找不齊','文件版本保存\n任務連到採購與營運紀錄','從任務找到版本與採購\n討論問題時能對照紀錄'],['換一個新品，\n又要重整整套工作','產業工作流模板\n多層任務、階段與模板版本','沿用流程並依專案調整\n把做法留給下一個團隊']],{top:216,height:350,widths:[300,460,392],size:23});
 for(let r=1;r<4;r++){t.getCell(r,1).fill='#123D48';t.getCell(r,1).text.style={typeface:FONT,fontSize:23,color:C.teal,bold:true,verticalAlignment:'middle',insets:14,autoFit:'none'};}
 text(s,'選用理由：已有可展示的研發交付流程，先套用、再按公司規則調整。',64,591,1152,42,27,C.gold,true);
 text(s,'實機依據：第 10 頁回報、第 12–13 頁版本與採購；模板依正式版功能總覽。',64,641,1152,28,19,C.muted);
 additions.push(s);
}
{
 const s=slide('如果卡在研發交付，專流值得優先試用','適合選專流的條件',
 '建議講約35秒。把推薦寫成具體條件：研發交付要明確放行、任務需要文件及採購依據、希望在自管環境驗證工作流，這些需求與專流目前可展示的能力吻合，因此值得先跑一個案。這是定位與適配度分析，不是全面優於市售工具。若現有Notion、Asana或monday已能順暢支援這些流程，就應把切換與訓練成本納入，不以功能相似為理由要求換系統。如果需求主要是完整ERP、BOM、批號追溯與成本核算，專流仍有缺口。比較時使用同一試作案例與角色資料，計入建置、資料匯入、規則設定、訓練、授權與維運成本，量測找延遲責任、文件版本與採購單的完成時間及正確率。AI仍為獨立展示資料，不能作為超越競品的證據。',true);
 table(s,[['你的管理需求','優先試用專流的理由','目前需要一起考量'],['交付需要明確放行','回報、前置與閘門已有流程','仍需設定企業的放行規則'],['任務要查到文件與採購','版本與營運紀錄可連回任務','尚未串接企業既有 ERP'],['希望掌握部署環境','可在本機／區網驗證工作流','正式帳號、HTTPS與備份待完成']],{top:216,height:302,widths:[300,450,402],size:23,light:true});
 text(s,'建議：用一個試作專案，驗證交付確認與追查速度。',64,552,1152,47,32,'#177F78',true);
 text(s,'與現用工具比較設定工時、查找正確率與總成本；改善幅度以實測為準。',64,613,1152,40,22,C.gray);
 additions.push(s);
}
const appendix=slide('比較來源與適用範圍','附錄　官方資料查核：2026-10-21',
 '這頁是備查，不需要逐條口述。完整URL及對應主張均在本頁與相關頁的講者備註，以及competition-sources.json。未採用第三方評分、未比較價格，也沒有宣稱已測試競品。Odoo部分官方頁面直接讀取逾時，僅採官方網域搜尋索引中已看見的內容；不延伸解讀未讀到的功能。');
const sourceLines=[
 ['[1–2] Notion','Relations & rollups\nSub-items & dependencies'],
 ['[3] Asana','Approvals'],
 ['[4] monday.com','The Connect Boards Column'],
 ['[5–7] Odoo','製造產品設定、需求配置（20.0）\nPricing 的部署選項說明']
];
for(const [i,r] of sourceLines.entries()){
 const y=208+i*86;text(appendix,r[0],64,y,260,48,27,C.teal,true);text(appendix,r[1],344,y,872,78,25,C.white);
}
text(appendix,'專流依據：README §2／§8 與本簡報實機畫面；完整網址見講者備註。',64,574,1152,40,22,C.muted);
text(appendix,'定位分析不等於橫向實測；功能與部署選項以實際方案及版本為準。',64,628,1152,40,22,C.gold);
const order=[];
for(const [i,s] of original.entries()){
 order.push(s);if(i===12)order.push(...additions);
}
order.push(appendix);p.slides.reorder(order.map(s=>'sl/'+s.id));
for(const [i,s] of p.slides.items.entries()){
 if(i===0)continue;
 const oldIndex=original.findIndex(o=>o.id===s.id);
 if(oldIndex>=0){
  const markers=s.shapes.items.filter(sh=>String(sh.text).trim()===String(oldIndex+1).padStart(2,'0'));
  // Text wrappers stringify differently across imports, so fall back to named page markers.
  const marker=markers[0]||s.shapes.items.find(sh=>/^\d{2}$/.test(sh.name));
  if(!marker)throw new Error('Missing page marker '+oldIndex);
  marker.text=String(i+1).padStart(2,'0');
 }else text(s,String(i+1).padStart(2,'0'),1155,672,60,25,16,s===additions[0]||s===additions[2]?C.gray:C.muted,false,'page-number');
}
await fs.mkdir(path.join(ROOT,'build/rendered-competition-focus'),{recursive:true});
const candidate=path.join(ROOT,'build/candidate-competition.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
for(const [i,s] of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(ROOT,`build/rendered-competition-focus/slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const tableOwners=[6,14,15,16,18,19,20];
const finalPath=path.join(ROOT,`output/專流_ProjectFlow_企業主管提案_差異化分析版_${revision}.pptx`);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath,pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:23,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'reference',families:[FONT],referencePath:SOURCE,referenceSha256:createHash('sha256').update(await fs.readFile(SOURCE)).digest('hex')},verifyArtifactToolImport:true,receiptPath:path.join(ROOT,`build/validation-competition-${revision}.json`)});
console.log(JSON.stringify(result));
