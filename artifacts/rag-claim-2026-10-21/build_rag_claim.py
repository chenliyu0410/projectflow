from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'RAG四模組分工認領表.docx'
groups = [
 dict(code='A', title='資料接入與知識整理', goal='把原始文件轉成可追溯、可更新的標準化片段，供檢索模組使用。',
 flow='接收檔案 → 格式檢查 → 解析清理 → 切塊 → 標記來源與版本',
 work=[('接入與狀態', '接收上傳、檢查格式與大小，記錄處理中、成功、失敗及重試。',3),('解析與清理','支援文字型 PDF、DOCX、TXT；保留標題與段落，清理重複頁首頁尾。',5),('切塊與來源','依章節、段落及長度切塊，保存文件 ID、版本、頁碼或章節。',5),('更新與刪除','識別重複上傳；更新產生新版本，通知 B 停用或移除舊索引。',3),('測試與串接','建立解析案例、驗證來源定位，與 B 完成片段資料交接。',4)],
 outputs=['可執行的文件處理模組與狀態介面。','DocumentChunk 格式說明、範例資料及版本處理規則。','解析與切塊測試紀錄，附一份從原文到片段的展示案例。'],
 criteria=['每個片段都能定位到原始文件版本及頁碼或章節。','同一文件重複上傳不會持續累積重複片段。','更新或刪除文件後，B 不再回傳已停用的舊版本。','不支援或損壞檔案會顯示失敗原因；重試不造成重複資料。'],
 interface='輸出給 B：DocumentChunk；接收 B 的索引完成或失敗狀態。',
 boundary='第一版限文字型 PDF、DOCX、TXT；掃描 PDF、OCR、複雜 Excel 與圖片理解另行排期。'),
 dict(code='B', title='索引與檢索', goal='從知識庫找出與問題相關、且使用者有權限閱讀的證據片段。',
 flow='問題與授權範圍 → 文字及向量搜尋 → 合併排序 → 去重 → Top-K',
 work=[('向量化與索引','統一文件與問題的 Embedding 模型、版本及維度，建立與更新索引。',5),('文字與向量檢索','支援精確詞彙與語意搜尋，比較單一搜尋與混合搜尋。',5),('排序與去重','合併搜尋結果，去除重複片段，控制回傳數量及來源資訊。',3),('權限過濾','依後端驗證的公司、專案與文件權限限制候選資料；處理撤權。',3),('測試與串接','串接 A、C；用標註題目檢查 Recall@K、查詢耗時及越權案例。',4)],
 outputs=['索引建立、更新、刪除流程及檢索介面。','SearchResult 格式說明與 Embedding／索引設定紀錄。','關鍵字、向量及混合搜尋的比較報告與權限測試結果。'],
 criteria=['固定題組的 Recall@K 達共同設定門檻，並記錄 K 與索引版本。','使用未授權帳號查詢時，回傳結果及模型上下文均不含受限內容。','刪除文件或撤銷權限後，後續查詢不再回傳該內容。','結果含有效片段 ID、文件版本、來源位置及排名或分數。'],
 interface='接收 A 的 DocumentChunk；提供 C 的 SearchResult。Embedding 由 B 統一管理。',
 boundary='沿用既有身分與權限系統。進階重排序模型及大規模效能調校另行排期。'),
 dict(code='C', title='回答生成與引用', goal='根據檢索證據產生可追溯的回答，處理資料不足、來源衝突與模型錯誤。',
 flow='接收問題 → 檢索 → 組合上下文 → 呼叫模型 → 檢查引用 → 回答',
 work=[('流程與上下文','協調檢索與生成，控制 Token 預算、去重並保留必要證據。',5),('模型串接','封裝模型呼叫，處理逾時、取消與錯誤，回傳一致狀態。',4),('Prompt 與不足處理','要求依據資料作答；處理無答案、來源矛盾及文件惡意指令。',4),('引用檢查','建立引用與片段的對應，攔截不存在或非本次檢索的引用 ID。',3),('測試與串接','串接 B、D；驗證正常回答、證據不足、引用錯誤及模型失敗。',4)],
 outputs=['回答生成模組、模型連線介面與錯誤處理。','Prompt 版本及 AnswerResponse 格式說明與範例。','回答與引用測試紀錄，附資料不足及模型失敗展示案例。'],
 criteria=['引用 ID 全部對應本次檢索結果，能連回原始文件位置。','人工抽查答案與來源，答案正確率及引用支持率達共同門檻。','無證據或證據互相矛盾時，清楚說明不足或差異。','逾時與失敗回傳可理解狀態；文件中的指令不能改寫系統規則。'],
 interface='呼叫 B 取得 SearchResult；向 D 回傳 AnswerResponse 與追蹤 ID。',
 boundary='引用 ID 合法不代表內容必然正確，仍須人工抽查。多模型路由及 Agent 工具操作另行排期。'),
 dict(code='D', title='問答介面與品質評估', goal='提供完整問答與來源檢視流程，建立可重複執行、可比較版本的評測工具。',
 flow='選範圍 → 提問 → 顯示狀態 → 回答與來源 → 回饋 → 評測報告',
 work=[('問答介面','提供問題輸入、對話顯示、送出與取消，以及錯誤與空狀態。',5),('引用與文件狀態','呈現來源、版本及位置；開啟原文；顯示 A 的文件處理狀態。',4),('使用者回饋','收集有幫助或沒幫助的回饋與原因，保留問題追蹤資訊。',2),('評測與報告','批次執行固定題組，彙整回答、引用、耗時與不同版本結果。',5),('測試與串接','串接 A、C；驗證完整操作、切專案與登出隔離、來源開啟。',4)],
 outputs=['可操作的問答頁面、引用檢視及文件處理狀態畫面。','批次評測工具、題組格式及品質比較報告。','端對端操作紀錄、使用者回饋紀錄與共同展示腳本。'],
 criteria=['使用者可完成選範圍、提問、查看回答及開啟原文。','切換專案或登出後，不保留或顯示未授權的對話與來源內容。','同一題組可重複執行；報告記錄模型、Prompt、索引版本與耗時。','報告能區分解析、檢索、生成及介面問題，並指派回主責模組。'],
 interface='接收 A 的處理狀態及 C 的 AnswerResponse；四人共同提供題目與標準證據。',
 boundary='D 負責評測工具與彙整；A、B、C 各自負責模組測試與缺陷修正，部署沿用既有環境。')
]

doc=Document(); sec=doc.sections[0]
sec.page_width=Cm(21); sec.page_height=Cm(29.7)
sec.top_margin=Cm(1.6); sec.bottom_margin=Cm(1.6); sec.left_margin=Cm(1.8);sec.right_margin=Cm(1.8)
sec.footer_distance=Cm(.7)
for grid in list(sec._sectPr.findall(qn('w:docGrid'))): sec._sectPr.remove(grid)
for style in doc.styles:
 pr=style.element.get_or_add_pPr()
 for el in list(pr.findall(qn('w:pBdr'))):pr.remove(el)
 snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');pr.append(snap)
for name,size in [('Normal',10.5),('Title',23),('Heading 1',18),('Heading 2',12)]:
 s=doc.styles[name];s.font.name='Microsoft JhengHei';s.font.size=Pt(size);s.font.color.rgb=RGBColor(0,0,0)
 s.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Microsoft JhengHei')
 s.paragraph_format.space_after=Pt(5);s.paragraph_format.line_spacing=1.1
 if name.startswith('Heading'):s.paragraph_format.space_before=Pt(9)
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('RAG 分工認領表　｜　').font.size=Pt(9)
f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');footer._p.append(f)

def p(text='',bold=False):
 x=doc.add_paragraph();r=x.add_run(text);r.bold=bold;return x
def h(text):return doc.add_heading(text,2)
def table(headers,rows,widths):
 t=doc.add_table(rows=1,cols=len(headers));t.autofit=False;t.alignment=WD_TABLE_ALIGNMENT.CENTER
 for c,w in zip(t.columns,widths):c.width=Cm(w)
 borders=OxmlElement('w:tblBorders')
 for edge in ['top','left','bottom','right','insideH','insideV']:
  el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
 t._tbl.tblPr.append(borders)
 for i,values in enumerate([headers]+rows):
  cells=t.rows[0].cells if i==0 else t.add_row().cells
  trpr=cells[0]._tc.getparent().get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
  if i==0:trpr.append(OxmlElement('w:tblHeader'))
  for j,(cell,value) in enumerate(zip(cells,values)):
   cell.width=Cm(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   pr=cell._tc.get_or_add_tcPr();sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'DCE6F1' if i==0 else 'FFFFFF');pr.append(sh)
   mar=OxmlElement('w:tcMar')
   for side in ['top','bottom','left','right']:
    el=OxmlElement('w:'+side);el.set(qn('w:w'),'80');el.set(qn('w:type'),'dxa');mar.append(el)
   pr.append(mar);x=cell.paragraphs[0];x.paragraph_format.space_after=Pt(1);x.paragraph_format.space_before=Pt(1);x.paragraph_format.line_spacing=1.08
   r=x.add_run(str(value));r.bold=i==0;r.font.size=Pt(10)
   if widths[j]<2.2:x.alignment=WD_ALIGN_PARAGRAPH.CENTER
 spacer=p();spacer.paragraph_format.space_after=Pt(0);spacer.paragraph_format.line_spacing=Pt(2);spacer.runs[0].font.size=Pt(2)
 return t

doc.add_paragraph('RAG 四模組分工認領表',style='Title')
p('請每位組員認領一個模組，填寫姓名與預定日期。各模組列有工作內容、交付成果及可勾選的驗收標準；串接完成後再共同驗收整條問答流程。')
p('專案名稱　____________________　　認領日期　________________')
p('預定整合日　__________________　　共同驗收日　______________')
h('模組認領總表')
table(['模組','主責範圍','工作點','認領姓名'],[(g['code'],g['title'],'20','____________') for g in groups],[1.3,9.1,1.8,5.2])
h('系統流程')
p('資料準備：原始文件 → A 解析與切塊 → B 建立文字與向量索引。')
p('使用者問答：D 接收問題 → C 協調問答 → B 檢索證據 → C 產生附引用回答 → D 顯示回答與來源。')
p('四個模組可放在同一後端專案，以明確介面串接；各模組先使用固定範例資料獨立開發，再進行整合。')
h('分工原則')
p('每包 20 相對工作點，合計 80 點，包含各自測試與串接。點數是第一版的複雜度估算，並非工時或個人歷史貢獻；認領後可依能力與實作難度調整。')
p('每位主責交付程式、介面說明、測試證據與展示案例。D 建立評測工具，四人共同提供題目與標準證據，各自修正所屬模組的問題。')
h('第一版範圍')
p('支援文字型 PDF、DOCX、TXT，沿用既有登入、權限與部署環境。OCR、複雜 Excel、圖片理解、進階重排序及多模型路由另行排期。')
p('專流現況為 FTS5＋BM25 文字搜尋與可選內網 Ollama；正式附件索引、向量檢索與 OCR 尚屬後續能力。本表為分工目標，不代表功能已完成。')
h('填寫方式')
p('各頁姓名與日期留白；驗收勾選須有實測證據。品質門檻在第 6 頁共同確認，空白項目不能視為通過。')

for g in groups:
 title=doc.add_heading(g['code']+' '+g['title'],1);title.paragraph_format.page_break_before=True
 p('認領姓名　________________　預定完成日　________________',True)
 p(g['goal']);p(g['flow'])
 h('工作內容')
 table(['工作項目','負責內容','點數'],g['work'],[3.0,13.2,1.2])
 h('交付成果')
 for s in g['outputs']:p('□ '+s)
 h('驗收標準')
 for s in g['criteria']:p('□ '+s)
 h('串接與範圍')
 p(g['interface']);p(g['boundary'])
 p('驗收人　____________　日期　____________　結果　□ 通過　□ 待修正')
 p('證據位置或待修事項　________________________________________________')

title=doc.add_heading('共同串接與整體驗收',1);title.paragraph_format.page_break_before=True
p('先確認資料格式與測試基準，再依 A→B、B→C、C→D 完成串接，由雙方共同確認。')
h('介面交接表')
table(['交接','介面與必要資料','雙方確認'],[
 ('A → B','DocumentChunk：片段／文件 ID、版本、文字、來源位置、公司／專案 ID。','□ 完成'),
 ('B → C','SearchResult：授權後的片段、來源、排名或分數、索引版本。','□ 完成'),
 ('C → D','AnswerResponse：回答、引用清單、完成／資料不足／失敗狀態、追蹤 ID。','□ 完成'),
 ('A → D','文件狀態：文件 ID、處理階段、成功或失敗、可顯示的錯誤原因。','□ 完成')],[2,12.9,2.5])
p('權限由後端依登入身分確認，專案 ID 僅為查詢條件；開啟引用原文時須重新檢查權限。')
h('品質門檻共同確認')
p('題組版本　____________　題數　________　確認日期　____________')
table(['評估項目','判定方式','目標'],[
 ('檢索 Recall@K','平均每題前 K 筆涵蓋的標準證據比例；先標註正確證據。','K ____\n≥ ____%'),
 ('答案正確率','依預先確認的評分規則，正確回答題數／可回答題數。','≥ ____%'),
 ('引用支持率','人工核對受引用支持的主張／需引用的主張；漏引用計失敗。','≥ ____%'),
 ('無答案處理','無資料題正確指出資料不足，且未捏造答案的比例。','≥ ____%'),
 ('問答延遲','固定環境與題組，記錄送出至完成的 P95 耗時。','≤ ____秒')],[3.1,11.8,2.5])
p('權限案例要求零洩漏。題組須含一般問答、精確詞彙、改寫、無答案、矛盾、越權及模型失敗。')
h('共同驗收清單')
p('□ 上傳 → 解析 → 索引 → 提問 → 回答 → 開啟原文，流程完整。\n□ 文件更新、刪除及撤權後，搜尋與引用行為符合預期。\n□ 無答案、模型失敗及切專案／登出狀態皆已實測。\n□ 各模組交付物與測試證據齊全，品質指標達共同門檻。')
p('整體驗收人　____________　日期　____________　□ 通過　□ 待修正')
p('證據位置或待修事項　________________________________________________')

assert len(groups)==4
assert all(sum(r[2] for r in g['work'])==20 for g in groups)
assert all(len(g['outputs'])==3 and len(g['criteria'])==4 for g in groups)
doc.core_properties.title='RAG 四模組分工認領表'
doc.core_properties.subject='四人模組認領 工作內容 交付成果與驗收標準'
doc.core_properties.author=''
doc.save(OUT)
check=Document(OUT)
assert len(check.tables)==7
assert sum('認領姓名' in p.text for p in check.paragraphs)==4
print(OUT)
print('Validated: four modules, 20 points each, 12 deliverables, 16 module criteria, all name fields blank.')
