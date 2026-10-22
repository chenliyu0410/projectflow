import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const ROOT='C:/Users/User/Desktop/專流/artifacts/pitch-2026-10-21';
const SKILL='C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.22136/skills/presentations';
const PY='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const p=await PresentationFile.importPptx(await FileBlob.load(path.join(ROOT,'build/source-before-shots.pptx')));
const original=[...p.slides.items];
const C={bg:'#071B2B',white:'#F5F8FA',muted:'#A5BBC8',teal:'#51D8C6'};
const FONT='Microsoft JhengHei';
function text(s,str,x,y,w,h,size=28,color=C.white,bold=false){const z=s.shapes.add({geometry:'textbox',name:str,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});z.text=str;z.text.style={typeface:FONT,fontSize:size,color,bold,autoFit:'none',wrap:'square',insets:0};return z;}
const shots=[
 {after:6,file:'01-overview.png',crop:[278,173,1137,497],title:'總覽列出延遲與待確認，主管直接找重點',caption:'看完成度、預計完成日與延遲項目，再決定要追哪個專案',note:'操作路徑：登入 → 所有專案總覽。展示資料的數字為截圖當下的8個專案與現有任務，不代表客戶成效。請指向完成度、時程、待確認三欄，說明主管可先定位需介入的專案，再下鑽到任務。裁切保留完整八個專案列及上方統計。'},
 {after:6,file:'02-timeline-full.png',crop:[294,208,1104,513],title:'看見逾期任務，也看見後續相依',caption:'紅色逾期標記與前置連線，讓改期討論有共同依據',note:'操作路徑：MY-2610 雞肉凍乾零食新品開發 → 專案總覽 → 時程 → 月 → 關鍵路徑。圖中可見包材與標示任務逾期，以及通往委外試產、檢驗、首批交付的相依連線。這是目前可見範圍的路徑估算，非完整CPM或AI預測。本次只切換檢視，未拖曳或儲存日期。'},
 {after:7,file:'03-report-full.png',crop:[278,210,1136,403],title:'主管看到回報內容，再確認或退回',caption:'成果說明、實際完成日與審核意見，留在同一張回報卡',note:'操作路徑：MY-2610 → 第二輪適口性紀錄審核 → 完成回報。截圖為既有v1等待確認，展示達成結果、成果說明與實際完成日，以及確認和退回操作。退回按鈕因尚未填寫必要意見而停用。本次未確認或退回，未改變原展示回報狀態。此功能不等同電子簽章或品質認證。'},
 {after:8,file:'04-documents-full.png',crop:[313,171,1067,380],title:'版本與修改說明，跟著文件一起保存',caption:'看得見目前版本、修改者、時間與說明；舊版可從版本紀錄選取',note:'操作路徑：MY-2610 → 文件 → 上傳示範試作規格.txt → 編輯文字 → 儲存新版本。因既有展示包沒有文件，本次在隔離資料庫實際上傳明確標示「示範」的TXT，再修改並存成v2；v1仍存在且可選取、下載。畫面不是合成介面。新增內容僅限隔離示例，不是實際生產規範，也未寫入使用者既有服務。'},
 {after:8,file:'05-linked-data-full.png',crop:[278,371,1136,367],title:'查任務時，直接找到相關採購單',caption:'高阻隔袋交期任務連到 MY-PO02，採購狀態跟著關聯資料顯示',note:'操作路徑：MY-2610 → 高阻隔袋交期確認 → 資料 → 搜尋採購MY-PO02 → 關聯。只在隔離資料庫實際建立此關聯。截圖可見已儲存、已關聯資料(1)、採購單名稱與打樣待確認狀態。這是任務與營運紀錄的關聯功能，不是ERP同步、收貨自動解鎖或已完成採購。'},
];
const added=[];
for(const def of shots){
 const s=p.slides.add();s.background.fill=C.bg;
 text(s,'實際操作畫面｜隔離展示資料',64,30,1152,30,18,C.muted);
 text(s,def.title,64,76,1152,70,40,C.white,true);
 const [x,y,w,h]=def.crop;const scale=Math.min(1152/w,455/h);const dw=w*scale,dh=h*scale;
 const img=await fs.readFile(path.join(ROOT,'screenshots',def.file));
 s.images.add({blob:img.buffer.slice(img.byteOffset,img.byteOffset+img.byteLength),contentType:'image/png',alt:def.title+'；實際介面使用虛構展示資料',fit:'cover',position:{left:(1280-dw)/2,top:166+(455-dh)/2,width:dw,height:dh},crop:{left:x/1440,top:y/900,right:(1440-x-w)/1440,bottom:(900-y-h)/900}});
 text(s,def.caption,64,638,1152,42,25,C.teal,true);
 s.speakerNotes.text=def.note+'\n\n截圖來源：ProjectFlow正式版React/FastAPI，feature/review-fixes，程式基準46102ad。於2026-10-21使用agent-browser擷取 http://127.0.0.1:15181。此為本次隔離SQLite展示環境，資料取自deploy/demo-data（1758列虛構展示資料）；並非使用者既有服務或客戶實績。未修改UI或偽造文字；僅在投影片內裁切以放大關鍵區域。\n原始截圖：'+path.join(ROOT,'screenshots',def.file);
 added.push({def,slide:s});
}
const order=[];
for(let i=0;i<original.length;i++){order.push(original[i].id);for(const item of added.filter(a=>a.def.after===i+1))order.push(item.slide.id);}

p.slides.reorder(order.map(id=>'sl/'+id));
for(const [i,s] of p.slides.items.entries()){
 if(i===0)continue;
 const oldIndex=original.findIndex(o=>o.id===s.id);
 if(oldIndex>=0){const marker=s.shapes.items.find(sh=>sh.name===String(oldIndex+1).padStart(2,'0'));if(!marker)throw new Error('Page number missing '+oldIndex);marker.text=String(i+1).padStart(2,'0');}
 else text(s,String(i+1).padStart(2,'0'),1155,688,60,24,16,C.muted);
}
await fs.writeFile(path.join(ROOT,'build/screenshot-provenance.json'),JSON.stringify(shots,null,2));
await fs.mkdir(path.join(ROOT,'build/rendered-shots'),{recursive:true});
const candidate=path.join(ROOT,'build/candidate-shots.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
for(const [i,s] of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(ROOT,`build/rendered-shots/slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 console.log('RENDERED',i+1);
}
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const tableOwners=[6,15,16,17];
const finalPath=path.join(ROOT,'output/專流_ProjectFlow_企業主管提案_實機截圖版_v2.pptx');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath,pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:19,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath:path.join(ROOT,'build/validation-shots-v2.json')});
console.log(JSON.stringify(result));
