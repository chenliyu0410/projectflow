import argparse
import json
from app.ai.store import import_pack, root

def main():
    p=argparse.ArgumentParser(description='Import synthetic AI data without modifying operational records')
    p.add_argument('pack')
    p.add_argument('--destination',default=str(root()))
    p.add_argument('--dataset', choices=['dataset-v1', 'starter-v1'], default='dataset-v1')
    args=p.parse_args()
    if args.dataset == 'starter-v1':
        from app.ai.starter import import_starter
        result = import_starter(args.pack, args.destination)
    else:
        result = import_pack(args.pack,args.destination)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
