"""Run the dedicated-PostgreSQL API tests, each stage on a brand-new database.

Usage (from the repo root): PG_ADMIN_URL=postgresql://user@host:port/db python .github/scripts/run_postgresql_tests.py
"""

import ast
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / 'api' / 'tests'
MIGRATIONS = 'api/tests/test_migrations.py'
P2A_TEST = 'test_postgresql_date_migration_preserves_existing_rows'

# 與 deploy/verify.py 的階段一致；migration 測試會從早期 revision 升級，必須各自在全新資料庫上跑。
STAGES = [
    ('P2a migration', 'p2a_migration_', 'P2A_MIGRATION_TEST_URL', f'{MIGRATIONS}::{P2A_TEST}'),
    ('P2b migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_p2b_postgresql_migration_constraints_and_parallel_pending'),
    ('P2c migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_p2c_postgresql_migration_and_dependency_constraints'),
    ('TP-A migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_tp_a_postgresql_migration_preserves_nodes'),
    ('TP-B migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_tp_b_postgresql_migration_preserves_nodes'),
    ('TP-C migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_tp_c_postgresql_migration_preserves_nodes'),
    ('TP-D migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_tp_d_postgresql_migration_preserves_data'),
    ('TP-E migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_tp_e_postgresql_migration_preserves_templates'),
    ('TP-F migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_tp_f_postgresql_migration_preserves_data'),
    ('TP-G migration', 'p2b_test_', 'P2B_TEST_DATABASE_URL', f'{MIGRATIONS}::test_tp_g_postgresql_migration_and_field_submit_race'),
    ('API races', 'p2b_test_', 'P2B_TEST_DATABASE_URL', 'api/tests/test_collaboration_postgresql.py'),
]


def postgresql_migration_tests() -> set[str]:
    tree = ast.parse((ROOT / MIGRATIONS).read_text(encoding='utf-8'))
    # 名稱含 `postgresql_` 的才是需要專用資料庫的測試；`..._for_postgresql` 只檢查 URL 轉換。
    return {node.name for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_') and 'postgresql_' in node.name}


def check_stages_cover_tests() -> None:
    listed = {target.split('::', 1)[1] for _, _, _, target in STAGES if '::' in target}
    missing = postgresql_migration_tests() - listed
    if missing:
        # 新增的 PG 測試若沒排進階段，只會在一般 job 被 skip，這裡直接擋下來。
        raise SystemExit('PostgreSQL tests missing from STAGES: ' + ', '.join(sorted(missing)))


def run_stage(admin_url: str, label: str, prefix: str, variable: str, target: str, plugin_dir: str) -> int:
    name = prefix + uuid.uuid4().hex
    assert re.fullmatch(r'(p2a_migration|p2b_test)_[0-9a-f]{32}', name)
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    url = make_url(admin_url).set(database=name).render_as_string(hide_password=False)
    try:
        with tempfile.TemporaryDirectory(prefix='pf-attachments-') as attachments:
            environment = {**os.environ, 'DATABASE_URL': url, variable: url,
                           'PF_ACCEPTANCE_MODE': 'true', 'PF_ATTACHMENT_ROOT': attachments,
                           'PYTHONPATH': os.pathsep.join(filter(None, [plugin_dir, os.environ.get('PYTHONPATH')]))}
            for other in ('P2A_MIGRATION_TEST_URL', 'P2B_TEST_DATABASE_URL'):
                if other != variable:
                    environment.pop(other, None)
            print(f'::group::PostgreSQL {label} ({name})', flush=True)
            result = subprocess.run([sys.executable, '-m', 'pytest', target, '-q', '-p', 'no_skip'],
                                    cwd=ROOT, env=environment, check=False, timeout=900)
            print('::endgroup::', flush=True)
            return result.returncode
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))


def main() -> int:
    admin_url = os.environ.get('PG_ADMIN_URL')
    if not admin_url:
        print('Set PG_ADMIN_URL to a PostgreSQL server that is only used for tests.', flush=True)
        return 2
    check_stages_cover_tests()
    plugin_dir = str(Path(__file__).resolve().parent)
    failed = []
    for label, prefix, variable, target in STAGES:
        if run_stage(admin_url, label, prefix, variable, target, plugin_dir):
            failed.append(label)
    if failed:
        print('Failed stages: ' + ', '.join(failed), flush=True)
        return 1
    print(f'All {len(STAGES)} PostgreSQL stages passed.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
