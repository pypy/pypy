
""" Simplified optimize.py
"""
from pypy.jit.metainterp.resoperation import rop, ResOperation, opname
from pypy.jit.metainterp.history import Const, Box, ConstInt

# For anybody reading.
# Next step is to fix this so cleanfields and dicts on specializer
# (additional_*) would be r_dicts so they can consider
# two different constants as the same.

class VirtualizedListAccessedWithVariableArg(Exception):
    pass

class InstanceNode(object):
    def __init__(self, source, const=False, escaped=False):
        self.source = source
        if const:
            assert isinstance(source, Const)
        self.const = const
        self.cls = None
        self.cleanfields = {}
        self.origfields = {}
        self.arrayfields = {}
        self.allocated_in_loop = False
        self.escaped = escaped
        self.virtual = False
        self.size = None

    def __repr__(self):
        flags = ''
        if self.escaped:           flags += 'e'
        #if self.startbox:          flags += 's'
        if self.const:             flags += 'c'
        if self.virtual:           flags += 'v'
        return "<InstanceNode %s (%s)>" % (self.source, flags)

class Specializer(object):
    loop = None
    nodes = None

    def __init__(self, opts):
        # NOT_RPYTHON
        self.optimizations = [[] for i in range(rop._LAST)]
        self.find_nodes_funcs = [[] for i in range(rop._LAST)]
        for opt in opts:
            for opnum, name in opname.iteritems():
                meth = getattr(opt, 'optimize_' + name.lower(), None)
                if meth is not None:
                    self.optimizations[opnum].append(meth)
        for opt in opts:
            for opnum, name in opname.iteritems():
                meth = getattr(opt, 'find_nodes_' + name.lower(), None)
                if meth is not None:
                    self.find_nodes_funcs[opnum].append(meth)

    def getnode(self, box):
        try:
            return self.nodes[box]
        except KeyError:
            if isinstance(box, Const):
                node = InstanceNode(box, const=True)
            else:
                node = InstanceNode(box, escaped=True)
            self.nodes[box] = node
            return node

    def getsource(self, box):
        if isinstance(box, Const):
            return box
        return self.nodes[box].source

    def find_nodes(self):
        for op in self.loop.operations:
            res = False
            for f in self.find_nodes_funcs[op.opnum]:
                res = f(op, self)
                if res:
                    break
            if res:
                continue
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
                nodes = []
                for box in op.args:
                    nodes.append(self.getnode(box))
                if op.has_no_side_effect() or op.is_guard():
                    pass
                elif (op.opnum in [rop.SETFIELD_GC, rop.SETFIELD_RAW,
                                   rop.SETARRAYITEM_GC]):
                    for i in range(1, len(nodes)):
                        nodes[i].escaped = True
                else:
                    for node in nodes:
                        node.escaped = True
            box = op.result
            if box is not None:
                node = self.getnode(box)
                node.escaped = False
                if op.opnum == rop.NEW or op.opnum == rop.NEW_WITH_VTABLE:
                    node.allocated_in_loop = True
                self.nodes[box] = node

    def new_arguments(self, op):
        newboxes = []
        for box in op.args:
            if isinstance(box, Box):
                instnode = self.nodes[box]
                box = instnode.source
            newboxes.append(box)
        return newboxes

    def rebuild_virtual(self, ops, node):
        assert node.virtual
        if node.cls is not None:
            ops.append(ResOperation(rop.NEW_WITH_VTABLE, [node.cls],
                                    node.source, node.size))
        else:
            ops.append(ResOperation(rop.NEW, [], node.source, node.size))
        for field, valuenode in node.cleanfields.iteritems():
            if valuenode.virtual:
                self.rebuild_virtual(ops, valuenode)
            ops.append(ResOperation(rop.SETFIELD_GC,
                     [node.source, valuenode.source], None, field))

    def optimize_guard(self, op):
        if op.is_foldable_guard():
            for arg in op.args:
                if not self.getnode(arg).const:
                    break
            else:
                return None
        assert len(op.suboperations) == 1
        op_fail = op.suboperations[0]
        op.suboperations = []
        self.rebuild_virtuals(op.suboperations, op_fail.args)
        op_fail.args = self.new_arguments(op_fail)
        op.suboperations.append(op_fail)
        op.args = self.new_arguments(op)
        return op

    def rebuild_virtuals(self, ops, args):
        self.already_build_nodes = {}
        for arg in args:
            node = self.getnode(arg)
            if node.virtual:
                self.rebuild_virtual(ops, node)

    def optimize_operations(self):
        self.additional_stores = {}
        self.additional_setarrayitems = {}
        newoperations = []
        opnum = 0
        for op in self.loop.operations:
            opnum += 1
            remove_op = False
            for opt in self.optimizations[op.opnum]:
                remove_op = opt(op, self)
                if remove_op:
                    break
            if remove_op:
                continue
            if op.is_guard():
                op = self.optimize_guard(op)
                if op is not None:
                    newoperations.append(op)
                continue
            # default handler
            if op.opnum == rop.FAIL or op.opnum == rop.JUMP:
                self.rebuild_virtuals(newoperations, op.args)
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

    def cleanup_nodes(self):
        for node in self.nodes.values():
            node.arrayfields.clear()
            node.cleanfields.clear()
    
    def optimize_loop(self, loop):
        self.nodes = {}
        self.field_caches = {}
        self.loop = loop
        self.find_nodes()
        self.cleanup_nodes()
        self.optimize_operations()

class ConsecutiveGuardClassRemoval(object):
    @staticmethod
    def optimize_guard_class(op, spec):
        instnode = spec.getnode(op.args[0])
        if instnode.cls is not None:
            return True
        instnode.cls = op.args[1]
        return False

    @staticmethod
    def optimize_oononnull(op, spec):
        # very simple optimization: if the class of something is known (via
        # guard_class) the thing cannot be a NULL
        instnode = spec.getnode(op.args[0])
        if instnode.cls is None:
            return False
        spec.nodes[op.result] = InstanceNode(ConstInt(1), const=True)
        return True

    @staticmethod
    def optimize_ooisnull(op, spec):
        # very simple optimization: if the class of something is known (via
        # guard_class) the thing cannot be a NULL
        instnode = spec.getnode(op.args[0])
        if instnode.cls is None:
            return False
        spec.nodes[op.result] = InstanceNode(ConstInt(0), const=True)
        return True


class SimpleVirtualOpt(object):
    @staticmethod
    def optimize_new_with_vtable(op, spec):
        node = spec.getnode(op.result)
        if node.escaped:
            return False
        node.virtual = True
        node.cls = op.args[0]
        node.size = op.descr
        return True

    @staticmethod
    def optimize_new(op, spec):
        node = spec.getnode(op.result)
        if node.escaped:
            return False
        node.virtual = True
        node.size = op.descr
        return True

    @staticmethod
    def optimize_setfield_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtual:
            return False
        field = op.descr
        node = spec.getnode(op.args[1])
        instnode.cleanfields[field] = node
        return True

    @staticmethod
    def optimize_getfield_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtual:
            return False
        field = op.descr
        spec.nodes[op.result] = instnode.cleanfields[field]
        return True

    optimize_getfield_gc_pure = optimize_getfield_gc

    @staticmethod
    def optimize_oononnull(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtual:
            return False
        spec.nodes[op.result] = InstanceNode(ConstInt(1), const=True)
        return True

    @staticmethod
    def optimize_ooisnull(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtual:
            return False
        spec.nodes[op.result] = InstanceNode(ConstInt(0), const=True)
        return True
    

specializer = Specializer([SimpleVirtualOpt(),
                           ConsecutiveGuardClassRemoval()])

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



