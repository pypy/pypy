"""
A socket server for GraphPages.
"""

import autopath, sys, thread, struct, marshal


def run_server(homepage, port=8888, quiet=False, background=False):
    import socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('', port))
    server_sock.listen(5)
    if not quiet:
        print >> sys.stderr, 'Accepting connexions on port %d...' % port
    def accept_connexions():
        while True:
            conn, addr = server_sock.accept()
            if not quiet:
                print >> sys.stderr, 'Connected by %r.' % (addr,)
            thread.start_new_thread(serve_connexion, (conn, homepage))
    if background:
        thread.start_new_thread(accept_connexions, ())
    else:
        accept_connexions()


def recv_all(s, count):
    buf = ''
    while len(buf) < count:
        data = s.recv(count - len(buf))
        if not data:
            raise SystemExit   # thread exit, rather
        buf += data
    return buf

def recv_msg(s):
    hdr_size = struct.calcsize("!i")
    msg_size, = struct.unpack("!i", recv_all(s, hdr_size))
    msg = recv_all(s, msg_size)
    return marshal.loads(msg)

def send_msg(s, msg):
    data = marshal.dumps(msg)
    s.sendall(struct.pack("!i", len(data)) + data)


def serve_connexion(s, homepage):
    pages = {0: homepage}
    while True:
        key, link = recv_msg(s)
        page = pages[key]
        if link is not None:
            try:
                page = page.content().followlink(link)
                key = len(pages)
            except KeyError:
                page = MissingPage()
                key = -1
            pages[key] = page
        page = page.content()
        reply = {
            'key': key,
            'dot': page.source,
            'links': page.links,
            }
        send_msg(s, reply)


class MissingPage:
    links  = {}
    source = '''
digraph error {
msg [shape="box", label="Error: a link has gone missing.", color="black", fillcolor="red", style="filled"];
}
'''
    def content(self):
        return self
