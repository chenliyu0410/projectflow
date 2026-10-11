import argparse
import json
from app.ai.store import import_pack, root

def main():
    p=argparse.ArgumentParser(description='Import synthetic AI data without modifying operational records')
    p.add_argument('pack')
    p.add_argument('--destination',default=str(root()))
    args=p.parse_args()
    print(json.dumps(import_pack(args.pack,args.destination),ensure_ascii=False))

if __name__=='__main__': main()
