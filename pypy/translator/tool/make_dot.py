from __future__ import generators
 
"""
"""

import autopath, os
import inspect, linecache
from pypy.objspace.flow.model import *
from pypy.objspace.flow import Space
from pypy.tool.udir import udir
from py.process import cmdexec
from pypy.interpreter.pytraceback import offset2lineno

class DotGen:

    def __init__(self, graphname, rankdir=None):
        self.graphname = graphname
        self.lines = []
        self.source = None
        self.emit("digraph %s {" % graphname)
        if rankdir:
            self.emit('rankdir="%s"' % rankdir)

    def generate(self, storedir=None, target='ps'):
        source = self.get_source()
        if target is None:
            return source    # unprocessed
        if storedir is None:
            storedir = udir
        pdot = storedir.join('%s.dot' % self.graphname)
        pdot.write(source)
        ptarget = pdot.new(ext=target)
        cmdexec('dot -T%s %s>%s' % (target, str(pdot),str(ptarget)))
        return ptarget

    def get_source(self):
        if self.source is None:
            self.emit("}")
            self.source = '\n'.join(self.lines)
            del self.lines
        return self.source

    def emit(self, line):
        self.lines.append(line)

    def enter_subgraph(self, name):
        self.emit("subgraph %s {" % (name,))

    def leave_subgraph(self):
        self.emit("}")

    def emit_edge(self, name1, name2, label="", 
                  style="dashed", 
                  color="black", 
                  dir="forward",
                  weight="5",
                  ):
        d = locals()
        attrs = [('%s="%s"' % (x, d[x].replace('"', '\\"')))
                 for x in ['label', 'style', 'color', 'dir', 'weight']]
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
        attrs = [('%s="%s"' % (x, d[x].replace('"', '\\"')))
                 for x in ['shape', 'label', 'color', 'fillcolor', 'style']]
        self.emit('%s [%s];' % (name, ", ".join(attrs)))


class FlowGraphDotGen(DotGen):

    def __init__(self, graphname, rankdir=None):
        DotGen.__init__(self, graphname.replace('.', '_'), rankdir)

    def emit_subgraph(self, name, node):
        name = name.replace('.', '_')
        self.blocks = {}
        self.func = None
        self.prefix = name
        self.enter_subgraph(name)
        traverse(self, node)
        self.leave_subgraph()

    def blockname(self, block):
        i = id(block)
        try:
            return self.blocks[i]
        except KeyError:
            self.blocks[i] = name = "%s_%d" % (self.prefix, len(self.blocks))
            return name

    def visit(self, obj):
        # ignore for now 
        return

    def visit_FunctionGraph(self, funcgraph):
        name = self.prefix # +'_'+funcgraph.name
        data = funcgraph.name
        if hasattr(funcgraph, 'source'):
            source = funcgraph.source
            data += "\\n" + "\\l".join(source.split('\n'))
        if hasattr(funcgraph, 'func'):
            self.func = funcgraph.func

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
        fillcolor = getattr(block, "fillcolor", "white")
        if not numblocks:
           shape = "box"
           fillcolor="green"
           if len(block.inputargs) == 1:
               lines[-1] += 'return %s' % tuple(block.inputargs)
           elif len(block.inputargs) == 2:
               lines[-1] += 'raise %s, %s' % tuple(block.inputargs)
        elif numblocks == 1:
            shape = "box"
        else:
            color = "red"
            lines.append("exitswitch: %s" % block.exitswitch)
            shape = "octagon"

        iargs = " ".join(map(repr, block.inputargs))
        if block.exc_handler:
            eh = 'EH'
        else:
            eh = ''
        data = "%s(%s %s)\\ninputargs: %s\\n\\n" % (name, block.__class__.__name__, eh, iargs)
        if block.operations and self.func:
            maxoffs = max([op.offset for op in block.operations])
            if maxoffs >= 0:
                minoffs = min([op.offset for op in block.operations
                               if op.offset >= 0])
                minlineno = offset2lineno(self.func.func_code, minoffs)
                maxlineno = offset2lineno(self.func.func_code, maxoffs)
                filename = inspect.getsourcefile(self.func)
                source = "\l".join([linecache.getline(filename, line).rstrip()
                                    for line in range(minlineno, maxlineno+1)])
                if minlineno == maxlineno:
                    data = data + r"line %d:\n%s\l\n" % (minlineno, source)
                else:
                    data = data + r"lines %d-%d:\n%s\l\n" % (minlineno,
                                                             maxlineno, source)

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
    dotgen = FlowGraphDotGen(basefilename)
    names = {basefilename: True}
    for graphname, graph in graphs:
        if graphname in names:
            i = 2
            while graphname + str(i) in names:
                i += 1
            graphname = graphname + str(i)
        names[graphname] = True
        dotgen.emit_subgraph(graphname, graph)
    return dotgen.generate(storedir, target)


if __name__ == '__main__':
    def f(x):
        i = 0
        while i < x:
            i += 1
        return i

    space = Space()
    graph = space.build_flow(f)
    make_dot('f', graph)
