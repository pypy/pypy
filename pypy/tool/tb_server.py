from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import threading
import sys

global content
content = ''
server_thread = None

class TBRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/quit':
            global server_thread
            server_thread = None
            raise SystemExit
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        pass

class TBServer(HTTPServer):
    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (SystemExit, KeyboardInterrupt)):
            raise
        else:
            HTTPServer.handle_error(self, request, client_address)

def serve():
    port = 8080
    while 1:
        try:
            server = TBServer(('localhost', port), TBRequestHandler)
        except socket.error:
            port += 1
            continue
        else:
            break
    global server_port
    server_port = port
    print "serving on", port
    server.serve_forever()

def start():
    global server_thread
    server_thread = threading.Thread(target=serve)
    server_thread.start()
    return server_thread

def stop():
    if server_thread is None:
        return
    import urllib2
    try:
        urllib2.urlopen('http://localhost:%s/quit'%(server_port,))
    except urllib2.HTTPError:
        pass

def wait_until_interrupt():
    if server_thread is None:
        return
    import signal
    try:
        signal.pause()
    except KeyboardInterrupt:
        stop()

def publish_tb(tb):
    import traceback
    s = traceback.format_tb(tb)
    global content
    content = ''.join(s)

if __name__ == "__main__":
    t = main()
    wait_until_interrupt()
