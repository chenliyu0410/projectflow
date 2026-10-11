import { useState } from 'react';
import raw from '../preview/industries.json';
import type { PreviewPage } from './PreviewBoundary';

type RecordItem = {
  code: string; title: string; status: string; fields: Record<string, string | undefined>;
  links: { group: string; code: string }[]; action: string | null; editable: boolean;
};
type Dataset = {
  company: { key: string; name: string; code: string; brand: string; established: number; employees: number; location: string; email: string; business: string; focus: string; asOf: string };
  people: { key: string; name: string; department: string; title: string }[];
  departments: { name: string; count: number; head: string }[];
  projects: { code: string; title: string; owner: string }[];
  groups: { key: string; label: string; records: RecordItem[] }[];
  journey: string;
};
const datasets: Record<string, Dataset> = raw;
export const hasIndustryDataset = (key?: string) => !!key && Object.hasOwn(datasets, key);

export default function IndustryPreview({ companyKey, initialPage, exit, legacy }: {
  companyKey: string; initialPage: PreviewPage; exit: () => void; legacy?: () => void;
}) {
  const data = datasets[companyKey];
  const [groupKey, setGroupKey] = useState(initialPage === 'documents' ? 'documents' : initialPage === 'data' ? 'links' : 'company');
  const [selected, setSelected] = useState<string | null>(null);
  const [applied, setApplied] = useState<string[]>([]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const group = data.groups.find(g => g.key === groupKey);
  const record = group?.records.find(r => r.code === selected);
  const navigate = (key: string, code: string | null = null) => { setGroupKey(key); setSelected(code); };
  const recordButton = (item: RecordItem, key: string) => <button className="preview-card" key={item.code} onClick={() => navigate(key, item.code)}><strong>{item.code}｜{item.title}</strong><span>{applied.includes(item.code) ? '已套用至預覽' : item.status}</span></button>;
  return <section className="preview-boundary" aria-label="產業公司展示資料">
    <header className="preview-banner"><span className="preview-badge">虛構案例 · 營運展示預覽</span><h2>{data.company.name}</h2>
      <p>基準日 {data.company.asOf}。新增專案、任務與回報可操作保存；此處單據／文件操作僅暫存，離開、切公司或重新整理即清除。原有公司資料保留，完整參考快照另存新增專案根層「紀錄」。</p>
      <button onClick={exit}>返回工作區</button>{legacy && <button onClick={legacy}>查看原食品試產示例</button>}
    </header>
    <nav className="preview-tabs" aria-label="產業資料分類">
      {[{ key: 'company', label: '公司與人員' }, ...data.groups, { key: 'links', label: '關聯流程' }].map(g => <button key={g.key} aria-current={groupKey === g.key ? 'page' : undefined} onClick={() => navigate(g.key)}>{g.label}</button>)}
    </nav>
    {groupKey === 'company' && <article className="preview-detail"><h3>公司概況</h3><p>{data.company.code}｜{data.company.brand}｜{data.company.established}年成立｜{data.company.employees}人編制</p><p>{data.company.location}</p><p>{data.company.business}</p><p>目前重點：{data.company.focus}</p><p>{data.company.email}（虛構聯絡信箱）</p>
      <h3>本次新增部門與主要人員</h3><p>{data.people.length}位具名展示人員；編制數是虛構規模，不等同系統帳號總數。原有部門與人員仍保留。</p>
      {data.departments.map(d => <section key={d.name}><h4>{d.name} · 編制{d.count}人</h4>{data.people.filter(p => p.department === d.name).map(p => <p key={p.key}>{p.name}｜{p.title}{p.key === d.head ? '（部門主管）' : ''}</p>)}</section>)}
      <h3>本次新增專案</h3>{data.projects.map(p => <p key={p.code}>{p.code}｜{p.title}｜{data.people.find(person => person.key === p.owner)?.name}</p>)}<p>從左側專案清單進入，可編輯任務、時程及回報審核；進度依系統實算。</p>
    </article>}
    {group && <><div className="preview-cards">{group.records.map(r => recordButton(r, group.key))}</div>
      {record && <article className="preview-detail" aria-label="單據詳情"><h3>{record.code}｜{record.title}</h3><p>{record.status}</p><dl>{Object.entries(record.fields).map(([label, value]) => value !== undefined && <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
        {record.links.length > 0 && <div className="preview-actions">{record.links.map(link => {
          const targetGroup = data.groups.find(g => g.key === link.group);
          const target = targetGroup?.records.find(r => r.code === link.code);
          return target && <button key={`${link.group}:${link.code}`} onClick={() => navigate(link.group, link.code)}>查看{target.code}｜{target.title}</button>;
        })}</div>}
        {record.action && <><button onClick={() => setApplied(values => values.includes(record.code) ? values : [...values, record.code])}>{record.action}至預覽</button>{applied.includes(record.code) && <p role="status">已套用至預覽；未修改正式庫存、合約、單據或任務。</p>}</>}
        {record.editable && <><label>文字編輯預覽<textarea rows={6} style={{ width: '100%', boxSizing: 'border-box' }} value={edits[record.code] ?? record.fields['內容'] ?? ''} onChange={event => setEdits(values => ({ ...values, [record.code]: event.target.value }))} /></label><p>只暫存在本頁，不代表已核准或儲存正式文件版本。</p></>}
      </article>}</>}
    {groupKey === 'links' && <article className="preview-detail"><h3>展示操作流程</h3><p>{data.journey}</p><p>單據關聯僅展示資料脈絡；正式任務以前置條件與回報控制，不由預覽動作自動解鎖。未連接ERP或外部服務。</p><div className="preview-cards">{data.groups.find(g => g.key === 'orders')?.records.map(r => recordButton(r, 'orders'))}</div></article>}
  </section>;
}
