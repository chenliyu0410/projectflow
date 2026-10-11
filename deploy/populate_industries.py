"""Append approved fictional datasets to five existing companies, all or nothing."""
import argparse
import json
from datetime import date
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import Base, get_engine
from populate_hemu import populate, AtomicSession

KEYS = {'food', 'electronics', 'events', 'software', 'construction'}


def validate(datasets):
    if set(datasets) != KEYS:
        raise ValueError('Expected exactly five approved company datasets')
    for key, data in datasets.items():
        if data['company']['key'] != key:
            raise ValueError('Company key mismatch')
        people = {p['key'] for p in data['people']}
        departments = {d['name'] for d in data['departments']}
        if len(people) != len(data['people']) or len(departments) != len(data['departments']):
            raise ValueError('Duplicate people or departments')
        if sum(d['count'] for d in data['departments']) != data['company']['employees']:
            raise ValueError('Headcount mismatch')
        for d in data['departments']:
            if d['head'] not in people or next(p for p in data['people'] if p['key'] == d['head'])['department'] != d['name']:
                raise ValueError('Department head mismatch')
        if any(p['department'] not in departments for p in data['people']):
            raise ValueError('Unknown department')
        refs = {(g['key'], r['code']) for g in data['groups'] for r in g['records']}
        if len(refs) != sum(len(g['records']) for g in data['groups']):
            raise ValueError('Duplicate record reference')
        for g in data['groups']:
            for r in g['records']:
                if any((link['group'], link['code']) not in refs for link in r['links']):
                    raise ValueError('Broken operational link')
        for project in data['projects']:
            if project['owner'] not in people:
                raise ValueError('Unknown project owner')
            tasks = [t for phase in project['phases'] for t in phase['tasks']]
            keys = {t['key'] for t in tasks}
            if len(keys) != len(tasks):
                raise ValueError('Duplicate task key')
            seen = set()
            for task in tasks:
                if task['owner'] not in people or not set(task['deps']) <= seen:
                    raise ValueError('Invalid owner or dependency ordering')
                if date.fromisoformat(task['start']) > date.fromisoformat(task['due']):
                    raise ValueError('Invalid dates')
                if task['state'] != 'todo' and task['start'] > data['company']['asOf']:
                    raise ValueError('Active task starts in future')
                seen.add(task['key'])


def populate_all(db, datasets):
    validate(datasets)
    return {key: populate(db, datasets[key], existing_company=True) for key in sorted(KEYS)}


def snapshot(db):
    return {t.name: [dict(r) for r in db.execute(select(t)).mappings()] for t in Base.metadata.sorted_tables}


def assert_preserved(before, after):
    for table, rows in before.items():
        actual = {json.dumps(r, sort_keys=True, default=str) for r in after[table]}
        if any(json.dumps(r, sort_keys=True, default=str) not in actual for r in rows):
            raise RuntimeError('Existing rows changed in ' + table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=Path(__file__).resolve().parents[1] / 'web/src/preview/industries.json')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with AtomicSession(get_engine()) as db:
        before = snapshot(db)
        results = populate_all(db, json.loads(args.data.read_text(encoding='utf-8')))
        assert_preserved(before, snapshot(db))
        if args.apply:
            Session.commit(db)
        else:
            db.rollback()
        print(json.dumps({'applied': args.apply, 'old_rows_preserved': True, 'companies': results}, ensure_ascii=False))
