"""Publish the local trial on the internet through Tailscale Funnel, or take it down.

    python deploy/public_trial.py          wait for Docker and Tailscale, start, publish, check
    python deploy/public_trial.py --stop   take the Funnel down, then restart on loopback only

開機自動啟動-公開試用.bat and 停止公開試用.bat in the repo root only call this file: cmd.exe reads
batch files in the console code page (950 here), so every Chinese message lives here instead.
Data is never reset and nothing is seeded. Docker keeps the stack running after the window closes.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import start as trial  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# Funnel only serves 443, 8443 and 10000; on this machine the first two belong to other projects.
FUNNEL_PORT = 10000
PUBLIC_TARGET = f'http://127.0.0.1:{trial.PUBLIC_WEB_PORT}'
PROGRAM_FILES = Path(os.environ.get('ProgramFiles', r'C:\Program Files'))
TAILSCALE = PROGRAM_FILES / 'Tailscale' / 'tailscale.exe'
DOCKER_DESKTOP = PROGRAM_FILES / 'Docker' / 'Docker' / 'Docker Desktop.exe'
LINE = '=' * 64


def say(message=''):
    print(message, flush=True)


def pause(seconds):
    time.sleep(seconds)


def command(args, timeout):
    """Run a CLI once: (returncode, stdout), or (None, '') when it is missing or hangs."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None, ''
    return result.returncode, result.stdout


def tailscale(*args, timeout=15):
    # tailscale.exe can block forever while tailscaled is not answering, so every call is bounded.
    return command([str(TAILSCALE), *args], timeout)


def docker_ready():
    return command(['docker', 'info', '--format', '{{.ServerVersion}}'], 30)[0] == 0


def wait_for_docker(timeout_s=300):
    """Right after logon Docker Desktop may still be starting; launch it once and wait for the engine."""
    deadline = time.monotonic() + timeout_s
    launched = False
    while not docker_ready():
        if not launched and DOCKER_DESKTOP.exists():
            launched = True
            try:
                subprocess.Popen([str(DOCKER_DESKTOP)])
            except OSError:
                pass
        if time.monotonic() >= deadline:
            return False
        pause(3)
    return True


def wait_for_tailscale(timeout_s=120):
    """This machine's tailnet name once Tailscale is connected, or None."""
    deadline = time.monotonic() + timeout_s
    while True:
        code, out = tailscale('status', '--json')
        try:
            status = json.loads(out) if code == 0 else {}
        except ValueError:
            status = {}
        status = status if isinstance(status, dict) else {}
        name = (status.get('Self') or {}).get('DNSName', '').rstrip('.')
        if status.get('BackendState') == 'Running' and name:
            return name
        if time.monotonic() >= deadline:
            return None
        pause(3)


def funnel_proxy():
    """Where Funnel port 10000 forwards to: '' when free, the proxy URL, or '?' for anything else."""
    code, out = tailscale('funnel', 'status', '--json')
    try:
        config = json.loads(out) if code == 0 and out.strip() else ({} if code == 0 else None)
    except ValueError:
        config = None
    if not isinstance(config, dict):
        raise RuntimeError('讀不到 Tailscale Funnel 設定（tailscale 沒有回應或尚未登入）。')
    port = str(FUNNEL_PORT)
    webs = [web for host, web in (config.get('Web') or {}).items() if host.rpartition(':')[2] == port]
    if not webs and port not in (config.get('TCP') or {}):
        return ''
    handlers = (webs[0].get('Handlers') or {}) if len(webs) == 1 else {}
    if list(handlers) == ['/']:
        return handlers['/'].get('Proxy') or '?'
    return '?'


def publish(target):
    current = funnel_proxy()
    if current not in ('', target):
        raise RuntimeError(f'Funnel {FUNNEL_PORT} 埠已經轉到別的服務（{current}），不覆蓋。'
                           '請先用 tailscale funnel status 確認。')
    code, _ = tailscale('funnel', '--bg', f'--https={FUNNEL_PORT}', target, timeout=60)
    if code != 0:
        raise RuntimeError('Tailscale Funnel 發布失敗；請確認這台電腦在 tailnet 有 Funnel 權限。')


def unpublish(target):
    """Turn Funnel port 10000 off only when it forwards to ProjectFlow; True when it was turned off."""
    if funnel_proxy() != target:
        return False
    code, _ = tailscale('funnel', f'--https={FUNNEL_PORT}', 'off', timeout=30)
    if code != 0:
        raise RuntimeError('Tailscale Funnel 關閉失敗。')
    return True


def http_status(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (OSError, ValueError):
        return None


def wait_for_status(url, attempts):
    """A newly published Funnel port may need a few seconds for its certificate."""
    for attempt in range(attempts):
        code = http_status(url, timeout=20)
        if code == 200 or attempt == attempts - 1:
            return code
        pause(5)


def verdict(code):
    if code == 200:
        return '200 OK'
    return '連不上' if code is None else f'異常（HTTP {code}）'


def up():
    say(LINE)
    say(f" ProjectFlow 公開試用 — 啟動   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    say(LINE)
    say('[1/4] Docker')
    if not wait_for_docker():
        say('      5 分鐘內沒等到 Docker 就緒。請開啟 Docker Desktop 後再執行一次。')
        return 1
    say('      已就緒。')
    say('[2/4] 啟動 ProjectFlow（保留資料、不 seed；映像有變時會重建，需要幾分鐘）')
    try:
        result = trial.start(ROOT, public=True)
    except (RuntimeError, OSError):
        say('      啟動失敗。可以先執行 python deploy/start.py，確認本機模式能不能啟動。')
        return 1
    say(f"      本機 {result['web_url']} 已就緒。")
    say(f'[3/4] Tailscale Funnel {FUNNEL_PORT} 埠')
    name = wait_for_tailscale()
    if not name:
        say('      Tailscale 未安裝、未登入，或 2 分鐘內沒有連線；目前只有本機能用。')
        return 1
    try:
        publish(result['public_target'])
    except RuntimeError as error:
        say(f'      {error}')
        return 1
    public = f'https://{name}:{FUNNEL_PORT}'
    say(f'      已發布 {public}')
    say('[4/4] 健檢')
    local = http_status(result['web_url'] + '/api/health/ready')
    remote = wait_for_status(public + '/api/health/ready', attempts=6)
    say()
    say(LINE)
    say(f"   本機   {result['web_url']:<44} {verdict(local)}")
    say(f'   公開   {public:<44} {verdict(remote)}')
    say()
    say('   把「公開」網址給測試者。登入要填公司代碼、帳號、密碼，')
    say('   見 docs/formal-development.md 的「網際網路試用」。')
    say('   關掉這個視窗不會停止服務；要停止公開，執行 停止公開試用.bat。')
    say(LINE)
    return 0 if local == 200 and remote == 200 else 1


def down():
    say(f'[1/2] 關閉 Funnel {FUNNEL_PORT} 埠')
    closed = True
    try:
        removed = unpublish(PUBLIC_TARGET)
        say('      已關閉。' if removed else '      沒有指向 ProjectFlow，不需要關。')
    except RuntimeError as error:
        closed = False
        say(f'      {error}下一步拿掉公開入口後，公開網址也會失效。')
    say('[2/2] 以本機模式重啟（拿掉公開入口；保留資料）')
    if not docker_ready():
        say('      Docker 沒有在執行，ProjectFlow 目前沒有對外服務。')
        return 0 if closed else 1
    try:
        result = trial.start(ROOT)
    except (RuntimeError, OSError):
        say('      重啟失敗。可以執行 python deploy/start.py 重試。')
        return 1
    say(f"      現在只有本機 {result['web_url']} 能用。")
    return 0 if closed else 1


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--stop', action='store_true', help='Take the Funnel down and restart on loopback only.')
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    return down() if args.stop else up()


if __name__ == '__main__':
    raise SystemExit(main())
