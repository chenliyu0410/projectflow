from contextlib import closing
import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.audit import log_audit
from app.ai import store, service, model, starter, formal_index

router=APIRouter(prefix='/ai',tags=['ai'])
Dataset = Literal['dataset-v1', 'starter-v1', 'formal-v1']


class Ask(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question: str=Field(min_length=1,max_length=2000)
    mode: Literal['rag','sql','work_orders']='rag'
    dataset: Dataset='dataset-v1'
    include_history: bool=False
    project_id: str | None=Field(default=None,max_length=120)
    query_id: str | None=Field(default=None,pattern=r'^q(0[1-9]|1[0-6])$')


class ModelConfig(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled: bool=False
    base_url: str=Field(default='',max_length=200)
    model: str=Field(default='',max_length=120,pattern=r'^[a-zA-Z0-9._:/-]*$')


def connection(current, dataset='dataset-v1'):
    try: return store.connect(current.organization.key, dataset)
    except (FileNotFoundError,sqlite3.Error): raise HTTPException(409,'AI展示資料尚未匯入') from None


def local_admin(request,current):
    if current.user.role!='admin' or request.url.hostname not in {'localhost','127.0.0.1','::1'}: raise HTTPException(403,'僅本機管理者可設定模型')
    origin=request.headers.get('origin')
    if origin and origin!=str(request.base_url).rstrip('/'): raise HTTPException(403,'不允許此來源')
    if request.headers.get('sec-fetch-site')=='cross-site': raise HTTPException(403,'不允許此來源')


@router.get('/status')
def status(request:Request,dataset:Dataset='dataset-v1',current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    try:
        config=model.settings(current.organization.key)
        model.validate_config(config)
    except (OSError, KeyError, TypeError, ValueError):
        config=dict(enabled=False,model='')
    result=dict(ready=False,as_of=store.AS_OF,company_name=current.organization.name,model_enabled=config['enabled'],model_name=config['model'] if config['enabled'] else '',can_configure=current.user.role=='admin' and request.url.hostname in {'localhost','127.0.0.1','::1'},can_sql=current.user.role in {'admin','project_owner'},projects=[],queries=[],counts={})
    result['dataset'] = dataset
    result['gateway'] = dict(policy='local_only', cloud_enabled=False)
    result['formal_available'] = formal_index.enabled() and db.bind.dialect.name == 'sqlite'
    if dataset == 'formal-v1':
        index = formal_index.status(db,current)
        result.update(ready=True,as_of=index['updated_at'],can_sql=False,projects=index.pop('projects'),
                      counts={'documents':index['counts']['indexed']},index=index)
        result['counts']['projects'] = len(result['projects'])
        return result
    if dataset == 'starter-v1':
        result.update(as_of=starter.AS_OF, can_sql=False)
    try:
        with closing(store.connect(current.organization.key, dataset)) as db:
            projects = starter.visible_projects(db, current.user.role) if dataset == 'starter-v1' else [dict(r) for r in db.execute('SELECT project_id,title FROM projects ORDER BY project_id')]
            result.update(ready=True,projects=projects,queries=[] if dataset == 'starter-v1' else [{'query_id':q['query_id'],'label':q['label']} for q in store.catalog()],counts={'projects':len(projects),'documents':db.execute('SELECT COUNT(*) FROM documents WHERE EXISTS (SELECT 1 FROM json_each(roles) WHERE value=?)',(current.user.role,)).fetchone()[0]})
    except (FileNotFoundError,sqlite3.Error): pass
    return result


@router.post('/ask')
def ask(payload:Ask,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return evaluate(payload,current,db,preview=False)


@router.post('/preview')
def preview(payload:Ask,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return evaluate(payload,current,db,preview=True)


def evaluate(payload,current,db,*,preview):
    if not payload.question.strip(): raise HTTPException(422,'請輸入問題')
    try:
        if payload.dataset == 'formal-v1':
            result=formal_index.ask(db,current,payload,preview=preview)
        else:
            with closing(connection(current, payload.dataset)) as data:
                if payload.project_id:
                    visible = {p['project_id'] for p in starter.visible_projects(data,current.user.role)} if payload.dataset == 'starter-v1' else {r[0] for r in data.execute('SELECT project_id FROM projects')}
                    if payload.project_id not in visible: raise HTTPException(404,'找不到AI專案')
                result=service.ask(data,current.organization.key,current.user.role,payload.question,payload.mode,payload.project_id,payload.query_id,payload.dataset,payload.include_history,preview=preview)
    except PermissionError: raise HTTPException(403,'沒有此AI查詢的資料權限') from None
    except ValueError: raise HTTPException(422,'不支援此查詢') from None
    log_audit(db,current,'ai.preview' if preview else 'ai.query',payload={'mode':payload.mode,'dataset':payload.dataset,'include_history':payload.include_history,'project_id':payload.project_id,'kind':'preview' if preview else result['kind'],'source_count':result['gateway']['source_count'],'query_id':result['analysis']['query_id'] if not preview and result['analysis'] else None,'gateway':result['gateway']})
    db.commit()
    return result


@router.get('/documents/{document_id}')
def document(document_id:str,dataset:Dataset='dataset-v1',include_history:bool=False,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    if dataset == 'formal-v1':
        return formal_index.document(db,current,document_id,include_history=include_history)
    with closing(connection(current, dataset)) as db:
        # Superseded starter documents are only readable when history was requested, as in search.
        history=include_history or dataset=='dataset-v1'
        row=db.execute('SELECT * FROM documents WHERE document_id=? AND (current=1 OR ?) AND EXISTS (SELECT 1 FROM json_each(roles) WHERE value=?)',(document_id,int(history),current.user.role)).fetchone()
        if row is None: raise HTTPException(404,'找不到文件')
        metadata=json.loads(row['metadata'])
        return dict(document_id=row['document_id'],title=row['title'],text=row['body'],project_id=row['project_id'],version=metadata['version'],is_current=metadata['is_current'])


@router.post('/index/refresh')
def refresh_index(current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    result=formal_index.refresh(db,current)
    log_audit(db,current,'ai.index.refresh',payload={'dataset':'formal-v1','counts':result['counts']})
    db.commit()
    return result


@router.get('/model')
def get_model(request:Request,current:CurrentUser=Depends(require_session)):
    local_admin(request,current)
    return model.settings(current.organization.key)


@router.put('/model')
def set_model(payload:ModelConfig,request:Request,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    local_admin(request,current)
    try: model.save(current.organization.key,payload.model_dump())
    except ValueError: raise HTTPException(422,'請填內網模型位址與模型名稱') from None
    log_audit(db,current,'ai.model.configure',payload={'enabled':payload.enabled})
    db.commit()
    return {'ok':True}


@router.post('/model/test')
def test_model(payload:ModelConfig,request:Request,current:CurrentUser=Depends(require_session)):
    local_admin(request,current)
    try:
        result=model.request(payload.model_dump(),'/api/tags')
        names=[m['name'] for m in result['models'] if isinstance(m.get('name'),str)]
        return {'ok':payload.model in names,'models':names,'message':'連線成功，請選擇已安裝的聊天模型。' if payload.model not in names else '連線成功，模型已安裝。'}
    except Exception:
        return {'ok':False,'models':[],'message':'無法連線。請確認內網位址、Ollama監聽設定與防火牆。'}
