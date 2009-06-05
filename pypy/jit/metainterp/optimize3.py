from pypy.rlib.objectmodel import r_dict
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.history import Const, Box, AbstractValue
from pypy.jit.metainterp.optimize import av_eq, av_hash


class InstanceNode(object):
    def __init__(self, source, const=False, escaped=True):
        self.source = source
        if const:
            assert isinstance(source, Const)
        self.const = const
        self.escaped = escaped

    def __repr__(self):
        flags = ''
        if self.escaped:           flags += 'e'
        #if self.startbox:          flags += 's'
        if self.const:             flags += 'c'
        #if self.virtual:           flags += 'v'
        #if self.virtualized:       flags += 'V'
        return "<InstanceNode %s (%s)>" % (self.source, flags)


class InstanceValue(object):
    """
    optimize_operations does an abstract interpretation of the loop.

    Each box is associated to an InstanceValue, that carries on extra
    informations about the box, e.g. whether it is a constant or its class is
    statically known.

    The concrete optimizations can modify the value of the box attribute: in
    that case, the optimized loop will contains a reference to the new box
    instead of the old one.
    """
    
    def __init__(self, box, const=False):
        self.box = box
        if const:
            assert isinstance(box, Const)
        self.const = const

    def __repr__(self):
        flags = ''
        if self.const:             flags += 'c'
        return "<InstanceValue %s (%s)>" % (self.box, flags)


class LoopSpecializer(object):

    def __init__(self, optlist):
        self.optlist = optlist
        self.nodes = None
        self.loop = None

    def _init(self, loop):
        self.nodes = {}
        self.loop = loop

    def newnode(self, *args, **kwds): # XXX RPython
        node = InstanceNode(*args, **kwds)
        for opt in self.optlist:
            opt.init_node(node)
        return node

    def getnode(self, box):
        try:
            return self.nodes[box]
        except KeyError:
            if isinstance(box, Const):
                node = self.newnode(box, const=True)
            else:
                node = self.newnode(box)
            self.nodes[box] = node
            return node

    def find_nodes(self):
        for box in self.loop.inputargs:
            self.nodes[box] = self.newnode(box, escaped=False,)
                                           #startbox=True)

        for op in self.loop.operations:
            self._find_nodes_in_guard_maybe(op)
            if self._is_pure_and_constfoldable(op):
                box = op.result
                assert box is not None
                self.nodes[box] = self.newnode(box.constbox(), const=True)
            else:
                # default case
                for box in op.args:
                    self.getnode(box)
                box = op.result
                if box is not None:
                    self.nodes[box] = self.newnode(box)

            for optimization in self.optlist:
                optimization.find_nodes_for_op(self, op)

    def _find_nodes_in_guard_maybe(self, op):
        if op.is_guard():
            assert len(op.suboperations) == 1
            for arg in op.suboperations[0].args:
                self.getnode(arg)

    def _is_pure_and_constfoldable(self, op):
        if not op.is_always_pure():
            return False
        for arg in op.args:
            if not self.getnode(arg).const:
                return False
        return True


class LoopOptimizer(object):

    def __init__(self, optlist):
        self.optlist = optlist
        self.spec = LoopSpecializer(optlist)
        self.fixedops = None
        self.values = None  # box --> InstanceValue
        

    def _init(self, loop):
        self.spec._init(loop)
        self.fixedops = {}
        self.values = {}
        self.loop = loop

    def newval(self, *args, **kwds): # XXX RPython
        val = InstanceValue(*args, **kwds)
        for opt in self.optlist:
            opt.init_value(val)
        return val

    def getval(self, box):
        try:
            return self.values[box]
        except KeyError:
            assert isinstance(box, Const)
            val = self.newval(box, const=True)
            self.values[box] = val
            return val

    def setval(self, box):
        assert box not in self.values
        assert not isinstance(box, Const)
        self.values[box] = self.newval(box)

    def optimize_loop(self, loop):
        self._init(loop)
        self.spec.find_nodes()
        self.optimize_operations()

    def optimize_operations(self):
        for box in self.loop.inputargs:
            self.setval(box) #  startbox=True)

        newoperations = []
        for op in self.loop.operations:
            newop = op
            for optimization in self.optlist:
                newop = optimization.handle_op(self, newop)
                if newop is None:
                    break
            newop = self.fixop(newop)
            if newop is not None:
                self.setval(newop.result)
                newoperations.append(newop)
        print "Length of the loop:", len(newoperations)
        self.loop.operations = newoperations

    def new_arguments(self, op):
        newboxes = []
        for box in op.args:
            if isinstance(box, Box):
                val = self.values[box]
                box = val.box
            newboxes.append(box)
        return newboxes

    def fixop(self, op):
        """
        Fix the arguments of the op by using the box stored on the
        InstanceValue of each argument.
        """
        if op is None:
            return None
        if op in self.fixedops:
            return op
        if op.is_guard():
            newop = self._fixguard(op)
        else:
            newop = self._fixop_default(op)
        self.fixedops[newop] = None
        return newop

    def _fixop_default(self, op):
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
                val = self.newval(box.constbox(), const=True)
                self.values[box] = val
                return
        return op

    def _fixguard(self, op):
        if op.is_foldable_guard():
            for arg in op.args:
                if not self.getval(arg).const:
                    break
            else:
                return None
        op.args = self.new_arguments(op)
        assert len(op.suboperations) == 1
        op_fail = op.suboperations[0]
        op_fail.args = self.new_arguments(op_fail)
        # modification in place. Reason for this is explained in mirror
        # in optimize.py
        op.suboperations = [op_fail]
        return op


# -------------------------------------------------------------------

class AbstractOptimization(object):

    def __init__(self):
        'NOT_RPYTHON'
        operations = [None] * (rop._LAST+1)
        find_nodes = [None] * (rop._LAST+1)
        for key, value in rop.__dict__.items():
            if key.startswith('_'):
                continue
            methname = key.lower()
            operations[value] = self._get_handle_method(methname)
            find_nodes[value] = self._get_find_nodes_method(methname)
        self.operations = operations
        self.find_nodes_ops = find_nodes

    def _get_handle_method(self, methname):
        'NOT_RPYTHON'
        if hasattr(self, methname):
            return getattr(self, methname).im_func
        else:
            return getattr(self, 'handle_default_op').im_func

    def _get_find_nodes_method(self, methname):
        'NOT_RPYTHON'
        methname = 'find_nodes_' + methname
        if hasattr(self, methname):
            return getattr(self, methname).im_func
        return None

    # hooks for LoopSpecializer
    # -------------------------
    
    def init_node(self, node):
        pass

    def find_nodes_for_op(self, spec, op):
        func = self.find_nodes_ops[op.opnum]
        if func:
            func(self, spec, op)


    # hooks for LoopOptimizer
    # -------------------------

    def init_value(self, value):
        pass

    def handle_op(self, spec, op):
        func = self.operations[op.opnum]
        return func(self, spec, op)
    
    def handle_default_op(self, spec, op):
        return op



class OptimizeGuards(AbstractOptimization):

    def init_value(self, val):
        val.cls = None

    def guard_class(self, opt, op):
        val = opt.values[op.args[0]]
        if val.cls is not None:
            # assert that they're equal maybe
            return
        val.cls = opt.newval(op.args[1], const=True)
        return op

    def guard_value(self, opt, op):
        val = opt.values[op.args[0]]
        assert isinstance(op.args[1], Const)
        if val.const:
            return
        op = opt.fixop(op)
        val.const = True
        val.box = op.args[0].constbox()
        return op



class OptimizeVirtuals(AbstractOptimization):

    def init_node(self, node):
        node.origfields = r_dict(av_eq, av_hash)
        node.curfields = r_dict(av_eq, av_hash)
        node.cls = None

    def find_nodes_guard_class(self, spec, op):
        # XXX: how does this relate to OptimizeGuards.guard_class?
        instnode = spec.getnode(op.args[0])
        if instnode.cls is None:
            instnode.cls = spec.newnode(op.args[1], const=True)

    def find_nodes_new_with_vtable(self, spec, op):
        box = op.result
        instnode = spec.newnode(box, escaped=False)
        instnode.cls = spec.newnode(op.args[0], const=True)
        spec.nodes[box] = instnode

    def find_nodes_setfield_gc(self, spec, op):
        instnode = spec.getnode(op.args[0])
        fielddescr = op.descr
        fieldnode = spec.getnode(op.args[1])
        assert isinstance(fielddescr, AbstractValue)
        instnode.curfields[fielddescr] = fieldnode
##         self.dependency_graph.append((instnode, fieldnode))

    def find_nodes_getfield_gc(self, spec, op):
        instnode = spec.getnode(op.args[0])
        fielddescr = op.descr
        resbox = op.result
        assert isinstance(fielddescr, AbstractValue)
        if fielddescr in instnode.curfields:
            fieldnode = instnode.curfields[fielddescr]
        elif fielddescr in instnode.origfields:
            fieldnode = instnode.origfields[fielddescr]
        else:
            fieldnode = InstanceNode(resbox, escaped=False)
##             if instnode.startbox:
##                 fieldnode.startbox = True
##             self.dependency_graph.append((instnode, fieldnode))
            instnode.origfields[fielddescr] = fieldnode
        spec.nodes[resbox] = fieldnode


# -------------------------------------------------------------------

OPTLIST = [
    OptimizeGuards(),
    ]

loop_optimizer = LoopOptimizer(OPTLIST)

def optimize_loop(options, old_loops, loop, cpu=None, opt=None):
    if opt is None:
        opt = loop_optimizer
    if old_loops:
        assert len(old_loops) == 1
        return old_loops[0]
    else:
        opt.optimize_loop(loop)
        return None

def optimize_bridge(options, old_loops, loop, cpu=None, spec=None):
    optimize_loop(options, [], loop, cpu, spec)
    return old_loops[0]

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)


