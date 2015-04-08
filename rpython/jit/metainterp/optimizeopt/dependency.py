import py
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import BoxPtr, ConstPtr, ConstInt, BoxInt, Box
from rpython.rtyper.lltypesystem import llmemory
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import we_are_translated

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

    def redefintions(self, arg):
        for _def in self.defs[arg]:
            yield _def[0]

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
                    # no information is available, safe default
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
        self.build_dependencies()
        self.index_vars = {}
        self.guards = []

    def build_dependencies(self):
        """ This is basically building the definition-use chain and saving this
            information in a graph structure. This is the same as calculating
            the reaching definitions and the 'looking back' whenever it is used.

            Write After Read, Write After Write dependencies are not possible,
            the operations are in SSA form
        """
        tracker = DefTracker(self.memory_refs)
        #
        intformod = IntegralForwardModification(self.index_vars)
        # pass 1
        for i,op in enumerate(self.operations):
            # the label operation defines all operations at the
            # beginning of the loop
            if op.getopnum() == rop.LABEL:
                for arg in op.getarglist():
                    tracker.define(arg, 0)
                    if isinstance(arg, BoxInt):
                        assert arg not in self.index_vars
                        self.index_vars[arg] = IndexVar(arg)
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
            elif op.is_guard():
                self.guards.append(i)
            else:
                self._build_non_pure_dependencies(op, i, tracker)
            intformod.inspect_operation(op, i)
        # pass 2 correct guard dependencies
        for guard_idx in self.guards:
            self._build_guard_dependencies(guard_idx, op.getopnum(), tracker)
        # pass 3 find schedulable nodes
        jump_pos = len(self.operations)-1
        for i,op in enumerate(self.operations):
            if len(self.adjacent_list[i]) == 0:
                self.schedulable_nodes.append(i)
            # every leaf instruction points to the jump_op. in theory every instruction
            # points to jump_op. this forces the jump/finish op to be the last operation
            if i != jump_pos:
                for dep in self.adjacent_list[i]:
                    if dep.idx_to > i:
                        break
                else:
                    self._put_edge(i, jump_pos, None)

    def _build_guard_dependencies(self, guard_idx, guard_opnum, tracker):
        if guard_opnum >= rop.GUARD_NOT_INVALIDATED:
            # ignure invalidated & future condition guard
            return
        # 'GUARD_TRUE/1d',
        # 'GUARD_FALSE/1d',
        # 'GUARD_VALUE/2d',
        # 'GUARD_CLASS/2d',
        # 'GUARD_NONNULL/1d',
        # 'GUARD_ISNULL/1d',
        # 'GUARD_NONNULL_CLASS/2d',
        guard_op = self.operations[guard_idx]
        for arg in guard_op.getarglist():
            self._def_use(arg, guard_idx, tracker)

        variables = []
        for dep in self.depends(guard_idx):
            idx = dep.idx_from
            op = self.operations[idx]
            for arg in op.getarglist():
                if isinstance(arg, Box):
                    variables.append(arg)
            if op.result:
                variables.append(op.result)
        #
        for var in variables:
            try:
                def_idx = tracker.definition_index(var)
                for dep in self.provides(def_idx):
                    if var in dep.args and dep.idx_to > guard_idx:
                        #print "checking", var, "def at", def_idx, " -> ", dep
                        #print " ==> yes"
                        self._put_edge(guard_idx, dep.idx_to, var)
            except KeyError:
                pass
        # handle fail args
        op = self.operations[guard_idx]
        if op.getfailargs():
            for arg in op.getfailargs():
                try:
                    for def_idx in tracker.redefintions(arg):
                        self._put_edge(def_idx, guard_idx, arg)
                        #print "put arg", arg, ":", def_idx, guard_idx,"!!!"
                except KeyError:
                    assert False
        #
        # guards check overflow or raise are directly dependent
        # find the first non guard operation
        prev_op_idx = guard_idx - 1
        while prev_op_idx > 0:
            prev_op = self.operations[prev_op_idx]
            if prev_op.is_guard():
                prev_op_idx -= 1
            else:
                break
        prev_op = self.operations[prev_op_idx]
        #
        if op.is_guard_exception() and prev_op.can_raise():
            self._guard_inhert(prev_op_idx, guard_idx)
        elif op.is_guard_overflow() and prev_op.is_ovf():
            self._guard_inhert(prev_op_idx, guard_idx)
        elif op.getopnum() == rop.GUARD_NOT_FORCED and prev_op.can_raise():
            self._guard_inhert(prev_op_idx, guard_idx)
        elif op.getopnum() == rop.GUARD_NOT_FORCED_2 and prev_op.can_raise():
            self._guard_inhert(prev_op_idx, guard_idx)

    def _guard_inhert(self, idx, guard_idx):
        self._put_edge(idx, guard_idx, None)
        for dep in self.provides(idx):
            if dep.idx_to > guard_idx:
                self._put_edge(guard_idx, dep.idx_to, None)

    def _build_non_pure_dependencies(self, op, index, tracker):
        self._update_memory_ref(op, index, tracker)
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
                else:
                    if destroyed:
                        # cannot be sure that only a one cell is modified
                        # assume all cells are (equivalent to a redefinition)
                        try:
                            # A trace is not entirely in SSA form. complex object
                            # modification introduces WAR/WAW dependencies
                            def_idx = tracker.definition_index(arg)
                            for dep in self.provides(def_idx):
                                if dep.idx_to >= index:
                                    break
                                self._put_edge(dep.idx_to, index, argcell)
                            self._put_edge(def_idx, index, argcell)
                        except KeyError:
                            pass
                    else:
                        # not destroyed, just a normal use of arg
                        self._def_use(arg, index, tracker)
                if destroyed:
                    tracker.define(arg, index, argcell=argcell)

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
                    op_args = op.getarglist()
                    if j == -1:
                        args.append((op.getarg(i), None, True))
                        for j in range(i+1,len(op_args)):
                            args.append((op.getarg(j), None, False))
                    else:
                        args.append((op.getarg(i), op.getarg(j), True))
                        for x in range(j+1,len(op_args)):
                            args.append((op.getarg(x), None, False))
                    break
        else:
            # assume this destroys every argument... can be enhanced by looking
            # at the effect info of a call for instance
            for arg in op.getarglist():
                args.append((arg,None,True))

        return args

    def _update_memory_ref(self, op, index, tracker):
        # deprecated
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
            for dep in self.depends(curidx):
                curop = self.operations[dep.idx_from]
                if curop.result == memref.origin:
                    curidx = dep.idx_from
                    break
            else:
                break # cannot go further, this might be the label, or a constant

    def _put_edge(self, idx_from, idx_to, arg):
        assert idx_from != idx_to
        dep = self.directly_depends(idx_from, idx_to)
        if not dep:
            if self.independent(idx_from, idx_to):
                dep = Dependency(idx_from, idx_to, arg)
                self.adjacent_list[idx_from].append(dep)
                self.adjacent_list[idx_to].append(dep)
        else:
            if arg not in dep.args:
                dep.args.append(arg)

    def provides_count(self, idx):
        i = 0
        for _ in self.provides(idx):
            i += 1
        return i

    def provides(self, idx):
        return self.get_uses(idx)
    def get_uses(self, idx):
        for dep in self.adjacent_list[idx]:
            if idx < dep.idx_to:
                yield dep

    def depends_count(self, idx):
        i = 0
        for _ in self.depends(idx):
            i += 1
        return i

    def depends(self, idx):
        return self.get_defs(idx)
    def get_defs(self, idx):
        for dep in self.adjacent_list[idx]:
            if idx > dep.idx_from:
                yield dep

    def dependencies(self, idx):
        return self.adjacent_list[idx]
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
            for dep in self.depends(idx):
                if ai > dep.idx_from:
                    # this points above ai (thus unrelevant)
                    continue

                if dep.idx_from == ai:
                    # dependent. There is a path from ai to bi
                    return False
                stmt_indices.append(dep.idx_from)
        return True

    def definition_dependencies(self, idx):
        # XXX remove
        deps = []
        for dep in self.adjacent_list[idx]:
            for dep_def in self.adjacent_list[dep.idx_from]:
                deps.append(dep_def)
        return deps

    def directly_depends(self, from_idx, to_idx):
        return self.instr_dependency(from_idx, to_idx)

    def instr_dependency(self, from_instr_idx, to_instr_idx):
        # XXX
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

    def remove_depencency(self, follow_dep, point_to_idx):
        """ removes a all dependencies that point to the second parameter.
        it is assumed that the adjacent_list[point_to_idx] is not iterated
        when calling this function.
        """
        idx = follow_dep.idx_from
        if idx == point_to_idx:
            idx = follow_dep.idx_to
        self.adjacent_list[idx] = [d for d in self.adjacent_list[idx] \
                if d.idx_to != point_to_idx and d.idx_from != point_to_idx]

    def __repr__(self):
        graph = "graph([\n"
        for i,l in enumerate(self.adjacent_list):
            graph += "       " + str(i) + ": "
            for d in l:
                if i == d.idx_from:
                    graph += str(d.idx_to) + ","
                else:
                    graph += str(d.idx_from) + ","
            graph += "\n"
        return graph + "      ])"

    def loads_from_complex_object(self, op):
        return rop._ALWAYS_PURE_LAST <= op.getopnum() <= rop._MALLOC_FIRST

    def modifies_complex_object(self, op):
        return rop.SETARRAYITEM_GC <= op.getopnum() <= rop.UNICODESETITEM

    def as_dot(self, operations):
        if not we_are_translated():
            dot = "digraph dep_graph {\n"
            for i in range(len(self.adjacent_list)):
                op = operations[i]
                dot += " n%d [label=\"[%d]: %s\"];\n" % (i,i,str(op))
            dot += "\n"
            for i,alist in enumerate(self.adjacent_list):
                for dep in alist:
                    if dep.idx_to > i:
                        dot += " n%d -> n%d;\n" % (i,dep.idx_to)
            dot += "\n}\n"
            return dot
        return ""

class SchedulerData(object):
    pass
class Scheduler(object):
    def __init__(self, graph, sched_data):
        assert isinstance(sched_data, SchedulerData)
        self.graph = graph
        self.schedulable_nodes = self.graph.schedulable_nodes
        self.sched_data = sched_data

    def has_more_to_schedule(self):
        return len(self.schedulable_nodes) > 0

    def next_schedule_index(self):
        return self.schedulable_nodes[0]

    def schedulable(self, indices):
        for index in indices:
            if index not in self.schedulable_nodes:
                break
        else:
            return True
        return False

    def schedule_later(self, index):
        node = self.schedulable_nodes[index]
        del self.schedulable_nodes[index]
        self.schedulable_nodes.append(node)

    def schedule_all(self, opindices):
        while len(opindices) > 0:
            opidx = opindices.pop()
            for i,node in enumerate(self.schedulable_nodes):
                if node == opidx:
                    break
            else:
                i = -1
            if i != -1:
                self.schedule(i)

    def schedule(self, index):
        node = self.schedulable_nodes[index]
        del self.schedulable_nodes[index]
        to_del = []
        adj_list = self.graph.adjacent_list[node]
        for dep in adj_list:
            self.graph.remove_depencency(dep, node)
        #
        for dep in self.graph.provides(node):
            candidate = dep.idx_to
            if self.is_schedulable(dep.idx_to):
                self.schedulable_nodes.append(dep.idx_to)
        self.graph.adjacent_list[node] = []

    def is_schedulable(self, idx):
        return self.graph.depends_count(idx) == 0

class IntegralForwardModification(object):
    """ Calculates integral modifications on an integer box. """
    def __init__(self, index_vars):
        self.index_vars = index_vars

    def is_const_integral(self, box):
        if isinstance(box, ConstInt):
            return True
        return False

    additive_func_source = """
    def operation_{name}(self, op, index):
        box_r = op.result
        if not box_r:
            return
        box_a0 = op.getarg(0)
        box_a1 = op.getarg(1)
        if self.is_const_integral(box_a0) and self.is_const_integral(box_a1):
            idx_ref = IndexVar(box_r)
            idx_ref.constant = box_a0.getint() {op} box_a1.getint())
            self.index_vars[box_r] = idx_ref 
        elif self.is_const_integral(box_a0):
            idx_ref = self.index_vars[box_a0]
            idx_ref = idx_ref.clone(box_r)
            idx_ref.constant {op}= box_a0.getint()
            self.index_vars[box_r] = idx_ref
        elif self.is_const_integral(box_a1):
            idx_ref = self.index_vars[box_a1]
            idx_ref = idx_ref.clone(box_r)
            idx_ref.constant {op}= box_a1.getint()
            self.index_vars[box_r] = idx_ref
    """
    exec py.code.Source(additive_func_source.format(name='INT_ADD', 
                                                    op='+')).compile()
    exec py.code.Source(additive_func_source.format(name='INT_SUB', 
                                                    op='-')).compile()
    del additive_func_source

    multiplicative_func_source = """
    def operation_{name}(self, op):
        box_r = op.result
        if not box_r:
            return
        box_a0 = op.getarg(0)
        box_a1 = op.getarg(1)
        if self.is_const_integral(box_a0) and self.is_const_integral(box_a1):
            idx_ref = IndexVar(box_r)
            idx_ref.constant = box_a0.getint() {cop} box_a1.getint())
            self.index_vars[box_r] = idx_ref 
        elif self.is_const_integral(box_a0):
            idx_ref = self.index_vars[box_a0]
            idx_ref = idx_ref.clone(box_r)
            self.coefficient_{tgt} *= box_a0.getint()
            self.constant {cop}= box_a0.getint()
            self.index_vars[box_r] = idx_ref
        elif self.is_const_integral(box_a1):
            idx_ref = self.index_vars[box_a1]
            idx_ref = idx_ref.clone(box_r)
            self.coefficient_{tgt} {op}= box_a1.getint()
            self.constant {cop}= box_a1.getint()
            self.index_vars[box_r] = idx_ref
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

integral_dispatch_opt = make_dispatcher_method(IntegralForwardModification, 'operation_')
IntegralForwardModification.inspect_operation = integral_dispatch_opt
del integral_dispatch_opt

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

    def is_const_integral(self, box):
        if isinstance(box, ConstInt):
            return True
        return False

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

class IndexVar(object):
    def __init__(self, var):
        self.var = var
        self.coefficient_mul = 1
        self.coefficient_div = 1
        self.constant = 0

    def __eq__(self, other):
        if self.same_variable(other):
            return self.diff(other) == 0
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def clone(self, box):
        c = IndexVar(box)
        c.coefficient_mul = self.coefficient_mul
        c.coefficient_div = self.coefficient_div
        c.constant = self.constant
        return c

    def same_variable(self, other):
        assert isinstance(other, IndexVar)
        return other.var == self.var

    def diff(self, other):
        """ calculates the difference as a second parameter """
        assert isinstance(other, IndexVar)
        mycoeff = self.coefficient_mul // self.coefficient_div
        othercoeff = other.coefficient_mul // other.coefficient_div
        return mycoeff + self.constant - (othercoeff + other.constant)

    def __repr__(self):
        return 'IndexVar(%s*(%s/%s)+%s)' % (self.var, self.coefficient_mul,
                                            self.coefficient_div, self.constant)

class MemoryRef(object):
    """ a memory reference to an array object. IntegralMod is able
    to propagate changes to this object if applied in backwards direction.
    Example:

    i1 = int_add(i0,1)
    i2 = int_mul(i1,2)
    setarrayitem_gc(p0, i2, 1, ...)

    will result in the linear combination i0 * (2/1) + 2
    """
    def __init__(self, array, origin, descr, index_ref, byte_index=False):
        assert descr is not None
        self.array = array
        self.descr = descr
        self.index_ref = index_ref
        self.byte_index = byte_index

    def is_adjacent_to(self, other):
        """ this is a symmetric relation """
        stride = self.stride()
        if self.match(other):
            return abs(self.index_ref.diff(other.index_ref)) - stride == 0
        return False

    def match(self, other):
        assert isinstance(other, MemoryRef)
        if self.array == other.array and self.descr == other.descr:
            return self.index_ref.same_variable(other.index_ref):
        return False

    def stride(self):
        """ the stride in bytes """
        if not self.byte_index:
            return 1
        return self.descr.get_item_size_in_bytes()

    def is_adjacent_after(self, other):
        """ the asymetric relation to is_adjacent_to """
        stride = self.stride()
        if self.match(other):
            return self.index_ref.diff(other.index_ref) == stride
        return False

    def indices_can_alias(self, other):
        """ can to array indices alias? they can alias iff 
        self.origin != other.origin, or their
        linear combination point to the same element.
        """
        if self.index_ref.same_variable(other.index_ref):
            return True
        stride = self.stride()
        if self.match(other):
            return abs(self.index_ref.diff(other.index_ref)) < stride
        return False

    def __eq__(self, other):
        if self.match(other):
            return self.index_ref.diff(other.index_ref) == 0
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'MemRef(%s,%s*(%s/%s)+%s)' % (self.array, self.origin, self.coefficient_mul,
                                            self.coefficient_div, self.constant)
