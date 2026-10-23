"""Launch the packaged local app and open its browser UI."""
import argparse
import sys
import threading
import webbrowser
from runtime_paths import DATA_ROOT

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=5056)
parser.add_argument('--no-browser', action='store_true')
args = parser.parse_args()
(DATA_ROOT / 'data').mkdir(exist_ok=True)
log = open(DATA_ROOT / 'data' / 'exe.log', 'a', encoding='utf-8', buffering=1)
sys.stdout = log
sys.stderr = log
from app import app, connection
from werkzeug.serving import make_server

with connection() as db:
 db.execute("UPDATE runs SET status='interrupted',error='App restarted; start a new check.' WHERE status='running'")
server = make_server('127.0.0.1', args.port, app, threaded=True)
if not args.no_browser:
 threading.Timer(0.5, lambda: webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
try:
 server.serve_forever()
finally:
 server.server_close()
