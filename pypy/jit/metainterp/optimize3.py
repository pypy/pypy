from pypy.rlib.objectmodel import r_dict
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.history import Const, Box, AbstractValue,\
     AbstractDescr, ConstObj
from pypy.jit.metainterp.optimize import av_eq, av_hash, sort_descrs
from pypy.jit.metainterp.specnode3 import VirtualInstanceSpecNode, \
     NotSpecNode, FixedClassSpecNode

   
class InstanceNode(object):
    def __init__(self, source, escaped=True):
        self.source = source
        self.escaped = escaped

    def __repr__(self):
        flags = ''
        if self.escaped:           flags += 'e'
        #if self.startbox:          flags += 's'
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
    
    def __init__(self, box):
        self.box = box

    def is_const(self):
        return isinstance(self.box, Const)

    def __repr__(self):
        flags = ''
        if self.is_const():        flags += 'c'
        return "<InstanceValue %s (%s)>" % (self.box, flags)


class LoopSpecializer(object):

    def __init__(self, optlist):
        self.optlist = optlist
        self.nodes = None
        self.loop = None
        self.dependency_graph = None
        
    def _init(self, loop):
        self.nodes = {}
        self.loop = loop
        self.dependency_graph = [] # XXX: it's used only by OptimizeVirtuals
        
    def newnode(self, *args, **kwds): # XXX RPython
        node = InstanceNode(*args, **kwds)
        for opt in self.optlist:
            opt.init_node(node)
        return node

    def getnode(self, box):
        try:
            return self.nodes[box]
        except KeyError:
            node = self.newnode(box)
            self.nodes[box] = node
            return node

    def find_nodes(self):
        assert not self.nodes
        for box in self.loop.inputargs:
            self.nodes[box] = self.newnode(box, escaped=False,)
                                           #startbox=True)

        for op in self.loop.operations:
            self._find_nodes_in_guard_maybe(op)
            for box in op.args:
                self.getnode(box)
            resbox = op.result
            if resbox is not None:
                self.nodes[resbox] = self.newnode(resbox)

            for optimization in self.optlist:
                optimization.find_nodes_for_op(self, op)

    def _find_nodes_in_guard_maybe(self, op):
        if op.is_guard():
            assert len(op.suboperations) == 1
            for arg in op.suboperations[0].args:
                self.getnode(arg)

    def recursively_find_escaping_values(self):
        for opt in self.optlist:
            opt.recursively_find_escaping_values(self)


    def intersect_input_and_output(self):
        # Step (3)
        self.recursively_find_escaping_values()
        jump = self.loop.operations[-1]
        assert jump.opnum == rop.JUMP
        specnodes = []
        for i in range(len(self.loop.inputargs)):
            enternode = self.nodes[self.loop.inputargs[i]]
            leavenode = self.getnode(jump.args[i])
            #specnodes.append(enternode.intersect(leavenode, self.nodes))
            specnodes.append(self.intersect_nodes(enternode, leavenode, self.nodes))
        self.specnodes = specnodes

    def intersect_nodes(self, a, b, nodes):
        for opt in self.optlist:
            specnode = opt.intersect_nodes(self, a, b, nodes)
            if specnode is not None:
                return specnode
        return NotSpecNode()

    def newinputargs(self):
        if self.loop.inputargs is not None:
            # closing a loop
            assert len(self.loop.inputargs) == len(self.specnodes)
            for i in range(len(self.specnodes)):
                box = self.loop.inputargs[i]
                self.specnodes[i].mutate_nodes(self.nodes[box])
            return self.expanded_version_of(self.loop.inputargs)
        else:
            # making a bridge
            return None

    def expanded_version_of(self, boxlist):
        newboxlist = []
        assert len(boxlist) == len(self.specnodes)
        for i in range(len(boxlist)):
            box = boxlist[i]
            specnode = self.specnodes[i]
            specnode.expand_boxlist(self.nodes[box], newboxlist)
        return newboxlist



class LoopOptimizer(object):

    def __init__(self, optlist):
        self.optlist = optlist
        self.spec = LoopSpecializer(optlist)
        self.fixedops = None
        self.values = None  # box --> InstanceValue
        

    def _init(self, loop, cpu):
        self.spec._init(loop)
        self.fixedops = {}
        self.values = {}
        self.loop = loop
        self.cpu = cpu

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
            val = self.newval(box)
            self.values[box] = val
            return val

    def setval(self, box):
        if box is None:
            return
        assert box not in self.values
        assert not isinstance(box, Const)
        self.values[box] = self.newval(box)

    def assertval(self, box, box2):
        if box in self.values:
            assert self.values[box].box is box2
        else:
            self.setval(box)
            self.values[box].box = box2

    def optimize_loop(self, loop, cpu):
        self._init(loop, cpu)
        self.spec.find_nodes()
        self.spec.intersect_input_and_output()
        newinputargs = self.spec.newinputargs()
        newoperations = self.optimize_operations(newinputargs)

        self.loop.specnodes = self.spec.specnodes
        self.loop.inputargs = newinputargs
        self.loop.operations = newoperations

    def optimize_operations(self, newinputargs):
        assert not self.values
        
        for box in newinputargs:
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
        #print "Length of the loop:", len(newoperations)
        return newoperations

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
                val = self.newval(box.constbox())
                self.values[box] = val
                return
        return op

    def _fixguard(self, op):
        if op.is_foldable_guard():
            for arg in op.args:
                if not self.getval(arg).is_const():
                    break
            else:
                return None
        assert len(op.suboperations) == 1
        op_fail = op.suboperations[0]
        assert op_fail.opnum == rop.FAIL
        oplist = self.rebuild_ops(op_fail)
        op_fail.args = self.new_arguments(op_fail) # modify in place, see optimize.py
        newop = op.clone()
        newop.args = self.new_arguments(newop)
        newop.suboperations = oplist + [op_fail]
        return newop

    def rebuild_ops(self, op):
        oplist = []
        memo = {}
        for box in op.args:
            if isinstance(box, Const) or box not in self.spec.nodes:
                continue
            node = self.spec.getnode(box)
            self.rebuild_box(oplist, memo, node, box)
        return oplist

    def rebuild_box(self, oplist, memo, node, box):
        if not isinstance(box, Box):
            return box
        if box in memo:
            return box
        memo[box] = None
        for opt in self.optlist:
            opt.rebuild_box(self, oplist, memo, node, box)
        return box


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
        elif hasattr(self, 'find_nodes_default_op'):
            return self.find_nodes_default_op.im_func
        return None

    # hooks for LoopSpecializer
    # -------------------------
    
    def init_node(self, node):
        pass

    def find_nodes_for_op(self, spec, op):
        func = self.find_nodes_ops[op.opnum]
        if func:
            func(self, spec, op)

    def recursively_find_escaping_values(self, spec):
        pass

    def intersect_nodes(self, spec, a, b, nodes):
        return None


    # hooks for LoopOptimizer
    # -------------------------

    def init_value(self, value):
        pass

    def handle_op(self, spec, op):
        func = self.operations[op.opnum]
        return func(self, spec, op)
    
    def handle_default_op(self, spec, op):
        return op

    def rebuild_box(self, opt, oplist, memo, node, box):
        pass


class OptimizeGuards(AbstractOptimization):

    def init_value(self, val):
        val.cls = None

    def guard_class(self, opt, op):
        val = opt.getval(op.args[0])
        if val.cls is not None:
            # assert that they're equal maybe
            return
        val.cls = opt.newval(op.args[1].constbox())
        return op

    def guard_value(self, opt, op):
        val = opt.getval(op.args[0])
        assert isinstance(op.args[1], Const)
        if val.is_const():
            return
        op = opt.fixop(op)
        val.box = op.args[0].constbox()
        return op


class OptimizeVirtuals(AbstractOptimization):

    def init_node(self, node):
        node.virtual = False
        node.known_class = None
        node.origfields = r_dict(av_eq, av_hash)
        node.curfields = r_dict(av_eq, av_hash)

    def find_nodes_default_op(self, spec, op):
        if not op.has_no_side_effect():
            #spec.first_escaping_op = False
            for box in op.args:
                if isinstance(box, Box):
                    spec.getnode(box).escaped = True

    def find_nodes_jump(self, spec, op):
        pass # this makes find_nodes_default_op not called

    def find_nodes_new_with_vtable(self, spec, op):
        box = op.result
        node = spec.newnode(box, escaped=False)
        node.known_class = spec.newnode(op.args[0])
        spec.nodes[box] = node

    def find_nodes_guard_class(self, spec, op):
        node = spec.getnode(op.args[0])
        if node.known_class is None:
            node.known_class = spec.newnode(op.args[1])

    def find_nodes_setfield_gc(self, spec, op):
        instnode = spec.getnode(op.args[0])
        fielddescr = op.descr
        fieldnode = spec.getnode(op.args[1])
        assert isinstance(fielddescr, AbstractValue)
        instnode.curfields[fielddescr] = fieldnode
        spec.dependency_graph.append((instnode, fieldnode))

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
            fieldnode = spec.newnode(resbox, escaped=False)
##             if instnode.startbox:
##                 fieldnode.startbox = True
            spec.dependency_graph.append((instnode, fieldnode))
            instnode.origfields[fielddescr] = fieldnode
        spec.nodes[resbox] = fieldnode

    def add_to_dependency_graph(self, a, b, dep_graph):
        dep_graph.append((a, b))
        for ofs, node in a.origfields.items():
            if ofs in b.curfields:
                self.add_to_dependency_graph(node, b.curfields[ofs], dep_graph)

    def recursively_find_escaping_values(self, spec):
        end_args = spec.loop.operations[-1].args
        assert len(spec.loop.inputargs) == len(end_args)
        memo = {}
        for i in range(len(end_args)):
            end_box = end_args[i]
##             if isinstance(end_box, Box):
##                 spec.nodes[end_box].escape_if_startbox(memo, spec.cpu)
        for i in range(len(end_args)):
            box = spec.loop.inputargs[i]
            other_box = end_args[i]
            if isinstance(other_box, Box):
                self.add_to_dependency_graph(spec.nodes[box],
                                             spec.nodes[other_box],
                                             spec.dependency_graph)
        # XXX find efficient algorithm, we're too fried for that by now
        done = False
        while not done:
            done = True
            for instnode, fieldnode in spec.dependency_graph:
                if instnode.escaped:
                    if not fieldnode.escaped:
                        fieldnode.escaped = True
                        done = False

    def intersect_nodes(self, spec, a, b, nodes):
        if not b.known_class:
            return NotSpecNode()
        if a.known_class:
            if not a.known_class.source.equals(b.known_class.source):
                #raise CancelInefficientLoop
                return NotSpecNode()
            known_class_box = a.known_class.source
        else:
            known_class_box = b.known_class.source
        if b.escaped:
            if a.known_class is None:
                return NotSpecNode()
##             if isinstance(known_class_box, FixedList):
##                 return NotSpecNode()
            return FixedClassSpecNode(known_class_box)
        
        assert a is not b
        fields = []
        d = b.curfields
        lst = d.keys()
        sort_descrs(lst)
        for ofs in lst:
            node = d[ofs]
            if ofs not in a.origfields:
                box = node.source.clonebox()
                a.origfields[ofs] = spec.newnode(box, escaped=False)
                a.origfields[ofs].known_class = node.known_class
                nodes[box] = a.origfields[ofs]
            specnode = spec.intersect_nodes(a.origfields[ofs], node, nodes)
            fields.append((ofs, specnode))
##         if isinstance(known_class_box, FixedList):
##             return VirtualFixedListSpecNode(known_class_box, fields,
##                                             b.cursize)
        return VirtualInstanceSpecNode(known_class_box, fields)

    # ---------------------------------------

    def _new_obj(self, cpu, clsbox, resbox):
##         if isinstance(clsbox, FixedList):
##             ad = clsbox.arraydescr
##             sizebox = ConstInt(node.cursize)
##             op = ResOperation(rop.NEW_ARRAY, [sizebox], box,
##                               descr=ad)
        if cpu.is_oo and isinstance(clsbox, ConstObj):
            # it's probably a ootype new
            cls = clsbox.getobj()
            typedescr = cpu.class_sizes[cls]
            return ResOperation(rop.NEW_WITH_VTABLE, [clsbox], resbox,
                                descr=typedescr)
        else:
            assert not cpu.is_oo
            vtable = clsbox.getint()
            if cpu.translate_support_code:
                vtable_addr = cpu.cast_int_to_adr(vtable)
                size = cpu.class_sizes[vtable_addr]
            else:
                size = cpu.class_sizes[vtable]
            return ResOperation(rop.NEW_WITH_VTABLE, [clsbox], resbox,
                                descr=size)

    def rebuild_box(self, opt, oplist, memo, node, box):
        if not node.virtual:
            return
        clsbox = node.known_class.source
        oplist.append(self._new_obj(opt.cpu, clsbox, box))
        # create the InstanceValue for this box, or reuse the old one if it
        # already exists (e.g., if you rebuild the same box twice, in two
        # different guards)
        opt.assertval(box, box)
        for descr, node in node.curfields.items():
            fieldbox = opt.rebuild_box(oplist, memo, node, node.source)
##             if isinstance(clsbox, FixedList):
##                 op = ResOperation(rop.SETARRAYITEM_GC,
##                                   [box, descr, fieldbox],
##                                   None, descr=clsbox.arraydescr)
##             else:
            assert isinstance(descr, AbstractDescr)
            op = ResOperation(rop.SETFIELD_GC, [box, fieldbox],
                              None, descr=descr)
            oplist.append(op)

    def jump(self, opt, op):
        args = opt.spec.expanded_version_of(op.args)
        for arg in args:
            if arg in opt.spec.nodes:
                assert not opt.spec.nodes[arg].virtual
        #self.cleanup_field_caches(newoperations)
        op = op.clone()
        op.args = args
        return op

    def guard_class(self, opt, op):
        node = opt.spec.getnode(op.args[0])
        if node.known_class is not None:
            assert op.args[1].equals(node.known_class.source)
            return None
        return op

    def new_with_vtable(self, opt, op):
        node = opt.spec.getnode(op.result)
        if not node.escaped:
            node.virtual = True
            assert node.known_class is not None
            return None
        return op

    def getfield_gc(self, opt, op):
        node = opt.spec.getnode(op.args[0])
        descr = op.descr
        assert isinstance(descr, AbstractValue)
        if node.virtual:
            fieldnode = node.curfields[descr]
            resbox = op.result
            opt.assertval(resbox, fieldnode.source)
            return None
        return op

    def setfield_gc(self, opt, op):
        node = opt.spec.getnode(op.args[0])
        valuenode = opt.spec.getnode(op.args[1])
        descr = op.descr
        if node.virtual:
            node.curfields[descr] = valuenode
            return None
        return op


# -------------------------------------------------------------------

OPTLIST = [
    OptimizeVirtuals(),
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
        opt.optimize_loop(loop, cpu)
        return None

def optimize_bridge(options, old_loops, loop, cpu=None, spec=None):
    optimize_loop(options, [], loop, cpu, spec)
    return old_loops[0]

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)

    @staticmethod
    def get_optimizer_name():
        return __file__
