import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../api';
import { sourceDownloadPath } from '../rag';
import type { RagOriginal } from '../rag';
import { location } from './RagConversation';
export default function RagSourceViewer({ original, loading, error, close, expired, denied }: { original: RagOriginal | null; loading: boolean; error: string; close: () => void; expired?: () => void; denied: () => void }) {
 const [downloadError, setDownloadError] = useState(''), [busy, setBusy] = useState(false); const controller = useRef<AbortController | null>(null);
 useEffect(() => () => controller.current?.abort(), []);
 async function download() { if (!original || busy) return; const c = new AbortController(); controller.current = c; setBusy(true); setDownloadError(''); const timer = setTimeout(() => c.abort(), 30000);
 try { const response = await fetch(sourceDownloadPath(original.download_url), { credentials: 'include', signal: c.signal }); if (!response.ok) throw new ApiError(response.status, response.status === 401 ? '登入已失效，請重新登入' : [403,404].includes(response.status) ? '原文件已無存取權限或不存在。' : '無法下載完整文件，請稍後重試。'); const blob = await response.blob(); if (c.signal.aborted) return; const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = original.title; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
 } catch(e) { if (e instanceof ApiError && [401,403,404].includes(e.status)) { denied(); if (e.status === 401) expired?.(); } setDownloadError(e instanceof ApiError ? e.message : c.signal.aborted ? '下載已取消或逾時，請重試。' : '無法下載完整文件。'); } finally { clearTimeout(timer); setBusy(false); } }
 return <section className="rag-sheet" aria-label="正式引用原文"><button onClick={close}>關閉來源</button>{loading && <p role="status">正在讀取來源…</p>}{error && <p role="alert">{error}</p>}{original && <><h3>{original.title}・版本 {original.version}</h3><p>{original.project_title}・{location(original.locator)}・{original.is_current ? '現行版本' : '非現行版本'}</p><pre><mark>{original.text}</mark></pre>{original.download_url && <button disabled={busy} onClick={() => void download()}>下載完整文件</button>}</>}{downloadError && <p role="alert">{downloadError}</p>}</section>;
}
