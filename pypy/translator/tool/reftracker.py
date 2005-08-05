"""
General-purpose reference tracker.
Usage: call track(obj).
"""

import autopath
import gc
from pypy.translator.tool.graphpage import GraphPage, DotGen


MARKER = object()


class RefTrackerPage(GraphPage):

    def compute(self, objectlist):
        assert objectlist[0] is MARKER
        self.objectlist = objectlist
        dotgen = DotGen('reftracker')
        id2typename = {}
        nodes = {}
        edges = {}

        def addedge(o1, o2):
            key = (id(o1), id(o2))
            slst = []
            if type(o1) in (list, tuple):
                for i in range(len(o1)):
                    if o1[i] is o2:
                        slst.append('[%d]' % i)
            elif type(o1) is dict:
                for k, v in o1.items():
                    if v is o2:
                        slst.append('[%r]' % (k,))
            edges[key] = ', '.join(slst)

        for i in range(1, len(objectlist)):
            s = repr(objectlist[i])
            word = '0x%x' % id(objectlist[i])
            if len(s) > 50:
                self.links[word] = s
                s = s[:20] + ' ... ' + s[-20:]
            s = '<%s> %s\\n%s' % (type(objectlist[i]).__name__,
                                    word,
                                    s)
            nodename = 'node%d' % len(nodes)
            dotgen.emit_node(nodename, label=s, shape="box")
            nodes[id(objectlist[i])] = nodename
            for o2 in gc.get_referents(objectlist[i]):
                if o2 is None:
                    continue
                addedge(objectlist[i], o2)
                id2typename[id(o2)] = type(o2).__name__
                del o2
            for o2 in gc.get_referrers(objectlist[i]):
                if o2 is None:
                    continue
                if type(o2) is list and o2 and o2[0] is MARKER:
                    continue
                addedge(o2, objectlist[i])
                id2typename[id(o2)] = type(o2).__name__
                del o2

        for ids, label in edges.items():
            for id1 in ids:
                if id1 not in nodes:
                    nodename = 'node%d' % len(nodes)
                    word = '0x%x' % id1
                    s = '<%s> %s' % (id2typename[id1], word)
                    dotgen.emit_node(nodename, label=s)
                    nodes[id1] = nodename
                    self.links[word] = s
            id1, id2 = ids
            dotgen.emit_edge(nodes[id1], nodes[id2], label=label)

        self.source = dotgen.generate(target=None)

    def followlink(self, word):
        id1 = int(word, 16)
        found = None
        objectlist = self.objectlist
        for i in range(1, len(objectlist)):
            for o2 in gc.get_referents(objectlist[i]):
                if id(o2) == id1:
                    found = o2
            for o2 in gc.get_referrers(objectlist[i]):
                if id(o2) == id1:
                    found = o2
        if found is not None:
            objectlist = objectlist + [found]
        else:
            print '*** NOTE: object not found'
        return RefTrackerPage(objectlist)


def track(o):
    """Invoke a dot+pygame object reference tracker."""
    page = RefTrackerPage([MARKER, o])
    del o
    page.display()


if __name__ == '__main__':
    d = {"lskjadldjslkj": "adjoiadoixmdoiemdwoi"}
    track(d)
