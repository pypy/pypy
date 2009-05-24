
""" Simplified optimize.py
"""
from pypy.jit.metainterp.resoperation import rop, ResOperation, opname
from pypy.jit.metainterp.history import Const, Box

class InstanceNode(object):
    def __init__(self, source, const=False):
        self.source = source
        if const:
            assert isinstance(source, Const)
        self.const = const
        self.cls = None
        self.cleanfields = {}
        self.dirtyfields = {}
        self.virtualized = False

    def __repr__(self):
        flags = ''
        #if self.escaped:           flags += 'e'
        #if self.startbox:          flags += 's'
        if self.const:             flags += 'c'
        #if self.virtual:           flags += 'v'
        if self.virtualized:       flags += 'V'
        return "<InstanceNode %s (%s)>" % (self.source, flags)

class Specializer(object):
    loop = None
    nodes = None

    def __init__(self, opts):
        # NOT_RPYTHON
        self.optimizations = [[] for i in range(rop._LAST)]
        for opt in opts:
            for opnum, name in opname.iteritems():
                meth = getattr(opt, 'optimize_' + name.lower(), None)
                if meth is not None:
                    self.optimizations[opnum].append(meth)

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
                    self.nodes[box] = self.getnode(box.constbox())
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
                self.nodes[box] = self.getnode(box)

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
        op.suboperations = []
        for node, field in self.additional_stores:
            op.suboperations.append(ResOperation(rop.SETFIELD_GC,
               [node.source, node.cleanfields[field].source], None, field))
        op.suboperations.append(op_fail)
        op.args = self.new_arguments(op)

    def optimize_operations(self):
        self.additional_stores = []
        newoperations = []
        for op in self.loop.operations:
            newop = op
            for opt in self.optimizations[op.opnum]:
                newop = opt(op, self)
                if newop is None:
                    break
            if newop is None:
                continue
            if op.is_guard():
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
        self.field_caches = {}
        self.loop = loop
        self.find_nodes()
        self.optimize_operations()

class ConsecutiveGuardClassRemoval(object):
    def optimize_guard_class(self, op, spec):
        instnode = spec.getnode(op.args[0])
        if instnode.cls is not None:
            return None
        instnode.cls = op.args[1]
        return op

class SimpleVirtualizableOpt(object):
    def optimize_guard_nonvirtualized(self, op, spec):
        instnode = spec.getnode(op.args[0])
        instnode.virtualized = True
        instnode.vdesc = op.descr
        return None

    def optimize_getfield_gc(self, op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return op
        field = op.descr
        if field not in instnode.vdesc.virtuals:
            return op
        node = instnode.cleanfields.get(field, None)
        if node is not None:
            spec.nodes[op.result] = node
            return None
        instnode.cleanfields[field] = spec.getnode(op.result)
        return op

    def optimize_setfield_gc(self, op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return op
        field = op.descr
        if field not in instnode.vdesc.virtuals:
            return op
        instnode.cleanfields[field] = spec.getnode(op.args[1])
        # we never set it here
        spec.additional_stores.append((instnode, field))
        return None

specializer = Specializer([])

def optimize_loop(options, old_loops, loop, cpu=None, spec=specializer):
    if old_loops:
        assert len(old_loops) == 1
        return old_loops[0]
    else:
        spec.optimize_loop(loop)
        return None

def optimize_bridge(options, old_loops, loop, cpu=None, spec=specializer):
    optimize_loop(options, [], loop, cpu, spec)
    return old_loops[0]

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)


