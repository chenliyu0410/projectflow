// Deliberately independent of all business IDs and API responses.
export const CASE_TITLE = '成貓雞肉主食罐・試產案例';
export const DOCUMENTS = [
  { id: 'preview-doc-spec', title: '試產規格書', source: '本層：新品試產', versions: ['v1｜研發初稿：雞肉主食罐，規劃試產 200 罐。', 'v2｜跨部門確認：試產 240 罐，每罐 80g；包材確認後安排試產，留樣送驗。'] },
  { id: 'preview-doc-test', title: '包材檢驗紀錄', source: '子層：包材確認', versions: ['v1｜已排定空罐密封測試，等待結果。', 'v2｜空罐密封測試完成；正式量產前仍須完成成品檢驗。'] },
];
export const OP_TABS = ['供應商', '原料 / 物料', '配方', '採購', '工單', '批號追溯', 'ERP 同步'] as const;
export type OpTab = typeof OP_TABS[number];
export const OPERATIONS: Record<Exclude<OpTab, 'ERP 同步'>, { id: string; title: string; status: string; fields: [string, string][] }> = {
  '供應商': { id: 'preview-supplier-01', title: '青禾原料（虛構）', status: '合格', fields: [['供應品項', '雞肉原料'], ['評等', 'A・示例評估'], ['關聯採購', 'PO-DEMO-01']] },
  '原料 / 物料': { id: 'preview-material-01', title: '冷凍雞肉原料', status: '待進料', fields: [['供應商', '青禾原料（虛構）'], ['採購數量', '20 kg'], ['示例批號', 'LOT-DEMO-01']] },
  '配方': { id: 'preview-formula-01', title: '雞肉主食罐配方 A / B', status: '研發比較', fields: [['A 試算', '100 元/kg'], ['B 試算', '92 元/kg'], ['差異', 'B 低 8%；固定示例，並非實際報價'], ['試產規格', '80g × 240 罐']] },
  '採購': { id: 'preview-po-01', title: 'PO-DEMO-01 雞肉原料採購', status: '待收貨', fields: [['供應商', '青禾原料（虛構）'], ['內容', '冷凍雞肉 20 kg'], ['預定用途', 'WO-DEMO-01 試產']] },
  '工單': { id: 'preview-wo-01', title: 'WO-DEMO-01 主食罐試產', status: '待備料', fields: [['產量', '240 罐 × 80g'], ['採購來源', 'PO-DEMO-01'], ['前置條件', '採購收貨與包材確認'], ['成品批號', 'FG-DEMO-01']] },
  '批號追溯': { id: 'preview-trace-01', title: 'FG-DEMO-01 成品追溯', status: '示例關聯', fields: [['供應商', '青禾原料（虛構）'], ['原料批號', 'LOT-DEMO-01'], ['採購', 'PO-DEMO-01'], ['工單 → 成品', 'WO-DEMO-01 → FG-DEMO-01']] },
};
export const AI_ACTIONS = ['本週進度報告', '延遲風險分析', '拆解下一階段', '會議紀錄抽待辦', '配方成本比較', '推薦模板與部門'] as const;
export type AiAction = typeof AI_ACTIONS[number];
export function answerExample(action: AiAction, meeting = ''): { text: string; suggestions: string[]; reference: string; route: string } {
  switch (action) {
    case '本週進度報告': return { text: '示例週報｜試產準備\n已完成：試產規格 v2、供應商評估。\n進行中：原料採購、包材確認。\n下一步：收貨後安排 240 罐試產，留樣送驗。', suggestions: [], reference: '試產規格書 v2、PO-DEMO-01、WO-DEMO-01', route: '公開摘要 → 雲端候選（僅示意，未送出）' };
    case '延遲風險分析': return { text: '示例風險｜原料未收貨，試產可能順延。\n影響：採購 → 備料 → 試產 → 成品送驗。\n建議先確認交貨與包材檢驗，再承諾試產日期。', suggestions: [], reference: 'PO-DEMO-01、WO-DEMO-01 的固定相依示例', route: '公開摘要 → 雲端候選（僅示意，未送出）' };
    case '拆解下一階段': return { text: '建議把試產階段拆為以下三項，套用只會加入此副手的預覽清單。', suggestions: ['確認原料與包材到位', '執行 240 罐試產並記錄', '留樣送驗與成果確認'], reference: '試產規格書 v2', route: '內部資料 → 遮罩示意（未送出）' };
    case '會議紀錄抽待辦': return { text: '本地規則：以換行、句號或分號分段，保留含「待辦／請／確認／安排／完成」的句子，最多五項；不是語意模型。', suggestions: meeting.split(/[\n。；;]/).map(x => x.trim()).filter(x => /待辦|請|確認|安排|完成/.test(x)).slice(0, 5), reference: '你在本次預覽輸入的會議文字', route: '輸入文字僅在此頁記憶體處理，未送出' };
    case '配方成本比較': return { text: '固定示例｜配方 A：100 元/kg；配方 B：92 元/kg。\nB 每公斤低 8 元（8%）。20 kg 的試算差額為 160 元。\n此結果不代表正式配方、採購價格或營養審核。', suggestions: [], reference: 'preview-formula-01 固定試算', route: '機密成本 → 僅本地規則示例，未連接模型' };
    case '推薦模板與部門': return { text: '建議使用「食品試產與送驗」模板，由研發、採購與品保協作。確認後只加入預覽，不建立正式模板或部門。', suggestions: ['食品試產與送驗（模板建議）', '研發：試產規格', '採購：原料到貨', '品保：留樣送驗'], reference: '食品試產固定案例', route: '公開摘要 → 雲端候選（僅示意，未送出）' };
  }
}
