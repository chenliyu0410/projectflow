import { useEffect, useState } from 'react';
import DocumentPreview from './DocumentPreview';
import LinkedDataPreview from './LinkedDataPreview';
import OperationsPreview from './OperationsPreview';
import AIGovernancePreview from './AIGovernancePreview';
import { CASE_TITLE } from '../preview/fixtures';
import type { OpTab } from '../preview/fixtures';
import HemuPreview from './HemuPreview';
export type PreviewPage = 'documents' | 'data' | 'operations' | 'governance';
const PAGES: [PreviewPage, string][] = [['documents', '文件示例'], ['data', '關聯資料示例'], ['operations', '營運示例'], ['governance', 'AI 政策示例']];
export default function PreviewBoundary({ initialPage, food, companyName, companyKey, exit }: { initialPage: PreviewPage; food: boolean; companyName: string; companyKey?: string; exit: () => void }) {
  const [page, setPage] = useState(initialPage);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [received, setReceived] = useState(false);
  const [opTab, setOpTab] = useState<OpTab>('供應商');
  useEffect(() => setPage(initialPage), [initialPage]);
  if (companyKey === 'hemu' && initialPage !== 'governance') return <HemuPreview key={initialPage} initialPage={initialPage} exit={exit} />;
  return <div className="preview-boundary" aria-label="展示預覽工作區"><header className="preview-banner"><span className="preview-badge">展示預覽</span><strong>{food ? CASE_TITLE : `${companyName}・預覽`}</strong><p>與正式專案無關的示例；僅暫存在本頁，離開預覽、切公司、登出或重新整理即清除。</p><button onClick={exit}>離開預覽，返回工作區</button></header>
    <nav className="preview-tabs" aria-label="示例導覽">{PAGES.map(([id, label]) => <button key={id} aria-current={page === id ? 'page' : undefined} onClick={() => setPage(id)}>{label}</button>)}</nav>
    {!food ? <div className="preview-detail"><h2>{PAGES.find(([id]) => id === page)?.[1]}</h2><p>{companyName}尚未建立此類展示示例。可返回工作區操作現有專案；此處不顯示食品資料。</p></div> : <>
      {page === 'documents' && <DocumentPreview edits={edits} apply={(id, text) => setEdits(value => ({ ...value, [id]: text }))} />}
      {page === 'data' && <LinkedDataPreview open={tab => { setOpTab(tab); setPage('operations'); }} />}
      {page === 'operations' && <OperationsPreview tab={opTab} changeTab={setOpTab} received={received} receive={() => setReceived(true)} back={() => setPage('data')} />}
      {page === 'governance' && <AIGovernancePreview />}
    </>}
  </div>;
}
