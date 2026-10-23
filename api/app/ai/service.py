import re
from app.ai import gateway, store

ALIASES = {
 'q01': ['任務狀態統計'],
 'q02': ['各部門有幾件逾期任務', '各部門逾期任務數'],
 'q03': ['各專案完成比例'],
 'q04': ['超支專案及金額', '哪些專案超支', '有哪些專案超支'],
 'q07': ['各專案不良率'],
 'q10': ['未完成工作最多的前5位負責人'],
}


def infer(question):
    # Full phrase matching prevents silently dropping dates, names, negations or status filters.
    phrase=question.strip().rstrip('？?。！!')
    phrase=re.sub(r'^(?:請問|請幫我查詢|幫我查詢|請查詢|查詢|請列出|列出)\s*','',phrase)
    for q in store.catalog():
        if phrase in [q['label'],*ALIASES.get(q['query_id'],[])]: return q['query_id']
    return None


def ask(db, company, role, question, mode, project_id=None, query_id=None, dataset='dataset-v1', include_history=False, *, preview=False):
    base=dict(as_of=store.AS_OF,synthetic=True,project_id=project_id,sources=[],analysis=None,warning=None)
    if dataset == 'starter-v1':
        from app.ai import starter
        base['as_of'] = starter.AS_OF
        if mode == 'sql':
            raise ValueError('Starter documents have no SQL dataset')
    if mode == 'work_orders':
        if dataset != 'starter-v1':
            raise ValueError('Work-order listing requires starter dataset')
        rows = starter.pending_orders(db, role, project_id)
        prepared = gateway.prepare(company, role, mode, question, rows, use_model=False, reason='rules_only')
        if preview: return prepared.preview()
        base['gateway'] = prepared.info
        base['sources'] = [dict(document_id=d['document_id'], title=d['title'], project_id=d['project_id'], excerpt=d['body'][:1200]) for d in rows]
        lines = [f"{d['document_id']} {d['title']}｜{d['owner']}｜期限{d['due_date']}｜{d['status']}" + (f"｜逾期{d['overdue_days']}天" if d['overdue_days'] else '') for d in rows]
        return dict(base, kind='work_orders', engine='rules', answer=f"截至{base['as_of']}，目前範圍共有{len(rows)}張未完成工單（日曆日計算）。\n" + '\n'.join(lines))
    if mode=='sql':
        if role not in {'admin','project_owner'}: raise PermissionError('SQL role')
        chosen=query_id or infer(question)
        prepared = gateway.prepare(company, role, mode, question, catalog=store.catalog(), use_model=not chosen, reason='rules_only' if chosen else None)
        if preview: return prepared.preview()
        base['gateway'] = prepared.info
        if prepared.info['route'] == 'blocked':
            base['warning'] = 'AI閘道拒絕目前模型設定；未送出內容，請管理者檢查本地模型設定。'
        engine='rules'
        if not chosen and prepared.info['route'] == 'local':
            try:
                proposed=prepared.run(); engine='model'
                if proposed:
                    label=next(q['label'] for q in store.catalog() if q['query_id']==proposed)
                    return dict(base,kind='query_suggestion',engine=engine,answer=f'模型建議使用「{label}」。尚未執行，請核對是否符合原問題。此分析只使用上方公司／AI專案範圍，基準日固定2026-10-11，不加入原問題中的其他條件。',suggestion={'query_id':proposed,'label':label})
            except Exception:
                base['warning']='模型無法完成辨識；請從分析選單選擇查詢。'
        if not chosen:
            return dict(base,kind='unsupported',engine=engine,answer='目前支援16種分析，尚無法可靠判斷這個問題。請選擇分析種類，或改問「各部門逾期未完成數」。時間基準固定2026-10-11；其他日期條件尚未支援。')
        result=store.execute_query(db,chosen,company,project_id)
        base['analysis']=result
        return dict(base,kind='sql',engine=engine,answer=f'查詢：{result["label"]}。找到{len(result["rows"])}列結果'+('（已截取前200列）。' if result['truncated'] else '。')+'以下為資料庫實際計算；未執行任意模型SQL。')
    if dataset == 'starter-v1':
        documents, base['retrieval'] = starter.search(db, company, question, role, project_id, include_history)
    else:
        documents, base['retrieval'] = store.search(db,question,role,project_id,include_history), 'keyword'
    return answer_documents(company, role, question, documents, base, include_history=include_history, preview=preview)


def answer_documents(company, role, question, documents, base, *, include_history=False, preview=False):
    prepared = gateway.prepare(company, role, 'rag', question, documents, use_model=bool(documents), reason=None if documents else 'no_sources', as_of=base['as_of'])
    if preview: return prepared.preview()
    base['gateway'] = prepared.info
    if not documents:
        return dict(base,kind='no_sources',engine='retrieval',answer='在目前公司、專案與權限範圍內找不到可引用資料。請換個關鍵詞、選擇其他專案，或確認文件索引已更新。')
    base['sources']=[dict(document_id=d['document_id'],title=d['title'],project_id=d['project_id'],excerpt=d['body'][:1200],is_current=bool(d['current']),**{k:d[k] for k in ('source_type','node_id','version','section') if k in d}) for d in documents]
    if prepared.info['route'] == 'blocked':
        base['warning'] = 'AI閘道拒絕目前模型設定；未送出內容，改顯示可核對的檢索原文。'
    if prepared.info['reason'] == 'context_too_large':
        base['warning'] = '最相關的來源段落超過本地模型長度上限；未送出內容，改顯示可核對的檢索原文。'
    if prepared.info['route'] == 'local':
        try:
            generated=prepared.run()
            return dict(base,kind='rag',engine='model',answer=generated['answer'],citations=generated['citations'])
        except Exception:
            base['warning']='模型連線或引用驗證失敗，改顯示可核對的檢索原文。'
    label = ('文件段落' if not base['synthetic'] else '文件') + ('（含歷史版本，請核對日期）' if include_history else '（現行版本）')
    return dict(base,kind='retrieval',engine='retrieval',answer=f'找到{len(documents)}份相關{label}。'+('模型尚未啟用，以下提供檢索原文；不是模型生成的答案。' if prepared.info['reason'] == 'model_disabled' else '請開啟引用查看原文。'))
