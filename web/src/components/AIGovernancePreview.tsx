import { useState } from 'react';
export default function AIGovernancePreview() {
  const [policy, setPolicy] = useState('全本地');
  return <section aria-label="AI 政策展示"><h2>AI 政策與稽核</h2><p>以下僅為政策選擇與路由說明，不會改變公司設定；沒有模型或雲端請求。</p>
    <div className="preview-grid"><article className="preview-detail"><h3>公司政策示例</h3><label>預覽政策<select value={policy} onChange={e => setPolicy(e.target.value)}><option>全本地</option><option>混合</option><option>允許雲端</option></select></label><p role="status">目前示意：{policy}。實際執行仍是瀏覽器內的固定示例。</p></article>
    <article className="preview-detail"><h3>分級與路由示例</h3><dl><div><dt>公開摘要</dt><dd>{policy === '全本地' ? '本地候選' : '雲端候選'}（未執行）</dd></div><div><dt>內部紀錄</dt><dd>{policy === '全本地' ? '本地候選' : policy === '混合' ? '遮罩後雲端候選' : '雲端候選'}（未執行）</dd></div><div><dt>配方與成本</dt><dd>僅本地候選（未執行）</dd></div></dl></article></div>
    <article className="preview-detail"><h3>遮罩稽核示例・非真實請求紀錄</h3><p>原句：青禾原料已確認交期。</p><p>示例遮罩：[供應商_01] 已確認交期。</p><p>固定字串替換示意；尚未提供真實遮罩引擎或安全掃描。</p><details><summary>查看示例送出內容</summary><pre>請整理交期風險：[供應商_01] 已確認交期。{ '\n' }此文字未送出；配方比例與單價不在此示例內容中。</pre></details></article>
  </section>;
}
