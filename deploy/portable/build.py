"""Assemble the portable demo package (Windows x64). Run from the repo with any Python 3.12+:

    python deploy/portable/build.py --gguf <Qwen3-4B-Instruct-2507-Q4_K_M.gguf> --bge-store <Ollama models dir with bge-m3>
        --ocr-models <dir> [--out ../output/portable/ProjectFlow-Portable-YYYYMMDD] [--zip]

Downloads only python-build-standalone 3.12 (through uv) and the locked Python packages. Everything else is
copied from this computer and verified. The output folder must not exist yet.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PYTHON_VERSION = '3.12.14'
MODEL_PORT = 11437
CHAT_MODEL = 'pf-qwen3-rag:latest'
QWEN_SHA256 = '2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e'
# The acceptance runs used this exact Modelfile; the raw prompt template matters (the API sends a finished prompt).
MODELFILE = 'FROM {gguf}\nTEMPLATE {{{{ .Prompt }}}}\nPARAMETER num_ctx 8192\nPARAMETER temperature 0\n'
OLLAMA_SKIP = {'ollama app.exe', 'app.ico', 'unins000.dat', 'unins000.exe', 'unins000.msg'}  # tray app auto-updates
VC_RUNTIME = ('msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll',
              'concrt140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'vcruntime140_threads.dll')
# Private keys and common API key formats; demo passwords (demo-<user>) are public by design.
SECRET = re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b|\bghp_[A-Za-z0-9]{36}\b')
STORED = ('.gguf', '.onnx', '.dll', '.exe', '.pyd', '.so', '.png', '.pdf', '.zip')


def step(text):
    print(f'\n== {text}', flush=True)


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def python_runtime(target):
    work = target.parent / '_python'
    run('uv', 'python', 'install', PYTHON_VERSION, '--install-dir', work, '--no-bin')
    source = next(p.parent for p in work.glob('*/python.exe'))
    shutil.copytree(source, target)
    shutil.rmtree(work)
    exe = target / 'python.exe'
    # The standalone build is marked externally managed; this copy belongs to the package alone.
    run('uv', 'pip', 'install', '--python', exe, '--break-system-packages', '--strict',
        '-r', REPO / 'api' / 'requirements.lock', '-r', REPO / 'api' / 'requirements-ocr.lock')
    # Console-script launchers embed this computer's python.exe path; the package never uses them.
    for launcher in (target / 'Scripts').glob('*.exe'):
        launcher.unlink()
    # onnxruntime (OCR) needs the C++ runtime, which a clean Windows may lack. Microsoft allows app-local copies;
    # python.exe's folder is searched before System32, so the package always loads these.
    system = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
    for name in VC_RUNTIME:
        shutil.copy2(system / name, target / name)
    check = ('import ctypes, ctypes.wintypes, onnxruntime, rapidocr_onnxruntime\n'
             'k = ctypes.WinDLL("kernel32"); k.GetModuleFileNameW.argtypes = [ctypes.wintypes.HMODULE, ctypes.c_wchar_p, ctypes.c_uint]\n'
             'k.GetModuleHandleW.restype = ctypes.wintypes.HMODULE\n'
             'buf = ctypes.create_unicode_buffer(1024); k.GetModuleFileNameW(k.GetModuleHandleW("msvcp140.dll"), buf, 1024); print(buf.value)')
    loaded = subprocess.run([str(exe), '-E', '-s', '-c', check], capture_output=True, text=True, check=True).stdout.strip()
    if Path(loaded).parent.resolve() != target.resolve():
        raise RuntimeError(f'OCR loads the C++ runtime from {loaded}, not from the package')
    return exe


def clean_caches(package):
    """Bytecode written while building records absolute source paths; the target computer rebuilds it."""
    for cache in package.rglob('__pycache__'):
        shutil.rmtree(cache, ignore_errors=True)


def web_build(target):
    web = REPO / 'web'
    node = REPO.parent / 'output' / 'rag-starter-node' / 'node_modules' / 'node' / 'bin' / 'node.exe'
    run(node, 'node_modules/typescript/bin/tsc', '--noEmit', cwd=web)
    run(node, 'node_modules/vite/bin/vite.js', 'build', '--outDir', target, '--emptyOutDir', cwd=web)


def copy_app(target):
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache', 'tests')
    shutil.copytree(REPO / 'api' / 'app', target / 'app', ignore=ignore)
    shutil.copytree(REPO / 'api' / 'alembic', target / 'alembic', ignore=ignore)
    shutil.copy2(REPO / 'api' / 'alembic.ini', target)
    shutil.copy2(HERE / 'serve.py', target)


class Ollama:
    """The package's own Ollama on the package port, storing models inside the package."""

    def __init__(self, exe, models):
        env = {k: v for k, v in os.environ.items() if not k.startswith('OLLAMA_')}
        env.update(OLLAMA_HOST=f'127.0.0.1:{MODEL_PORT}', OLLAMA_MODELS=str(models), OLLAMA_NO_CLOUD='1', OLLAMA_NOPRUNE='1')
        self.exe, self.env = exe, env

    def __enter__(self):
        self.process = subprocess.Popen([str(self.exe), 'serve'], env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                self.tags()
                return self
            except OSError:
                time.sleep(0.5)
        raise RuntimeError('Package Ollama did not start')

    def tags(self):
        with urllib.request.urlopen(f'http://127.0.0.1:{MODEL_PORT}/api/tags', timeout=5) as response:
            return {m['name']: m['digest'] for m in json.load(response)['models']}

    def create(self, name, modelfile):
        run(self.exe, 'create', name, '-f', modelfile, env=self.env)

    def __exit__(self, *exc):
        # `serve` starts runner children; stop everything running from the package's Ollama folder.
        self.process.terminate()
        self.process.wait(30)
        prefix = str(self.exe.parent).lower()
        subprocess.run(['powershell', '-NoProfile', '-Command',
            "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.ToLower().StartsWith('%s') } |"
            " ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" % prefix.replace("'", "''")], check=False)


def models(package, gguf, bge_store, ollama_dir):
    store = package / 'models' / 'ollama'
    manifest = bge_store / 'manifests' / 'registry.ollama.ai' / 'library' / 'bge-m3' / 'latest'
    body = json.loads(manifest.read_text(encoding='utf-8'))
    for layer in [body['config'], *body['layers']]:
        name = layer['digest'].replace(':', '-')
        (store / 'blobs').mkdir(parents=True, exist_ok=True)
        shutil.copy2(bge_store / 'blobs' / name, store / 'blobs' / name)
        if sha256(store / 'blobs' / name) != layer['digest'].split(':')[1]:
            raise RuntimeError(f'bge-m3 blob {name} is damaged')
    target = store / manifest.relative_to(bge_store)
    target.parent.mkdir(parents=True)
    shutil.copy2(manifest, target)
    if sha256(gguf) != QWEN_SHA256:
        raise RuntimeError('The GGUF is not the Qwen3-4B-Instruct-2507 Q4_K_M file used in acceptance')
    modelfile = package / '_Modelfile'
    modelfile.write_text(MODELFILE.format(gguf=gguf), encoding='utf-8')
    ollama = Ollama(package / 'runtime' / 'ollama' / 'ollama.exe', store)
    with ollama:
        ollama.create(CHAT_MODEL, modelfile)
        tags = ollama.tags()
    modelfile.unlink()
    missing = {CHAT_MODEL, 'bge-m3:latest'} - set(tags)
    if missing:
        raise RuntimeError(f'Models missing after import: {missing}')
    return tags


def seed(package, python):
    ollama = Ollama(package / 'runtime' / 'ollama' / 'ollama.exe', package / 'models' / 'ollama')
    with ollama:
        run(python, '-E', '-s', '-X', 'utf8', HERE / 'build_seed.py', '--out', package / 'seed',
            '--ollama', f'http://127.0.0.1:{MODEL_PORT}', '--ocr-models', package / 'models' / 'ocr')
    return json.loads((package / 'seed' / 'seed.json').read_text(encoding='utf-8'))


def scan(package):
    """Nothing tied to this computer or the repo may ship."""
    problems = []
    texts = set()
    for base in (str(REPO), str(Path.home())):
        for form in (base, base.replace('\\', '/'), base.replace('\\', '\\\\')):
            texts |= {form, form.lower()}
    markers = {t.encode() for t in texts} | {t.encode('utf-16-le') for t in texts}
    for path in package.rglob('*'):
        relative = path.relative_to(package).as_posix()
        if path.name == '.git' or path.name.startswith('.env') or path.suffix == '.env' or 'gemma' in relative.lower():
            problems.append(f'不應打包：{relative}')
        # Model weights and GPU libraries are the only files this large; they are copied, never written here.
        if path.is_file() and path.stat().st_size < 50 << 20:
            data = path.read_bytes()
            if any(m in data for m in markers):
                problems.append(f'含本機路徑：{relative}')
            if SECRET.search(data):
                problems.append(f'疑似金鑰：{relative}')
    return problems


def archive(package):
    target = package.with_suffix('.zip')
    with zipfile.ZipFile(target, 'w', allowZip64=True) as bundle:
        for path in sorted(package.rglob('*')):
            if path.is_file():
                kind = zipfile.ZIP_STORED if path.suffix.lower() in STORED or 'blobs' in path.parts else zipfile.ZIP_DEFLATED
                bundle.write(path, Path(package.name) / path.relative_to(package), compress_type=kind)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--gguf', type=Path, required=True)
    parser.add_argument('--bge-store', type=Path, required=True, help='An Ollama models folder that has bge-m3')
    parser.add_argument('--ocr-models', type=Path, required=True)
    parser.add_argument('--ollama-dir', type=Path, default=Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama')
    parser.add_argument('--out', type=Path, default=REPO.parent / 'output' / 'portable' / f"ProjectFlow-Portable-{datetime.date.today():%Y%m%d}")
    parser.add_argument('--zip', action='store_true')
    args = parser.parse_args()
    package = args.out.resolve()
    if package.exists():
        parser.error(f'{package} 已存在；每次打包請用新的資料夾')
    package.mkdir(parents=True)

    step('Python 執行環境'); python = python_runtime(package / 'runtime' / 'python')
    step('網頁'); web_build(package / 'app' / 'web')
    step('後端程式'); copy_app(package / 'app')
    step('Ollama')
    # Installer shortcuts (*.lnk) point into this user's profile.
    shutil.copytree(args.ollama_dir, package / 'runtime' / 'ollama',
                    ignore=lambda d, names: [n for n in names if n in OLLAMA_SKIP or n.lower().endswith('.lnk')])
    version = subprocess.run([str(package / 'runtime' / 'ollama' / 'ollama.exe'), '--version'], capture_output=True, text=True).stdout.strip()
    step('模型'); tags = models(package, args.gguf.resolve(), args.bge_store.resolve(), args.ollama_dir)
    shutil.copytree(args.ocr_models, package / 'models' / 'ocr')
    step('乾淨展示資料'); seeded = seed(package, python)
    step('啟動腳本與說明')
    shutil.copytree(HERE / 'launcher', package / 'runtime' / 'launcher', ignore=shutil.ignore_patterns('*.bat'))
    for bat in (HERE / 'launcher').glob('*.bat'):
        shutil.copy2(bat, package / bat.name)
    shutil.copy2(HERE / '使用說明.txt', package)
    shutil.copytree(HERE / 'licenses', package / 'licenses')
    step('檢查')
    clean_caches(package)
    problems = scan(package)
    info = {'built_at': datetime.datetime.now().isoformat(timespec='seconds'), 'commit': subprocess.run(
        ['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, capture_output=True, text=True).stdout.strip(),
        'python': PYTHON_VERSION, 'ollama': version, 'models': tags, 'seed': seeded, 'problems': problems}
    (package / 'build.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=2))
    if problems:
        raise SystemExit('打包檢查沒通過，見 build.json')
    if args.zip:
        step('壓縮'); print(archive(package))


if __name__ == '__main__':
    main()
