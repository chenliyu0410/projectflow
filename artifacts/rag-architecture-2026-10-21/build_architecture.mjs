import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/package.json');
const sharp=require('sharp');
const root=path.dirname(fileURLToPath(import.meta.url));
const qa=path.resolve(root,'../../.superpowers/rag-architecture-qa');
await fs.mkdir(qa,{recursive:true});
const W=1920,H=1080;
const C={bg:'#071B2B',panel:'#0C2638',ink:'#F5F8FA',muted:'#B3C7D3',border:'#38586D',teal:'#51D8C6',blue:'#87BEFF',gold:'#F4C16D',violet:'#CCB9FF'};
const elements=[];
const labels=[];
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function text(value,x,y,size=26,color=C.ink,weight=400,anchor='start'){
 labels.push({value,x,y,size,anchor});
 elements.push(`<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}">${esc(value)}</text>`);
}
function rect(x,y,w,h,fill,stroke='none',sw=1){elements.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`);}
function line(x1,y1,x2,y2,color=C.border,width=2,dashed=false){elements.push(`<path d="M ${x1} ${y1} L ${x2} ${y2}" stroke="${color}" stroke-width="${width}" fill="none"${dashed?' stroke-dasharray="9 7"':''}/>`);}
function arrow(x1,y1,x2,y2,kind,dashed=false){elements.push(`<path d="M ${x1} ${y1} L ${x2} ${y2}" stroke="${C[kind]}" stroke-width="3" fill="none" marker-end="url(#${kind})"${dashed?' stroke-dasharray="9 7"':''}/>`);}
function module(code,title,x,y,accent,rows,foot){
 rect(x,y,650,300,C.panel,C.border,1.5);
 rect(x,y,5,300,accent);
 text(code,x+28,y+45,36,accent,700);
 text(title,x+84,y+44,32,C.ink,700);
 text(`組員 ${code} 姓名：____________`,x+28,y+78,22,C.muted);
 text('主責 20 點',x+620,y+78,22,C.muted,400,'end');
 line(x+28,y+96,x+622,y+96);
 for(let i=0;i<rows.length;i++){
  text(rows[i][0],x+28,y+133+i*35,25,accent,700);
  text(rows[i][1],x+188,y+133+i*35,25);
 }
 text(foot,x+28,y+280,21,C.muted);
}

rect(0,0,W,H,C.bg);
text('RAG 四模組責任與資料流架構',72,67,46,C.ink,700);
text('文件問答第一版規劃　姓名待認領　每人負責模組實作、測試與串接',74,111,24,C.muted);
// Legend is independent of the responsibility colors.
for(const [x,kind,label] of [[1254,'teal','建索引'],[1454,'blue','查詢請求'],[1670,'gold','結果回傳']]){
 arrow(x,104,x+48,104,kind);text(label,x+62,111,22,C[kind]);
}

module('A','資料接入與知識整理',72,170,C.teal,[
 ['解析清理','文字型 PDF／DOCX／TXT'],
 ['切塊策略','依章節、段落及長度分段'],
 ['來源標記','文件 ID、版本、頁碼或章節'],
 ['生命週期','去重、更新、刪除與失敗重試']
],'保存原文與片段　　驗證：解析完整、來源可追溯');

module('B','索引與檢索',1198,170,C.blue,[
 ['向量與索引','統一 Embedding 模型及版本'],
 ['資料檢索','關鍵字與向量搜尋、合併排序'],
 ['存取控制','後端授權過濾、撤權及版本篩選'],
 ['檢索輸出','去重、Top-K 與可追溯來源']
],'管理文字與向量索引　　驗證：Recall@K、零越權');

module('D','問答介面與品質評估',72,670,C.violet,[
 ['使用者入口','選專案、上傳文件與提出問題'],
 ['回答呈現','處理狀態、回答、引用與原文'],
 ['互動處理','取消、錯誤、切案與登出隔離'],
 ['品質評測','固定題組、回饋、版本比較']
],'彙整評測報告　　各模組主責提供測試證據與修正');

module('C','回答生成與引用',1198,670,C.gold,[
 ['問答協調','接收問題、呼叫檢索、整理證據'],
 ['上下文組合','去重、Token 預算與 Prompt'],
 ['模型生成','LLM 呼叫、逾時、取消與錯誤'],
 ['引用與不足','引用 ID 檢查、無答案與矛盾處理']
],'驗證：答案正確、引用支持　　引用合法仍需核對內容');

// A -> B data contracts.
text('① DocumentChunk',960,245,26,C.teal,700,'middle');
text('片段／版本／來源／公司與專案',960,280,22,C.muted,400,'middle');
arrow(722,309,1198,309,'teal');
text('IndexStatus　索引完成／失敗',960,340,21,C.gold,400,'middle');
arrow(1198,353,722,353,'gold');
text('IndexChange',960,380,25,C.teal,700,'middle');
text('新增／更新／刪除　含文件版本',960,414,22,C.muted,400,'middle');
arrow(722,438,1198,438,'teal',true);

// D -> A uploads and A -> D status. Separate lanes prevent label collisions.
arrow(120,670,120,470,'teal');
text('UploadDocument',155,526,25,C.teal,700);
text('檔案／專案範圍',155,559,23,C.muted);
arrow(674,470,674,670,'gold');
text('DocumentStatus',640,606,25,C.gold,700,'end');
text('處理階段／可用狀態／錯誤',640,638,22,C.muted,400,'end');

// C -> B query and B -> C evidence.
arrow(1246,670,1246,470,'blue');
text('③ SearchRequest',1281,526,25,C.blue,700);
text('問題／後端授權範圍／Top-K',1281,559,22,C.muted);
arrow(1800,470,1800,670,'gold');
text('④ SearchResult',1766,606,25,C.gold,700,'end');
text('授權片段／排名／來源／索引版本',1766,638,22,C.muted,400,'end');

// D -> C question and C -> D answer.
text('② AskRequest',960,727,26,C.blue,700,'middle');
text('問題／對話／範圍／登入身分',960,761,22,C.muted,400,'middle');
arrow(722,788,1198,788,'blue');
text('⑤ AnswerResponse',960,859,26,C.gold,700,'middle');
text('回答／引用清單／狀態／追蹤 ID',960,894,22,C.muted,400,'middle');
arrow(1198,926,722,926,'gold');

// Keep cross-cutting constraints visible without adding a fifth module.
line(72,997,1848,997,C.border,1.5);
text('共同約定',72,1031,22,C.teal,700);
text('權限由後端依登入身分確認；開啟原文仍須授權。介面名稱為建議契約，不代表現有 API 路徑。',195,1031,22,C.muted);
text('規劃範圍：向量與正式附件索引待建置；第一版不含 OCR。圖示為邏輯模組，可共用同一後端部署。',195,1063,21,C.muted);

const defs=['teal','blue','gold'].map(k=>`<marker id="${k}" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 Z" fill="${C[k]}"/></marker>`).join('');
const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="title desc"><title id="title">RAG 四模組責任與資料流架構</title><desc id="desc">A 資料整理交付 B 索引。D 使用者介面將問題交付 C 生成，C 向 B 檢索，取得證據後回覆 D。A 至 D 姓名待認領，每包二十點。連線標示建議資料契約。</desc><defs>${defs}</defs><g font-family="Microsoft JhengHei, Noto Sans CJK TC, sans-serif">${elements.join('\n')}</g></svg>`;
await fs.writeFile(path.join(root,'RAG四模組詳細架構圖.svg'),svg);
await sharp(Buffer.from(svg),{density:144}).png().toFile(path.join(root,'RAG四模組詳細架構圖.png'));
await sharp(Buffer.from(svg),{density:72}).png().toFile(path.join(qa,'preview.png'));
await fs.writeFile(path.join(qa,'architecture-labels.json'),JSON.stringify(labels,null,2));
const meta=await sharp(path.join(root,'RAG四模組詳細架構圖.png')).metadata();
if(meta.width!==3840||meta.height!==2160)throw Error('Unexpected image dimensions');
for(const s of ['DocumentChunk','IndexChange','IndexStatus','UploadDocument','DocumentStatus','SearchRequest','SearchResult','AskRequest','AnswerResponse'])if(!svg.includes(s))throw Error(`Missing ${s}`);
if((svg.match(/姓名：____________/g)||[]).length!==4)throw Error('Expected four blank owner names');
console.log(JSON.stringify({size:[meta.width,meta.height],modules:4,interfaces:9,blankNames:4,output:root}));
