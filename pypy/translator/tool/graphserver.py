"""
A socket server for GraphPages.
"""

import sys
import autopath

from pypy.translator.tool import port as portutil

send_msg = portutil.send_msg
recv_msg = portutil.recv_msg

def run_async_server(t, listen_port):
    import graphpage
    homepage = graphpage.TranslatorPage(t)
    print repr(t),repr(homepage)
    return run_server(homepage, port=listen_port, background=True)

class GraphserverPort(portutil.Port):

    def __init__(self, s, homepage):
        portutil.Port.__init__(self, s)
        self.pages = {0: homepage}

    def on_msg(self, msg):
        if msg is None:
            print "Closing %r." % (self.s.getpeername(),)
            self.put_msg(None)
            return
        key, link = msg
        page = self.pages[key]
        if link is not None:
            try:
                page = page.content().followlink(link)
                key = len(self.pages)
            except KeyError:
                page = MissingPage()
                key = -1
            self.pages[key] = page
        page = page.content()
        reply = {
            'key': key,
            'dot': page.source,
            'links': page.links,
            }
        self.put_msg(reply)

    def force_page(self, page):
        key = sys.maxint # dummy
        self.pages[key] = page
        page = page.content()
        self.put_msg({
            'key': key,
            'dot': page.source,
            'links': page.links
            })

def run_server(homepage, port=8888, quiet=False, background=False):

    last = [None]

    def make_port(s):
       gport = GraphserverPort(s, homepage)
       last[0] = gport
       return gport

    def start():
        pass

    def show(page): # xxx better broadcast in this case?
        if last[0]:
            last[0].force_page(page)

    def stop():
        pass

    portutil.run_server(make_port, port=port, quiet=quiet, background=background)

    return start, show, stop, stop

class MissingPage:
    links  = {}
    source = '''
digraph error {
msg [shape="box", label="Error: a link has gone missing.", color="black", fillcolor="red", style="filled"];
}
'''
    def content(self):
        return self
