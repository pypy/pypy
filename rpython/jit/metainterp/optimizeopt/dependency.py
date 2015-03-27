import py
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import BoxPtr, ConstPtr, ConstInt, BoxInt
from rpython.rtyper.lltypesystem import llmemory
from rpython.rlib.unroll import unrolling_iterable

MODIFY_COMPLEX_OBJ = [ (rop.SETARRAYITEM_GC, 0, 1)
                     , (rop.SETARRAYITEM_RAW, 0, 1)
                     , (rop.RAW_STORE, 0, 1)
                     , (rop.SETINTERIORFIELD_GC, 0, -1)
                     , (rop.SETINTERIORFIELD_RAW, 0, -1)
                     , (rop.SETFIELD_GC, 0, -1)
                     , (rop.SETFIELD_RAW, 0, -1)
                     , (rop.ZERO_PTR_FIELD, 0, -1)
                     , (rop.ZERO_ARRAY, 0, -1)
                     , (rop.STRSETITEM, 0, -1)
                     , (rop.UNICODESETITEM, 0, -1)
                     ]

LOAD_COMPLEX_OBJ = [ (rop.GETARRAYITEM_GC, 0, 1)
                   , (rop.GETARRAYITEM_RAW, 0, 1)
                   , (rop.GETINTERIORFIELD_GC, 0, 1)
                   , (rop.RAW_LOAD, 0, 1)
                   , (rop.GETFIELD_GC, 0, 1)
                   , (rop.GETFIELD_RAW, 0, 1)
                   ]

class Dependency(object):
    def __init__(self, idx_from, idx_to, arg):
        assert idx_from != idx_to
        self.args = [] 
        if arg is not None:
            self.args.append(arg)

        self.idx_from = idx_from 
        self.idx_to = idx_to

    def adjust_dep_after_swap(self, idx_old, idx_new):
        if self.idx_from == idx_old:
            self.idx_from = idx_new
        elif self.idx_to == idx_old:
            self.idx_to = idx_new

    def __repr__(self):
        return 'Dep(trace[%d] -> trace[%d], arg: %s)' \
                % (self.idx_from, self.idx_to, self.args)

class DefTracker(object):
    def __init__(self, memory_refs):
        self.memory_refs = memory_refs
        self.defs = {}

    def define(self, arg, index, argcell=None):
        if arg in self.defs:
            self.defs[arg].append((index,argcell))
        else:
            self.defs[arg] = [(index,argcell)]

    def definition_index(self, arg, index = -1, argcell=None):
        def_chain = self.defs[arg]
        if len(def_chain) == 1:
            return def_chain[0][0]
        else:
            if argcell == None:
                return def_chain[-1][0]
            else:
                assert index != -1
                i = len(def_chain)-1
                try:
                    mref = self.memory_refs[index]
                    while i >= 0:
                        def_index = def_chain[i][0]
                        oref = self.memory_refs.get(def_index)
                        if oref is not None and mref.indices_can_alias(oref):
                            return def_index
                        elif oref is None:
                            return def_index
                        i -= 1
                except KeyError:
                    # when a key error is raised, this means
                    # no information is available, assume the worst
                    pass
                return def_chain[-1][0]

class DependencyGraph(object):
    """ A graph that represents one of the following dependencies:
          * True dependency
          * Anti dependency (not present in SSA traces)
          * Ouput dependency (not present in SSA traces)
        Representation is an adjacent list. The number of edges between the
        vertices is expected to be small.
        Note that adjacent lists order their dependencies. They are ordered
        by the target instruction they point to if the instruction is
        a dependency.

        memory_refs: a dict that contains indices of memory references
        (load,store,getarrayitem,...). If none provided, the construction
        is conservative. It will never dismiss dependencies of two
        modifications of one array even if the indices can never point to
        the same element.
    """
    def __init__(self, operations, memory_refs):
        self.operations = operations
        self.memory_refs = memory_refs
        self.adjacent_list = [ [] for i in range(len(self.operations)) ]
        self.integral_mod = IntegralMod()
        self.schedulable_nodes = [0] # label is always scheduleable
        self.build_dependencies(self.operations)

    def build_dependencies(self, operations):
        """ This is basically building the definition-use chain and saving this
            information in a graph structure. This is the same as calculating
            the reaching definitions and the 'looking back' whenever it is used.

            Write After Read, Write After Write dependencies are not possible,
            the operations are in SSA form
        """
        tracker = DefTracker(self.memory_refs)

        for i,op in enumerate(operations):
            # the label operation defines all operations at the
            # beginning of the loop
            if op.getopnum() == rop.LABEL:
                for arg in op.getarglist():
                    tracker.define(arg, 0)
                continue # prevent adding edge to the label itself

            # definition of a new variable
            if op.result is not None:
                # In SSA form. Modifications get a new variable
                tracker.define(op.result, i)

            # usage of defined variables
            if op.is_always_pure() or op.is_final():
                # normal case every arguments definition is set
                for arg in op.getarglist():
                    self._def_use(arg, i, tracker)
            else:
                self.put_edges_for_complex_objects(op, i, tracker)

            # guard specifics
            if op.is_guard():
                for arg in op.getfailargs():
                    self._def_use(arg, i, tracker)
                if i > 0:
                    self._guard_dependency(op, i, operations, tracker)

            if len(self.adjacent_list[i]) == 0:
                self.schedulable_nodes.append(i)

    def update_memory_ref(self, op, index, tracker):
        if index not in self.memory_refs:
            return
        memref = self.memory_refs[index]
        self.integral_mod.reset()
        try:
            curidx = tracker.definition_index(memref.origin)
        except KeyError:
            return
        curop = self.operations[curidx]
        while True:
            self.integral_mod.inspect_operation(curop)
            if self.integral_mod.is_const_mod:
                self.integral_mod.update_memory_ref(memref)
            else:
                break # an operation that is not tractable
            for dep in self.get_defs(curidx):
                curop = self.operations[dep.idx_from]
                if curop.result == memref.origin:
                    curidx = dep.idx_from
                    break
            else:
                break # cannot go further, this might be the label, or a constant

    def put_edges_for_complex_objects(self, op, index, tracker):
        self.update_memory_ref(op, index, tracker)
        if self.loads_from_complex_object(op):
            # If this complex object load operation loads an index that has been
            # modified, the last modification should be used to put a def-use edge.
            for opnum, i, j in unrolling_iterable(LOAD_COMPLEX_OBJ):
                if opnum == op.getopnum():
                    cobj = op.getarg(i)
                    index_var = op.getarg(j)
                    self._def_use(cobj, index, tracker, argcell=index_var)
                    self._def_use(index_var, index, tracker)
        else:
            for arg, argcell, destroyed in self._side_effect_argument(op):
                if argcell is not None:
                    # tracks the exact cell that is modified
                    self._def_use(arg, index, tracker, argcell=argcell)
                    self._def_use(argcell, index, tracker)
                    if destroyed:
                        tracker.define(arg, index, argcell=argcell)
                else:
                    if destroyed:
                        # we cannot be sure that only a one cell is modified
                        # assume the worst, this is a complete redefintion
                        try:
                            # A trace is not in SSA form, but this complex object
                            # modification introduces a WAR/WAW dependency
                            def_idx = tracker.definition_index(arg)
                            for dep in self.get_uses(def_idx):
                                if dep.idx_to >= index:
                                    break
                                self._put_edge(dep.idx_to, index, argcell)
                            self._put_edge(def_idx, index, argcell)
                        except KeyError:
                            pass
                    else:
                        # not destroyed, just a normal use of arg
                        self._def_use(arg, index, tracker)

    def _def_use(self, arg, index, tracker, argcell=None):
        try:
            def_idx = tracker.definition_index(arg, index, argcell)
            self._put_edge(def_idx, index, arg)
        except KeyError:
            pass

    def _side_effect_argument(self, op):
        # if an item in array p0 is modified or a call contains an argument
        # it can modify it is returned in the destroyed list.
        args = []
        if self.modifies_complex_object(op):
            for opnum, i, j in unrolling_iterable(MODIFY_COMPLEX_OBJ):
                if op.getopnum() == opnum:
                    if j == -1:
                        args.append((op.getarg(i), None, True))
                    else:
                        args.append((op.getarg(i), op.getarg(j), True))
                    break
        else:
            # assume this destroys every argument... can be enhanced by looking
            # at the effect info of a call for instance
            for arg in op.getarglist():
                args.append((arg,None,True))

        return args

    def _guard_dependency(self, op, i, operations, defining_indices):
        # respect a guard after a statement that can raise!
        assert i > 0

        j = i-1
        while j > 0:
            prev_op = operations[j]
            if prev_op.is_guard():
                j -= 1
            else:
                break
        prev_op = operations[j]

        if op.is_guard_exception() and prev_op.can_raise():
            self._inhert_all_dependencies(operations, j, i)
        # respect an overflow guard after an ovf statement!
        if op.is_guard_overflow() and prev_op.is_ovf():
            self._inhert_all_dependencies(operations, j, i)
        if op.getopnum() == rop.GUARD_NOT_FORCED and prev_op.can_raise():
            self._inhert_all_dependencies(operations, j, i)
        if op.getopnum() == rop.GUARD_NOT_FORCED_2 and prev_op.can_raise():
            self._inhert_all_dependencies(operations, j, i)

    def _inhert_all_dependencies(self, operations, op_idx, from_idx):
        assert op_idx < from_idx
        for dep in self.instr_dependencies(from_idx):
            for dep in self.instr_dependencies(dep.idx_from):
                if dep.idx_to >= op_idx:
                    break
                self._put_edge(dep.idx_to, op_idx, None)
            if dep.idx_from < op_idx:
                self._put_edge(dep.idx_from, op_idx, None)
        self._put_edge(op_idx, from_idx, None)

    def _put_edge(self, idx_from, idx_to, arg):
        assert idx_from != idx_to
        dep = self.instr_dependency(idx_from, idx_to)
        if dep is None:
            dep = Dependency(idx_from, idx_to, arg)
            self.adjacent_list[idx_from].append(dep)
            self.adjacent_list[idx_to].append(dep)
        else:
            if arg not in dep.args:
                dep.args.append(arg)

    def get_uses(self, idx):
        for dep in self.adjacent_list[idx]:
            if idx < dep.idx_to:
                yield dep

    def get_defs(self, idx):
        deps = []
        for dep in self.adjacent_list[idx]:
            if idx > dep.idx_from:
                yield dep

    def instr_dependencies(self, idx):
        edges = self.adjacent_list[idx]
        return edges

    def independent(self, ai, bi):
        """ An instruction depends on another if there is a dependency path from
        A to B. It is not enough to check only if A depends on B, because
        due to transitive relations.
        """
        if ai == bi:
            return True
        if ai > bi:
            ai, bi = bi, ai
        stmt_indices = [bi]
        while len(stmt_indices) > 0:
            idx = stmt_indices.pop()
            for dep in self.instr_dependencies(idx):
                if idx < dep.idx_to:
                    # this dependency points downwards (thus unrelevant)
                    continue
                if ai > dep.idx_from:
                    # this points above ai (thus unrelevant)
                    continue

                if dep.idx_from == ai:
                    # dependent. There is a path from ai to bi
                    return False
                stmt_indices.append(dep.idx_from)
        return True

    def definition_dependencies(self, idx):
        deps = []
        for dep in self.adjacent_list[idx]:
            for dep_def in self.adjacent_list[dep.idx_from]:
                deps.append(dep_def)
        return deps

    def instr_dependency(self, from_instr_idx, to_instr_idx):
        """ Does there exist a dependency from the instruction to another?
            Returns None if there is no dependency or the Dependency object in
            any other case.
        """
        if from_instr_idx > to_instr_idx:
            to_instr_idx, from_instr_idx = from_instr_idx, to_instr_idx
        for edge in self.instr_dependencies(from_instr_idx):
            if edge.idx_to == to_instr_idx:
                return edge
        return None 

    def __repr__(self):
        graph = "graph([\n"

        for i,l in enumerate(self.adjacent_list):
            graph += "       "
            for d in l:
                if i == d.idx_from:
                    graph += str(d.idx_to) + ","
                else:
                    graph += str(d.idx_from) + ","
            graph += "\n"

        return graph + "      ])"

    def swap_instructions(self, ia, ib):
        depa = self.adjacent_list[ia]
        depb = self.adjacent_list[ib]

        for d in depa:
            d.adjust_dep_after_swap(ia, ib)

        for d in depb:
            d.adjust_dep_after_swap(ib, ia)

        self.adjacent_list[ia] = depb
        self.adjacent_list[ib] = depa

    def loads_from_complex_object(self, op):
        opnum = op.getopnum()
        return rop._ALWAYS_PURE_LAST <= opnum and opnum <= rop._MALLOC_FIRST

    def modifies_complex_object(self, op):
        opnum = op.getopnum()
        return rop.SETARRAYITEM_GC<= opnum and opnum <= rop.UNICODESETITEM

class Scheduler(object):
    def __init__(self, graph):
        self.graph = graph
        self.schedulable_nodes = self.graph.schedulable_nodes

    def has_more_to_schedule(self):
        return len(self.schedulable_nodes) > 0

    def next_schedule_index(self):
        return self.schedulable_nodes[0]

    def schedule(self, index):
        node = self.schedulable_nodes[index]
        del self.schedulable_nodes[index]
        #
        for dep in self.graph.get_uses(node):
            self.schedulable_nodes.append(dep.idx_to)
        #
        # self.graph.adjacent_list[node] = None

class IntegralMod(object):
    """ Calculates integral modifications on an integer object.
    The operations must be provided in backwards direction and of one
    variable only. Call reset() to reuse this object for other variables.
    See MemoryRef for an example.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.is_const_mod = False
        self.coefficient_mul = 1
        self.coefficient_div = 1
        self.constant = 0
        self.used_box = None

    def _update_additive(self, i):
        return (i * self.coefficient_mul) / self.coefficient_div

    def is_const_integral(self, box):
        if isinstance(box, ConstInt):
            return True
        return False

    additive_func_source = """
    def operation_{name}(self, op):
        box_a0 = op.getarg(0)
        box_a1 = op.getarg(1)
        self.is_const_mod = True
        if self.is_const_integral(box_a0) and self.is_const_integral(box_a1):
            self.used_box = None
            self.constant += self._update_additive(box_a0.getint() {op} \
                                                      box_a1.getint())
        elif self.is_const_integral(box_a0):
            self.constant {op}= self._update_additive(box_a0.getint())
            self.used_box = box_a1
        elif self.is_const_integral(box_a1):
            self.constant {op}= self._update_additive(box_a1.getint())
            self.used_box = box_a0
        else:
            self.is_const_mod = False
    """
    exec py.code.Source(additive_func_source.format(name='INT_ADD', 
                                                    op='+')).compile()
    exec py.code.Source(additive_func_source.format(name='INT_SUB', 
                                                    op='-')).compile()
    del additive_func_source

    multiplicative_func_source = """
    def operation_{name}(self, op):
        box_a0 = op.getarg(0)
        box_a1 = op.getarg(1)
        self.is_const_mod = True
        if self.is_const_integral(box_a0) and self.is_const_integral(box_a1):
            # here this factor becomes a constant, thus it is
            # handled like any other additive operation
            self.used_box = None
            self.constant += self._update_additive(box_a0.getint() {cop} \
                                                      box_a1.getint())
        elif self.is_const_integral(box_a0):
            self.coefficient_{tgt} {op}= box_a0.getint()
            self.used_box = box_a1
        elif self.is_const_integral(box_a1):
            self.coefficient_{tgt} {op}= box_a1.getint()
            self.used_box = box_a0
        else:
            self.is_const_mod = False
    """
    exec py.code.Source(multiplicative_func_source.format(name='INT_MUL', 
                                                 op='*', tgt='mul',
                                                 cop='*')).compile()
    exec py.code.Source(multiplicative_func_source.format(name='INT_FLOORDIV',
                                                 op='*', tgt='div',
                                                 cop='/')).compile()
    exec py.code.Source(multiplicative_func_source.format(name='UINT_FLOORDIV',
                                                 op='*', tgt='div',
                                                 cop='/')).compile()
    del multiplicative_func_source

    def update_memory_ref(self, memref):
        memref.constant = self.constant
        memref.coefficient_mul = self.coefficient_mul
        memref.coefficient_div = self.coefficient_div
        memref.origin = self.used_box

    def default_operation(self, operation):
        pass
integral_dispatch_opt = make_dispatcher_method(IntegralMod, 'operation_',
        default=IntegralMod.default_operation)
IntegralMod.inspect_operation = integral_dispatch_opt
del integral_dispatch_opt

class MemoryRef(object):
    """ a memory reference to an array object. IntegralMod is able
    to propagate changes to this object if applied in backwards direction.
    Example:

    i1 = int_add(i0,1)
    i2 = int_mul(i1,2)
    setarrayitem_gc(p0, i2, 1, ...)

    will result in the linear combination i0 * (2/1) + 2
    """
    def __init__(self, array, origin, descr):
        self.array = array
        self.origin = origin
        self.descr = descr
        self.coefficient_mul = 1
        self.coefficient_div = 1
        self.constant = 0

    def is_adjacent_to(self, other):
        """ this is a symmetric relation """
        match, off = self.calc_difference(other)
        if match:
            return off == 1 or off == -1
        return False

    def is_adjacent_after(self, other):
        """ the asymetric relation to is_adjacent_to """
        match, off = self.calc_difference(other)
        if match:
            return off == 1
        return False

    def indices_can_alias(self, other):
        """ can to array indices alias? they can alias iff 
        self.origin != other.origin, or their
        linear combination point to the same element.
        """
        match, off = self.calc_difference(other)
        if match:
            return off == 0
        return False

    def __eq__(self, other):
        match, off = self.calc_difference(other)
        if match:
            return off == 0
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def accesses_same_object(self, other):
        assert isinstance(other, MemoryRef)
        return self.array == other.array

    def calc_difference(self, other):
        assert isinstance(other, MemoryRef)
        if self.array == other.array \
            and self.origin == other.origin:
            mycoeff = self.coefficient_mul // self.coefficient_div
            othercoeff = other.coefficient_mul // other.coefficient_div
            diff = other.constant - self.constant
            return mycoeff == othercoeff, diff
        return False, 0

    def __repr__(self):
        return 'MemoryRef(%s*(%s/%s)+%s)' % (self.origin, self.coefficient_mul,
                                            self.coefficient_div, self.constant)

