import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/package.json');
const sharp=require('sharp');
const root=path.dirname(fileURLToPath(import.meta.url));
const qa=path.resolve(root,'../../.superpowers/rag-architecture-v2-qa');
await fs.mkdir(qa,{recursive:true});
const W=2560,H=1440;
const C={bg:'#071B2B',panel:'#0C2638',ink:'#F5F8FA',muted:'#B3C7D3',border:'#38586D',teal:'#51D8C6',blue:'#87BEFF',gold:'#F4C16D',violet:'#CCB9FF',trace:'#91AABB'};
const E=[],texts=[];
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function text(s,x,y,size=28,color=C.ink,weight=400,anchor='start'){
 texts.push({s,x,y,size,anchor});E.push(`<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}">${esc(s)}</text>`);
}
function rect(x,y,w,h,fill,stroke='none',sw=1){E.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`);}
function route(points,kind,width=3,dashed=false,arrow=true){const d=points.map((p,i)=>`${i?'L':'M'} ${p[0]} ${p[1]}`).join(' ');E.push(`<path d="${d}" fill="none" stroke="${C[kind]||kind}" stroke-width="${width}"${dashed?' stroke-dasharray="10 8"':''}${arrow?` marker-end="url(#${kind})"`:''}/>`);}
function line(x1,y1,x2,y2){route([[x1,y1],[x2,y2]],'border',1.5,false,false);}
function panel(code,title,x,color,rows,store,map){
 const y=270,w=600,h=580;
 rect(x,y,w,h,C.panel,C.border,1.5);rect(x,y,6,h,color);
 text(code,x+28,y+49,42,color,700);text(title,x+85,y+47,31,C.ink,700);
 text(`組員 ${code} 姓名：____________`,x+28,y+90,25,C.muted);
 text('20 點',x+w-28,y+90,25,C.muted,400,'end');
 line(x+28,y+112,x+w-28,y+112);
 for(let i=0;i<rows.length;i++){
  const yy=y+152+i*64;
  text(rows[i][0],x+28,yy,28,color,700);
  text(rows[i][1],x+28,yy+32,26);
 }
 line(x+28,y+494,x+w-28,y+494);
 text(store,x+28,y+530,25,C.ink,600);
 text(map,x+28,y+562,22,C.muted);
}

rect(0,0,W,H,C.bg);
text('企業級 RAG 四模組分工架構',60,73,54,C.ink,700);
text('新版分工　A 管知識　B 管檢索　C 管回答與介面　D 貫穿治理與評估',62,125,29,C.muted);
text('建議架構　姓名待認領　各包 20 相對工作點',2498,75,26,C.muted,400,'end');
text('介面是資料契約，可共用同一後端部署',2498,123,25,C.muted,400,'end');

// The application owns the upload UI; ingestion and file status belong to A.
text('C → A　文件上傳：檔案／專案範圍',1280,177,25,C.teal,600,'middle');
route([[1960,270],[1960,190],[120,190],[120,270]],'teal');
text('A → C　文件狀態：解析／索引中／可查詢／失敗',1280,222,25,C.gold,600,'middle');
route([[160,270],[160,235],[1920,235],[1920,270]],'gold');

panel('A','知識接入與資料生命週期',60,C.teal,[
 ['知識盤點','來源、擁有者、權威文件與有效版本'],
 ['解析與清理','文字、標題、表格、重複內容處理'],
 ['結構化切片','依章條節切割，保留父子片段關係'],
 ['元資料管理','版本、生效日、來源位置與權限標籤'],
 ['生命週期','新增、改版、停用、封存與刪除']
],'管理原文、片段及結構化元資料','六層映射：數據源／處理／結構化存儲');

panel('B','智慧檢索與上下文建構',980,C.blue,[
 ['向量化與索引','統一 Embedding，維護文字及向量索引'],
 ['查詢理解','糾錯、意圖、同義詞與多輪問題改寫'],
 ['混合檢索','先限制授權範圍，再召回與排名融合'],
 ['重排序','Rerank 精選可支持回答的候選片段'],
 ['上下文建構','父片段再授權、去重、長度與來源']
],'交付已授權、可引用的證據包','六層映射：向量化／檢索索引／檢索增強');

panel('C','生成服務與應用互動',1900,C.gold,[
 ['問答協調','接收問題，呼叫檢索與模型服務'],
 ['生成與引用','Prompt、引用檢查、無答案與矛盾處理'],
 ['模型連線','LLM 呼叫、逾時、取消、錯誤處理'],
 ['使用者介面','Web／API、上傳、提問與回答呈現'],
 ['來源與回饋','原文檢視、使用者回饋與登入狀態隔離']
],'管理問答 API、對話介面及 Prompt','六層映射：生成／應用入口');

// Data preparation and lifecycle contracts.
text('KnowledgePackage',820,418,27,C.teal,700,'middle');
text('片段／父子關係／來源',820,454,24,C.muted,400,'middle');
text('有效版本／權限標籤',820,485,24,C.muted,400,'middle');
route([[660,507],[980,507]],'teal');
text('KnowledgeChange',820,590,27,C.teal,700,'middle');
text('新增／改版／停用／刪除',820,626,24,C.muted,400,'middle');
route([[660,650],[980,650]],'teal',3,true);
text('IndexStatus',820,741,27,C.gold,700,'middle');
text('索引版本／完成／失敗',820,777,24,C.muted,400,'middle');
route([[980,807],[660,807]],'gold');

// C issues a retrieval request; B returns the fully assembled evidence.
text('RetrievalRequest',1740,418,27,C.blue,700,'middle');
text('問題／範圍／授權資訊',1740,454,24,C.muted,400,'middle');
text('檢索設定／追蹤 ID',1740,485,24,C.muted,400,'middle');
route([[1900,507],[1580,507]],'blue');
text('ContextBundle',1740,646,27,C.gold,700,'middle');
text('證據文字／引用 ID／來源',1740,682,24,C.muted,400,'middle');
text('排序／索引版本',1740,713,24,C.muted,400,'middle');
route([[1580,744],[1900,744]],'gold');

// D spans every module, with separate trace and governance lanes.
for(const x of [60,980,1900]){
 route([[x+52,850],[x+52,1090]],'trace',3,true);
 text('TraceEvent',x+84,922,26,C.trace,700);
 text('階段／版本／耗時／錯誤',x+84,955,23,C.muted);
}
route([[608,1090],[608,850]],'violet',3,true);
text('EvaluationReport',576,1019,26,C.violet,700,'end');
text('品質回饋／生命週期規則',576,1052,23,C.muted,400,'end');
for(const x of [980,1900]){
 route([[x+548,1090],[x+548,850]],'violet',3,true);
 text('AccessContext',x+516,1008,26,C.violet,700,'end');
 text('EvaluationReport',x+516,1041,26,C.violet,700,'end');
 text('後端授權範圍／評測回饋',x+516,1073,22,C.muted,400,'end');
}

rect(60,1090,2440,280,C.panel,C.border,1.5);rect(60,1090,6,280,C.violet);
text('D',88,1143,42,C.violet,700);text('安全治理與運維評估',145,1141,34,C.ink,700);
text('組員 D 姓名：____________',1740,1141,25,C.muted);
text('20 點',2472,1141,25,C.muted,400,'end');
line(88,1162,2472,1162);
const governance=[
 [88,'權限與分級',['角色／部門／密級／授權規則','各模組執行檢查，原文開啟再授權']],
 [690,'全流程追蹤與稽核',['追蹤 ID、紀錄格式、保存期限','限制日誌存取，敏感內容遮罩']],
 [1290,'監控與設定版本',['錯誤率／延遲／Token／成本','模型、Prompt、索引與參數版本']],
 [1890,'品質評估與改善',['Recall／Precision／忠實度／引用','固定題組、版本比較、問題分派']]
];
for(const [x,title,rows] of governance){text(title,x,1209,29,C.violet,700);rows.forEach((s,i)=>text(s,x,1252+i*36,25));}
text('共同責任：A／B／C 提供紀錄與測試證據並修正所屬問題；D 負責規則、評測工具及結果彙整。',88,1344,24,C.muted);
text('來源：企業級 RAG 教學簡報第 14–20、26–32、37–40 頁。此圖為規劃分工，非已完成功能；20 點為本版相對估算。',60,1412,23,C.muted);

const defs=['teal','blue','gold','violet','trace'].map(k=>`<marker id="${k}" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 Z" fill="${C[k]}"/></marker>`).join('');
const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="title desc"><title id="title">企業級 RAG 新版四模組分工架構</title><desc id="desc">A 知識接入與生命週期，B 智慧檢索與上下文，C 生成與應用，D 安全治理與運維評估貫穿三者。四人各二十相對點，姓名留白。箭頭區分知識更新、問答檢索、追蹤紀錄及治理回饋。</desc><defs>${defs}</defs><g font-family="Microsoft JhengHei, Noto Sans CJK TC, sans-serif">${E.join('\n')}</g></svg>`;
const stem='企業級RAG_新版四模組架構圖';
await fs.writeFile(path.join(root,stem+'.svg'),svg);
await sharp(Buffer.from(svg),{density:108}).png().toFile(path.join(root,stem+'.png'));
await sharp(Buffer.from(svg),{density:72}).resize(1920,1080).png().toFile(path.join(qa,'preview.png'));
await fs.writeFile(path.join(qa,'labels.json'),JSON.stringify(texts,null,2));
const meta=await sharp(path.join(root,stem+'.png')).metadata();
if(meta.width!==3840||meta.height!==2160)throw Error('Unexpected dimensions');
for(const s of ['KnowledgePackage','KnowledgeChange','IndexStatus','RetrievalRequest','ContextBundle','AccessContext','TraceEvent','EvaluationReport'])if(!svg.includes(s))throw Error(`Missing contract: ${s}`);
if((svg.match(/姓名：____________/g)||[]).length!==4)throw Error('Expected four blank names');
console.log(JSON.stringify({width:meta.width,height:meta.height,modules:4,contracts:8,blankNames:4}));
