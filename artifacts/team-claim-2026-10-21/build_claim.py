from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

ROOT = Path(__file__).resolve().parent
OUT = ROOT / '專流_四包分工認領表.docx'
packages = [
 dict(n='第一包', title='使用者工作區與文件檢索', total=19, goal='讓使用者完成任務操作，並找到相關文件與依據。',
 rows=[('AI 應用 A1','副手介面與互動','提問、查詢模式、專案選擇、回答與引用、等待及錯誤提示',2),('AI 應用 A3','文件搜尋與排序','關鍵詞處理、FTS5、BM25、現行文件與範圍篩選',4),('非 AI B1','工作區與導覽','專案總覽、側欄、任務定位、桌機與手機操作',2),('非 AI B2','任務樹與進度','多層任務、移動、複製、升降級、刪除與復原、加權進度',4),('非 AI B8','完成回報與審核','自訂欄位、草稿、送審、核准、退回、筆記及例外申請',4),('非 AI B9','附件與文件版本','上傳下載、TXT／CSV 編輯、版本保存、歷史下載',3)],
 slides=[('第 1 頁 45 秒','工作區架構','放工作區截圖與元件／API 關係圖，說明任務、回報與文件入口。'),('第 2 頁 75 秒','AI 文件檢索','畫出提問、關鍵詞處理、FTS5／BM25、結果與引用的流程；說明與模型生成的分界。'),('第 3 頁 60 秒','問題與驗證','選一個實際處理的互動或搜尋問題，展示原因、修改與測試；說明方案取捨。')],
 demo='00:00–00:40 開啟食品研發專案與任務樹；01:30–02:10 以成員身分提交預備好的完成回報；02:50–03:15 展示相關文件版本。AI 引用介面另交第三包在 03:40 後操作，避免重複。',
 prep='準備專案與任務定位、回報文字、附件、兩個文件版本；交付第三包可用的 AI 提問入口與引用開啟方式。', interface='第二包提供權限與審核設定；第四包提供模型回答及回退狀態。'),
 dict(n='第二包', title='工作流 權限與 AI 資料管理', total=19, goal='讓正確的人，在允許的範圍內執行工作與查詢資料。',
 rows=[('AI 應用 A2','展示資料與匯入','文件與結構化資料、公司／專案識別、版本、角色欄位、匯入驗證',3),('AI 應用 A6','資料權限與限制','公司隔離、文件角色、SQL 使用權限、唯讀及允許操作限制',3),('非 AI B4','前置條件與閘門','FS／SS／FF、延遲天數、硬性／軟性、相依圖與階段閘門',4),('非 AI B5','工作流與模板','產業模板、另存與套用、模板版本、變數替換、建立專案',3),('非 AI B6','登入與角色權限','Session、登入登出、公司範圍、角色及節點操作權限',3),('非 AI B7','部門與協作','主管、負責人、協作者、協作請求、負載與站內通知',3)],
 slides=[('第 1 頁 45 秒','身分與工作流','畫公司、角色、節點與操作的關係，說明登入與授權如何連到工作流。'),('第 2 頁 75 秒','AI 資料範圍','展示匯入資料欄位與查詢範圍，說明哪些文件可見、誰能執行分析。'),('第 3 頁 60 秒','規則與權限驗證','比較合法、越權、前置未滿足三個案例，附預期與實際結果。')],
 demo='01:05–01:30 說明硬性前置的阻擋原因；02:10–02:50 使用審核者身分核准回報，查看任務狀態與預設下游條件。角色切換用不同瀏覽器設定檔。',
 prep='設定成員／審核者、硬性前置與可重複操作的任務；確認 AI 展示資料已匯入、角色可見性正確。', interface='與第一包對齊錯誤提示；與第三包對齊 AI 資料格式、查詢權限及範圍。'),
 dict(n='第三包', title='營運管理與 AI 資料分析', total=18, goal='理解營運資料如何產生，讓查詢結果可以計算與核對。',
 rows=[('AI 應用 A5','受控 Text-to-SQL','16 種模板、問題對應、模型建議確認、參數化查詢、結果及 SQL',4),('AI 應用 A8','品質評估與測試','問題集、答案與引用核對、SQL 比對、無來源及失敗案例',2),('非 AI B10','營運資料與任務關聯','供應商、原料、配方等紀錄，以及與任務的關聯',2),('非 AI B11','採購與收貨','採購單、明細、收貨、退貨與庫存連動',3),('非 AI B12','庫存 盤點與沖銷','餘額、異動流水、盤點、反向沖銷與原始紀錄保存',4),('非 AI B13','工單與生產','工單計畫、領料、退料、完工及庫存連動',3)],
 slides=[('第 1 頁 45 秒','營運資料流程','畫採購、收貨、庫存與工單關係；另外標示獨立的 AI 展示資料區。'),('第 2 頁 75 秒','AI 受控分析','畫自然語言、查詢模板、參數、唯讀執行與結果流程，說明與自由生成 SQL 的取捨。'),('第 3 頁 60 秒','分析結果驗證','選一題比對標準答案與系統結果，補不支援問題或錯誤引用案例；只列實測數據。')],
 demo='03:15–03:40 開啟任務關聯的採購／收貨紀錄；03:40–04:20 切入 AI 展示區，問「現行交付需要幾張截圖？」並展開原文；04:40–05:20 查「各部門逾期未完成數」，展示 SQL 與範圍。',
 prep='準備關聯單據、已匯入的 AI 專案、兩個預演題目與標準答案。分析基準日為 2026-10-11，與前段正式任務操作不會即時同步。', interface='第二包提供資料與權限；第一包提供查詢介面；第四包協助模型及測試環境。'),
 dict(n='第四包', title='排程 模型串接與系統整合', total=19, goal='處理排程與系統底層，讓模型服務與整套系統可執行及驗證。',
 rows=[('AI 應用 A4','模型問答與引用驗證','檢索來源、提示詞、結構化回答、引用 ID 檢查與失敗回退',4),('AI 應用 A7','Ollama 連線與設定','內網位址、模型選擇、設定權限、連線及逾時處理',2),('非 AI B3','時程與排程','日週月、拖曳改期、里程碑、鎖定、順延與關鍵路徑',4),('非 AI B14','資料庫與稽核','資料關聯與約束、Migration、舊資料保存、交易與稽核',3),('非 AI B15','部署環境','Docker Compose、nginx、資料 volume、健康檢查、試用入口',3),('非 AI B16','測試整合與 CI','pytest、Vitest、Playwright、隔離資料、CI 與整合回歸',3)],
 slides=[('第 1 頁 45 秒','系統整合架構','畫 web／api／db、資料 volume 與 Ollama，指出排程服務的位置。'),('第 2 頁 75 秒','AI 模型回答','說明來源、提示詞、格式與引用 ID 驗證、模型失敗回退；合法引用不等於內容一定正確。'),('第 3 頁 60 秒','失敗處理與驗證','選模型逾時或引用驗證失敗案例，附回退畫面與測試。排程細節放備用頁。')],
 demo='00:40–01:05 展示時程與相依；04:20–04:40 接續 AI 問答畫面，說明本次是模型整理或純檢索，指出失敗時的回退方式。模型異常備用截圖只在需要時替換此段。',
 prep='檢查容器、健康狀態、資料持久化與 Ollama；統整同版本測試紀錄，準備本機展示與短錄影備援，避免現場等待模型逾時。', interface='與第一包對齊回答格式；第三包提供 AI 評估案例，各包仍須負責自己的功能測試。')
]

doc=Document(); sec=doc.sections[0]
for grid in list(sec._sectPr.findall(qn('w:docGrid'))): sec._sectPr.remove(grid)
for style in doc.styles:
 pr=style.element.get_or_add_pPr()
 for border in list(pr.findall(qn('w:pBdr'))): pr.remove(border)
 snap=OxmlElement('w:snapToGrid'); snap.set(qn('w:val'),'0');pr.append(snap)
sec.page_width=Inches(8.5); sec.page_height=Inches(11)
sec.top_margin=Inches(.65); sec.bottom_margin=Inches(.65)
sec.left_margin=Inches(.7); sec.right_margin=Inches(.7)
sec.header_distance=Inches(.25); sec.footer_distance=Inches(.25)
for name in ['Normal','Title','Heading 1','Heading 2','Heading 3']:
 s=doc.styles[name]; s.font.name='Microsoft JhengHei'; s.font.color.rgb=RGBColor(0,0,0)
 s.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Microsoft JhengHei')
 s.font.size=Pt({'Title':23,'Heading 1':17,'Heading 2':12,'Heading 3':11}.get(name,11))
 s.paragraph_format.space_after=Pt(5); s.paragraph_format.line_spacing=1.12
doc.styles['Normal'].paragraph_format.widow_control=True
for n in ['Heading 1','Heading 2','Heading 3']:
 doc.styles[n].paragraph_format.space_before=Pt(10)
header=sec.header.paragraphs[0]; header.text='ProjectFlow 專流　團隊報告認領表'; header.runs[0].font.size=Pt(9)
footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('2026 年 10 月 21 日　｜　')
f=OxmlElement('w:fldSimple'); f.set(qn('w:instr'),'PAGE'); footer._p.append(f)
for r in footer.runs:r.font.size=Pt(9)

def p(text='',bold=False,style=None):
 x=doc.add_paragraph(style=style); r=x.add_run(text); r.bold=bold; return x
def heading(text): return doc.add_heading(text,level=2)
def table(headers,rows,widths,ai=False):
 t=doc.add_table(rows=1,cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
 for c,w in zip(t.columns,widths): c.width=Inches(w)
 borders=OxmlElement('w:tblBorders')
 for edge in ['top','left','bottom','right','insideH','insideV']:
  el=OxmlElement('w:'+edge); el.set(qn('w:val'),'single'); el.set(qn('w:sz'),'4'); el.set(qn('w:color'),'D9D9D9'); borders.append(el)
 t._tbl.tblPr.append(borders)
 for i,vals in enumerate([headers]+rows):
  cells=t.rows[0].cells if i==0 else t.add_row().cells
  is_ai=i>0 and ai and str(vals[0]).startswith('AI')
  trPr=cells[0]._tc.getparent().get_or_add_trPr(); ns=OxmlElement('w:cantSplit');trPr.append(ns)
  if i==0: trPr.append(OxmlElement('w:tblHeader'))
  for j,(cell,value) in enumerate(zip(cells,vals)):
   cell.width=Inches(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   pr=cell._tc.get_or_add_tcPr(); sh=OxmlElement('w:shd'); sh.set(qn('w:fill'),'DCE6F1' if i==0 else ('EAF4FF' if is_ai else 'FFFFFF')); pr.append(sh)
   mar=OxmlElement('w:tcMar')
   for side in ['top','left','bottom','right']:
    e=OxmlElement('w:'+side);e.set(qn('w:w'),'55');e.set(qn('w:type'),'dxa');mar.append(e)
   pr.append(mar); x=cell.paragraphs[0];x.paragraph_format.space_after=Pt(1);x.paragraph_format.space_before=Pt(1);x.paragraph_format.line_spacing=Pt(14)
   r=x.add_run(str(value));r.font.size=Pt(10.5);r.bold=i==0 or (is_ai and j<2)
   if j==len(vals)-1 and len(vals)>3:x.alignment=WD_ALIGN_PARAGRAPH.CENTER
 spacer=p();spacer.paragraph_format.space_after=Pt(0);spacer.paragraph_format.line_spacing=Pt(3);spacer.runs[0].font.size=Pt(3)
 return t

doc.add_paragraph('專流四包分工認領表',style='Title')
p('請每位組員認領一包，填入姓名後，依本表準備個人簡報與 DEMO。四包涵蓋全部 24 項工作，每包都有 2 項 AI 相關工作及 4 項非 AI 工作。')
p('認領截止日　____________　　簡報初稿日　____________')
p('共同彩排日　____________　　正式報告日　____________')
heading('姓名認領總表')
table(['工作包','主題','AI／非 AI 點數','姓名'],[(g['n'],g['title'],f"6／{g['total']-6}　共 {g['total']} 點",'____________') for g in packages],[.7,3.0,1.8,1.6])
p('AI 標示：工作明細中的「AI 應用」以粗體及淡藍底標記。AI 相關包含資料、檢索與權限等支援工程，並非每項都直接呼叫模型。')
p('點數是接手理解、驗證、維護及報告準備的相對估算。四包為 19／19／18／19 點，每包 AI 均為 6 點；實際貢獻依本人參與內容描述。')
heading('報告時間')
p('團體介紹 5 分鐘（6 頁）＋個人報告 12 分鐘（每人 3 分鐘、3 頁）＋系統 DEMO 6 分鐘＋成果與後續 1 分鐘＋換場緩衝 1 分鐘。')
p('合計 25 分鐘，不包含老師問答。DEMO 建議固定一人操作，各包主責接續講解。',bold=True)
heading('每位組員共同交付')
p('□ 三頁個人簡報與三分鐘講稿　□ 一張子系統架構圖\n□ 一個實際問題與解法　□ 一份測試或比較證據\n□ 自己的 DEMO 資料與講解稿　□ 備用截圖或短錄影')
p('請保留目前功能的界線：AI 使用獨立展示資料；向量檢索、正式業務資料接入與 ERP 串接不列為已完成功能。')

for g in packages:
 h=doc.add_heading(g['n']+' '+g['title'],level=1);h.paragraph_format.page_break_before=True
 p(f"主責姓名　________________　　協作姓名　________________\n工作量 {g['total']} 點，其中 AI 6 點　｜　個人報告 3 分鐘",bold=True)
 p(g['goal'])
 table(['類別與編號','工作項目','負責範圍','點數'],g['rows'],[1.05,1.55,4.0,.5],ai=True)
 heading('個人簡報準備')
 for timing,title,body in g['slides']:
  x=p();x.add_run(timing+'　'+title+'：').bold=True;x.add_run(body)
 heading('DEMO 分工')
 p(g['demo']);p('事前準備：'+g['prep']);p('跨包接口：'+g['interface'])
 p('準備狀態　□ 範圍確認　□ 三頁簡報　□ 驗證證據　□ DEMO 彩排')
 p('需要協助或調整　________________________________________________')

h=doc.add_heading('六分鐘 DEMO 與共同準備',level=1);h.paragraph_format.page_break_before=True
p('情境：食品研發專案從送驗、交付審核，追查到文件與營運紀錄；最後明確切換到獨立 AI 展示資料區。以下時間以 DEMO 開始為 00:00。')
table(['時間','講解主責','操作與觀眾要看到的結果'],[
('00:00–00:40','第一包','開啟專案、任務樹與負責人，指出本次送驗任務。'),
('00:40–01:05','第四包','顯示時程與相依，說明上下游工作的關係。'),
('01:05–01:30','第二包','展示硬性前置與阻擋原因。'),
('01:30–02:10','第一包','填入預備內容，以成員身分送出完成回報。'),
('02:10–02:50','第二包','以審核者核准，檢查狀態及預設下游條件。'),
('02:50–03:15','第一包','開啟相關文件，展示版本與原文。'),
('03:15–03:40','第三包','開啟任務關聯的採購／收貨紀錄。'),
('03:40–04:20','第三包','切 AI 展示區，問截圖張數，展開引用與原文。'),
('04:20–04:40','第四包','說明本次模型／檢索模式，以及失敗回退方式。'),
('04:40–05:20','第三包','查各部門逾期未完成數，展示 SQL、結果與範圍。'),
('05:20–06:00','總結講者','返回專案，回扣進度、前置與交付依據三個痛點。')],[1.2,.9,5.0])
heading('共同工作認領')
table(['工作','主責姓名','工作','主責姓名'],[('團體五分鐘開場','____________','簡報整併與版型','____________'),('DEMO 電腦操作','____________','彩排與計時','____________'),('DEMO 總結及最後結尾','____________','截圖與錄影備援','____________')],[2.05,1.5,2.05,1.5])
heading('彩排前確認')
p('□ 使用可重複操作的隔離資料，預設前置、審核人、文件與單據關聯。\n□ 成員與審核者使用不同瀏覽器設定檔，避免登入狀態互相覆蓋。\n□ AI 資料已匯入；要展示模型生成時，先確認 Ollama 可用。\n□ 所有展示問題與預期結果已預演；卡住約 10 秒就改用備援。')
p('AI 查詢不會同步反映剛才的正式任務操作；分析基準日固定為 2026-10-11。未啟用模型時，文件查詢顯示檢索原文。DEMO 路徑須完成彩排後再確認可用。')

ids=[row[0].split()[-1] for g in packages for row in g['rows']]
assert len(ids)==24 and len(set(ids))==24
assert set(ids)=={f'A{i}' for i in range(1,9)}|{f'B{i}' for i in range(1,17)}
assert [sum(row[3] for row in g['rows']) for g in packages]==[19,19,18,19]
assert all(sum(row[3] for row in g['rows'] if row[0].startswith('AI'))==6 for g in packages)
doc.core_properties.title='專流四包分工認領表';doc.core_properties.subject='四人分工認領與簡報及DEMO準備'
doc.save(OUT)
print(OUT)
print('Validated: 24 unique work items; package points 19/19/18/19; AI 6 each; all names blank.')
