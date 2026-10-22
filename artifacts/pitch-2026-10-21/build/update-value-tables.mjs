import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const ROOT='C:/Users/User/Desktop/專流/artifacts/pitch-2026-10-21';
const SKILL='C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.22136/skills/presentations';
const PY='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const SOURCE=path.join(ROOT,'output/專流_ProjectFlow_AI應用工程師求職簡報.pptx');
const rev=process.argv[2]||'tables1';
const p=await PresentationFile.importPptx(await FileBlob.load(SOURCE));
const original=[...p.slides.items];
if(original.length!==22)throw new Error('Expected 22-slide source');
const C={bg:'#071B2B',ink:'#112D3D',white:'#F5F8FA',muted:'#526975',teal:'#51D8C6',dark:'#123747',paper:'#F4F6F4'};
const FONT='Microsoft JhengHei';
function text(s,str,x,y,w,h,size=24,color=C.ink,bold=false,name=str){const z=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});z.text=str;z.text.style={typeface:FONT,fontSize:size,color,bold,autoFit:'none',wrap:'square',insets:0,verticalAlignment:'top'};return z;}
function slide(title,tag,page){const s=p.slides.add();s.background.fill=C.paper;text(s,tag,64,34,1152,30,18,C.muted);text(s,title,64,85,1152,65,40,C.ink,true);text(s,String(page),1155,688,60,24,16,C.muted,false,'page-number');return s;}
function table(s,rows,widths,{top=172,height=454,size=21,highlight=1}={}){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:64,top,width:1152,height,columnWidths:widths,values:rows});
 t.borders.assign({fill:'#D3DEDF',width:1,style:'solid'});
 for(let r=0;r<rows.length;r++){t.rows[r].height=r===0?64:(height-64)/(rows.length-1);for(let c=0;c<rows[0].length;c++){
  const cell=t.getCell(r,c);const hero=c===highlight;
  cell.fill=hero?(r===0?C.teal:C.dark):(r===0?'#DDE6E5':C.paper);
  cell.text.style={typeface:FONT,fontSize:r===0?(hero?26:22):size,color:hero?(r===0?C.ink:C.white):(r===0?C.ink:C.muted),bold:r===0||hero,verticalAlignment:'middle',insets:11,autoFit:'none'};
 }}return t;
}
const comparison=slide('專流串起研發進度、交付證據與營運紀錄','競品比較：以研發交付情境選工具',18);
table(comparison,[
 ['比較重點','專流 ProjectFlow','Notion','Asana','monday.com','Odoo'],
 ['主要\n切入點','研發專案從執行\n到交付的完整脈絡','文件與\n資料庫組織','任務協作\n與核准','看板配置\n與跨板資訊','採購、庫存\n與製造作業'],
 ['工作\n如何組織','專案、階段與任務\n搭配前置條件及階段閘門','資料庫、\n子任務與相依','以任務安排\n工作與核准','以看板及\n關聯項目組織','以業務模組\n及單據處理'],
 ['如何確認\n真的完成','成果與附件送審\n退回留意見，重送留舊版','資料庫與頁面\n設計回報流程','核准或拒絕\n要求修改','依流程配置\n欄位與看板','依模組的\n單據流程處理'],
 ['如何追查\n交付問題','從任務查看回報歷程\n文件版本及營運關聯','資料庫關聯\n彙整資訊','從任務與\n核准流程追蹤','跨板連結\n與鏡像欄位','採購、庫存與\n製造模組查詢'],
 ['團隊選用\n的理由','已有可展示的交付流程\n用實際案例驗證適配性','重視資訊\n組織彈性','重視任務\n協作與核准','重視看板\n及流程配置','重視完整\n營運管理']
],[130,310,178,178,178,178]);
text(comparison,'情境比較，非完整功能排名；競品亦可配置相關流程。官方來源 [1–7] 見第 22 頁。',64,644,1152,30,18,C.muted);
comparison.speakerNotes.text=`本頁依使用者確認方向，將比較重點放在研發交付流程的整合起點。專流已實作專案／階段／任務、前置與閘門、回報送審／退回／版本、文件版本及營運關聯。具權限者可覆寫前置或閘門，但須留理由與紀錄。資料關聯不代表自動ERP同步，文件版本不代表已有文件簽核或版本還原。\n競品各欄是此情境中的能力切入點與選用分析，不是唯一用途，也沒有聲稱對手做不到相關流程。Notion以資料庫設計回報、monday以欄位配置回報為分析建議，非已實測的同等審核流程。未比較價格、速度、導入工時或完整資安成熟度。\n專流來源：README.md §2／§8、既有第13頁回報與第14–15頁文件／採購實機畫面。\n[1] https://www.notion.com/help/relations-and-rollups\n[2] https://www.notion.com/help/tasks-and-dependencies\n[3] https://help.asana.com/s/article/approvals\n[4] https://support.monday.com/hc/en-us/articles/360001733859-The-Mirror-Column\n[5–7] https://www.odoo.com/documentation/20.0/applications/inventory_and_mrp.html\n官方資料與本地專案於2026-10-21核對。Odoo以已讀官方搜尋索引佐證模組範圍，部分文件直接讀取逾時。`;
const value=slide('選專流：交付有依據，流程可追查，經驗能沿用','差異化價值：主管的問題與專流的解法',19);
table(value,[
 ['主管面對的問題','專流已做出的解法','主管得到的價值'],
 ['「說完成了，\n成果在哪裡？」','結構化回報、成果附件\n確認與退回、重送版本','完成狀態\n有交付依據'],
 ['「前面還沒確認，\n後面怎麼就開始？」','前置條件與階段閘門\n有權限的例外放行須留理由與紀錄','流程條件與\n例外決策可追查'],
 ['「這次試作用哪份文件、\n哪筆採購？」','任務中的文件版本\n關聯採購、收貨與工單等營運紀錄','從專案任務\n找回執行脈絡'],
 ['「下次做類似專案，\n又要重新整理？」','任務樹另存模板、模板版本\n變數與相對日期','既有流程成為\n可重複使用的起點']
],[310,510,332],{height:454,size:24});
text(value,'同一個專案脈絡中，查看做了什麼、交付了什麼、如何確認，以及相關資料在哪裡。',64,645,1152,31,21,C.ink,true);
value.speakerNotes.text=`這四項是專流現有機制對主管問題的價值映射，不宣稱為獨家功能或已量測的客戶成效。\n第一列：完成回報送審、意見必填退回與重送版本，實機見第13頁。第二列：前置條件與階段閘門；有權限者可覆寫，須保留理由及紀錄，不能宣稱永遠禁止跳關。第三列：文件版本與任務營運關聯，實機見第14–15頁；不是自動BOM、批號追溯或ERP同步。第四列：正式版模板的任務樹、版本、變數與相對日期能力。\n講法：團隊需要一起管理研發階段、交付審核與相關營運紀錄時，專流已有可演示的整合流程，可以先用實際研發案例驗證適配性。AI維持工程能力展示，不把尚未接正式資料的AI當成勝過競品的主要理由。\n本地來源：README.md §2／§3.2／F2／F11／§8。2026-10-21核對。`;
p.slides.keep(p.slides.items.map((_,i)=>i).filter(i=>i!==17&&i!==18));
const order=[...original.slice(0,17),comparison,value,...original.slice(19)];
p.slides.reorder(order.map(s=>'sl/'+s.id));
const outDir=path.join(ROOT,`build/rendered-${rev}`);await fs.mkdir(outDir,{recursive:true});
const candidate=path.join(ROOT,`build/candidate-${rev}.pptx`);await (await PresentationFile.exportPptx(p)).save(candidate);
for(const [i,s] of order.entries()){const png=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(outDir,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));}
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const tables=[4,5,8,9,10,17,18,19,20];
const r=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:path.join(ROOT,`output/專流_ProjectFlow_AI應用工程師求職簡報_${rev}.pptx`),pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:22,requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'reference',families:[FONT],referencePath:SOURCE,referenceSha256:createHash('sha256').update(await fs.readFile(SOURCE)).digest('hex')},verifyArtifactToolImport:true,receiptPath:path.join(ROOT,`build/validation-${rev}.json`)});
console.log(JSON.stringify(r));
