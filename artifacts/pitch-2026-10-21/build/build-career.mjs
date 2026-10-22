import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const ROOT='C:/Users/User/Desktop/專流/artifacts/pitch-2026-10-21';
const SKILL='C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.22136/skills/presentations';
const PY='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const SOURCE=path.join(ROOT,'output/專流_ProjectFlow_企業主管提案_差異化分析版.pptx');
const rev=process.argv[2]||'1';
const p=await PresentationFile.importPptx(await FileBlob.load(SOURCE));
const original=[...p.slides.items];
if(original.length!==23)throw new Error('Expected 23-slide source');
const kept=[0,1,4,6,7,9,11,12,16,13,14,19,22];
p.slides.keep(kept);
const C={bg:'#071B2B',ink:'#112D3D',white:'#F5F8FA',muted:'#A5BBC8',teal:'#51D8C6',gold:'#F4C16D',paper:'#F4F6F4',gray:'#526975'};
const FONT='Microsoft JhengHei';
const tasks=[
 {name:'李奕儒',role:'AI 互動與前端整合',skill:'React、TypeScript、Vitest',items:[['工作區與任務互動','梳理元件、狀態與操作流程',4],['AI 副手使用流程','驗證提問、引用、切案與錯誤提示',3],['API 契約整合','核對型別、請求與錯誤顯示',2],['前端測試與展示','整理測試證據與一條示範路徑',3]],evidence:'web/src/components/CopilotPanel.tsx；web/src/ai.ts；web/src/ai.test.tsx；web/src/components/NodeWorkspace.tsx'},
 {name:'李倫安',role:'API、權限與工作流',skill:'FastAPI、Session、pytest',items:[['公司與角色權限','驗證 Session、節點與 AI 存取範圍',4],['任務與交付規則','追蹤回報、閘門與覆寫 API',3],['稽核與例外處理','核對錯誤回應及業務操作紀錄',2],['後端測試與展示','整理越權、退回與例外案例',3]],evidence:'api/app/auth.py；api/app/permissions.py；api/app/routes/ai.py；api/app/services；api/tests'},
 {name:'廖洪茹',role:'資料建模與檢索',skill:'PostgreSQL、FTS5、SQL',items:[['業務資料模型','說明任務、營運關聯與交易規則',4],['文件檢索流程','驗證 FTS5／BM25 與角色過濾',3],['受控 SQL 分析','核對 16 種模板、參數與唯讀限制',3],['資料升級與匯入','整理 migration 與隔離資料驗證',2]],evidence:'api/app/models.py；api/alembic；api/app/ai/store.py；api/app/ai/queries.json；api/app/ai/import_cli.py'},
 {name:'劉力瑜',role:'模型串接與部署驗證',skill:'Ollama、Docker、測試評估',items:[['模型連線與回退','驗證端點、格式、引用及失敗回退',4],['容器部署與健檢','梳理 web／api／db 與資料 volume',3],['AI 情境評估','核對有來源、無來源與不支援問題',3],['CI 與端對端交付','整理測試流程、展示與重現步驟',2]],evidence:'api/app/ai/model.py；api/app/ai/service.py；deploy；.github/workflows/ci.yml；web/e2e/ai.spec.ts'}
];
for(const t of tasks)if(t.items.reduce((a,b)=>a+b[2],0)!==12)throw new Error('Unequal allocation');
await fs.writeFile(path.join(ROOT,'career-responsibilities.json'),JSON.stringify({purpose:'AI應用工程師求職作品集',status:'建議認領，非歷史個人貢獻紀錄',basis:'依使用者提供姓名順序分配。每人4項、12點，共48點；點數是相對工作量估算，不是工時、實績或程式貢獻比例。工作範圍為程式理解、驗證、維護與展示，不聲稱已由該人獨立開發。',tasks},null,2)+'\n');
function text(s,str,x,y,w,h,size=28,color=C.white,bold=false,name=str){const z=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});z.text=str;z.text.style={typeface:FONT,fontSize:size,color,bold,autoFit:'none',wrap:'square',insets:0,verticalAlignment:'top'};return z;}
function slide(title,tag,note,{light=false,source='README.md §2／§8'}={}){const s=p.slides.add();s.background.fill=light?C.paper:C.bg;text(s,tag,64,34,1152,30,18,light?C.gray:C.muted);text(s,title,64,86,1152,105,44,light?C.ink:C.white,true);s.speakerNotes.text=note+'\n\n本地查核：2026-10-21，feature/review-fixes，69a464c。來源：'+source+'。本輪只核對檔案與既有驗證紀錄，未重跑產品測試。分工為建議認領，不是歷史實績。';return s;}
function table(s,rows,{top=210,height=350,widths=[260,450,442],size=24,light=false}={}){const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:64,top,width:1152,height,columnWidths:widths,values:rows});t.borders.assign({fill:light?'#D3DEDF':'#355064',width:1,style:'solid'});for(let r=0;r<rows.length;r++){t.rows[r].height=r===0?58:(height-58)/(rows.length-1);for(let c=0;c<rows[0].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?'#123747':(light?C.paper:'#0A2232');cell.text.style={typeface:FONT,fontSize:r===0?22:size,color:r===0?C.teal:(light?C.ink:C.white),bold:r===0,verticalAlignment:'middle',insets:14,autoFit:'none'};}}return t;}
function node(s,title,body,x,y,w,h,{accent=C.teal,fill='#123747'}={}){const z=s.shapes.add({geometry:'rect',name:title,position:{left:x,top:y,width:w,height:h},fill,line:{fill:accent,width:1.5}});text(s,title,x+14,y+13,w-28,40,25,accent,true);text(s,body,x+14,y+53,w-28,h-57,20,C.white);return z;}
function link(s,a,b,from='right',to='left',dashed=false){return s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:dashed?C.gold:C.teal,width:2,style:dashed?'dashed':'solid'},tail:{type:'triangle',width:'med',length:'med'}});}
function setByName(s,starts,str){const z=s.shapes.items.find(sh=>sh.name.startsWith(starts));if(!z)throw new Error('Missing '+starts);z.text=str;}
setByName(original[0],'讓延誤','把研發交付流程\n做成可驗證的系統');
setByName(original[0],'企業專案','AI 應用工程師求職作品簡報');
setByName(original[0],'企業老闆','李奕儒、李倫安、廖洪茹、劉力瑜　2026.10');
original[0].speakerNotes.text='四人共同使用AI agent開發的ProjectFlow作品。重點是問題拆解、實際系統、AI資料與模型邊界、測試及交付。分工是本次按模組提出的責任認領建議，不把共同生成的程式碼說成某人已獨立完成。封面背景為AI生成情境圖，非產品證據。';
const app=slide('同一套流程，可延伸到四類協作場景','可以套用在哪裡',
 '食品新品研發已用虛構資料展示。產品導入、採購交付與內部流程是依現有任務／模板／文件／營運關聯提出的適用情境，尚非實際客戶部署或成效。前置條件可人工確認，跨系統ERP同步、完整BOM與批號成本仍未完成。',{light:true});
table(app,[['業務場景','可沿用的能力','導入時調整'],['食品新品研發（已展示）','配方／包材任務、試作、回報與版本','品保回報欄位與放行條件'],['新產品導入（可延伸）','階段、相依排程、文件與里程碑','各階段責任與驗收規則'],['採購交付專案（可延伸）','採購、收貨與任務關聯','供應商欄位及既有系統邊界'],['跨部門改善案（可延伸）','任務模板、角色、回報與稽核','部門權限與交付標準']],{height:365,widths:[310,470,372],size:22,light:true});
text(app,'AI 可延伸到 SOP／規格文件問答與部門報表查詢，需另接資料與驗權。',64,603,1152,40,23,'#177F78',true);
text(app,'食品為虛構展示案例；其他為適配分析，並非客戶導入實績。',64,649,1152,28,19,C.gray);
const tech=slide('技術棧從互動、資料到 AI 查詢完整串接','實際檔案核對',
 '版本以package.json、requirements.txt及Dockerfile核對。採React19、TypeScript7、Vite8，Python3.13、FastAPI、Uvicorn，SQLAlchemy2、Alembic與PostgreSQL17。AI用文字檢索FTS5/BM25，不是已完成向量RAG；可選Ollama，沒有實際遠端推論驗收主張。CI定義API SQLite、專用PostgreSQL、Vitest與build；Playwright是另外的隔離驗收。',{source:'web/package.json；api/requirements.txt；deploy/api.Dockerfile；deploy/docker-compose.yml；api/app/ai/store.py；.github/workflows/ci.yml',light:true});
table(tech,[['層次','目前使用','在專案中的用途'],['前端','React 19／TypeScript 7／Vite 8','任務工作區、時程、AI 對話'],['後端','Python 3.13／FastAPI／Uvicorn','REST API、公司權限、業務規則'],['正式資料','PostgreSQL 17／SQLAlchemy 2／Alembic','交易、資料模型與結構升級'],['AI 展示','SQLite FTS5／BM25／可選 Ollama','文件檢索、引用與受控 SQL'],['部署與測試','nginx／Docker Compose／GitHub Actions','pytest／Vitest／Playwright']],{height:380,widths:[180,535,437],size:22,light:true});
text(tech,'AI 查詢使用獨立展示資料，尚未接正式專案資料或向量檢索。',64,620,1152,40,24,C.gray);
const arch=slide('一頁看懂：三個服務與獨立的 AI 資料路徑','系統架構',
 '這張圖用原生PowerPoint形狀及連線製作。瀏覽器執行React，nginx供應靜態檔並將/api轉發FastAPI。正式業務資料存PostgreSQL，附件與版本檔在files volume。API的AI模組查每公司唯讀SQLite展示資料，FTS5/BM25取文件，再可選擇呼叫內網Ollama整理回覆；無模型時回退原文。Ollama為選用外部服務，不是第四個Compose容器。API主機埠限loopback，DB未對外發佈埠。正式內網HTTPS、帳號生命週期與排程備份仍待完成。',{source:'deploy/docker-compose.yml；deploy/nginx.conf；api/app/ai/store.py；api/app/ai/model.py；README.md §6'});
arch.shapes.add({geometry:'rect',name:'Docker Compose host',position:{left:290,top:195,width:926,height:375},fill:'#0A2232',line:{fill:'#355064',width:1.5}});
text(arch,'Docker Compose 主機',310,207,850,30,20,C.muted,true);
const browser=node(arch,'使用者瀏覽器','React SPA\n桌面／手機',64,260,186,120);
const web=node(arch,'web 容器','nginx 靜態檔\n/api 反向代理',320,260,200,120);
const api=node(arch,'api 容器','FastAPI／權限\n工作流與 AI 模組',570,260,260,120);
const pg=node(arch,'db 容器','PostgreSQL 17\n正式業務資料／pgdata',910,242,270,115);
const files=node(arch,'files volume','附件與文件版本',910,403,270,90);
const ai=node(arch,'ai_data volume','唯讀 SQLite／FTS5\n獨立 AI 展示資料',570,430,260,120,{accent:C.gold});
const ollama=node(arch,'選用 Ollama','內網模型服務',910,585,270,90,{accent:C.gold});
function segment(x1,y1,x2,y2,{arrow=false,dashed=false}={}){arch.shapes.add({geometry:'connector',kind:'straight',position:{left:x1,top:y1,width:x2-x1,height:y2-y1},line:{fill:dashed?C.gold:C.teal,width:2.5,style:dashed?'dashed':'solid'},...(arrow?{tail:{type:'triangle',width:'med',length:'med'}}:{})});}
segment(250,320,320,320,{arrow:true});segment(520,320,570,320,{arrow:true});
segment(830,300,910,300,{arrow:true});segment(830,350,850,350);segment(850,350,850,448);segment(850,448,910,448,{arrow:true});
segment(700,380,700,430,{arrow:true});
segment(830,366,870,366,{dashed:true});segment(870,366,870,630,{dashed:true});segment(870,630,910,630,{dashed:true,arrow:true});
text(arch,'API 主機埠限本機\nDB 未對外發佈埠',320,430,220,70,21,C.muted);
text(arch,'AI 模組讀展示資料後，可選擇呼叫模型。\n正式業務資料尚未提供 AI 查詢。',64,608,790,66,22,C.gold);
const aiwork=slide('開發用 AI Agent，產品提供受控的 AI 副手','兩種 AI 用途，責任清楚分開',
 '使用者說明四人共同用AI agent架構與開發，尚無明確歷史分工。repo有spec/plan、獨立審查、測試與PROGRESS/Git紀錄，這是可核對的開發過程，不能推定每一位人類完成某項程式。產品內的副手是檢索問答和受控SQL，不是自主執行所有專案決策的agent。四人可用後面的工作包認領理解、驗證、維護及展示。',{source:'使用者本輪說明；AGENTS.md；docs/WORKFLOW.md §14；docs/ai-assistant.md'});
text(aiwork,'開發協作',64,218,510,50,34,C.teal,true);
text(aiwork,'四人共同使用 AI Agent 開發\n以規格、計畫與版本記錄銜接工作\n透過獨立審查與隔離測試核對結果',64,302,535,170,28,C.white);
text(aiwork,'產品內的 AI 副手',680,218,536,50,34,C.teal,true);
text(aiwork,'FTS5／BM25 檢索文件並附引用\nOllama 為可選的回答整理模型\nSQL 僅能選固定分析模板',680,302,536,170,28,C.white);
text(aiwork,'本次分工：各自認領模組理解、驗證、維護與展示責任。',64,567,1152,50,31,C.gold,true);
text(aiwork,'下頁比例為建議工作量分配，不代表歷史個人程式貢獻。',64,632,1152,32,21,C.muted);
const team=slide('四人各承接一個模組，工作量均衡分配','組員分工建議',
 '姓名依使用者提供順序配置。每人4項工作，共12點，總48點，比例25%。點數為相對複雜度與展示準備工作量的初估，非真實工時，也不等於歷史貢獻或程式碼佔比。實際認領及熟悉程度需由組員確認；共同使用AI agent的事實保留。',{light:true,source:'使用者姓名與求職方向；career-responsibilities.json'});
table(team,[['組員','建議主責','工作包／估算比例'],...tasks.map(t=>[t.name,t.role,'4 項／12 點／25%'])],{height:342,widths:[220,530,402],size:27,light:true});
text(team,'共同交付：程式導讀、測試證據、可重現展示與限制說明。',64,585,1152,45,28,'#177F78',true);
text(team,'共 48 點，屬相對工作量估算；非實際工時或歷史個人貢獻比例。',64,640,1152,32,20,C.gray);
function taskSlide(a,b){const s=slide(`${a.name} × ${b.name}：可認領的工作項目`,'四人均分的工作包',
 '本頁是建議責任認領，沒有宣稱這兩位已完成所列功能。每人各4項工作12點，著重理解既有程式、補足證據、驗證及維護。面試時只使用自己能說明和重現的內容。\n'+a.name+'來源：'+a.evidence+'\n'+b.name+'來源：'+b.evidence,{light:true,source:'career-responsibilities.json'});
 const rows=[[a.name+'：'+a.role,b.name+'：'+b.role],...a.items.map((x,i)=>[`${x[2]} 點　${x[0]}\n${x[1]}`,`${b.items[i][2]} 點　${b.items[i][0]}\n${b.items[i][1]}`])];
 table(s,rows,{height:370,widths:[576,576],size:24,light:true});
 text(s,a.skill,64,607,540,40,23,'#177F78',true);text(s,b.skill,658,607,558,40,23,'#177F78',true);
 text(s,'每人 12 點；建議認領模組理解、驗證、維護與展示任務。',64,652,1152,28,18,C.gray);return s;}
const ab=taskSlide(tasks[0],tasks[1]),cd=taskSlide(tasks[2],tasks[3]);
const engineering=slide('AI 應用工程的重點：讓查詢可控、結果可查','面試可深入說明的工程決策',
 '三項皆由本地程式核對。auth.require_session從cookie查出公司與使用者，API檢查權限。AI文件檢索使用公司分庫、角色過濾與來源引用，model/service對回覆格式及引用作檢查，失敗回退原文，但引用正確不保證每句語意正確。SQL白名單參數化、read-only及authorizer，模型選query id而不是生成任意SQL；查詢還有步數及200列上限。這些是工程控制，不宣稱無漏洞、無幻覺或完整商業資安。',{source:'api/app/auth.py；api/app/permissions.py；api/app/routes/ai.py；api/app/ai/store.py；api/app/ai/model.py；api/app/ai/service.py'});
table(engineering,[['工程問題','目前的做法','可以用來驗證的情境'],['誰可以查哪些資料？','Session 決定公司與角色\nAPI 再檢查可見範圍','不同公司／角色查同一資料'],['答案能不能追到來源？','FTS5／BM25 檢索與引用\n模型異常時回退原文','無來源、錯誤引用、模型離線'],['模型會不會亂執行 SQL？','16 種模板、參數化與唯讀\n模型僅建議查詢種類','不支援問題、越權與寫入嘗試']],{height:342,widths:[300,450,402],size:24});
text(engineering,'已實作控制邊界；正式資料接入、向量檢索與模型品質評估仍待推進。',64,602,1152,55,25,C.gold,true);
const close=slide('從需求到驗證，展示一條完整的 AI 應用流程','作品總結',
 '總結時用實際能重現的流程及來源說明能力，不把團隊AI產出的所有程式當成每個人獨立掌握。四人建議按前端互動、API邊界、資料檢索、模型與部署各講一段。程式、測試與架構有實物可查；實際個人貢獻待認領和確認。下一步優先正式帳號／HTTPS／備份，再正式資料接入與檢索品質評估，遵循既有路線圖，不承諾時程。');
text(close,'業務問題',64,228,250,60,36,C.teal,true);text(close,'研發交付、版本與跨部門追查',360,228,856,70,36,C.white,true);
text(close,'工程成果',64,356,250,60,36,C.teal,true);text(close,'前端、API、資料與受控 AI 查詢',360,356,856,70,36,C.white,true);
text(close,'展示方式',64,484,250,60,36,C.teal,true);text(close,'四人各說明一個模組，重現同一條流程',360,484,856,90,32,C.white,true);
text(close,'後續：正式部署與帳號、正式資料接入、檢索與回答品質評估。',64,620,1152,40,25,C.gold);
const order=[original[0],original[1],original[4],app,tech,arch,aiwork,team,ab,cd,original[6],original[7],original[9],original[11],original[12],original[16],engineering,original[13],original[14],original[19],close,original[22]];
p.slides.reorder(order.map(s=>'sl/'+s.id));
// Update cross-references in retained comparison slides.
setByName(original[13],'官方依據','官方依據 [1–7]\n完整來源見第 22 頁');
setByName(original[14],'實機依據','實機依據：第 13 頁回報、第 14–15 頁版本與採購；模板依正式版功能總覽。');
original[13].speakerNotes.text+='\n求職版頁碼：來源附錄第22頁。';
original[14].speakerNotes.text=original[14].speakerNotes.text.replaceAll('第10頁','第13頁').replaceAll('第12至13頁','第14至15頁').replaceAll('第12–13頁','第14–15頁');
for(const [i,s] of order.entries()){
 if(i===0)continue;
 const marker=s.shapes.items.find(sh=>sh.name==='page-number'||/^\d{2}$/.test(sh.name));
 if(marker)marker.text=String(i+1).padStart(2,'0');
 else text(s,String(i+1).padStart(2,'0'),1155,688,60,24,16,C.muted,false,'page-number');
}
await fs.mkdir(path.join(ROOT,'build/rendered-career'),{recursive:true});
const candidate=path.join(ROOT,'build/candidate-career.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
for(const [i,s] of order.entries()){const png=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(ROOT,`build/rendered-career/slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));}
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const tables=[4,5,8,9,10,17,18,19,20];
const r=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:path.join(ROOT,`output/專流_ProjectFlow_AI應用工程師求職簡報_${rev}.pptx`),pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:22,requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'reference',families:[FONT],referencePath:SOURCE,referenceSha256:createHash('sha256').update(await fs.readFile(SOURCE)).digest('hex')},verifyArtifactToolImport:true,receiptPath:path.join(ROOT,`build/validation-career-${rev}.json`)});
console.log(JSON.stringify(r));
