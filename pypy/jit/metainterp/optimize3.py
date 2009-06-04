from pypy.jit.metainterp.resoperation import rop, ResOperation
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
    fixedops = None

    def __init__(self, optlist):
        self.optlist = optlist

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

    def find_nodes(self):
        for op in self.loop.operations:
            self._find_nodes_in_guard_maybe(op)
            if self._is_pure_and_constfoldable(op):
                box = op.result
                assert box is not None
                self.nodes[box] = InstanceNode(box.constbox(), const=True)
            else:
                # default case
                for box in op.args:
                    self.getnode(box)
                box = op.result
                if box is not None:
                    self.nodes[box] = InstanceNode(box)

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

    def new_arguments(self, op):
        newboxes = []
        for box in op.args:
            if isinstance(box, Box):
                instnode = self.nodes[box]
                box = instnode.source
            newboxes.append(box)
        return newboxes

    def optimize_operations(self):
        newoperations = []
        for op in self.loop.operations:
            newop = op
            for optimization in self.optlist:
                newop = optimization.handle_op(self, newop)
                if newop is None:
                    break
            newop = self.fixop(newop)
            if newop is not None:
                newoperations.append(newop)
        print "Length of the loop:", len(newoperations)
        self.loop.operations = newoperations

    def fixop(self, op):
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
                instnode = InstanceNode(box.constbox(), const=True)
                self.nodes[box] = instnode
                return
        return op

    def _fixguard(self, op):
        if op.is_foldable_guard():
            for arg in op.args:
                if not self.nodes[arg].const:
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

    def optimize_loop(self, loop):
        self.nodes = {}
        self.field_caches = {}
        self.fixedops = {}
        self.loop = loop
        self.find_nodes()
        self.optimize_operations()

# -------------------------------------------------------------------

class AbstractOptimization(object):

    def __init__(self):
        'NOT_RPYTHON'
        operations = [None] * (rop._LAST+1)
        for key, value in rop.__dict__.items():
            if key.startswith('_'):
                continue
            methname = key.lower()
            if hasattr(self, methname):
                func = getattr(self, methname).im_func
            else:
                func = getattr(self, 'handle_default_op').im_func
            operations[value] = func
        self.operations = operations

    def handle_op(self, spec, op):
        func = self.operations[op.opnum]
        return func(self, spec, op)
    
    def handle_default_op(self, spec, op):
        return op



class OptimizeGuards(AbstractOptimization):

    def guard_class(self, spec, op):
        node = spec.nodes[op.args[0]]
        if node.cls is not None:
            # assert that they're equal maybe
            return
        node.cls = InstanceNode(op.args[1], const=True)
        return op

    def guard_value(self, spec, op):
        instnode = spec.nodes[op.args[0]]
        assert isinstance(op.args[1], Const)
        if instnode.const:
            return
        op = spec.fixop(op)
        instnode.const = True
        instnode.source = op.args[0].constbox()
        return op

##     def guard_nonvirtualized(self, spec, op):
##         return

##     def handle_default_op(self, spec, op):
##         if op.is_guard():
##             return self.optimize_guard(op)
##         return op



# -------------------------------------------------------------------

OPTLIST = [
    OptimizeGuards(),
    ]
specializer = Specializer(OPTLIST)

def optimize_loop(options, old_loops, loop, cpu=None, spec=None):
    if spec is None:
        spec = specializer
    if old_loops:
        assert len(old_loops) == 1
        return old_loops[0]
    else:
        spec.optimize_loop(loop)
        return None

def optimize_bridge(options, old_loops, loop, cpu=None, spec=None):
    optimize_loop(options, [], loop, cpu, spec)
    return old_loops[0]

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)


