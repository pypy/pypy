
""" Simplified optimize.py
"""
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import Const, Box

class InstanceNode(object):
    def __init__(self, source, const=False):
        self.source = source
        if const:
            assert isinstance(source, Const)
        self.const = const
        self.cls = None

    def __repr__(self):
        flags = ''
        #if self.escaped:           flags += 'e'
        #if self.startbox:          flags += 's'
        if self.const:             flags += 'c'
        #if self.virtual:           flags += 'v'
        #if self.virtualized:       flags += 'V'
        return "<InstanceNode %s (%s)>" % (self.source, flags)

class Specializer(object):
    loop = None
    nodes = None

    def getnode(self, box):
        try:
            return self.nodes[box]
        except KeyError:
            if isinstance(box, Const):
                node = InstanceNode(box, const=True)
            else:
                node = InstanceNode(box)
            self.nodes[box] = node
            return node

    def getsource(self, box):
        if isinstance(box, Const):
            return box
        return self.nodes[box].source

    def find_nodes(self):
        for op in self.loop.operations:
            if op.is_always_pure():
                is_pure = True
                for arg in op.args:
                    if not self.getnode(arg).const:
                        is_pure = False
                if is_pure:
                    box = op.result
                    assert box is not None
                    self.nodes[box] = InstanceNode(box.constbox(), const=True)
                    continue
            else:
                if op.is_guard():
                    for arg in op.suboperations[0].args:
                        self.getnode(arg)
                # default case
                for box in op.args:
                    self.getnode(box)
            box = op.result
            if box is not None:
                self.nodes[box] = InstanceNode(box)

    def new_arguments(self, op):
        newboxes = []
        for box in op.args:
            if isinstance(box, Box):
                instnode = self.nodes[box]
                box = instnode.source
            newboxes.append(box)
        return newboxes

    def optimize_guard(self, op):
        assert len(op.suboperations) == 1
        op_fail = op.suboperations[0]
        op_fail.args = self.new_arguments(op_fail)
        # modification in place. Reason for this is explained in mirror
        # in optimize.py
        op.suboperations = [op_fail]

    def optimize_operations(self):
        newoperations = []
        for op in self.loop.operations:
            if op.is_guard():
                if op.opnum == rop.GUARD_NONVIRTUALIZED:
                    continue
                elif op.opnum == rop.GUARD_CLASS:
                    node = self.getnode(op.args[0])
                    if node.cls is not None:
                        # assert that they're equal maybe
                        continue
                    node.cls = InstanceNode(op.args[1], const=True)
                elif op.opnum == rop.GUARD_VALUE:
                    instnode = self.nodes[op.args[0]]
                    assert isinstance(op.args[1], Const)
                    if instnode.const:
                        continue
                    self.optimize_guard(op)
                    instnode.const = True
                    instnode.source = op.args[0].constbox()
                    newoperations.append(op)
                    continue
                self.optimize_guard(op)
                newoperations.append(op)
                continue
            # default handler
            op = op.clone()
            op.args = self.new_arguments(op)
            if op.is_always_pure():
                for box in op.args:
                    if isinstance(box, Box):
                        break
                else:
                    # all constant arguments: constant-fold away
                    box = op.result
                    assert box is not None
                    instnode = InstanceNode(box.constbox(), const=True)
                    self.nodes[box] = instnode
                    continue
            newoperations.append(op)
        print "Length of the loop:", len(newoperations)
        self.loop.operations = newoperations
    
    def optimize_loop(self, loop):
        self.nodes = {}
        self.loop = loop
        self.find_nodes()
        self.optimize_operations()

specializer = Specializer()

def optimize_loop(options, old_loops, loop, cpu=None):
    if old_loops:
        assert len(old_loops) == 1
        return old_loops[0]
    else:
        specializer.optimize_loop(loop)
        return None

def optimize_bridge(options, old_loops, loop, cpu=None):
    optimize_loop(options, [], loop, cpu)
    return old_loops[0]

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)


