"""Run the original fixed 20 or separate conversation cases in isolated synthetic data."""
import argparse,importlib.util,json,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True,help='New output directory; existing directories are refused')
parser.add_argument('--followup',action='store_true',help='Run isolated single/renamed/ambiguous followups instead of the fixed 20')
args=parser.parse_args()
OUT=args.output;OUT.mkdir(parents=True,exist_ok=False)
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
sys.path.insert(0,str(ROOT/'api'));os.environ['PF_RAG_AUTO_INDEX']='false'
spec=importlib.util.spec_from_file_location('runner',ROOT/'artifacts/rag-demo-data-2026-10-21/run_demo.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
from app.rag import provider
request=provider._request;checked=runner.checked;grade=runner.grade
raw=[];results=[];responses=[];client_ref=None;project_id=None
def save(name,value):
 (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def capture(config,path,payload):
 value=request(config,path,payload)
 if path=='/api/chat':raw.append({'request':payload,'response':value});save('model-responses.json',raw)
 return value
def observe(client,method,path,**kw):
 global client_ref,project_id
 value=checked(client,method,path,**kw)
 if path=='/rag/ask':
  client_ref=client;project_id=kw['json']['project_id']
  responses.append({'request':kw['json'],'response':value});save('full-responses.json',responses)
 return value
def ask(label,scope,question,history=None):
 payload={'scope':scope,'question':question,'history':history or []}
 value=checked(client_ref,'POST','/rag/ask',json=payload)
 results.append({'case':label,'request':payload,'response':value});save('results.json',results)
 print(json.dumps({'case':label,'engine':value['engine'],'code':value.get('code'),'answer':value['answer']},ensure_ascii=False),flush=True)
 return value
def extra(case,result,documents):
 scope={'kind':'project','project_id':project_id}
 first=ask('single_subject',scope,'那需要誰簽核？',[{'question':case['question'],'query_id':result['query_id']}])
 multi_question='G2 與包裝版面核准，各由誰負責？'
 multi=ask('two_subjects_context',scope,multi_question)
 ambiguous=ask('two_subjects_followup',scope,'那需要誰簽核？',[{'question':multi_question,'query_id':multi['query_id']}])
 project=checked(client_ref,'POST','/projects',json={'title':'完全虛構：追問改名驗證'})
 manifest=json.loads((runner.HERE/'manifest.json').read_text(encoding='utf-8'))
 item=next(d for d in manifest['documents'] if d['key']=='04')
 content=(runner.HERE/item['path']).read_text(encoding='utf-8').replace('G2','K7').replace('陳奕安','葉子庭')
 doc=checked(client_ref,'POST',f"/projects/{project['id']}/documents",params={'filename':'改名關卡.txt'},headers={'Content-Type':'application/octet-stream'},content=content.encode())
 index=checked(client_ref,'POST',f"/rag/documents/{doc['document_id']}/index");assert index['state']=='ready'
 renamed_scope={'kind':'project','project_id':project['id']};question='K7 要具備什麼才能通過？'
 renamed_context=ask('renamed_context',renamed_scope,question)
 renamed=ask('renamed_followup',renamed_scope,'那需要誰簽核？',[{'question':question,'query_id':renamed_context['query_id']}])
 checks={'single_subject':first['engine']=='model' and '陳奕安' in first['answer'] and bool(first['citations']),
         'two_subjects_clarifies':ambiguous.get('code')=='clarification_required' and not ambiguous['citations'],
         'renamed_subject':renamed['engine']=='model' and '葉子庭' in renamed['answer'] and bool(renamed['citations'])}
 save('checks.json',checks)
 return grade(case,result,documents)
provider._request=capture;runner.checked=observe;runner.grade=extra if args.followup else grade
runner.evaluate(OUT/'evaluation.json',case_ids=['Q06'] if args.followup else None,generation_model='qwen2.5-coder:7b')
assert not args.followup or all(json.loads((OUT/'checks.json').read_text()).values()),'Conversation acceptance failed; inspect checks.json'
