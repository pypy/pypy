import BaseHTTPServer
from cStringIO import StringIO
import httpserver
from httpserver import htmlquote
from pypy.translator.tool.pygame.graphviewer import GraphViewer
from pypy.translator.tool.make_dot import make_dot_graphs


class Server:

    def __init__(self, translator):
        self.translator = translator
        self.viewercache = {}
        self.binding_by_name = {}
        self.binding_history = {}
        for var, s_value in self.translator.annotator.bindings.items():
            self.binding_by_name[var.name] = '%s :  %r' % (var.name, s_value)
        for var, history in self.translator.annotator.bindingshistory.items():
            self.binding_history[var.name] = history

    def getviewer(self, i):
        t = self.translator
        func = t.functions[i]
        if func in self.viewercache:
            return self.viewercache[func]
        name = '%s_%d' % (func.__name__, i)
        graph = t.getflowgraph(func)
        graphs = [(graph.name, graph)]
        xdotfile = str(make_dot_graphs(name, graphs, target='xdot'))
        pngfile = str(make_dot_graphs(name, graphs, target='png'))
        viewer = GraphViewer(xdotfile, pngfile)
        zones = []
        for (x,y,w,h), name in viewer.getzones():
            if name in self.binding_by_name:
                zones.append((name, (x,y,x+w,y+h), self.binding_by_name[name]))
        result = zones, pngfile
        self.viewercache[func] = result
        return result

    def indexloader(self, **options):
        t = self.translator
        return httpserver.load('index.html', 'text/html', {'t': t})

    def funcloader(self, i, **options):
        i = int(i[0])
        zones, pngfile = self.getviewer(i)
        t = self.translator
        return httpserver.load('func.html', 'text/html',
                               {'t': t,
                                'zones': zones,
                                'img': 'img?i=%d' % i,
                                })

    def imgloader(self, i, **options):
        i = int(i[0])
        zones, pngfile = self.getviewer(i)
        return open(pngfile, 'rb'), 'image/png'

    def varloader(self, n, **options):
        n = n[0]
        s = self.binding_by_name[n]
        assert s.startswith('%s :' % n)
        s = s[len('%s :' % n):]
        data = '<html><head><title>%s</title></head><body>' % n
        data += '<h1>%s</h1>' % n
        data += '<p>%s</p>' % htmlquote(s)
        if n in self.binding_history:
            lines = ['<li>%s' % htmlquote(repr(s))
                     for s in self.binding_history[n]]
            lines.reverse()
            data += '<h2>Previous values</h2>'
            data += '<ul>'
            data += '\n'.join(lines)
            data += '</ul>'
        data += '</body></html>'
        return StringIO(data), 'text/html'

    def cdefloader(self, i, **options):
        i = int(i[0])
        t = self.translator
        classdef = t.annotator.getuserclassdefinitions()[i]
        return httpserver.load('cdef.html', 'text/html',
                               {'t': t,
                                'classdef': classdef,
                                })

    def serve(self, port=8000):
        httpserver.register('', self.indexloader)
        httpserver.register('func', self.funcloader)
        httpserver.register('img', self.imgloader)
        httpserver.register('var', self.varloader)
        httpserver.register('cdef', self.cdefloader)
        httpserver.serve(port)

# ____________________________________________________________

if __name__ == '__main__':
    from pypy.translator.translator import Translator
    from pypy.translator.test import snippet
    t = Translator(snippet.sieve_of_eratosthenes)
    t.simplify()
    a = t.annotate([])
    a.simplify()
    Server(t).serve()
