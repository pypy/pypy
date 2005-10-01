#! /usr/bin/env python
"""
Client for a graph server (either in-process or over a socket).
"""

import autopath
from pypy.translator.tool.pygame.drawgraph import GraphLayout
from pypy.translator.tool.pygame.drawgraph import display_async_cmd
from pypy.translator.tool.pygame.drawgraph import display_async_quit
from pypy.translator.tool.pygame.drawgraph import wait_for_async_cmd
from pypy.translator.tool.graphserver import MissingPage, portutil
from pypy.tool.udir import udir
import py


DOT_FILE   = udir.join('graph.dot')
PLAIN_FILE = udir.join('graph.plain')

def dot2plain(dotfile, plainfile, use_codespeak=False):
    if not use_codespeak:
        py.process.cmdexec('dot -Tplain %s>%s' % (dotfile, plainfile))
    elif 0: 
        gw = py.execnet.SshGateway('codespeak.net')
        channel = gw.remote_exec("""
            import py
            content = channel.receive()
            fn = py.path.local.make_numbered_dir('makegraph').join('graph.dot')
            fn.write(content)
            tfn = fn.new(ext='.plain')
            py.process.cmdexec("dot -Tplain %s >%s" %(fn, tfn))
            channel.send(tfn.read())
        """) 
        channel.send(py.path.local(dotfile).read())
        plainfile = py.path.local(plainfile) 
        plainfile.write(channel.receive())
    else:
        import urllib
        content = py.path.local(dotfile).read()
        request = urllib.urlencode({'dot': content})
        urllib.urlretrieve('http://codespeak.net/pypy/convertdot.cgi',
                           str(plainfile),
                           data=request)

class ClientGraphLayout(GraphLayout):

    def __init__(self, connexion, key, dot, links, **ignored):
        # generate a temporary .dot file and call dot on it
        DOT_FILE.write(dot)
        try:
            dot2plain(DOT_FILE, PLAIN_FILE, use_codespeak=False)
            GraphLayout.__init__(self, PLAIN_FILE)
        except (py.error.Error, IOError, TypeError, ValueError):
            # failed, try via codespeak
            dot2plain(DOT_FILE, PLAIN_FILE, use_codespeak=True)
            GraphLayout.__init__(self, PLAIN_FILE)
        self.connexion = connexion
        self.key = key
        self.links.update(links)

    def request_followlink(self, name):
        self.connexion.initiate_display(self.key, name)

    def request_reload(self):
        self.connexion.initiate_display(self.key)


class InProcessConnexion:

    def get_layout(self, page, link=None):
        if link is not None:
            try:
                page = page.content().followlink(link)
            except KeyError:
                page = MissingPage()
        key = page
        page = page.content()
        layout = ClientGraphLayout(self, key, page.source, page.links)
        return layout

    def initiate_display(self, page, link=None, do_display=False):
        layout = self.get_layout(page, link)
        if do_display:
            layout.display()
        else:
            display_async_cmd(layout=layout)

    def quit(self):
        display_async_quit()

class SocketConnexion(portutil.Port):

    def initiate_display(self, key, link=None):
        self.put_msg((key, link))
        wait_for_async_cmd()

    def on_msg(self, msg):
        if msg is None:
            self.put_msg(None)
            return
        
        data = msg
        layout = ClientGraphLayout(self, **data)
        display_async_cmd(layout=layout)        

def get_layout(homepage): # only local
    conn = InProcessConnexion()
    return conn.get_layout(homepage)

def display_layout(homepage):
    conn = InProcessConnexion()
    conn.initiate_display(homepage, do_display=True)

def display_remote_layout(hostname, port=8888):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))
    conn = SocketConnexion(s)
    display = ClientGraphLayout(conn, None, "digraph empty {}", {}).get_display()
    conn.initiate_display(0)
    display.run()


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2 or sys.argv[1].count(':') != 1:
        print >> sys.stderr, 'Connects to a graph server like goal/translate_pypy.'
        print >> sys.stderr, 'Usage:  %s hostname:port' % (sys.argv[0],)
        print >> sys.stderr, '   or   %s :port' % (sys.argv[0],)
        sys.exit(2)
    hostname, port = sys.argv[1].split(':')
    port = int(port)
    display_remote_layout(hostname, port)
