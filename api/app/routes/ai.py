from contextlib import closing
from datetime import timezone
import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.audit import log_audit
from app.ai import store, service, model, starter, formal_index, vectors, policy, masking
from app.models import AuditLog, Document, DocumentVersion, Node, Project

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
    result['vectors'] = dict(enabled=vectors.available(current.organization.key) and dataset != 'dataset-v1', model=vectors.model_name() if dataset != 'dataset-v1' else '')
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


class Classification(BaseModel):
    model_config=ConfigDict(extra='forbid')
    scope: Literal['company','project','node','document']
    id: str | None=Field(default=None,max_length=120)
    level: Literal['public','internal','confidential','inherit']


class AIPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mode: Literal['local_only','mixed','cloud_allowed']


class MaskSample(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text: str=Field(min_length=1,max_length=4000)


def utc(value):
    # SQLite returns naive datetimes; they were written in UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def governance_admin(db,current):
    formal_index.require_enabled(db)
    if current.user.role!='admin': raise HTTPException(403,'只有管理者可管理AI政策與分級')


def classification_tree(db,current,value):
    org=current.organization.id
    projects=list(db.scalars(select(Project).where(Project.organization_id==org).order_by(Project.title)))
    # Deleted ancestors still pass their level down (as enforced by the index); only live nodes are listed.
    all_nodes={n.id:n for n in db.scalars(select(Node).where(Node.organization_id==org))}
    nodes={i:n for i,n in all_nodes.items() if n.deleted_at is None}
    levels=policy.Resolver(value,all_nodes)
    def item(scope,row_id,title,effective,inherited,**extra):
        return dict(scope=scope,id=row_id,title=title,own=value['overrides'].get(f'{scope}:{row_id}'),effective=effective,inherited=inherited,**extra)
    return dict(
        projects=[item('project',p.id,p.title,levels.project(p.id),value['company']) for p in projects],
        nodes=[item('node',n.id,n.title,levels.node(n.id),levels.inherited('node',n.id,project_id=n.project_id,parent_id=n.parent_id if n.parent_id in all_nodes else None),project_id=n.project_id,parent_id=n.parent_id) for n in nodes.values()][:2000],
        documents=[item('document',d.id,name,levels.document(d.id,d.node_id,d.project_id),levels.inherited('document',d.id,node_id=d.node_id,project_id=d.project_id),project_id=d.project_id,node_id=d.node_id)
                   for d,name in db.execute(select(Document,DocumentVersion.filename).join(DocumentVersion,(DocumentVersion.document_id==Document.id)&(DocumentVersion.version==Document.current_version))
                                           .where(Document.organization_id==org).order_by(DocumentVersion.filename))])


@router.get('/governance')
def governance(request:Request,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    governance_admin(db,current)
    value=policy.load(current.organization.key)
    audits=db.scalars(select(AuditLog).where(AuditLog.organization_id==current.organization.id,AuditLog.action.like('ai.%')).order_by(AuditLog.created_at.desc()).limit(30))
    # Only routing metadata: audit payloads never hold question text, document text or mask mappings.
    keys=('dataset','mode','kind','source_count','scope','level','from','to')
    recent=[dict(action=a.action,created_at=utc(a.created_at).isoformat(),**{k:a.payload.get(k) for k in keys if isinstance(a.payload,dict) and k in a.payload},
                 classification=(a.payload.get('gateway') or {}).get('classification') if isinstance(a.payload,dict) else None,
                 cloud=(a.payload.get('gateway') or {}).get('cloud') if isinstance(a.payload,dict) else None) for a in audits]
    return dict(mode=value['mode'],company=value['company'],cloud_provider=None,can_set_policy=request.url.hostname in {'localhost','127.0.0.1','::1'},
                recent=recent,**classification_tree(db,current,value))


def save_with_audit(db,current,value,previous,action,payload):
    # Save the file first; if the audit row cannot be committed, put the old file back.
    policy.save(current.organization.key,value)
    try:
        log_audit(db,current,action,payload=payload)
        db.commit()
    except Exception:
        db.rollback()
        policy.save(current.organization.key,previous)
        raise


@router.put('/classification')
def set_classification(payload:Classification,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    governance_admin(db,current)
    with policy.locked(current.organization.key):
        return change_classification(payload,current,db)


def change_classification(payload,current,db):
    value=policy.load(current.organization.key)
    original=json.loads(json.dumps(value))
    org=current.organization.id
    if payload.scope=='company':
        if payload.level=='inherit': raise HTTPException(422,'公司預設必須指定等級')
        previous,value['company']=value['company'],payload.level
    else:
        model_type={'project':Project,'node':Node,'document':Document}[payload.scope]
        row=db.get(model_type,payload.id or '')
        if row is None or row.organization_id!=org: raise HTTPException(404,'找不到分級對象')
        nodes={n.id:n for n in db.scalars(select(Node).where(Node.organization_id==org))}
        inherited=policy.Resolver(value,nodes).inherited(payload.scope,row.id,node_id=getattr(row,'node_id',None),project_id=getattr(row,'project_id',None),parent_id=getattr(row,'parent_id',None))
        key=f'{payload.scope}:{row.id}'
        previous=value['overrides'].get(key)
        if payload.level=='inherit':
            value['overrides'].pop(key,None)
        elif policy.LEVELS[payload.level]<policy.LEVELS[inherited]:
            raise HTTPException(422,'只能設定得比上層更嚴格；要放寬請調整上層等級')
        else:
            value['overrides'][key]=payload.level
    save_with_audit(db,current,value,original,'ai.classification.set',{'scope':payload.scope,'from':previous,'to':payload.level})
    return {'ok':True}


@router.put('/policy')
def set_policy(payload:AIPolicy,request:Request,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    governance_admin(db,current)
    local_admin(request,current)
    with policy.locked(current.organization.key):
        value=policy.load(current.organization.key)
        original=dict(value)
        previous,value['mode']=value['mode'],payload.mode
        save_with_audit(db,current,value,original,'ai.policy.set',{'from':previous,'to':payload.mode})
    return {'ok':True}


@router.post('/mask-preview')
def mask_preview(payload:MaskSample,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    governance_admin(db,current)
    masker=masking.Masker(formal_index.partner_names(db,current))
    # Local only: no model call, nothing stored; the placeholder mapping is not returned.
    return dict(masked=masker.mask(payload.text),counts=masker.counts)
