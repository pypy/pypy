from __future__ import generators
 
"""
"""

import autopath, os
from pypy.objspace.flow.model import *
from pypy.objspace.flow import Space
from pypy.tool.udir import udir
from std.process import cmdexec

debug = 0

class DotGen:
    def get_source(self, funcgraph):
        content = "\n".join(self.lines)
        return """
digraph test { 
node [fontname=Times];
edge [fontname=Times];
%(content)s
}""" % locals()

    def getsubgraph(self, name, node):
        self.blocks = {}
        self.lines = []
        self.prefix = name
        traverse(self, node)
        content = "\n".join(self.lines)
        return "subgraph %s {\n%s}" % (name, content) 

    def getdigraph(self, name, node):
        self.blocks = {}
        self.lines = []
        self.prefix = name
        traverse(self, node)
        content = "\n".join(self.lines)
        return "digraph %s {\n%s}" % (name, content) 

    def getgraph(self, name, subgraphlist):
        content = "\n".join(subgraphlist)
        return "digraph %s {\n%s}" % (name, content)

    def blockname(self, block):
        i = id(block)
        try:
            return self.blocks[i]
        except KeyError:
            self.blocks[i] = name = "%s_%d" % (self.prefix, len(self.blocks))
            return name

    def emit(self, line):
        self.lines.append(line)

    def emit_edge(self, name1, name2, label="", 
                  style="dashed", 
                  color="black", 
                  dir="forward",
                  weight="5",
                  ):
        d = locals()
        attrs = [('%s="%s"' % (x, d[x])) for x in d if isinstance(x, str)]
        self.emit('edge [%s];' % ", ".join(attrs))
        self.emit('%s -> %s' % (name1, name2))

    def emit_node(self, name, 
                  shape="diamond", 
                  label="", 
                  color="black",
                  fillcolor="white", 
                  style="filled",
                  ):
        d = locals()
        attrs = [('%s="%s"' % (x, d[x])) for x in d if isinstance(x, str)]
        self.emit('%s [%s];' % (name, ", ".join(attrs)))

    def visit(self, obj):
        # ignore for now 
        return

    def visit_FunctionGraph(self, funcgraph):
        name = self.prefix # +'_'+funcgraph.name
        data = name
        if hasattr(funcgraph, 'source'):
            source = funcgraph.source.replace('"', "'")
            data += "\\n" + "\\l".join(source.split('\n'))
           
        self.emit_node(name, label=data, shape="box", fillcolor="green", style="filled")
        #('%(name)s [fillcolor="green", shape=box, label="%(data)s"];' % locals())
        self.emit_edge(name, self.blockname(funcgraph.startblock), 'startblock')
        #self.emit_edge(name, self.blockname(funcgraph.returnblock), 'returnblock', style="dashed")

    def visit_Block(self, block):
        # do the block itself
        name = self.blockname(block)
        lines = map(repr, block.operations)
        lines.append("")
        numblocks = len(block.exits)
        color = "black"
        fillcolor = "white"
        if not numblocks:
           shape = "box"
           fillcolor="green"
           if hasattr(block, 'exc_type'):
               lines.insert(0, 'exc_type: %s' % block.exc_type.__name__)
        elif numblocks == 1:
            shape = "box"
        else:
            color = "red"
            lines.append("exitswitch: %s" % block.exitswitch)
            shape = "octagon"

        iargs = " ".join(map(repr, block.inputargs))
        data = "%s(%s)\\ninputargs: %s\\n\\n" % (name, block.__class__.__name__, iargs)
        data = data + "\l".join(lines)

        self.emit_node(name, label=data, shape=shape, color=color, style="filled", fillcolor=fillcolor)

        # do links/exits
        if numblocks == 1:
            name2 = self.blockname(block.exits[0].target)
            label = " ".join(map(repr, block.exits[0].args))
            self.emit_edge(name, name2, label, style="solid")
        elif numblocks >1:
            for link in block.exits:
                name2 = self.blockname(link.target)
                label = " ".join(map(repr, link.args))
                label = "%s: %s" %(link.exitcase, label)
                self.emit_edge(name, name2, label, style="dotted", color=color)


def make_dot(graphname, graph, storedir=None, target='ps'):
    return make_dot_graphs(graph.name, [(graphname, graph)], storedir, target)

def show_dot(graph, storedir = None, target = 'ps'):
    name = graph.name
    fn = make_dot(name, graph, storedir, target)
    os.system('gv %s' % fn)

def make_dot_graphs(basefilename, graphs, storedir=None, target='ps'):
    if storedir is None:
        storedir = udir

    dotgen = DotGen()
    dest = storedir.join('%s.dot' % basefilename)
    #dest = storedir.dirname().join('%s.dot' % name)
    subgraphs = []
    basefilename = '_'+basefilename
    names = {basefilename: True}
    for graphname, graph in graphs:
        if graphname in names:
            i = 2
            while graphname + str(i) in names:
                i += 1
            graphname = graphname + str(i)
        names[graphname] = True
        subgraphs.append(dotgen.getsubgraph(graphname, graph))
    source = dotgen.getgraph(basefilename, subgraphs)
    #print source
    dest.write(source)
    psdest = dest.newext(target)
    out = cmdexec('dot -T%s %s' % (target, str(dest)))
    psdest.write(out)
    #print "wrote", psdest
    return psdest


if __name__ == '__main__':
    def f(x):
        i = 0
        while i < x:
            i += 1
        return i

    space = Space()
    graph = space.build_flow(f)
    make_dot('f', graph)
