"""本地预览：只提供公开网页文件，配置、源码及状态文件无法通过 HTTP 读取。"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
PUBLIC = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'),
          '/app.js': ('app.js', 'text/javascript'), '/schedules.json': ('schedules.json', 'application/json'),
          '/movies.ics': ('movies.ics', 'text/calendar')}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        item = PUBLIC.get(urlsplit(self.path).path)
        if item is None or not (ROOT / item[0]).is_file():
            self.send_error(404)
            return
        content = (ROOT / item[0]).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', item[1] + '; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(content)


if __name__ == '__main__':
    print('Open http://127.0.0.1:8000/ (Ctrl+C to stop)', flush=True)
    try:
        ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
