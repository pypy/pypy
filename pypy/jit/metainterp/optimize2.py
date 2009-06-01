
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
        self.virtualized = False
        self.allocated_in_loop = False
        self.vdesc = None
        self.escaped = escaped
        self.virtual = False
        self.size = None

    def __repr__(self):
        flags = ''
        if self.escaped:           flags += 'e'
        #if self.startbox:          flags += 's'
        if self.const:             flags += 'c'
        if self.virtual:           flags += 'v'
        if self.virtualized:       flags += 'V'
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

    def _guard_for_node(self, node):
        gop = ResOperation(rop.GUARD_NONVIRTUALIZED,
                           [node.source], None)
        gop.vdesc = node.vdesc
        gop.suboperations = [ResOperation(rop.FAIL, [], None)]
        return gop

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
        rebuild = False
        for arg in args:
            node = self.getnode(arg)
            if node.virtual:
                self.rebuild_virtual(ops, node)
            if node.virtualized:
                rebuild = True
        # modification in place. Reason for this is explained in mirror
        # in optimize.py
        # XXX in general, it's probably not correct, but should work
        #     because we always pass frame anyway
        if rebuild:
            for node, d in self.additional_stores.iteritems():
                for field, fieldnode in d.iteritems():
                    if fieldnode.virtual:
                        self.rebuild_virtual(ops, fieldnode)
                    gop = self._guard_for_node(node)
                    ops.append(gop)
                    ops.append(ResOperation(rop.SETFIELD_GC,
                               [node.source, fieldnode.source], None, field))
            for node, d in self.additional_setarrayitems.iteritems():
                for field, (fieldnode, descr) in d.iteritems():
                    box = fieldnode.source
                    if fieldnode.virtual:
                        self.rebuild_virtual(ops, fieldnode)
                    gop = self._guard_for_node(node)
                    ops.append(gop) 
                    ops.append(ResOperation(rop.SETARRAYITEM_GC,
                              [node.source, ConstInt(field), box], None, descr))

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

class SimpleVirtualizableOpt(object):
    @staticmethod
    def find_nodes_setfield_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return False
        field = op.descr
        if field not in instnode.vdesc.virtuals:
            return False
        node = spec.getnode(op.args[1])
        instnode.cleanfields[field] = node
        return True

    @staticmethod
    def find_nodes_getfield_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return False
        field = op.descr
        if field not in instnode.vdesc.virtuals:
            return False
        node = instnode.cleanfields.get(field, None)
        if node:
            spec.nodes[op.result] = node
            node.virtualized = True
            return True
        node = spec.getnode(op.result)
        instnode.cleanfields[field] = node
        node.virtualized = True
        return False

    @staticmethod
    def find_nodes_setarrayitem_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return False
        field = op.args[1].getint()
        node = spec.getnode(op.args[2])
        instnode.arrayfields[field] = node
        return True

    @staticmethod
    def find_nodes_getarrayitem_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return False
        field = op.args[1].getint()
        node = instnode.arrayfields.get(field, None)
        if node is not None:
            spec.nodes[op.result] = node
            return True
        instnode.arrayfields[field] = node
        return False

    @staticmethod
    def find_nodes_guard_nonvirtualized(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.allocated_in_loop:
            instnode.virtualized = True
            instnode.vdesc = op.vdesc
        return False

    @staticmethod
    def optimize_guard_nonvirtualized(op, spec):
        return True

    @staticmethod
    def optimize_getfield_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return False
        field = op.descr
        if field not in instnode.vdesc.virtuals:
            return False
        node = instnode.cleanfields.get(field, None)
        if node is not None:
            spec.nodes[op.result] = node
            return True
        node = spec.getnode(op.result)
        instnode.cleanfields[field] = node
        return False

    @staticmethod
    def optimize_setfield_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return False
        field = op.descr
        if field not in instnode.vdesc.virtuals:
            return False
        node = spec.getnode(op.args[1])
        instnode.cleanfields[field] = node
        # we never set it here
        d = spec.additional_stores.setdefault(instnode, {})
        d[field] = node
        return True

    @staticmethod
    def optimize_getarrayitem_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return False
        if not spec.getnode(op.args[1]).const:
            raise VirtualizedListAccessedWithVariableArg()
        field = spec.getnode(op.args[1]).source.getint()
        node = instnode.arrayfields.get(field, None)
        if node is not None:
            spec.nodes[op.result] = node
            return True
        node = spec.getnode(op.result)
        instnode.arrayfields[field] = node
        return False

    @staticmethod
    def optimize_setarrayitem_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return False
        argnode = spec.getnode(op.args[1])
        if not argnode.const:
            raise VirtualizedListAccessedWithVariableArg()
        fieldnode = spec.getnode(op.args[2])
        field = argnode.source.getint()
        instnode.arrayfields[field] = fieldnode
        d = spec.additional_setarrayitems.setdefault(instnode, {})
        d[field] = (fieldnode, op.descr)
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
    

specializer = Specializer([SimpleVirtualizableOpt(),
                           SimpleVirtualOpt(),
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



