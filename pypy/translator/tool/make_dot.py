from __future__ import generators
 
"""
"""

import autopath, os
from pypy.objspace.flow.model import *
from pypy.objspace.flow import Space
from pypy.tool.udir import udir

debug = 0

class DotGen:
    def __init__(self):
        self.nodes = {}
        self.counters = {}

    def get_source(self, funcgraph):
        self.blocks = {}
        self.lines = []
        traverse(self, funcgraph)
        content = "\n".join(self.lines)
        return """
digraph test { 
node [fontname=Times];
edge [fontname=Times];
%(content)s
}""" % locals()

    def blockname(self, block):
        i = id(block)
        try:
            return self.blocks[i]
        except KeyError:
            self.blocks[i] = name = "block%d" % len(self.blocks)
            return name

    def emit(self, line):
        self.lines.append(line)

    def emit_edge(self, name1, name2, label="", style="dashed", color="black", **kw):
        d = locals()
        d.update(kw)
        self.emit('edge [style=%(style)s, color=%(color)s, dir="forward", weight=0, label="%(label)s"];' % d)
        self.emit('%(name1)s -> %(name2)s;' % d)

    def emit_node(self, name, shape, label, color="black", **kw):
        d = locals()
        d.update(kw)
        self.emit('%(name)s [shape=%(shape)s, color="%(color)s" label="%(label)s"];' % d)

    def visit(self, obj):
        # ignore for now 
        return

    def visit_FunctionGraph(self, funcgraph):
        name = funcgraph.name
        data = name
        self.emit('%(name)s [shape=circle, label="%(data)s"];' % locals())
        self.emit_edge(name, self.blockname(funcgraph.startblock), 'startblock')

    def visit_Block(self, block):
        name = self.blockname(block)
        lines = []

        lines.extend(map(repr, block.operations))
        lines.append("")

        numblocks = len(block.exits)

        color = "black"
        if not numblocks:
           shape = "circle"
        elif numblocks == 1:
            shape = "box"
        else:
            color = "red"
            lines.append("exitswitch: %s" % block.exitswitch)
            shape = "octagon"

        iargs = " ".join(map(repr, block.inputargs))
        data = "%s(%s)\\ninputargs: %s\\n\\n" % (name, block.__class__.__name__, iargs)
        data = data + "\l".join(lines)
        self.emit_node(name, label=data, shape=shape, color=color)

        if numblocks == 1:
            name2 = self.blockname(block.exits[0].target)
            label = " ".join(map(repr, block.exits[0].args))
            self.emit_edge(name, name2, label, style="solid")
        elif numblocks >1:
            i = 0
            for link in block.exits:
                name2 = self.blockname(link.target)
                label = " ".join(map(repr, link.args))
                label = "%s: %s" %(str(i), label)
                self.emit_edge(name, name2, label, style="dotted", color=color)
                i+=1


def make_dot(graph, storedir=None, target='ps'):
    from vpath.adapter.process import exec_cmd

    if storedir is None:
        storedir = udir

    dotgen = DotGen()
    name = graph.name
    dest = storedir.join('%s.dot' % name)
    #dest = storedir.dirname().join('%s.dot' % name)
    source = dotgen.get_source(graph)
    #print source
    dest.write(source)
    psdest = dest.newext(target)
    out = exec_cmd('dot -T%s %s' % (target, str(dest)))
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
    make_dot(graph, udir.dirname())
