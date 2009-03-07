from pypy.jit.metainterp.history import (Box, Const, ConstInt, BoxInt,
                                         MergePoint, ResOperation, Jump)
from pypy.jit.metainterp.heaptracker import (always_pure_operations,
                                             operations_without_side_effects,
                                             operation_never_raises)
from pypy.jit.metainterp.specnode import (FixedClassSpecNode,
                                          FixedListSpecNode,
                                          VirtualInstanceSpecNode,
                                          VirtualizableSpecNode,
                                          NotSpecNode,
                                          DelayedSpecNode,
                                          SpecNodeWithBox,
                                          DelayedListSpecNode,
                                          VirtualListSpecNode)
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp.codewriter import ListDescr

class CancelInefficientLoop(Exception):
    pass

class AllocationStorage(object):
    def __init__(self):
        # allocations: list of vtables to allocate
        # setfields: list of triples
        #                 (index_in_allocations, ofs, ~index_in_arglist)
        #                  -or-
        #                 (index_in_allocations, ofs, index_in_allocations)
        #                  -or-
        #                 (~index_in_arglist, ofs, index_in_allocations)
        #                  -or-
        #                 (~index_in_arglist, ofs, ~index_in_arglist)
        # last two cases are for virtualizables only
        self.allocations = []
        self.setfields = []
        # the same as above, but for lists and for running setitem
        self.list_allocations = []
        self.setitems = []

    def deal_with_box(self, box, nodes, liveboxes, memo, ready):
        if isinstance(box, Const) or box not in nodes:
            virtual = False
            virtualized = False
        else:
            prevbox = box
            instnode = nodes[box]
            box = instnode.source
            if box in memo:
                return memo[box]
            virtual = instnode.virtual
            virtualized = instnode.virtualized
        if virtual:
            if isinstance(instnode.cls.source, ListDescr):
                ld = instnode.cls.source
                assert isinstance(ld, ListDescr)
                alloc_offset = len(self.list_allocations)
                malloc_func = ld.malloc_func
                assert instnode.cursize != -1
                self.list_allocations.append((malloc_func,
                                              instnode.cursize))
                res = (alloc_offset + 1) << 16
            else:
                alloc_offset = len(self.allocations)
                self.allocations.append(instnode.cls.source.getint())
                res = alloc_offset
            memo[box] = res
            for ofs, node in instnode.curfields.items():
                num = self.deal_with_box(node.source, nodes, liveboxes, memo,
                                         ready)
                if isinstance(instnode.cls.source, ListDescr):
                    ld = instnode.cls.source
                    x = (alloc_offset + 1) << 16
                    assert ofs < instnode.cursize
                    self.setitems.append((ld.setfunc, x, ofs, num))
                else:
                    self.setfields.append((alloc_offset, ofs, num))
        elif virtualized:
            res = ~len(liveboxes)
            memo[box] = res
            liveboxes.append(box)
            for ofs, node in instnode.curfields.items():
                num = self.deal_with_box(node.source, nodes, liveboxes, memo,
                                         ready)
                self.setfields.append((res, ofs, num))
        else:
            res = ~len(liveboxes)
            memo[box] = res
            liveboxes.append(box)
        return res

class InstanceNode(object):
    def __init__(self, source, escaped=True, startbox=False, const=False):
        if isinstance(source, Const):
            assert const
        self.source = source       # a Box
        self.escaped = escaped
        self.startbox = startbox
        self.virtual = False
        self.virtualized = False
        self.const = const
        self.cls = None
        self.origfields = {}
        self.curfields = {}
        self.cleanfields = {}
        self.dirtyfields = {}
        self.expanded_fields = {}
        self.origsize = -1
        self.cursize  = -1

    def escape_if_startbox(self, memo):
        if self in memo:
            return
        memo[self] = None
        if self.startbox:
            self.escaped = True
        if not self.virtualized:
            for node in self.curfields.values():
                node.escape_if_startbox(memo)

    def add_to_dependency_graph(self, other, dep_graph):
        dep_graph.append((self, other))
        for ofs, node in self.origfields.items():
            if ofs in other.curfields:
                node.add_to_dependency_graph(other.curfields[ofs], dep_graph)

    def intersect(self, other):
        if not other.cls:
            return NotSpecNode()
        if self.cls:
            if not self.cls.source.equals(other.cls.source):
                raise CancelInefficientLoop
            known_class = self.cls.source
        else:
            known_class = other.cls.source
        if (other.escaped and not other.virtualized and
            not self.expanded_fields):
            if self.cls is None:
                return NotSpecNode()
            if isinstance(known_class, ListDescr):
                return FixedListSpecNode(known_class)
            return FixedClassSpecNode(known_class)
        if not other.escaped:
            if (isinstance(known_class, ListDescr)
                and self.cursize != other.origsize):
                # or DelayedListSpecNode, later on
                self.escaped = True
                other.escaped = True
                return FixedListSpecNode(known_class)
            fields = []
            if self is other:
                d = other.curfields.copy()
                d.update(self.origfields)
            else:
                d = other.curfields
            lst = d.items()
            lst.sort()
            for ofs, node in lst:
                if ofs in self.origfields:
                    specnode = self.origfields[ofs].intersect(node)
                else:
                    self.origfields[ofs] = InstanceNode(node.source.clonebox())
                    specnode = NotSpecNode()
                fields.append((ofs, specnode))
            if isinstance(known_class, ListDescr):
                return VirtualListSpecNode(known_class, fields,
                                           other.cursize)
            return VirtualInstanceSpecNode(known_class, fields)
        if not other.virtualized and self.expanded_fields:
            fields = []
            lst = self.expanded_fields.keys()
            lst.sort()
            for ofs in lst:
                specnode = SpecNodeWithBox(self.origfields[ofs].source)
                fields.append((ofs, specnode))
            if isinstance(known_class, ListDescr):
                return DelayedListSpecNode(known_class, fields)
            return DelayedSpecNode(known_class, fields)
        else:
            assert self is other
            d = self.origfields.copy()
            d.update(other.curfields)
            offsets = d.keys()
            offsets.sort()
            fields = []
            for ofs in offsets:
                if ofs in self.origfields and ofs in other.curfields:
                    node = other.curfields[ofs]
                    specnode = self.origfields[ofs].intersect(node)
                elif ofs in self.origfields:
                    node = self.origfields[ofs]
                    specnode = node.intersect(node)
                else:
                    # ofs in other.curfields
                    node = other.curfields[ofs]
                    self.origfields[ofs] = InstanceNode(node.source.clonebox())
                    specnode = NotSpecNode()
                fields.append((ofs, specnode))
            return VirtualizableSpecNode(known_class, fields)

    def __repr__(self):
        flags = ''
        if self.escaped:           flags += 'e'
        if self.startbox:          flags += 's'
        if self.const:             flags += 'c'
        if self.virtual:           flags += 'v'
        if self.virtualized:       flags += 'V'
        return "<InstanceNode %s (%s)>" % (self.source, flags)


def optimize_loop(options, old_loops, loop):
    if not options.specialize:         # for tests only
        if old_loops:
            return old_loops[0]
        else:
            return None

    # This does "Perfect specialization" as per doc/jitpl5.txt.
    perfect_specializer = PerfectSpecializer(loop, options)
    perfect_specializer.find_nodes()
    perfect_specializer.intersect_input_and_output()
    for old_loop in old_loops:
        if perfect_specializer.match_exactly(old_loop):
            return old_loop
    perfect_specializer.optimize_loop()
    return None

def optimize_bridge(options, old_loops, bridge):
    if not options.specialize:         # for tests only
        return old_loops[0]

    perfect_specializer = PerfectSpecializer(bridge, options)
    perfect_specializer.find_nodes()
    for old_loop in old_loops:
        if perfect_specializer.match(old_loop.operations):
            perfect_specializer.adapt_for_match(old_loop.operations)
            perfect_specializer.optimize_loop()
            return old_loop
    return None     # no loop matches

class PerfectSpecializer(object):

    def __init__(self, loop, options):
        self.loop = loop
        self.options = options
        self.nodes = {}
        self.dependency_graph = []

    def getnode(self, box):
        try:
            return self.nodes[box]
        except KeyError:
            assert isinstance(box, Const)
            node = self.nodes[box] = InstanceNode(box, escaped=True,
                                                  const=True)
            return node

    def getsource(self, box):
        if isinstance(box, Const):
            return box
        return self.nodes[box].source

    def find_nodes_setfield(self, instnode, ofs, fieldnode):
        instnode.curfields[ofs] = fieldnode
        self.dependency_graph.append((instnode, fieldnode))

    def find_nodes_getfield(self, instnode, field, box):
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
        if (self.first_escaping_op and
            instnode.cls and
            not isinstance(instnode.cls.source, ListDescr)):
            instnode.expanded_fields[field] = None

    def find_nodes_insert(self, instnode, field, fieldnode):
        for ofs, node in instnode.curfields.items():
            if ofs >= field:
                instnode.curfields[ofs + 1] = node
        instnode.curfields[field] = fieldnode
        instnode.cursize += 1
        self.dependency_graph.append((instnode, fieldnode))
        
    def find_nodes(self):
        # Steps (1) and (2)
        self.first_escaping_op = True
        # only catch can have consts
        for box in self.loop.operations[0].args:
            self.nodes[box] = InstanceNode(box, escaped=False, startbox=True,
                                           const=isinstance(box, Const))
        for op in self.loop.operations[1:-1]:
            opname = op.opname
            if opname == 'new_with_vtable':
                box = op.results[0]
                instnode = InstanceNode(box, escaped=False)
                instnode.cls = InstanceNode(op.args[1], const=True)
                self.nodes[box] = instnode
                self.first_escaping_op = False
                continue
            elif opname == 'newlist':
                box = op.results[0]
                instnode = InstanceNode(box, escaped=False)
                self.nodes[box] = instnode
                self.first_escaping_op = False
                if (isinstance(op.args[1], ConstInt) or
                    self.nodes[op.args[1]].const):
                    size = self.getsource(op.args[1]).getint()
                    instnode.cursize = size
                    instnode.origsize = size
                    # XXX following guard_builtin will set the
                    #     correct class, otherwise it's a mess
                    continue
            elif opname == 'guard_builtin':
                instnode = self.nodes[op.args[0]]
                # all builtins have equal classes
                instnode.cls = InstanceNode(op.args[1])
                continue
            elif opname == 'guard_len':
                instnode = self.nodes[op.args[0]]
                if instnode.cursize == -1:
                    instnode = self.nodes[op.args[0]]
                    size = op.args[1].getint()
                    instnode.cursize = size
                    instnode.origsize = size
                continue
            elif opname == 'setfield_gc':
                instnode = self.getnode(op.args[0])
                fieldbox = op.args[1]
                assert isinstance(fieldbox, ConstInt)
                field = fieldbox.getint()
                self.find_nodes_setfield(instnode, field,
                                         self.getnode(op.args[2]))
                continue
            elif opname == 'getfield_gc':
                instnode = self.getnode(op.args[0])
                fieldbox = op.args[1]
                assert isinstance(fieldbox, ConstInt)
                field = fieldbox.getint()
                box = op.results[0]
                self.find_nodes_getfield(instnode, field, box)
                continue
            elif opname == 'getitem':
                instnode = self.getnode(op.args[1])
                fieldbox = op.args[2]
                if (isinstance(fieldbox, ConstInt) or
                    self.nodes[op.args[2]].const):
                    field = self.getsource(fieldbox).getint()
                    if field < 0:
                        field = instnode.cursize + field
                    box = op.results[0]
                    self.find_nodes_getfield(instnode, field, box)
                    continue
                else:
                    instnode.escaped = True
                    self.nodes[op.results[0]] = InstanceNode(op.results[0],
                                                             escaped=True)
                    continue
            elif opname == 'append':
                instnode = self.getnode(op.args[1])
                assert isinstance(instnode.cls.source, ListDescr)
                if instnode.cursize != -1:
                    field = instnode.cursize
                    instnode.cursize += 1
                    self.find_nodes_setfield(instnode, field,
                                             self.getnode(op.args[2]))
                continue
            elif opname == 'insert':
                instnode = self.getnode(op.args[1])
                assert isinstance(instnode.cls.source, ListDescr)
                if instnode.cursize != -1:
                    fieldbox = self.getsource(op.args[2])
                    assert isinstance(fieldbox, Const) or fieldbox.const
                    field = fieldbox.getint()
                    if field < 0:
                        field = instnode.cursize + field
                    self.find_nodes_insert(instnode, field,
                                           self.getnode(op.args[3]))
                continue
            elif opname == 'pop':
                instnode = self.getnode(op.args[1])
                assert isinstance(instnode.cls.source, ListDescr)
                if instnode.cursize != -1:
                    instnode.cursize -= 1
                    field = instnode.cursize
                    self.find_nodes_getfield(instnode, field, op.results[0])
                    if field in instnode.curfields:
                        del instnode.curfields[field]                
                    continue
                self.nodes[op.results[0]] = InstanceNode(op.results[0],
                                                         escaped=True)
                self.dependency_graph.append((instnode,
                                              self.nodes[op.results[0]]))
                continue
            elif opname == 'len' or opname == 'listnonzero':
                instnode = self.getnode(op.args[1])
                if not instnode.escaped:
                    assert instnode.cursize != -1
                    lgtbox = op.results[0].constbox()
                    self.nodes[op.results[0]] = InstanceNode(lgtbox, const=True)
                    continue
            elif opname == 'setitem':
                instnode = self.getnode(op.args[1])
                fieldbox = op.args[2]
                if (isinstance(fieldbox, ConstInt)
                    or self.nodes[op.args[2]].const):
                    field = self.getsource(fieldbox).getint()
                    if field < 0:
                        field = instnode.cursize + field
                    assert field < instnode.cursize
                    self.find_nodes_setfield(instnode, field,
                                             self.getnode(op.args[3]))
                    continue
                else:
                    self.dependency_graph.append((instnode,
                                                 self.getnode(op.args[3])))
                    instnode.escaped = True
            elif opname == 'guard_class':
                instnode = self.getnode(op.args[0])
                if instnode.cls is None:
                    instnode.cls = InstanceNode(op.args[1], const=True)
                continue
            elif opname == 'guard_value':
                instnode = self.getnode(op.args[0])
                assert isinstance(op.args[1], Const)
                self.nodes[instnode.source] = InstanceNode(op.args[1],
                                                           const=True)
                continue
            elif opname == 'guard_nonvirtualized':
                instnode = self.getnode(op.args[0])
                if instnode.startbox:
                    instnode.virtualized = True
                if instnode.cls is None:
                    instnode.cls = InstanceNode(op.args[1], const=True)
                continue
            elif opname in always_pure_operations:
                for arg in op.args:
                    if not self.getnode(arg).const:
                        break
                else:
                    for box in op.results:
                        self.nodes[box] = InstanceNode(box.constbox(),
                                                       escaped=True,
                                                       const=True)
                    continue
            elif opname not in operations_without_side_effects:
                # default case
                self.first_escaping_op = False
                for box in op.args:
                    if isinstance(box, Box):
                        self.nodes[box].escaped = True
            for box in op.results:
                self.nodes[box] = InstanceNode(box, escaped=True)

    def recursively_find_escaping_values(self):
        assert self.loop.operations[0].opname == 'merge_point'
        end_args = self.loop.operations[-1].args
        memo = {}
        for i in range(len(end_args)):
            self.nodes[end_args[i]].escape_if_startbox(memo)
        for i in range(len(end_args)):
            box = self.loop.operations[0].args[i]
            other_box = end_args[i]
            self.nodes[box].add_to_dependency_graph(self.nodes[other_box],
                                                    self.dependency_graph)
        # XXX find efficient algorithm, we're too fried for that by now
        done = False
        while not done:
            done = True
            for instnode, fieldnode in self.dependency_graph:
                if instnode.escaped and not instnode.virtualized:
                    if not fieldnode.escaped:
                        fieldnode.escaped = True
                        done = False

    def intersect_input_and_output(self):
        # Step (3)
        self.recursively_find_escaping_values()
        mp = self.loop.operations[0]
        jump = self.loop.operations[-1]
        assert mp.opname == 'merge_point'
        assert jump.opname == 'jump'
        specnodes = []
        for i in range(len(mp.args)):
            enternode = self.nodes[mp.args[i]]
            leavenode = self.getnode(jump.args[i])
            specnodes.append(enternode.intersect(leavenode))
        self.specnodes = specnodes

    def expanded_version_of(self, boxlist, oplist):
        # oplist is None means at the start
        newboxlist = []
        assert len(boxlist) == len(self.specnodes)
        for i in range(len(boxlist)):
            box = boxlist[i]
            specnode = self.specnodes[i]
            specnode.expand_boxlist(self.nodes[box], newboxlist, oplist)
        return newboxlist

    def optimize_guard(self, op):
        liveboxes = []
        storage = AllocationStorage()
        memo = {}
        indices = []
        old_boxes = op.liveboxes
        op = op.clone()
        for box in old_boxes:
            indices.append(storage.deal_with_box(box, self.nodes,
                                                 liveboxes, memo,
                                                 self.ready_results))
        rev_boxes = {}
        for i in range(len(liveboxes)):
            box = liveboxes[i]
            rev_boxes[box] = i
        for node in self.nodes.values():
            for ofs, subnode in node.dirtyfields.items():
                box = node.source
                if box not in rev_boxes:
                    rev_boxes[box] = len(liveboxes)
                    liveboxes.append(box)
                index = ~rev_boxes[box]
                fieldbox = subnode.source
                if fieldbox not in rev_boxes:
                    rev_boxes[fieldbox] = len(liveboxes)
                    liveboxes.append(fieldbox)
                fieldindex = ~rev_boxes[fieldbox]
                if node.cls is not None and isinstance(node.cls.source, ListDescr):
                    f = node.cls.source.setfunc
                    storage.setitems.append((f, index, ofs, fieldindex))
                else:
                    storage.setfields.append((index, ofs, fieldindex))
        if not we_are_translated():
            items = [box for box in liveboxes if isinstance(box, Box)]
            assert len(dict.fromkeys(items)) == len(items)
        storage.indices = indices
        op.args = self.new_arguments(op)
        op.liveboxes = liveboxes
        op.storage_info = storage
        return op

    def new_arguments(self, op):
        newboxes = []
        for box in op.args:
            if isinstance(box, Box):
                instnode = self.nodes[box]
                assert not instnode.virtual
                box = instnode.source
            assert isinstance(box, Const) or box in self.ready_results
            newboxes.append(box)
        return newboxes

    def replace_arguments(self, op):
        op = op.clone()
        op.args = self.new_arguments(op)
        return op

    def optimize_getfield(self, instnode, ofs, box):
        if instnode.virtual or instnode.virtualized:
            if ofs < 0:
                ofs = instnode.cursize + ofs
            assert ofs in instnode.curfields
            return True # this means field is never actually
        elif ofs in instnode.cleanfields:
            self.nodes[box] = instnode.cleanfields[ofs]
            return True
        else:
            instnode.cleanfields[ofs] = InstanceNode(box)
            return False

    def optimize_setfield(self, instnode, ofs, valuenode, valuebox):
        if instnode.virtual or instnode.virtualized:
            if ofs < 0:
                ofs = instnode.cursize + ofs
            instnode.curfields[ofs] = valuenode
        else:
            assert not valuenode.virtual
            instnode.cleanfields[ofs] = self.nodes[valuebox]
            instnode.dirtyfields[ofs] = self.nodes[valuebox]
            # we never perform this operation here, note

    def optimize_insert(self, instnode, field, valuenode, valuebox):
        assert instnode.virtual
        for ofs, node in instnode.curfields.items():
            if ofs >= field:
                instnode.curfields[ofs + 1] = node
        instnode.curfields[field] = valuenode
        instnode.cursize += 1

    def optimize_loop(self):
        self.ready_results = {}
        newoperations = []
        exception_might_have_happened = False
        ops_so_far = []
        mp = self.loop.operations[0]
        if mp.opname == 'merge_point':
            assert len(mp.args) == len(self.specnodes)
            for i in range(len(self.specnodes)):
                box = mp.args[i]
                self.specnodes[i].mutate_nodes(self.nodes[box])
        else:
            assert mp.opname == 'catch'
            for box in mp.args:
                self.nodes[box].cls = None
                assert not self.nodes[box].virtual

        for op in self.loop.operations:
            ops_so_far.append(op)

            if newoperations and newoperations[-1].results:
                self.ready_results[newoperations[-1].results[0]] = None
            opname = op.opname
            if opname == 'merge_point':
                args = self.expanded_version_of(op.args, None)
                op = MergePoint('merge_point', args, [])
                newoperations.append(op)
                for arg in op.args:
                    self.ready_results[arg] = None
                continue
            elif opname == 'catch':
                for arg in op.args:
                    self.ready_results[arg] = None
            elif opname == 'jump':
                args = self.expanded_version_of(op.args, newoperations)
                self.cleanup_field_caches(newoperations)
                op = Jump('jump', args, [])
                newoperations.append(op)
                continue
            elif opname == 'guard_class':
                instnode = self.nodes[op.args[0]]
                if instnode.cls is not None:
                    assert op.args[1].equals(instnode.cls.source)
                    continue
                op = self.optimize_guard(op)
                newoperations.append(op)
                continue
            elif opname == 'guard_builtin':
                instnode = self.nodes[op.args[0]]
                if instnode.cls is None:
                    instnode.cls = InstanceNode(op.args[1])
                continue
            elif opname == 'guard_len':
                # it should be completely gone, because if it escapes
                # we don't virtualize it anymore
                instnode = self.nodes[op.args[0]]
                if not instnode.escaped and instnode.cursize == -1:
                    instnode = self.nodes[op.args[0]]
                    instnode.cursize = op.args[1].getint()
                continue
            elif opname == 'guard_nonvirtualized':
                instnode = self.nodes[op.args[0]]
                if instnode.virtualized or instnode.virtual:
                    continue
                op = self.optimize_guard(op)
                newoperations.append(op)
                continue
            elif opname.startswith('guard_'):
                if opname == 'guard_true' or opname == 'guard_false':
                    if self.nodes[op.args[0]].const:
                        continue
                if (opname == 'guard_no_exception' or
                    opname == 'guard_exception'):
                    if not exception_might_have_happened:
                        continue
                    exception_might_have_happened = False
                if opname == 'guard_value':
                    if (self.nodes[op.args[0]].const and
                        self.nodes[op.args[1]].const):
                        continue
                op = self.optimize_guard(op)
                newoperations.append(op)
                continue
            elif opname == 'getfield_gc':
                instnode = self.nodes[op.args[0]]
                ofs = op.args[1].getint()
                if self.optimize_getfield(instnode, ofs, op.results[0]):
                    continue
                # otherwise we need this getfield, but it does not
                # invalidate caches
            elif opname == 'getitem':
                instnode = self.nodes[op.args[1]]
                ofsbox = self.getsource(op.args[2])
                if isinstance(ofsbox, ConstInt):
                    ofs = ofsbox.getint()
                    if self.optimize_getfield(instnode, ofs, op.results[0]):
                        continue
            elif opname == 'new_with_vtable':
                # self.nodes[op.results[0]] keep the value from Steps (1,2)
                instnode = self.nodes[op.results[0]]
                if not instnode.escaped:
                    instnode.virtual = True
                    assert instnode.cls is not None
                    continue
            elif opname == 'newlist':
                instnode = self.nodes[op.results[0]]
                assert isinstance(instnode.cls.source, ListDescr)
                if not instnode.escaped:
                    instnode.virtual = True
                    valuesource = self.getsource(op.args[2])
                    instnode.cursize = op.args[1].getint()
                    curfields = {}
                    for i in range(instnode.cursize):
                        curfields[i] = InstanceNode(valuesource,
                                                    const=True)
                    instnode.curfields = curfields
                    continue
            elif opname == 'append':
                instnode = self.nodes[op.args[1]]
                valuenode = self.getnode(op.args[2])
                if not instnode.escaped:
                    ofs = instnode.cursize
                    instnode.cursize += 1
                    self.optimize_setfield(instnode, ofs, valuenode, op.args[2])
                    continue
            elif opname == 'insert':
                instnode = self.nodes[op.args[1]]
                if not instnode.escaped:
                    ofs = self.getsource(op.args[2]).getint()
                    valuenode = self.nodes[op.args[3]]
                    self.optimize_insert(instnode, ofs, valuenode, op.args[3])
                    continue
            elif opname == 'pop':
                instnode = self.nodes[op.args[1]]
                if not instnode.escaped:
                    instnode.cursize -= 1
                    ofs = instnode.cursize
                    if self.optimize_getfield(instnode, ofs, op.results[0]):
                        del instnode.curfields[ofs]
                    continue
            elif opname == 'len' or opname == 'listnonzero':
                instnode = self.nodes[op.args[1]]
                if instnode.virtual:
                    continue
            elif opname == 'setfield_gc':
                instnode = self.nodes[op.args[0]]
                valuenode = self.nodes[op.args[2]]
                ofs = op.args[1].getint()
                self.optimize_setfield(instnode, ofs, valuenode, op.args[2])
                continue
            elif opname == 'setitem':
                instnode = self.nodes[op.args[1]]
                valuenode = self.getnode(op.args[3])
                ofsbox = self.getsource(op.args[2])
                if isinstance(ofsbox, ConstInt):
                    ofs = ofsbox.getint()
                    self.optimize_setfield(instnode, ofs, valuenode, op.args[3])
                    continue
            elif opname == 'ooisnull' or opname == 'oononnull':
                instnode = self.nodes[op.args[0]]
                if instnode.virtual:
                    box = op.results[0]
                    instnode = InstanceNode(box.constbox(), const=True)
                    self.nodes[box] = instnode
                    continue
            elif opname == 'oois' or opname == 'ooisnot':
                instnode_x = self.nodes[op.args[0]]
                instnode_y = self.nodes[op.args[1]]
                if not instnode_x.virtual or not instnode_y.virtual:
                    box = op.results[0]
                    instnode = InstanceNode(box.constbox(), const=True)
                    self.nodes[box] = instnode
                    continue
            # default handling of arguments and return value(s)
            op = self.replace_arguments(op)
            if opname in always_pure_operations:
                for box in op.args:
                    if isinstance(box, Box):
                        break
                else:
                    # all constant arguments: constant-fold away
                    for box in op.results:
                        instnode = InstanceNode(box.constbox(), const=True)
                        self.nodes[box] = instnode
                    continue
            elif opname not in operations_without_side_effects:
                if opname not in ('getfield_gc', 'getitem',
                                  'setfield_gc', 'setitem'):
                    # those operations does not clean up caches, although
                    # they have side effects (at least set ones)
                    self.cleanup_field_caches(newoperations)
            if opname not in operation_never_raises:
                exception_might_have_happened = True
            for box in op.results:
                instnode = InstanceNode(box)
                self.nodes[box] = instnode
            newoperations.append(op)

        newoperations[0].specnodes = self.specnodes
        self.loop.operations = newoperations

    def cleanup_field_caches(self, newoperations):
        # we need to invalidate everything
        for node in self.nodes.values():
            for ofs, valuenode in node.dirtyfields.items():
                # XXX move to IntanceNode eventually
                if (node.cls is not None and
                    isinstance(node.cls.source, ListDescr)):
                    newoperations.append(ResOperation('setitem',
                            [node.cls.source.setfunc, node.source,
                             ConstInt(ofs), valuenode.source], []))
                else:
                    newoperations.append(ResOperation('setfield_gc',
                       [node.source, ConstInt(ofs), valuenode.source], []))
            node.dirtyfields = {}
            node.cleanfields = {}

    def match_exactly(self, old_loop):
        old_operations = old_loop.operations
        old_mp = old_operations[0]
        assert len(old_mp.specnodes) == len(self.specnodes)
        for i in range(len(self.specnodes)):
            old_specnode = old_mp.specnodes[i]
            new_specnode = self.specnodes[i]
            if not old_specnode.equals(new_specnode):
                return False
        return True

    def match(self, old_operations):
        old_mp = old_operations[0]
        jump_op = self.loop.operations[-1]
        assert jump_op.opname == 'jump'
        assert len(old_mp.specnodes) == len(jump_op.args)
        for i in range(len(old_mp.specnodes)):
            old_specnode = old_mp.specnodes[i]
            new_instnode = self.nodes[jump_op.args[i]]
            if not old_specnode.matches(new_instnode):
                return False
        return True

    def adapt_for_match(self, old_operations):
        old_mp = old_operations[0]
        jump_op = self.loop.operations[-1]
        self.specnodes = old_mp.specnodes
        for i in range(len(old_mp.specnodes)):
            old_specnode = old_mp.specnodes[i]
            new_instnode = self.nodes[jump_op.args[i]]
            old_specnode.adapt_to(new_instnode)

def box_from_index(allocated_boxes, allocated_lists,
                   boxes_from_frame, index):
    if index < 0:
        return boxes_from_frame[~index]
    if index > 0xffff:
        return allocated_lists[(index - 1) >> 16]
    return allocated_boxes[index]

def rebuild_boxes_from_guard_failure(guard_op, metainterp, boxes_from_frame):
    allocated_boxes = []
    allocated_lists = []
    storage = guard_op.storage_info
    history = metainterp.history

    for vtable in storage.allocations:
        sizebox = ConstInt(metainterp.class_sizes[vtable])
        vtablebox = ConstInt(vtable)
        [instbox] = history.execute_and_record('new_with_vtable',
                                               [sizebox, vtablebox],
                                               'ptr', False)
        allocated_boxes.append(instbox)
    for malloc_func, lgt in storage.list_allocations:
        sizebox = ConstInt(lgt)
        [listbox] = history.execute_and_record('newlist',
                                        [malloc_func, sizebox],
                                               'ptr', False)
        allocated_lists.append(listbox)
    for index_in_alloc, ofs, index_in_arglist in storage.setfields:
        fieldbox = box_from_index(allocated_boxes, allocated_lists,
                                  boxes_from_frame, index_in_arglist)
        box = box_from_index(allocated_boxes, allocated_lists, boxes_from_frame,
                             index_in_alloc)
        history.execute_and_record('setfield_gc',
                                   [box, ConstInt(ofs), fieldbox],
                                   'void', False)
    for setfunc, index_in_alloc, ofs, index_in_arglist in storage.setitems:
        itembox = box_from_index(allocated_boxes, allocated_lists,
                                 boxes_from_frame, index_in_arglist)
        box = box_from_index(allocated_boxes, allocated_lists, boxes_from_frame,
                             index_in_alloc)
        history.execute_and_record('setitem',
                                   [setfunc, box, ConstInt(ofs), itembox],
                                   'void', False)
    if storage.setitems:
        #history.execute_and_record('guard_no_exception', [], 'void', False)
        # XXX this needs to check for exceptions somehow
        # create guard_no_excpetion somehow, needs tests
        pass
    newboxes = []
    for index in storage.indices:
        if index < 0:
            newboxes.append(boxes_from_frame[~index])
        elif index > 0xffff:
            newboxes.append(allocated_lists[(index - 1) >> 16])
        else:
            newboxes.append(allocated_boxes[index])

    return newboxes
