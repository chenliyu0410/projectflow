// Categories for the AI copilot, with fixed shortcut questions taken from docs/ai-demo-questions.md. A category picks
// the dataset and query mode; a question may also ask for history, the complete work-order list or one project, so the
// user never has to set those by hand. Typed questions use the category with all visible projects and no history.
export type CopilotQuestion = {
  text: string;
  mode?: 'work_orders';
  history?: boolean;
  /** Matched by title prefix against the dataset's projects when the question is asked. */
  project?: string;
};

export type CopilotCategory = {
  id: 'docs' | 'sql' | 'starter' | 'formal';
  title: string;
  dataset: 'dataset-v1' | 'starter-v1' | 'formal-v1';
  mode: 'rag' | 'sql';
  /** Company names that have this category's data; omitted when every company has it. */
  companies?: string[];
  placeholder: string;
  questions: CopilotQuestion[];
};

const FOOD = ['毛研食品'];

export const CATEGORIES: CopilotCategory[] = [
  { id: 'docs', title: '文件問答', dataset: 'dataset-v1', mode: 'rag', placeholder: '問交付規範、風險或採購文件…',
    questions: [{ text: '現行交付需要幾張截圖？' }, { text: '風險原因與處理方式' }, { text: '採購追蹤紀錄' }] },
  { id: 'sql', title: '資料分析', dataset: 'dataset-v1', mode: 'sql', placeholder: '例如：各部門逾期未完成數',
    questions: [{ text: '各部門逾期未完成數' }, { text: '請問有哪些專案超支？' }, { text: '各專案加權不良率' }, { text: '本週到期未完成任務' }, { text: '供應商已收貨延遲率' }] },
  { id: 'starter', title: '新人報到', dataset: 'starter-v1', mode: 'rag', companies: FOOD, placeholder: '問報到、教育訓練或工單…',
    questions: [{ text: '新人課程目前什麼時候、在哪裡上？' }, { text: '只有2位新人，為什麼做20份歡迎包？' }, { text: '給新同事用的電腦弄好了沒？' },
      { text: '新人課程原本哪天？為什麼改期？', history: true }, { text: '列出全部未完成工單', mode: 'work_orders' }] },
  { id: 'formal', title: '正式文件', dataset: 'formal-v1', mode: 'rag', companies: FOOD, placeholder: '問正式文件與附件…',
    questions: [{ text: '新人報到地點在哪一樓？', project: '增量索引展示' }, { text: '新人報到地點原本和現在分別在哪一樓？', project: '增量索引展示', history: true },
      { text: '設備申請流程怎麼做？', project: '隔離索引展示' }, { text: '新人報到要先去哪裡換證？', project: 'OCR 示範' }] },
];
