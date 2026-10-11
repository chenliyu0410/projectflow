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
from app.ai import store, service, model

router=APIRouter(prefix='/ai',tags=['ai'])


class Ask(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question: str=Field(min_length=1,max_length=2000)
    mode: Literal['rag','sql']='rag'
    project_id: str | None=Field(default=None,max_length=120)
    query_id: str | None=Field(default=None,pattern=r'^q(0[1-9]|1[0-6])$')


class ModelConfig(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled: bool=False
    base_url: str=Field(default='',max_length=200)
    model: str=Field(default='',max_length=120,pattern=r'^[a-zA-Z0-9._:/-]*$')


def connection(current):
    try: return store.connect(current.organization.key)
    except (FileNotFoundError,sqlite3.Error): raise HTTPException(409,'AI展示資料尚未匯入') from None


def local_admin(request,current):
    if current.user.role!='admin' or request.url.hostname not in {'localhost','127.0.0.1','::1'}: raise HTTPException(403,'僅本機管理者可設定模型')
    origin=request.headers.get('origin')
    if origin and origin!=str(request.base_url).rstrip('/'): raise HTTPException(403,'不允許此來源')
    if request.headers.get('sec-fetch-site')=='cross-site': raise HTTPException(403,'不允許此來源')


@router.get('/status')
def status(request:Request,current:CurrentUser=Depends(require_session)):
    config=model.settings(current.organization.key)
    result=dict(ready=False,as_of=store.AS_OF,company_name=current.organization.name,model_enabled=config['enabled'],model_name=config['model'] if config['enabled'] else '',can_configure=current.user.role=='admin' and request.url.hostname in {'localhost','127.0.0.1','::1'},can_sql=current.user.role in {'admin','project_owner'},projects=[],queries=[],counts={})
    try:
        with closing(store.connect(current.organization.key)) as db:
            result.update(ready=True,projects=[dict(r) for r in db.execute('SELECT project_id,title FROM projects ORDER BY project_id')],queries=[{'query_id':q['query_id'],'label':q['label']} for q in store.catalog()],counts={'projects':db.execute('SELECT COUNT(*) FROM projects').fetchone()[0],'documents':db.execute('SELECT COUNT(*) FROM documents WHERE EXISTS (SELECT 1 FROM json_each(roles) WHERE value=?)',(current.user.role,)).fetchone()[0]})
    except (FileNotFoundError,sqlite3.Error): pass
    return result


@router.post('/ask')
def ask(payload:Ask,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    if not payload.question.strip(): raise HTTPException(422,'請輸入問題')
    with closing(connection(current)) as data:
        if payload.project_id and not data.execute('SELECT 1 FROM projects WHERE project_id=?',(payload.project_id,)).fetchone(): raise HTTPException(404,'找不到AI專案')
        try: result=service.ask(data,current.organization.key,current.user.role,payload.question,payload.mode,payload.project_id,payload.query_id)
        except PermissionError: raise HTTPException(403,'沒有資料分析權限') from None
        except ValueError: raise HTTPException(422,'不支援此查詢') from None
    log_audit(db,current,'ai.query',payload={'mode':payload.mode,'project_id':payload.project_id,'kind':result['kind'],'source_count':len(result['sources']),'query_id':result['analysis']['query_id'] if result['analysis'] else None})
    db.commit()
    return result


@router.get('/documents/{document_id}')
def document(document_id:str,current:CurrentUser=Depends(require_session)):
    with closing(connection(current)) as db:
        row=db.execute('SELECT * FROM documents WHERE document_id=? AND EXISTS (SELECT 1 FROM json_each(roles) WHERE value=?)',(document_id,current.user.role)).fetchone()
        if row is None: raise HTTPException(404,'找不到文件')
        metadata=json.loads(row['metadata'])
        return dict(document_id=row['document_id'],title=row['title'],text=row['body'],project_id=row['project_id'],version=metadata['version'],is_current=metadata['is_current'])


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
