from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import (Box, Const, ConstInt, BoxInt, BoxPtr,
                                         ResOperation, AbstractDescr,
                                         Options, AbstractValue, ConstPtr,
                                         ConstObj)
from pypy.jit.metainterp.specnode4 import (FixedClassSpecNode,
                                           prebuiltNotSpecNode,
                                           VirtualInstanceSpecNode)
from pypy.jit.metainterp import executor
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import r_dict


def av_eq(self, other):
    return self.sort_key() == other.sort_key()

def av_hash(self):
    return self.sort_key()

class InstanceNode(object):
    def __init__(self, source, escaped=True, startbox=False, const=False):
        if isinstance(source, Const):
            assert const
        self.source = source       # a Box
        self.escaped = escaped
        self.startbox = startbox
        self.virtual = False
        self.const = const
        self.cls = None
        self.origfields = r_dict(av_eq, av_hash)
        self.curfields = r_dict(av_eq, av_hash)

    def is_nonzero(self):
        return self.cls is not None or (self.const and self.source.get_() != 0)

    def is_zero(self):
        return self.const and self.source.get_() == 0

    def escape_if_startbox(self, memo, cpu):
        if self in memo:
            return
        memo[self] = None
        if self.startbox:
            self.escaped = True
        for node in self.curfields.values():
            node.escape_if_startbox(memo, cpu)

    def add_to_dependency_graph(self, other, dep_graph):
        dep_graph.append((self, other))
        for ofs, node in self.origfields.items():
            if ofs in other.curfields:
                node.add_to_dependency_graph(other.curfields[ofs], dep_graph)

    def intersect(self, other, nodes):
        if not other.cls:
            return prebuiltNotSpecNode
        if self.cls:
            if not self.cls.source.equals(other.cls.source):
                return prebuiltNotSpecNode
            known_class = self.cls.source
        else:
            known_class = other.cls.source
        if other.escaped:
            if self.cls is None:
                return prebuiltNotSpecNode
            return FixedClassSpecNode(known_class)
        else:
            assert self is not other
            fields = []
            d = other.curfields
            lst = d.keys()
            sort_descrs(lst)
            for ofs in lst:
                node = d[ofs]
                if ofs not in self.origfields:
                    box = node.source.clonebox()
                    self.origfields[ofs] = InstanceNode(box, escaped=False)
                    self.origfields[ofs].cls = node.cls
                    nodes[box] = self.origfields[ofs]
                specnode = self.origfields[ofs].intersect(node, nodes)
                fields.append((ofs, specnode))
            return VirtualInstanceSpecNode(known_class, fields)

    def __repr__(self):
        flags = ''
        if self.escaped:           flags += 'e'
        if self.startbox:          flags += 's'
        if self.const:             flags += 'c'
        if self.virtual:           flags += 'v'
        return "<InstanceNode %s (%s)>" % (self.source, flags)

def optimize_loop(options, old_loops, loop, cpu=None):
    if not options.specialize:         # for tests only
        if old_loops:
            return old_loops[0]
        else:
            return None

    # This does "Perfect specialization" as per doc/jitpl5.txt.
    perfect_specializer = PerfectSpecializer(loop, options, cpu)
    perfect_specializer.find_nodes()
    perfect_specializer.intersect_input_and_output()
    for old_loop in old_loops:
        if perfect_specializer.match_exactly(old_loop):
            return old_loop
    perfect_specializer.optimize_loop()
    return None

def optimize_bridge(options, old_loops, loop, cpu=None):
    if not options.specialize:         # for tests only
        return old_loops[0]

    perfect_specializer = PerfectSpecializer(loop, options, cpu)
    perfect_specializer.find_nodes()
    for old_loop in old_loops:
        if perfect_specializer.match(old_loop):
            # xxx slow, maybe
            # XXX the next loop is a big hack.  Ideally it should set cls=None
            # to prevent assuming something about the cls -- but only if there
            # is no code in the previous loop that checks the cls.
            for node in perfect_specializer.nodes.values():
                if node.startbox:
                    node.cls = None
                    assert not node.virtual
            perfect_specializer.propagate_escapes()
            perfect_specializer.adapt_for_match(old_loop)
            perfect_specializer.optimize_loop()
            return old_loop
    return None     # no loop matches

class PerfectSpecializer(object):
    _allow_automatic_node_creation = False

    def __init__(self, loop, options=Options(), cpu=None):
        self.loop = loop
        self.options = options
        self.cpu = cpu
        self.nodes = {}
        self.dependency_graph = []

    def getnode(self, box):
        try:
            return self.nodes[box]
        except KeyError:
            if isinstance(box, Const):
                node = InstanceNode(box, escaped=True, const=True)
            else:
                assert self._allow_automatic_node_creation
                node = InstanceNode(box, escaped=True, startbox=True)
            self.nodes[box] = node
            return node

    def getsource(self, box):
        if isinstance(box, Const):
            return box
        return self.nodes[box].source

    def find_nodes_setfield(self, instnode, ofs, fieldnode):
        assert isinstance(ofs, AbstractValue)
        instnode.curfields[ofs] = fieldnode
        self.dependency_graph.append((instnode, fieldnode))

    def find_nodes_getfield(self, instnode, field, box):
        assert isinstance(field, AbstractValue)
        if field in instnode.curfields:
            fieldnode = instnode.curfields[field]
        elif field in instnode.origfields:
            fieldnode = instnode.origfields[field]
        else:
            fieldnode = InstanceNode(box, escaped=False)
            if instnode.startbox:
                fieldnode.startbox = True
            self.dependency_graph.append((instnode, fieldnode))
            instnode.origfields[field] = fieldnode
        self.nodes[box] = fieldnode

    def find_nodes(self):
        # Steps (1) and (2)
        if self.loop.inputargs is not None:
            for box in self.loop.inputargs:
                self.nodes[box] = InstanceNode(box, escaped=False,
                                               startbox=True)
        else:
            self._allow_automatic_node_creation = True
        #
        for op in self.loop.operations:
            #print '| ' + op.repr()
            opnum = op.opnum
            if opnum == rop.JUMP:
                break
            elif opnum == rop.NEW_WITH_VTABLE:
                box = op.result
                instnode = InstanceNode(box, escaped=False)
                instnode.cls = InstanceNode(op.args[0], const=True)
                self.nodes[box] = instnode
                continue
            elif opnum == rop.SETFIELD_GC:
                instnode = self.getnode(op.args[0])
                field = op.descr
                self.find_nodes_setfield(instnode, field,
                                         self.getnode(op.args[1]))
                continue
            elif opnum == rop.GETFIELD_GC:
                instnode = self.getnode(op.args[0])
                field = op.descr
                box = op.result
                self.find_nodes_getfield(instnode, field, box)
                continue
            elif opnum == rop.GETFIELD_GC_PURE:
                instnode = self.getnode(op.args[0])
                field = op.descr
                if not instnode.const:
                    box = op.result
                    self.find_nodes_getfield(instnode, field, box)
                    continue
            elif opnum == rop.GUARD_CLASS:
                instnode = self.getnode(op.args[0])
                if instnode.cls is None:
                    instnode.cls = InstanceNode(op.args[1], const=True)
                continue
            elif opnum == rop.GUARD_VALUE:
                instnode = self.getnode(op.args[0])
                assert isinstance(op.args[1], Const)
                # XXX need to think more about the 'const' attribute
                #     (see test_send.test_indirect_call_unknown_object_1)
                #self.nodes[instnode.source] = InstanceNode(op.args[1],
                #                                           const=True)
                continue
            elif op.is_always_pure():
                is_pure = True
                for arg in op.args:
                    if not self.getnode(arg).const:
                        is_pure = False
                if is_pure:
                    box = op.result
                    assert box is not None
                    self.nodes[box] = InstanceNode(box.constbox(),
                                                   escaped=True,
                                                   const=True)
                    continue
            elif not op.has_no_side_effect():
                # default case
                for box in op.args:
                    if isinstance(box, Box):
                        self.getnode(box).escaped = True
            if op.is_guard():
                self.find_nodes_guard(op)
            box = op.result
            if box is not None:
                self.nodes[box] = InstanceNode(box, escaped=True)

    def find_nodes_guard(self, op):
        assert len(op.suboperations) == 1
        for arg in op.suboperations[0].args:
            self.getnode(arg)

    def recursively_find_escaping_values(self):
        end_args = self.loop.operations[-1].args
        assert len(self.loop.inputargs) == len(end_args)
        memo = {}
        for i in range(len(end_args)):
            end_box = end_args[i]
            if isinstance(end_box, Box):
                self.nodes[end_box].escape_if_startbox(memo, self.cpu)
        for i in range(len(end_args)):
            box = self.loop.inputargs[i]
            other_box = end_args[i]
            if isinstance(other_box, Box):
                self.nodes[box].add_to_dependency_graph(self.nodes[other_box],
                                                        self.dependency_graph)
        self.propagate_escapes()

    def propagate_escapes(self):
        # XXX find efficient algorithm, we're too fried for that by now
        done = False
        while not done:
            done = True
            for instnode, fieldnode in self.dependency_graph:
                if instnode.escaped:  ## and not instnode.virtualized:
                    if not fieldnode.escaped:
                        fieldnode.escaped = True
                        done = False

    def intersect_input_and_output(self):
        # Step (3)
        self.recursively_find_escaping_values()
        jump = self.loop.operations[-1]
        assert jump.opnum == rop.JUMP
        specnodes = []
        for i in range(len(self.loop.inputargs)):
            enternode = self.nodes[self.loop.inputargs[i]]
            leavenode = self.getnode(jump.args[i])
            specnodes.append(enternode.intersect(leavenode, self.nodes))
        self.specnodes = specnodes

    def expanded_version_of(self, boxlist):
        newboxlist = []
        assert len(boxlist) == len(self.specnodes)
        for i in range(len(boxlist)):
            box = boxlist[i]
            specnode = self.specnodes[i]
            specnode.expand_boxlist(self.nodes[box], newboxlist)
        return newboxlist

    def prepare_rebuild_ops(self, instnode, rebuild_ops, memo, box=None):
        if box is None:
            box = instnode.source
        if not isinstance(box, Box):
            return box
        if box in memo:
            return box
        if instnode.virtual:
            ld = instnode.cls.source
            if self.cpu.is_oo and isinstance(ld, ConstObj):
                # it's probably a ootype new
                cls = ld.getobj()
                typedescr = self.cpu.class_sizes[cls] # XXX this is probably not rpython
                op = ResOperation(rop.NEW_WITH_VTABLE, [ld], box,
                                  descr=typedescr)
            else:
                assert not self.cpu.is_oo
                vtable = ld.getint()
                if self.cpu.translate_support_code:
                    vtable_addr = self.cpu.cast_int_to_adr(vtable)
                    size = self.cpu.class_sizes[vtable_addr]
                else:
                    size = self.cpu.class_sizes[vtable]
                op = ResOperation(rop.NEW_WITH_VTABLE, [ld], box,
                                  descr=size)
            rebuild_ops.append(op)
            memo[box] = None
            for ofs, node in instnode.curfields.items():
                fieldbox = self.prepare_rebuild_ops(node, rebuild_ops, memo)
                assert isinstance(ofs, AbstractDescr)
                op = ResOperation(rop.SETFIELD_GC, [box, fieldbox],
                                  None, descr=ofs)
                rebuild_ops.append(op)
            return box
        memo[box] = None
        return box

    def optimize_guard(self, op):
        # Make a list of operations to run to rebuild the unoptimized objects.
        rebuild_ops = []
        memo = {}
        assert len(op.suboperations) == 1
        op_fail = op.suboperations[0]
        assert op_fail.opnum == rop.FAIL
        for box in op_fail.args:
            if isinstance(box, Const):
                continue
            self.prepare_rebuild_ops(self.nodes[box], rebuild_ops, memo, box)

        newboxes = []
        for box in op_fail.args:
            if box in self.nodes:
                box = self.nodes[box].source
            newboxes.append(box)
        op_fail.args = newboxes
        # NB. we mutate op_fail in-place above.  That's bad.  Hopefully
        # it does not really matter because no-one is going to look again
        # at its unoptimized version.  We cannot really clone it because
        # of how the rest works (e.g. it is returned by
        # cpu.execute_operations()).
        rebuild_ops.append(op_fail)
        op1 = op.clone()
        op1.suboperations = rebuild_ops
        op.optimized = op1
        return op1

    def new_arguments(self, op):
        newboxes = []
        for box in op.args:
            if isinstance(box, Box):
                instnode = self.nodes[box]
                assert not instnode.virtual
                box = instnode.source
            newboxes.append(box)
        return newboxes

    def optimize_getfield(self, instnode, ofs, box):
        assert isinstance(ofs, AbstractValue)
        if instnode.virtual:
            assert ofs in instnode.curfields
            return True # this means field is never actually
        return False

    def optimize_setfield(self, instnode, ofs, valuenode, valuebox):
        assert isinstance(ofs, AbstractValue)
        if instnode.virtual: ## or instnode.virtualized:
            instnode.curfields[ofs] = valuenode
            return True
        else:
            assert not valuenode.virtual
            return False
            # we never perform this operation here, note

    def optimize_loop(self):
        self._allow_automatic_node_creation = False
        newoperations = []
        exception_might_have_happened = False
        if self.loop.inputargs is not None:
            # closing a loop
            assert len(self.loop.inputargs) == len(self.specnodes)
            for i in range(len(self.specnodes)):
                box = self.loop.inputargs[i]
                self.specnodes[i].mutate_nodes(self.nodes[box])
            newinputargs = self.expanded_version_of(self.loop.inputargs)
        else:
            # making a bridge
            newinputargs = None
        #
        for op in self.loop.operations:
            opnum = op.opnum
            if opnum == rop.JUMP:
                args = self.expanded_version_of(op.args)
                for arg in args:
                    if arg in self.nodes:
                        assert not self.nodes[arg].virtual
                op = op.clone()
                op.args = args
                newoperations.append(op)
                break
            elif opnum == rop.GUARD_NO_EXCEPTION:
                if not exception_might_have_happened:
                    continue
                exception_might_have_happened = False
                newoperations.append(self.optimize_guard(op))
                continue
            elif opnum == rop.GUARD_EXCEPTION:
                newoperations.append(self.optimize_guard(op))
                continue
            elif (opnum == rop.GUARD_TRUE or
                  opnum == rop.GUARD_FALSE):
                instnode = self.nodes[op.args[0]]
                if instnode.const:
                    continue
                newoperations.append(self.optimize_guard(op))
                continue
            elif opnum == rop.GUARD_CLASS:
                instnode = self.nodes[op.args[0]]
                if instnode.cls is not None:
                    assert op.args[1].equals(instnode.cls.source)
                    continue
                instnode.cls = InstanceNode(op.args[1], const=True)
                newoperations.append(self.optimize_guard(op))
                continue
            elif opnum == rop.GUARD_VALUE:
                instnode = self.nodes[op.args[0]]
                assert isinstance(op.args[1], Const)
                if instnode.const:
                    continue
                instnode.const = True
                newoperations.append(self.optimize_guard(op))
                continue
            elif opnum == rop.GETFIELD_GC:
                instnode = self.nodes[op.args[0]]
                if self.optimize_getfield(instnode, op.descr, op.result):
                    continue
                # otherwise we need this getfield, but it does not
                # invalidate caches
            elif opnum == rop.GETFIELD_GC_PURE:
                instnode = self.nodes[op.args[0]]
                if not instnode.const:
                    if self.optimize_getfield(instnode, op.descr, op.result):
                        continue
            elif opnum == rop.NEW_WITH_VTABLE:
                # self.nodes[op.result] keeps the value from Steps (1,2)
                instnode = self.nodes[op.result]
                instnode.curfields = r_dict(av_eq, av_hash)
                if not instnode.escaped:
                    instnode.virtual = True
                    assert instnode.cls is not None
                    continue
            elif opnum == rop.SETFIELD_GC:
                instnode = self.nodes[op.args[0]]
                valuenode = self.nodes[op.args[1]]
                ofs = op.descr
                if self.optimize_setfield(instnode, ofs, valuenode, op.args[1]):
                    continue
            elif (opnum == rop.OOISNULL or
                  opnum == rop.OONONNULL):
                instnode = self.getnode(op.args[0])
                # we know the result is constant if instnode is a virtual,
                # or known to be non-zero.
                if instnode.virtual or instnode.is_nonzero():
                    box = op.result
                    instnode = InstanceNode(box.constbox(), const=True)
                    self.nodes[box] = instnode
                    continue
            elif (opnum == rop.OOIS or
                  opnum == rop.OOISNOT):
                instnode_x = self.getnode(op.args[0])
                instnode_y = self.getnode(op.args[1])
                # we know the result is constant in one of these 5 cases:
                if (instnode_x.virtual or    # x is a virtual (even if y isn't)
                    instnode_y.virtual or    # y is a virtual (even if x isn't)
                    # x != NULL and y == NULL
                    (instnode_x.is_nonzero() and instnode_y.is_zero()) or
                    # x == NULL and y != NULL
                    (instnode_x.is_zero() and instnode_y.is_nonzero()) or
                    # x == NULL and y == NULL
                    (instnode_x.is_zero() and instnode_y.is_zero())):
                    #
                    box = op.result
                    instnode = InstanceNode(box.constbox(), const=True)
                    self.nodes[box] = instnode
                    continue
            # default handling of arguments and return value
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
            if op.can_raise():
                exception_might_have_happened = True
            box = op.result
            if box is not None:
                instnode = InstanceNode(box)
                self.nodes[box] = instnode
            newoperations.append(op)
        #
        self.loop.specnodes = self.specnodes
        self.loop.inputargs = newinputargs
        self.loop.operations = newoperations

    def match_exactly(self, old_loop):
        assert len(old_loop.specnodes) == len(self.specnodes)
        for i in range(len(self.specnodes)):
            old_specnode = old_loop.specnodes[i]
            new_specnode = self.specnodes[i]
            if not old_specnode.equals(new_specnode):
                return False
        return True

    def match(self, old_loop):
        jump_op = self.loop.operations[-1]
        assert jump_op.opnum == rop.JUMP
        assert len(old_loop.specnodes) == len(jump_op.args)
        for i in range(len(old_loop.specnodes)):
            old_specnode = old_loop.specnodes[i]
            new_instnode = self.getnode(jump_op.args[i])
            if not old_specnode.matches(new_instnode):
                return False
        return True

    def adapt_for_match(self, old_loop):
        jump_op = self.loop.operations[-1]
        assert jump_op.opnum == rop.JUMP
        self.specnodes = old_loop.specnodes
        for i in range(len(old_loop.specnodes)):
            old_specnode = old_loop.specnodes[i]
            new_instnode = self.getnode(jump_op.args[i])
            old_specnode.adapt_to(new_instnode, None)

# ---------------------------------------------------------------

def partition(array, left, right):
    last_item = array[right]
    pivot = last_item.sort_key()
    storeindex = left
    for i in range(left, right):
        if array[i].sort_key() <= pivot:
            array[i], array[storeindex] = array[storeindex], array[i]
            storeindex += 1
    # Move pivot to its final place
    array[storeindex], array[right] = last_item, array[storeindex]
    return storeindex

def quicksort(array, left, right):
    # sort array[left:right+1] (i.e. bounds included)
    if right > left:
        pivotnewindex = partition(array, left, right)
        quicksort(array, left, pivotnewindex - 1)
        quicksort(array, pivotnewindex + 1, right)

def sort_descrs(lst):
    quicksort(lst, 0, len(lst)-1)
