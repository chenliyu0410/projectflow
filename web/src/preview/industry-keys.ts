// 只列公司代碼，讓主程式不必為了判斷「有沒有展示資料」就把 133 kB 的 industries.json 打包進來。
export const INDUSTRY_KEYS = ['food', 'electronics', 'events', 'software', 'construction'] as const;
export const hasIndustryDataset = (key?: string) => !!key && (INDUSTRY_KEYS as readonly string[]).includes(key);
