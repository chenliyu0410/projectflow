import { useState } from 'react';
import { DOCUMENTS } from '../preview/fixtures';

export default function DocumentPreview({ edits, apply }: { edits: Record<string, string>; apply: (id: string, text: string) => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [version, setVersion] = useState(1);
  const [draft, setDraft] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const doc = DOCUMENTS.find(item => item.id === selected);
  const content = doc ? edits[`${doc.id}:${version}`] ?? doc.versions[version] : '';
  return <section aria-label="文件展示"><h2>文件</h2><p>案例文件與版本；不代表目前專案的正式文件。</p>
    <div className="preview-grid">{DOCUMENTS.map(item => <button className="preview-card" key={item.id} onClick={() => { setSelected(item.id); setVersion(1); setDraft(null); setNotice(''); }}><span>▤ 文件・v2</span><strong>{item.title}</strong><small>{item.source}</small></button>)}</div>
    {doc && <article className="preview-detail"><h3>{doc.title}</h3><label>示例版本<select value={version} onChange={e => { setVersion(Number(e.target.value)); setDraft(null); setNotice(''); }}><option value={0}>v1・初稿</option><option value={1}>v2・確認稿</option></select></label>
      <p className="preview-prose">{content}</p>
      {draft === null ? <button onClick={() => setDraft(content)}>編輯文字預覽</button> : <div><label>文件文字<textarea maxLength={5000} value={draft} onChange={e => setDraft(e.target.value)} /></label><div className="preview-actions"><button disabled={!draft.trim()} onClick={() => { apply(`${doc.id}:${version}`, draft); setDraft(null); setNotice('已套用至預覽；離開預覽即清除。'); }}>套用至預覽</button><button onClick={() => setDraft(null)}>取消編輯</button></div></div>}
      {notice && <p role="status">{notice}</p>}<p className="muted">正式儲存、上傳與核准尚未提供。</p>
    </article>}
  </section>;
}
