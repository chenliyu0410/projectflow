// Demo scenarios for the AI copilot, taken from docs/ai-demo-questions.md. Choosing one sets up the copilot
// (dataset, query mode, project, history) and lists that scenario's questions. Steps that need another account
// or page are shown as instructions instead, because the copilot cannot switch accounts.
export type CopilotScenario = {
  id: string;
  title: string;
  /** Company names that have this scenario's data; omitted when every company has it. */
  companies?: string[];
  dataset?: 'dataset-v1' | 'starter-v1' | 'formal-v1';
  mode?: 'rag' | 'sql' | 'work_orders';
  /** The project is chosen by title prefix once the dataset has loaded. */
  project?: string;
  history?: boolean;
  questions?: string[];
  steps?: string[];
};

const FOOD = ['毛研食品'];

export const SCENARIOS: CopilotScenario[] = [
  { id: 'starter', title: '新人報到（文件問答）', companies: FOOD, dataset: 'starter-v1', mode: 'rag',
    questions: ['新人課程目前什麼時候、在哪裡上？', '只有2位新人，為什麼做20份歡迎包？', '給新同事用的電腦弄好了沒？', '迎新禮物準備到哪裡了？', '李小晴的月薪是多少？', '人資訓練預算草案金額是多少？'] },
  { id: 'starter-history', title: '改期與歷史版本', companies: FOOD, dataset: 'starter-v1', mode: 'rag', history: true,
    questions: ['新人課程原本哪天？為什麼改期？'] },
  { id: 'work-orders', title: '未完成工單清單', companies: FOOD, dataset: 'starter-v1', mode: 'work_orders',
    questions: ['列出全部未完成工單'] },
  { id: 'formal-current', title: '正式文件：現行版本', companies: FOOD, dataset: 'formal-v1', mode: 'rag', project: '增量索引展示',
    questions: ['新人報到地點在哪一樓？'] },
  { id: 'formal-history', title: '正式文件：新舊版本對照', companies: FOOD, dataset: 'formal-v1', mode: 'rag', project: '增量索引展示', history: true,
    questions: ['新人報到地點原本和現在分別在哪一樓？'] },
  { id: 'formal-attachment', title: '正式文件：附件來源', companies: FOOD, dataset: 'formal-v1', mode: 'rag', project: '隔離索引展示',
    questions: ['設備申請流程怎麼做？'] },
  { id: 'ocr', title: '圖片與掃描文字辨識（OCR）', companies: FOOD, dataset: 'formal-v1', mode: 'rag', project: 'OCR 示範',
    questions: ['新人報到要先去哪裡換證？', '投影機預定什麼時候歸還？'] },
  { id: 'sql', title: '資料分析（Text-to-SQL）', dataset: 'dataset-v1', mode: 'sql',
    questions: ['各部門逾期未完成數', '請問有哪些專案超支？', '各專案加權不良率', '本週到期未完成任務', '供應商已收貨延遲率'] },
  { id: 'dataset-docs', title: '交付規範、風險與採購文件', dataset: 'dataset-v1', mode: 'rag',
    questions: ['現行交付需要幾張截圖？', '風險原因與處理方式', '採購追蹤紀錄'] },
  { id: 'guide-permission', title: '權限與公司隔離（需換帳號）', companies: FOOD, steps: [
    '登出後以 ming／demo-ming（一般成員）登入，選「新人報到」情境，問「人資訓練預算草案金額是多少？」：應回答資料不足，不出現金額。',
    '一般成員的「查詢方式」裡，Text-to-SQL 是停用的。',
    '登出後以公司 electronics、elaine／demo-elaine 登入，選入門文件問「新人課程什麼時候上？」：10月29日，只看到峰曜科技自己的文件。',
  ] },
  { id: 'guide-policy', title: '資料分級與遮罩（到 AI 政策頁）', companies: FOOD, steps: [
    '左側點「AI 政策與稽核」：雲端供應商「未設定」、政策全本地、公司預設機密。',
    '公司預設改「內部」、政策改「混合」並儲存；回到副手選「正式文件：現行版本」並把專案改成「遮罩示範（虛構）」，輸入「配方成本試算是多少？」按「預覽」：雲端送出內容中的比例、金額、廠商、電話、Email 都變成佔位符。',
    '把該專案設為「機密」再預覽一次：只能本地，沒有雲端內容。',
    '頁面下方「遮罩測試」與「最近 AI 稽核紀錄」：只記處理方式與等級，不記問題原文。',
  ] },
];
