from __future__ import generators
 
"""
"""

import autopath
from pypy.translator.controlflow import *
import os


counters = {}
class Node:
    allnodes = []
    def __init__(self, obj):
        self.obj = obj
        self.allnodes.append(self)
        self.edges = []
        self.make_name()
        self.data = []

    def make_name(self):
        cls = type(self)
        num = counters.setdefault(cls, 0)
        counters[cls] += 1
        self.name = '%s%d' % (self.__class__.__name__, num)

    def addedge(self, othernode, name=None):
        """ append edge (if not already in the list)
        return true if it really was added
        """
        if othernode not in self.edges:
            self.edges.append((othernode, name))
            return 1

    def descr_edges(self):
        l = []
        for node,name in self.edges:
            if node in self.allnodes:
                style = node.linestyle()
                l.append('edge [style=%s, label="%s"]; %s -> %s;' % (style, name, self, node))
            else:
                pass
        return "\n".join(l)

    def linestyle(self):
        return "solid"

    def get_data(self):
        return "\\n".join(self.data)

    def __str__(self):
        return self.name

class NodeFunctionGraph(Node):
    def descr_node(self):
        """ obj attrs startblock, functionname """   
        name = self.name
        data = self.get_data()
        return '%(name)s [shape=box, label="%(data)s"];' % locals()

    def make_name(self):
        self.name = self.obj.functionname

class NodeBasicBlock(Node):
    def descr_node(self):
        """ condition, ifbranch, elsebranch """
        name = self.name
        data = self.get_data()
        #content = "\\n".join([name] + map(repr,self.obj.operations)) + "\\n"+data
        return '%(name)s [shape=box, label="%(data)s"];' % locals()

class NodeBranch(Node):
    def descr_node(self):
        """ args, target """
        name = self.name
        data = self.get_data()
        return '%(name)s [shape=box, label="%(data)s"];' % locals()

class NodeConditionalBranch(Node):
    def descr_node(self):
        """ args, target """
        name = self.name
        data = self.get_data()
        return '%(name)s [shape=box, label="%(data)s"];' % locals()

class NodeEndBranch(Node):
    def descr_node(self):
        """ args, target """
        name = self.name
        data = self.get_data()
        return '%(name)s [shape=box, label="%(data)s"];' % locals()

def flatten(*args):
    for arg in args:
        try:
            for atom in apply(flatten,arg):
                yield atom
        except: yield arg

   
class DotGen:
    def __init__(self):
        self.nodes = {}
        self.counters = {}

    def get_source(self, fun):
        self.traverse(fun)
        l = []
        for node in self.nodes.values():
            l.append(node.descr_node())
            l.append(node.descr_edges())

        content = "\n".join(l)

        return """
digraph test { 
node [fontname=Times];
edge [fontname=Times];
%(content)s
}""" % locals()

    def makenode(self, obj):
        try:
            return self.nodes[obj]
        except KeyError:
            pass
        try:
            name = obj.__class__.__name__
        except AttributeError:
            return
        g = globals()
        cls = g.get('Node%s' % name, None)
        if cls is not None:
            node = cls(obj)
            self.nodes[obj] = node
            return node

    def traverse(self, obj, objname=None):
        try:
            return self.nodes[obj]
        except KeyError:
            pass
        except TypeError:
            return
        node = self.makenode(obj)
        if node:
            self.nodes[obj] = node
            for name, attr in obj.__dict__.items():
                trynode = self.traverse(attr, name)
                if trynode:
                    node.addedge(trynode, name)
                else:
                    node.data.append("%s=%r" % (name, attr))
                    #print "unknown attribute", name, item
            return node
        else:
            print "unknown obj", obj

def make_png(fun):
    dotgen = DotGen()
   
    from vpath.local import Path
    from vpath.adapter.process import exec_cmd
    dest = Path('/tmp/testgraph.dot')
    #print dotgen.get_source(fun)
    dest.write(dotgen.get_source(fun))
    psdest = dest.newsuffix('.png')
    out = exec_cmd('dot -Tpng %s' % str(dest))
    psdest.write(out)
    print "wrote", psdest
    raise SystemExit, 0

if __name__ == '__main__':
        i = Variable("i")
        sum = Variable("sum")

        conditionres = Variable("conditionres")
        conditionop = SpaceOperation("gt", [i, Constant(0)], conditionres)
        decop = SpaceOperation("add", [i, Constant(-1)], i)
        addop = SpaceOperation("add", [i, sum], sum)

        conditionbranch = ConditionalBranch()
        headerbranch = Branch()
        headerbranch2 = Branch()
        whileblock = BasicBlock([i, sum], [i, sum], [addop, decop], headerbranch2)
        whilebranch = Branch([i, sum], whileblock)

        endbranch = EndBranch(sum)
        conditionbranch.set(conditionres, whilebranch, endbranch)

        headerblock = BasicBlock([i, sum], [i, conditionres],
                                 [conditionop], conditionbranch)

        headerbranch.set([i, Constant(0)], headerblock)
        headerbranch2.set([i, sum], headerblock)
        startblock = BasicBlock([i], [i, sum],
                                [], headerbranch)

        fun = FunctionGraph(startblock, "f")

        make_png(fun)
