import { useEffect, useRef, useState } from 'react';
import { ai } from '../ai';
import type { ModelConfig } from '../ai';

export default function ModelSettings({ saved }: { saved: () => void }) {
  const [value, setValue] = useState<ModelConfig>({ enabled: false, base_url: '', model: '' });
  const [busy, setBusy] = useState(true);
  const [notice, setNotice] = useState('');
  const [models, setModels] = useState<string[]>([]);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const request = new AbortController(); controller.current = request;
    ai.config(request.signal).then(data => { if (!request.signal.aborted) setValue(data); }).catch(() => { if (!request.signal.aborted) setNotice('無法讀取模型設定'); }).finally(() => { if (!request.signal.aborted) setBusy(false); });
    return () => controller.current?.abort();
  }, []);
  async function run(test: boolean) {
    controller.current?.abort(); const request = new AbortController(); controller.current = request;
    setBusy(true); setNotice('');
    try {
      if (test) { const result = await ai.test(value, request.signal); if (!request.signal.aborted) { setNotice(result.message); setModels(result.models); } }
      else { await ai.save(value, request.signal); if (!request.signal.aborted) { setNotice('已儲存本公司模型設定'); saved(); } }
    } catch { if (!request.signal.aborted) setNotice('設定未完成，請檢查內網位址與模型名稱。'); }
    finally { if (!request.signal.aborted) setBusy(false); }
  }
  return <form className="ai-settings" onSubmit={e => { e.preventDefault(); void run(false); }}>
    <p>本公司設定。Ollama 主機可在另一台內網電腦；啟用後，問題與可見文件片段會送到該主機。</p>
    <label>Ollama 位址<input type="url" placeholder="http://192.168.1.20:11434" value={value.base_url} disabled={busy} onChange={e => setValue({ ...value, base_url: e.target.value })} /></label>
    <label>聊天模型名稱<input list="installed-ai-models" placeholder="填入 Ollama 已安裝的模型名稱" value={value.model} disabled={busy} onChange={e => setValue({ ...value, model: e.target.value })} /></label>
    <datalist id="installed-ai-models">{models.map(name => <option key={name} value={name} />)}</datalist>
    <label className="ai-enable"><input type="checkbox" checked={value.enabled} disabled={busy} onChange={e => setValue({ ...value, enabled: e.target.checked })} />啟用本地模型整理回答</label>
    <div className="preview-actions"><button type="button" disabled={busy || !value.base_url} onClick={() => void run(true)}>測試連線</button><button disabled={busy} type="submit">儲存設定</button></div>
    {notice && <p role="status">{notice}</p>}
  </form>;
}
