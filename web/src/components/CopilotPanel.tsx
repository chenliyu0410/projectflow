import NavIcon from './NavIcons';

// Same position and layout as the Demo copilot, but an explicit preview: no AI answers, risks or policy states are produced.
const ACTIONS = ['本週進度報告', '延遲風險分析', '拆解下一階段', '會議紀錄抽待辦', '配方成本比較', '推薦模板與部門'];

export default function CopilotPanel({ scope, open, close }: { scope: string; open: boolean; close: () => void }) {
  return <aside id="copilot-panel" className={`copilot ${open ? 'open' : ''}`} aria-label="AI 專案副手">
    <div className="copilot-head">
      <span className="copilot-avatar"><NavIcon name="ai" /></span>
      <div><strong className="brand-name">AI 專案副手</strong><small>範圍：{scope}</small></div>
      <button className="copilot-close" aria-label="關閉 AI 副手" onClick={close}>✕</button>
    </div>
    <p className="copilot-policy"><span className="preview-badge">展示預覽</span>AI 政策：尚未提供</p>
    <div className="copilot-notice">
      <strong>尚未提供</strong>
      <p>正式版還沒有 AI 副手。規則式摘要（週報、延遲風險、任務拆解）排在 F1；這裡先保留位置，不會產生任何建議或回答。</p>
    </div>
    <div className="copilot-actions" role="group" aria-label="副手快捷動作（尚未提供）">
      {ACTIONS.map(label => <button key={label} disabled title="尚未提供">{label}</button>)}
    </div>
    <div className="copilot-chat"><p>目前沒有對話。</p></div>
    <form className="copilot-ask" onSubmit={event => event.preventDefault()}>
      <label className="sr-only" htmlFor="copilot-input">詢問 AI</label>
      <input id="copilot-input" disabled placeholder="AI 副手尚未提供" />
      <button type="submit" disabled aria-label="送出（尚未提供）"><NavIcon name="send" /></button>
    </form>
  </aside>;
}
