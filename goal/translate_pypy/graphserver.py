import BaseHTTPServer
from cStringIO import StringIO
import httpserver
from pypy.translator.tool.pygame.graphviewer import GraphViewer
from pypy.translator.tool.make_dot import make_dot_graphs


class Server:

    def __init__(self, translator):
        self.translator = translator
        self.viewercache = {}
        self.binding_by_name = {}
        for var, s_value in self.translator.annotator.bindings.items():
            self.binding_by_name[var.name] = '%s :  %r' % (var.name, s_value)

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
        import textwrap
        data = textwrap.fill(self.binding_by_name[n])
        data = '=== %s ===\n\n%s' % (n, data)
        return StringIO(data), 'text/plain'

    def serve(self):
        httpserver.register('', self.indexloader)
        httpserver.register('func', self.funcloader)
        httpserver.register('img', self.imgloader)
        httpserver.register('var', self.varloader)
        BaseHTTPServer.test(HandlerClass=httpserver.MiniHandler)

# ____________________________________________________________

if __name__ == '__main__':
    from pypy.translator.translator import Translator
    from pypy.translator.test import snippet
    t = Translator(snippet.sieve_of_eratosthenes)
    t.simplify()
    a = t.annotate([])
    a.simplify()
    Server(t).serve()
