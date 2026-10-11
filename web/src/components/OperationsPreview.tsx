import { useState } from 'react';
import { OP_TABS, OPERATIONS } from '../preview/fixtures';
import type { OpTab } from '../preview/fixtures';
export default function OperationsPreview({ tab, changeTab, received, receive, back }: { tab: OpTab; changeTab: (tab: OpTab) => void; received: boolean; receive: () => void; back: () => void }) {
  const [detail, setDetail] = useState(true);
  const item = tab === 'ERP 同步' ? null : OPERATIONS[tab];
  const status = tab === '採購' && received ? '已收貨（預覽）' : tab === '工單' && received ? '原料到位，待包材確認' : item?.status;
  function go(next: OpTab) { setDetail(true); changeTab(next); }
  return <section aria-label="營運資料展示"><h2>研發營運資料</h2><p>供應商 → 採購 → 工單，一個試產案例的資料脈絡。</p>
    <div className="preview-tabs" role="tablist" aria-label="營運分頁">{OP_TABS.map(label => <button role="tab" key={label} aria-selected={tab === label} onClick={() => go(label)}>{label}</button>)}</div>
    {item ? <><div className="preview-detail"><small>示例列表・1 筆</small><button className="preview-list-row" onClick={() => setDetail(value => !value)} aria-expanded={detail}><strong>{item.title}</strong><span>{status}　{detail ? '收合' : '查看詳情'}</span></button></div>
      {detail && <article className="preview-detail"><h3>{item.title}</h3><span className="preview-badge">{status}</span><dl>{item.fields.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>
        <div className="preview-actions">{tab === '供應商' && <button onClick={() => go('採購')}>查看關聯採購</button>}
        {tab === '採購' && <><button disabled={received} onClick={receive}>{received ? '已套用至預覽：收貨' : '模擬收貨（僅預覽）'}</button><button onClick={() => go('工單')}>查看關聯工單</button></>}
        {tab === '工單' && <><button onClick={() => go('採購')}>查看來源採購</button><button onClick={() => go('批號追溯')}>查看批號追溯</button></>}
        <button onClick={back}>返回關聯資料</button></div>
      </article>}</> : <article className="preview-detail"><h3>ERP 尚未連線</h3><p>沒有同步、匯入或外部傳輸。前六個分頁使用虛構示例，並非 ERP 資料。</p></article>}
  </section>;
}
