import re
from app.ai import fallback, gateway, store

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


def ask(db, company, role, question, mode, project_id=None, query_id=None, dataset='dataset-v1', include_history=False, *, preview=False, other_companies=()):
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
        names = None if chosen else fallback.vocabulary(db)
        # Refusals and written help are decided by rules alone, so the model never sees those questions.
        early = None if chosen else fallback.early_reply(question, other_companies, names)
        prepared = gateway.prepare(company, role, mode, question, catalog=store.catalog(), use_model=not (chosen or early), reason='rules_only' if chosen or early else None)
        if preview: return prepared.preview()
        base['gateway'] = prepared.info
        if early:
            return dict(base, engine='rules', **early)
        if prepared.info['route'] == 'blocked':
            base['warning'] = 'AI閘道拒絕目前模型設定；未送出內容，請管理者檢查本地模型設定。'
        engine='rules'
        if not chosen:
            proposed = None
            if prepared.info['route'] == 'local':
                try:
                    proposed=prepared.run(); engine='model'
                except Exception:
                    base['warning']='模型無法完成辨識；請點下方快捷題，或換個問法。'
            # The model may only add a catalog id; its own words never reach the reply.
            return dict(base, engine=engine, **fallback.suggest(question, names, proposed))
        result=store.execute_query(db,chosen,company,project_id)
        base['analysis']=result
        return dict(base,kind='sql',engine=engine,answer=f'查詢：{result["label"]}。找到{len(result["rows"])}列結果'+('（已截取前200列）。' if result['truncated'] else '。')+'以下為資料庫實際計算；未執行任意模型SQL。')
    if dataset == 'starter-v1':
        documents, base['retrieval'] = starter.search(db, company, question, role, project_id, include_history)
    else:
        documents, base['retrieval'] = store.search(db,question,role,project_id,include_history), 'keyword'
    return answer_documents(company, role, question, documents, base, include_history=include_history, preview=preview, other_companies=other_companies)


SUFFIXES = ('股份有限公司', '有限公司', '公司', '科技', '食品', '電子', '工程', '軟體', '活動', '營造')


def foreign_company(question, documents, names):
    """Name of another company the question asks about when no visible source mentions it at all.

    Users can never see another company's documents, so such a question cannot be answered from
    their sources; answering anyway makes the model pin this company's facts on the other one."""
    for name in names:
        core = name
        for suffix in SUFFIXES:
            if core.endswith(suffix) and len(core) - len(suffix) >= 2:
                core = core[:-len(suffix)]
        aliases = {name, core}
        if any(a in question for a in aliases) and not any(a in d.get('body', '') or a in d.get('title', '') for d in documents for a in aliases):
            return name
    return None


def answer_documents(company, role, question, documents, base, *, include_history=False, preview=False, mask_terms=(), other_companies=()):
    other = foreign_company(question, documents, other_companies)
    if other:
        prepared = gateway.prepare(company, role, 'rag', question, documents, use_model=False, reason='other_company', as_of=base['as_of'])
        if preview: return prepared.preview()
        base['gateway'] = prepared.info
        return dict(base, kind='other_company', engine='rules',
                    answer=f'目前可引用的資料不足：這個問題詢問的是{other}，但目前公司與權限範圍內沒有{other}的資料，無法回答，也不會用本公司的資料代替。')
    prepared = gateway.prepare(company, role, 'rag', question, documents, use_model=bool(documents), reason=None if documents else 'no_sources', as_of=base['as_of'], mask_terms=mask_terms)
    if preview: return prepared.preview()
    base['gateway'] = prepared.info
    if not documents:
        return dict(base,kind='no_sources',engine='retrieval',answer='在目前公司、專案與權限範圍內找不到可引用資料。請換個關鍵詞、選擇其他專案，或確認文件索引已更新。')
    base['sources']=[dict(document_id=d['document_id'],title=d['title'],project_id=d['project_id'],excerpt=d['body'][:1200],is_current=bool(d['current']),**{k:d[k] for k in ('source_type','node_id','version','section','document_ref','project_title','node_title','page') if k in d}) for d in documents]
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
