import { useState } from 'react';
import data from '../preview/hemu.json';
import type { PreviewPage } from './PreviewBoundary';

type RecordItem = { code: string; title: string; status: string; fields: Record<string, string> };
const groups: [string, RecordItem[]][] = [
  ['供應商', data.suppliers], ['原料 / 包材', data.materials], ['採購', data.orders],
  ['工單', data.workOrders], ['文件', data.documents],
];

export default function HemuPreview({ initialPage, exit }: { initialPage: PreviewPage; exit: () => void }) {
  const [group, setGroup] = useState(initialPage === 'documents' ? '文件' : initialPage === 'data' ? '關聯資料' : '公司與人員');
  const [selected, setSelected] = useState<string | null>(null);
  const [received, setReceived] = useState<string[]>([]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const records = groups.find(([name]) => name === group)?.[1] ?? [];
  const record = records.find(item => item.code === selected);
  const navigate = (name: string, code: string | null = null) => { setGroup(name); setSelected(code); };
  return <section className="preview-boundary" aria-label="禾沐公司展示資料">
    <header className="preview-banner"><span className="preview-badge">虛構公司資料 · 營運展示預覽</span>
      <h2>{data.company.name}</h2><p>案例基準日：{data.company.asOf}。專案、任務與回報是真正保存的展示資料；此處文件及營運操作僅為預覽，離開或重新整理會清除。完整參考快照亦保存在各專案根層「紀錄」筆記。</p>
      <button onClick={exit}>返回工作區</button></header>
    <nav className="preview-tabs" aria-label="禾沐資料分類">{['公司與人員', ...groups.map(([name]) => name), '關聯資料', '配方 / 追溯 / ERP'].map(name => <button key={name} aria-current={group === name ? 'page' : undefined} onClick={() => navigate(name)}>{name}</button>)}</nav>
    {group === '公司與人員' && <div className="preview-detail"><h3>公司概況</h3><p>{data.company.code} · {data.company.brand} · {data.company.established}年成立 · {data.company.employees}人</p><p>{data.company.location}</p><p>{data.company.business}</p><p>目前重點：{data.company.focus}</p><p>{data.company.email}（虛構聯絡信箱）</p><h3>部門與主要人員</h3><p>下列12位是展示操作人員，其餘員工僅計入公司規模，沒有建立虛構登入帳號。</p>
      {data.departments.map(dept => <article key={dept.name}><h4>{dept.name} · 編制{dept.count}人</h4>{data.people.filter(person => person.department === dept.name).map(person => <p key={person.key}>{person.name}｜{person.title}</p>)}</article>)}
      <h3>進行中的專案</h3>{data.projects.map(project => <p key={project.code}>{project.code}｜{project.title}｜負責人：{data.people.find(p => p.key === project.owner)?.name}</p>)}<p>回工作區可編輯任務、安排時程及審核回報；進度由系統依任務狀態計算。</p></div>}
    {records.length > 0 && <><div className="preview-cards">{records.map(item => <button key={item.code} className="preview-card" onClick={() => setSelected(item.code)}><strong>{item.code}｜{item.title}</strong><span>{received.includes(item.code) ? '已模擬收貨（預覽）' : item.status}</span></button>)}</div>
      {record && <article className="preview-detail"><h3>{record.code}｜{record.title}</h3><p>{record.status}</p><dl>{Object.entries(record.fields).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
        {group === '採購' && <><button onClick={() => setReceived(values => values.includes(record.code) ? values : [...values, record.code])}>模擬收貨至預覽</button>{received.includes(record.code) && <p role="status">已套用至預覽；未增加庫存或修改正式任務。</p>}<button onClick={() => navigate('供應商', record.fields['供應商'])}>查看供應商</button>{record.code !== 'PO-261005-03' && <button onClick={() => navigate('工單', 'WO-261022-01')}>查看關聯工單</button>}</>}
        {group === '文件' && <><label>文字編輯預覽<textarea rows={6} style={{ width: '100%', boxSizing: 'border-box' }} value={edits[record.code] ?? record.fields['內容']} onChange={event => setEdits(values => ({ ...values, [record.code]: event.target.value }))} /></label><p>文字只暫存在本頁，不代表已核准或已儲存文件版本。</p></>}
      </article>}</>}
    {group === '關聯資料' && <div className="preview-detail"><h3>成貓雞肉主食罐85g開發</h3><p>第二輪試作審核與包材相容性確認 → 委外排程 → 10/22工程試產 → 送驗與保存試驗 → 量產放行。</p><p>雞胸肉由SUP-001供應；罐身／蓋由SUP-004供應。營運卡片是案例關聯，不會自動解鎖正式任務。</p><button onClick={() => navigate('文件', 'DOC-RD-026')}>產品規格書</button><button onClick={() => navigate('採購', 'PO-261002-01')}>雞胸肉採購</button><button onClick={() => navigate('採購', 'PO-260925-02')}>罐身與易開蓋採購</button><button onClick={() => navigate('工單', 'WO-261022-01')}>工程試產工單</button></div>}
    {group === '配方 / 追溯 / ERP' && <div className="preview-detail"><h3>研發與整合狀態</h3><p>本案例尚未提供可投產的完整營養配方，不以原料清單冒充核准配方。</p><p>10/22工單尚未執行，尚無實際成品批號與批號追溯紀錄。</p><p>ERP未連線；採購、庫存與工單均為虛構參考資料。</p></div>}
  </section>;
}
