import type { OpTab } from '../preview/fixtures';
export default function LinkedDataPreview({ open }: { open: (tab: OpTab) => void }) {
  return <section aria-label="關聯資料展示"><h2>本層關聯資料</h2><p>來源：示例「新品試產」，並非目前正式節點的關聯。</p><div className="preview-grid">
    <article className="preview-card"><small>供應商・合格</small><h3>青禾原料（虛構）</h3><p>雞肉原料供應與評估</p><button onClick={() => open('供應商')}>查看供應商詳情</button></article>
    <article className="preview-card"><small>採購・待收貨</small><h3>PO-DEMO-01</h3><p>冷凍雞肉 20 kg</p><button onClick={() => open('採購')}>查看採購詳情</button></article>
  </div><article className="preview-detail"><h3>子層的關聯資料</h3><p>示例子任務「執行試產」→ WO-DEMO-01 → 成品 FG-DEMO-01</p><button onClick={() => open('工單')}>查看子層工單詳情</button></article></section>;
}
