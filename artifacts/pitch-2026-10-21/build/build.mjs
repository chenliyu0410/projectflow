import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const ROOT = 'C:/Users/User/Desktop/專流/artifacts/pitch-2026-10-21';
const SKILL = 'C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.22136/skills/presentations';
const PY = 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const FONT = 'Microsoft JhengHei';
process.env.RUNTIME_NODE_MODULES='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const C={bg:'#071B2B',ink:'#112D3D',muted:'#A5BBC8',white:'#F5F8FA',teal:'#51D8C6',red:'#FF806B',gold:'#F4C16D',paper:'#F4F6F4',gray:'#526975'};
const p=Presentation.create({slideSize:{width:1280,height:720}});
const narrative=[];
function text(s,str,x,y,w,h,size=28,color=C.white,bold=false){
 const z=s.shapes.add({geometry:'textbox',name:str.slice(0,28),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 z.text=str; z.text.style={typeface:FONT,fontSize:size,color,bold,autoFit:'none',wrap:'square',insets:0,verticalAlignment:'top'};return z;
}
function slide(title,{light=false,tag='',note='',source='README.md §2 正式版功能總覽；§8 後續路線圖'}={}){
 const s=p.slides.add(); s.background.fill=light?C.paper:C.bg;
 const n=p.slides.items.length;
 if(tag)text(s,tag,64,34,1120,30,18,light?C.gray:C.muted);
 text(s,title,64,86,1152,112,44,light?C.ink:C.white,true);
 text(s,String(n).padStart(2,'0'),1155,672,60,25,16,light?C.gray:C.muted);
 s.speakerNotes.text=`${note}\n\n依據：${source.startsWith('README')?'C:/Users/User/Desktop/專流/':''}${source}\n內容基準：2026-10-21，本地 feature/review-fixes（c9ad212）；功能現況以 README §2 與 §8 為準，規格願景不當作已完成能力。`;
 narrative.push({slide:n,title,note,source});return s;
}
function table(s,rows,{top=218,widths=[260,440,452],height=330,size=25,light=false}={}){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:64,top,width:1152,height,columnWidths:widths,values:rows});
 t.borders.assign({fill:light?'#D3DEDF':'#355064',width:1,style:'solid'});
 for(let r=0;r<rows.length;r++){
  t.rows[r].height=r===0?58:(height-58)/(rows.length-1);
  for(let c=0;c<rows[0].length;c++){
   let cell=t.getCell(r,c);cell.fill=r===0?(light?'#123D48':'#123747'):(light?'#F4F6F4':'#0A2232');
   cell.text.style={typeface:FONT,fontSize:r===0?22:size,color:r===0?C.teal:(light?C.ink:C.white),bold:r===0,verticalAlignment:'middle',insets:16,autoFit:'none'};
  }
 }
 return t;
}
function row(s,k,head,body,y,{light=false,accent=C.teal}={}){
 text(s,k,64,y,k.startsWith('第')?104:80,58,k.startsWith('第')?28:34,accent,true);text(s,head,176,y,390,55,30,light?C.ink:C.white,true);text(s,body,592,y,624,82,25,light?C.gray:C.muted);
}

// 01: cover; the generated photo is an illustrative background, never product evidence.
{
 const s=p.slides.add();s.background.fill=C.bg;
 const b=await fs.readFile(path.join(ROOT,'build/cover.png'));
 s.images.add({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/png',position:{left:0,top:0,width:1280,height:720},fit:'cover',alt:'製造業管理情境意象，AI生成背景'});
 text(s,'專流 ProjectFlow',64,72,700,50,30,C.teal,true);
 text(s,'讓延誤更早被看見\n讓交付有據可查',64,222,780,180,60,C.white,true);
 text(s,'企業專案協作與管理效益提案',64,490,740,55,30,C.white);
 text(s,'企業老闆／主管簡報  ·  2026.10',64,626,760,32,20,C.muted);
 const note='開場：今天談的是管理成本。當任務、文件與跨部門交接分散在不同地方，主管常在交期受到影響後才知道。專流要把專案進度、前置條件與交付證據放回同一個工作脈絡。這次提案先看風險，再看目前能力，最後提出可衡量的試用。';
 s.speakerNotes.text=note+'\n\n依據：README.md §2、§8。封面為內建圖像生成工具製作的製造業情境意象，非客戶現場、非產品截圖。';narrative.push({slide:1,title:'專流 ProjectFlow：讓延誤更早被看見，讓交付有據可查',note,source:'README.md §2、§8'});
}
{
 const s=slide('四個管理盲點，讓交付風險累積',{tag:'企業痛點',note:'請主管對照自己的公司：進度是不是要逐一追問？跨部門交接是否只剩訊息？同一份文件是否有多個版本？關鍵人休假時，是否有人能完整接手？這是常見風險情境，不是對貴公司的現況斷言，也沒有引用未驗證的產業比例。'});
 row(s,'01','進度靠人追','週報更新後又落後，主管仍要重新確認',222,{accent:C.red});
 row(s,'02','交接靠訊息','誰接手、何時完成、缺哪項條件說不清',324,{accent:C.red});
 row(s,'03','版本靠記憶','錯版文件進入試作，重工才發現差異',426,{accent:C.red});
 row(s,'04','知識靠個人','人員請假或離職，專案脈絡跟著斷線',528,{accent:C.red});
}
{
 const s=slide('等到交期變紅，補救成本已經發生',{tag:'風險情境｜示意，非實際客戶事件',note:'用一個假設的新產品試作專案說明風險傳遞：材料延遲但沒有及時同步，試作仍照原計畫排程，品保與後續驗收再被壓縮，最後需要加班、加急或對客戶重新承諾。這些不是每次都必然發生，但如果沒有前置關係與明確的關卡，管理者很難提早定位問題。'});
 text(s,'原料延遲',64,242,350,65,40,C.red,true);
 text(s,'試作排程受影響',460,242,480,65,40,C.white,true);
 text(s,'品保驗證被壓縮',64,359,560,65,40,C.white,true);
 text(s,'交期承諾承壓',660,359,520,65,40,C.red,true);
 text(s,'可能的代價：加急採購、重排工時、重工與客戶信任流失',64,526,1152,78,31,C.gold,true);
}
{
 const s=slide('24 人每天追查 15 分鐘，全年 1,320 人時',{tag:'管理成本｜可替換的情境試算',light:true,note:'假設24位成員，每人每天花15分鐘追進度、找檔案或確認版本，每年220個工作天。24乘0.25乘220等於1320人時。再假設每人時完整成本為新台幣500元，機會成本就是66萬元。這是容量與機會成本試算，不代表能直接減少薪資或保證節省。也不包含延誤、加急與重工，以免重複計算。',source:'情境假設與算式：24 × 15/60 × 220 = 1,320人時；1,320 × NT$500 = NT$660,000；無外部統計'});
 text(s,'1,320',64,227,690,150,116,C.ink,true);
 text(s,'人時／年',72,396,600,50,35,C.gray);
 text(s,'NT$ 66 萬',750,267,470,80,54,'#177F78',true);
 text(s,'年機會成本',750,364,450,50,30,C.gray);
 text(s,'24 人 × 每天 15 分鐘 × 220 個工作天',64,522,1152,50,30,C.ink,true);
 text(s,'假設人時成本 NT$500；非實測效益，亦非可直接減少的現金支出',64,602,1152,45,22,C.gray);
}
{
 const s=slide('專流，把專案脈絡放回同一處',{tag:'核心價值',note:'產品的主體是專案。專案、階段、任務、子任務可以向下展開，每一層都有負責人、時程與相關紀錄。讓主管往下看得到阻塞點，讓執行者知道下一步，讓文件和營運資料能連回任務。這是目前產品的整合價值；跨部門實際效益仍須試用量測。',source:'README.md §2、§3 核心概念'});
 text(s,'專案 → 階段 → 任務 → 子任務',64,220,1152,90,52,C.teal,true);
 row(s,'看見','進度與阻塞','任務樹、時程、前置條件與負載',366);
 row(s,'落實','責任與審核','負責人、回報確認、閘門與覆寫紀錄',462);
 row(s,'留下','文件與證據','文件版本、附件、營運關聯與稽核',558);
}
{
 const s=slide('主管少一輪追問，團隊多一份共同事實',{tag:'價值一｜降低追蹤與彙整負擔',light:true,note:'任務樹可以展開到子任務，看板和時程提供不同檢視，進度由子節點加權彙總。時程已有前置關係與可見範圍的關鍵路徑估算，負載頁可看人員與部門分配。展示時從專案總覽點入一個延誤任務，指出負責人與相依關係即可。不要把關鍵路徑估算說成完整CPM或AI預測。'});
 table(s,[['主管要知道','目前可用能力','期待改善'],['卡在哪裡？','任務樹、看板、時程','減少逐一詢問與彙整'],['誰需要支援？','負責人、部門與人員負載','把協調聚焦在阻塞處'],['改期影響誰？','前置關係、順延、路徑估算','提早討論後續排程']],{height:330,light:true});
 text(s,'關鍵路徑目前為可見範圍估算；管理效益需由試用驗證',64,596,1152,44,23,C.gray);
}
{
 const s=slide('把「完成了」變成可確認的交付',{tag:'價值二｜減少漏接與過早放行',note:'一項任務的完成不只是一個狀態。執行者送出回報與附件，審核者可以確認或退回；前置條件與階段閘門表達進入下一步所需的條件。必要的跳過或覆寫需核准並留紀錄。這並不等同完整電子簽章或品質合規認證。條件型前置目前由管理者人工確認。'});
 row(s,'01','回報有內容','回報欄位、筆記與附件一起保存',230);
 row(s,'02','交付有人確認','確認、退回與重新回報有跡可循',340);
 row(s,'03','例外有理由','前置／閘門與跳過、覆寫申請留紀錄',450);
 text(s,'管理者能追問：誰確認、依據是什麼、為何例外放行？',64,590,1152,55,28,C.gold,true);
}
{
 const s=slide('把現場紀錄接回專案，縮短追查路徑',{tag:'價值三｜文件與營運資料留在工作脈絡',light:true,note:'目前正式版已有文件上傳、版本保存與歷史下載；營運紀錄可關聯任務，支援採購明細與收貨、庫存流水、工單領料與完工，以及退貨、退料與沖銷。價值是查任務時能找到相關資料。ERP同步、批號追溯、BOM自動扣料及成本核算都未完成，不能把這一頁講成ERP替代方案。'});
 row(s,'文件','找到當時使用的版本','上傳、版本保存、歷史下載',230,{light:true,accent:'#177F78'});
 row(s,'營運','看到相關執行紀錄','採購／收貨、庫存、工單與退貨',350,{light:true,accent:'#177F78'});
 row(s,'任務','保留交付與查核脈絡','文件與營運紀錄關聯到任務',470,{light:true,accent:'#177F78'});
 text(s,'ERP 串接、批號追溯、BOM 自動扣料與成本核算仍在路線圖',64,610,1152,40,22,C.gray);
}
{
 const s=slide('AI 的管理價值，從可查證的答案開始',{tag:'AI 副手｜目前為展示能力',note:'AI展示區能做帶引用的文件問答與16種受控Text-to-SQL，可接內網Ollama。未接模型時回傳檢索原文。這些能力目前查詢的是獨立展示資料，不是正式專案資料；正式文件權限檢索、資料分級、遮罩、AI路由和向量檢索仍待建置。今天可以展示互動與引用方式，但不宣稱已能安全查詢全公司資料或自動完成專案決策。',source:'README.md §2、§6 系統架構、§8.5、§8.6'});
 text(s,'問文件，有引用\n查數據，有受控範圍',64,235,710,175,50,C.teal,true);
 text(s,'16 種',870,240,340,90,68,C.white,true);
 text(s,'受控資料查詢',870,350,340,60,27,C.muted);
 text(s,'現在：獨立展示資料區，可接內網 Ollama',64,486,1152,50,30,C.white,true);
 text(s,'下一階段：正式資料、權限檢索、分級與遮罩',64,568,1152,50,28,C.gold);
}
{
 const s=slide('價值要落在指標上，才值得擴大導入',{tag:'價值貢獻｜試用前後用同一方法量測',light:true,note:'不要只看登入次數。管理層需要看到追蹤與彙整時間是否下降、阻塞能否提早被發現、交付是否有證據、跨人接手是否更快。這裡列的是待驗證指標，不是已達成的改善幅度。先量基準，再用同樣的方法量試用期間，並記錄專案規模差異。'});
 table(s,[['價值面向','試用時量什麼','管理意義'],['效率','每週追進度／找資料工時','工作時間回到交付'],['交期','阻塞發現至交期的提前天數','保留協調與補救空間'],['品質','交付資料完整率、退回原因','減少漏件與重複確認'],['延續性','他人接手所需時間','降低關鍵人依賴']],{height:385,light:true,size:24});
}
{
 const s=slide('少追查一小時，就多一小時可投入交付',{tag:'效益敏感度｜沿用第 4 頁情境，非產品實績',note:'以每年1320人時為基準，假設減少20%、30%、40%的追查時間，分別釋放264、396、528人時；以每人時500元計，對應13.2、19.8、26.4萬元的容量價值。這不是營收，也不是可直接減員的現金節省。導入成本尚未報價，因此不計算ROI或回本期；試用後把實測比例、授權與部署、培訓和維運成本一起帶入。',source:'本簡報第4頁情境；1,320 × 20/30/40%；人時 × NT$500'});
 table(s,[['追查時間減少（假設）','釋放人時／年','容量價值／年'],['20%','264 人時','NT$ 13.2 萬'],['30%','396 人時','NT$ 19.8 萬'],['40%','528 人時','NT$ 26.4 萬']],{widths:[420,350,382],height:328,size:29});
 text(s,'採購決策前，需納入授權、部署、培訓與維運成本',64,595,1152,50,26,C.gold);
}
{
 const s=slide('目前可試用的範圍，與正式導入的下一步',{tag:'產品成熟度｜2026.10 現況',light:true,note:'這一頁主動說清楚現況，以免展示能力被當成商用就緒。可用核心包含任務、時程相依、審核回報、文件版本、營運紀錄及15套產業工作流模板。AI與部署目前為試用等級。正式導入前仍需帳號管理、改密碼、登入限流、內網HTTPS、自動備份與還原演練，以及效能和資安檢查。ERP、AD/LDAP與正式AI資料串接需另定範圍。'});
 table(s,[['可用核心','試用能力','待建置／驗證'],['任務、時程、相依、回報審核\n文件版本、營運紀錄\n15 套產業工作流模板','AI 展示資料問答／查詢\n本機、區網與公開試用','正式帳號與內網 HTTPS\n自動備份及還原演練\n正式資料 AI、ERP／AD 整合']],{widths:[415,330,407],height:296,size:25,light:true});
 text(s,'先以核准範圍試用，通過資料保護與部署檢查後，再擴大使用',64,568,1152,75,27,C.ink,true);
}
{
 const s=slide('用一個專案、四週，驗證管理效益',{tag:'建議試用方案｜時程與門檻待雙方確認',note:'README建議1到2個研發團隊試用2到4週。這裡提出四週版本：第一週選一個跨部門專案、明確流程與基準；第二週將任務、責任、前置條件與文件放入核准環境；第三週完成一輪回報審核和例外交接；第四週檢視指標和是否願意持續使用。正式帳號、存取權與資料保護未就緒時，用去敏資料做流程演練，不導入敏感營運資料。試用通過門檻需事先協商，非產品保證。',source:'README.md §8.1 試用與上線；本頁為提案時程'});
 row(s,'第1週','選案與量基準','一個跨部門專案；記錄追查工時與交接問題',220);
 row(s,'第2週','整理流程與責任','任務、負責人、前置條件與文件到位',320);
 row(s,'第3週','跑完一輪交付','實際完成回報、審核與例外處理',420);
 row(s,'第4週','用數據決定去留','比較工時與完整率；確認團隊是否願意續用',520);
 text(s,'真實資料使用前，先確認帳號、權限、部署與備份條件',64,629,1152,30,21,C.gold);
}
{
 const s=slide('下一次交期承壓前，先看清專案全貌',{tag:'建議決策',note:'結尾請主管批准的是一個範圍清楚的試用：指定一位主管支持、一位專案窗口、一個跨部門專案。先確認部署與資料使用條件，再以四週量測管理效益。決策重點是能否更早看見阻塞、減少追查、留下交付證據；不是要求現在就全面替換現有系統。收尾後可用產品展示任務、回報審核、文件、營運關聯與AI展示區。'});
 text(s,'批准一個範圍清楚的試用',64,226,1152,85,54,C.teal,true);
 text(s,'1 位主管支持  ·  1 位專案窗口  ·  1 個跨部門專案',64,354,1152,74,32,C.white);
 text(s,'把追進度的時間，還給真正的交付',64,506,1152,100,44,C.white,true);
}

await fs.mkdir(path.join(ROOT,'build/rendered'),{recursive:true});
await fs.writeFile(path.join(ROOT,'build/narrative.json'),JSON.stringify(narrative,null,2));
await fs.writeFile(path.join(ROOT,'build/presentation.json'),JSON.stringify(p.toProto()));
const candidate=path.join(ROOT,'build/candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log('EXPORTED',candidate,p.slides.items.length);
for(const [i,s] of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(ROOT,`build/rendered/slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 console.log('RENDERED',i+1);
}
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:path.join(ROOT,'output/專流_ProjectFlow_企業主管提案.pptx'),pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...[6,10,11,12].flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:14,requiredNativeTableOwnerSlides:[6,10,11,12],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath:path.join(ROOT,'build/validation.json')});
console.log(JSON.stringify(result));
