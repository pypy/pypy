#<MROgraph.py>
 
"""
"""

import autopath
from pypy.translator.controlflow import *
import os

class Source:
    def __init__(self):
        self.lines = []

    def getsource(self):
        content = "\n".join(self.lines)

        return """digraph test { 
            node [fontname=Times];
            edge [fontname=Times];
        %(content)s
        }
        """ % locals()

    def putnode(self, name, node):
        self.lines.append('%(name)s [shape=box, label=%(name)s];' % locals())

    def putedge(self, name, othername):
        self.lines.append('%(name)s -> %(othername)s;' % locals())

#class Node:
#    def __init__(self, **kwargs):
#        self.__dict__.update(kwargs)
#
#class NodeFunctionGraph(Node):
#    def dotsource(self):

class DotGen:
    def __init__(self):
        self.graph = {} # node1 : [node1,node2,node3] }
        self.names = {} # obj : string 
        self.blocknum = 0
        self.branchnum = 0

    def get_source(self, obj):
        self.dispatch(obj)
        source = Source()
        for obj,edges in self.graph.items():
            objname = self.names[obj]
            source.putnode(objname, obj)
            for edge in edges:
                source.putedge(objname, edge)
        return source.getsource()

    def dispatch(self, obj):
        try:
            return self.names[obj]
        except KeyError:
            pass
        typename = obj.__class__.__name__
        method = getattr(self, "gen_%s" % typename, None)
        if method is not None:
            return method(obj)

        raise ValueError, "unknown type for %r" % typename

    def append_edge(self, obj, otherobj):
        points_to = self.graph.setdefault(obj, [])
        points_to.append(otherobj)

    def gen_FunctionGraph(self, obj):
        name = obj.functionname
        self.names[obj] = name
        self.append_edge(obj, self.dispatch(obj.startblock))
        return name

    def gen_BasicBlock(self, obj):
        name = "block%s" % self.blocknum
        self.blocknum += 1
        self.names[obj] = name
        self.append_edge(obj, self.dispatch(obj.branch))
        return name

    def gen_Branch(self, obj):
        name = "branch%s" % self.branchnum
        self.branchnum += 1
        self.names[obj] = name
        self.append_edge(obj, self.dispatch(obj.target))
        return name

    def gen_ConditionalBranch(self, obj):
        name = "Condbranch%s" % self.branchnum
        self.branchnum += 1
        self.names[obj] = name
        self.append_edge(obj, self.dispatch(obj.ifbranch))
        self.append_edge(obj, self.dispatch(obj.elsebranch))
        return name

    def gen_EndBranch(self, obj):
        name = "endbranch%s" % self.branchnum
        self.branchnum += 1
        self.names[obj] = name
        self.graph[obj] = [] 
        return name
        #self.append_edge(self.dispatch(obj.target))

def make_ps(fun):
    dotgen = DotGen()
   
    from vpath.local import Path
    from vpath.adapter.process import exec_cmd
    dest = Path('/tmp/testgraph.dot')
    dest.write(dotgen.get_source(fun))
    psdest = dest.newsuffix('.ps')
    out = exec_cmd('dot -Tps %s' % str(dest))
    psdest.write(out)
    print "wrote", psdest

#if __name__ == '__main__':
    
        
