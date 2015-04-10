import py
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import BoxPtr, ConstPtr, ConstInt, BoxInt, Box, Const
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

class Path(object):
    def __init__(self,path):
        self.path = path

    def walk(self, idx):
        self.path.append(idx)

    def clone(self):
        return Path(self.path[:])

class Node(object):
    def __init__(self, op, opidx):
        self.op = op
        self.opidx = opidx
        self.adjacent_list = []
        self.adjacent_list_back = []
        self.memory_ref = None
        self.pack = None

    def getoperation(self):
        return self.op
    def getindex(self):
        return self.opidx

    def dependency_count(self):
        return len(self.adjacent_list)

    def getopnum(self):
        return self.op.getopnum()
    def getopname(self):
        return self.op.getopname()

    def edge_to(self, to, arg, label=None):
        assert self != to
        dep = self.depends_on(to)
        if not dep:
            #if force or self.independent(idx_from, idx_to):
            dep = Dependency(self, to, arg)
            self.adjacent_list.append(dep)
            dep_back = Dependency(to, self, arg)
            to.adjacent_list_back.append(dep_back)
            if not we_are_translated():
                if label is None:
                    label = ''
                dep.label = label
        else:
            if not dep.because_of(arg):
                dep.add_dependency(self,to,arg)
            if not we_are_translated() and label is not None:
                _label = getattr(dep, 'label', '')
                dep.label = _label + ", " + label

    def depends_on(self, to):
        """ Does there exist a dependency from the instruction to another?
            Returns None if there is no dependency or the Dependency object in
            any other case.
        """
        for edge in self.adjacent_list:
            if edge.to == to:
                return edge
        return None 

    def clear_dependencies(self):
        self.adjacent_list.clear()
        self.adjacent_list_back.clear()

    def is_guard_early_exit(self):
        return self.op.getopnum() == rop.GUARD_NO_EARLY_EXIT

    def loads_from_complex_object(self):
        return rop._ALWAYS_PURE_LAST <= self.op.getopnum() <= rop._MALLOC_FIRST

    def modifies_complex_object(self):
        return rop.SETARRAYITEM_GC <= self.op.getopnum() <= rop.UNICODESETITEM

    def side_effect_arguments(self):
        # if an item in array p0 is modified or a call contains an argument
        # it can modify it is returned in the destroyed list.
        args = []
        op = self.op
        if self.modifies_complex_object():
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

    def provides_count(self):
        return len(self.adjacent_list)

    def provides(self):
        return self.adjacent_list

    def depends_count(self, idx):
        return len(self.adjacent_list_back)

    def depends(self):
        return self.adjacent_list_back

    def dependencies(self):
        return self.adjacent_list[:] + self.adjacent_list_back[:]

    def is_after(self, other):
        return self.opidx > other.opidx

    def is_before(self, other):
        return self.opidx < other.opidx

    def independent(self, other):
        """ An instruction depends on another if there is a path from
        self to other. """
        if self == other:
            return True
        # forward
        worklist = [self]
        while len(worklist) > 0:
            node = worklist.pop()
            for dep in node.provides():
                if dep.points_to(other):
                    # dependent. There is a path from self to other
                    return False
                worklist.append(dep.to)
        # backward
        worklist = [self]
        while len(worklist) > 0:
            node = worklist.pop()
            for dep in node.depends():
                if dep.points_to(other):
                    # dependent. There is a path from self to other
                    return False
                worklist.append(dep.to)
        return True

    def iterate_paths_backward(self, ai, bi):
        if ai == bi:
            return
        if ai > bi:
            ai, bi = bi, ai
        worklist = [(Path([bi]),bi)]
        while len(worklist) > 0:
            path,idx = worklist.pop()
            for dep in self.depends(idx):
                if ai > dep.idx_from or dep.points_backward():
                    # this points above ai (thus unrelevant)
                    continue
                cloned_path = path.clone()
                cloned_path.walk(dep.idx_from)
                if dep.idx_from == ai:
                    yield cloned_path
                else:
                    worklist.append((cloned_path,dep.idx_from))

    def getedge_to(self, other):
        for dep in self.adjacent_list:
            if dep.to == other:
                return dep
        return None

    def i_remove_dependency(self, idx_at, idx_to):
        at = self.nodes[idx_at]
        to = self.nodes[idx_to]
        self.remove_dependency(at, to)
    def remove_dependency(self, at, to):
        """ Removes a all dependencies that point to 'to' """
        self.adjacent_list[at] = \
            [d for d in self.adjacent_list[at] if d.to != to]
        self.adjacent_list[to] = \
            [d for d in self.adjacent_list[to] if d.at != at]

        return args
    def __repr__(self):
        return "Node(opidx: %d)"%self.opidx

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.opidx == other.opidx
        return False


class Dependency(object):
    def __init__(self, at, to, arg):
        assert at != to
        self.args = [] 
        if arg is not None:
            self.add_dependency(at, to, arg)
        self.at = at
        self.to = to

    def because_of(self, var):
        for arg in self.args:
            if arg[1] == var:
                return True
        return False

    def to_index(self):
        return self.to.getindex()
    def at_index(self):
        return self.at.getindex()

    def points_after_to(self, to):
        return self.to.opidx < to.opidx
    def points_above_at(self, at):
        return self.at.opidx < at.opidx
    def i_points_above_at(self, idx):
        return self.at.opidx < idx

    def points_to(self, to):
        return self.to == to
    def points_at(self, at):
        return self.at == at
    def i_points_at(self, idx):
        # REM
        return self.at.opidx == idx

    def add_dependency(self, at, to, arg):
        self.args.append((at,arg))

    def reverse_direction(self, ref):
        """ if the parameter index is the same as idx_to then
        this edge is in reverse direction.
        """
        return self.to == ref

    def __repr__(self):
        return 'Dep(T[%d] -> T[%d], arg: %s)' \
                % (self.at.opidx, self.to.opidx, self.args)

class DefTracker(object):
    def __init__(self, graph):
        self.graph = graph
        self.defs = {}

    def define(self, arg, node, argcell=None):
        if arg in self.defs:
            self.defs[arg].append((node,argcell))
        else:
            self.defs[arg] = [(node,argcell)]

    def redefintions(self, arg):
        for _def in self.defs[arg]:
            yield _def[0]

    def definition(self, arg, node=None, argcell=None):
        def_chain = self.defs[arg]
        if len(def_chain) == 1:
            return def_chain[0][0]
        else:
            if argcell == None:
                return def_chain[-1][0]
            else:
                assert node is not None
                i = len(def_chain)-1
                try:
                    mref = node.memory_ref
                    while i >= 0:
                        def_node = def_chain[i][0]
                        oref = def_node.memory_ref
                        if oref is not None and mref.indices_can_alias(oref):
                            return def_node
                        elif oref is None:
                            return def_node
                        i -= 1
                except KeyError:
                    # when a key error is raised, this means
                    # no information is available, safe default
                    pass
                return def_chain[-1][0]

    def depends_on_arg(self, arg, to, argcell=None):
        try:
            at = self.definition(arg, to, argcell)
            at.edge_to(to, arg)
        except KeyError:
            if not we_are_translated():
                if not isinstance(arg, Const):
                    assert False, "arg %s must be defined" % arg


class DependencyGraph(object):
    """ A graph that represents one of the following dependencies:
          * True dependency
          * Anti dependency (not present in SSA traces)
          * Ouput dependency (not present in SSA traces)
        Traces in RPython are not in SSA form when it comes to complex
        object modification such as array or object side effects.
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
    def __init__(self, operations):
        self.nodes = [ Node(op,i) for i,op in enumerate(operations) ]
        self.memory_refs = {}
        self.schedulable_nodes = [0] # label is always scheduleable
        self.index_vars = {}
        self.guards = []
        self.build_dependencies()

    def getnode(self, i):
        return self.nodes[i]

    def build_dependencies(self):
        """ This is basically building the definition-use chain and saving this
            information in a graph structure. This is the same as calculating
            the reaching definitions and the 'looking back' whenever it is used.

            Write After Read, Write After Write dependencies are not possible,
            the operations are in SSA form
        """
        tracker = DefTracker(self)
        #
        intformod = IntegralForwardModification(self.memory_refs, self.index_vars)
        # pass 1
        for i,node in enumerate(self.nodes):
            op = node.op
            # the label operation defines all operations at the
            # beginning of the loop
            if op.getopnum() == rop.LABEL:
                # TODO is it valid that a label occurs at the end of a trace?
                ee_node = self.nodes[i+1]
                if ee_node.is_guard_early_exit():
                    node.edge_to(ee_node,None,label='L->EE')
                    node = ee_node
                for arg in op.getarglist():
                    tracker.define(arg, node)
                continue # prevent adding edge to the label itself
            intformod.inspect_operation(node)
            # definition of a new variable
            if op.result is not None:
                # In SSA form. Modifications get a new variable
                tracker.define(op.result, node)
            # usage of defined variables
            if op.is_always_pure() or op.is_final():
                # normal case every arguments definition is set
                for arg in op.getarglist():
                    tracker.depends_on_arg(arg, node)
            elif op.is_guard():
                self.guards.append(node)
            else:
                self._build_non_pure_dependencies(node, tracker)
        # pass 2 correct guard dependencies
        for guard_node in self.guards:
            self._build_guard_dependencies(guard_node, op.getopnum(), tracker)
        # pass 3 find schedulable nodes
        jump_pos = len(self.nodes)-1
        jump_node = self.nodes[jump_pos]
        for node in self.nodes:
            if node.dependency_count() == 0:
                self.schedulable_nodes.append(node.opidx)
            # every leaf instruction points to the jump_op. in theory every instruction
            # points to jump_op. this forces the jump/finish op to be the last operation
            if node != jump_node:
                if node.provides_count() == 0:
                    node.edge_to(jump_node, None, label='jump')

    def _build_guard_dependencies(self, guard_node, guard_opnum, tracker):
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
        guard_op = guard_node.op
        for arg in guard_op.getarglist():
            tracker.depends_on_arg(arg, guard_node)

        variables = []
        for dep in guard_node.depends():
            op = dep.to.op
            for arg in op.getarglist():
                if isinstance(arg, Box):
                    variables.append(arg)
            if op.result:
                variables.append(op.result)
        #
        for var in variables:
            try:
                def_node = tracker.definition(var)
                for dep in def_node.provides():
                    if guard_node.is_before(dep.to) and dep.because_of(var):
                        guard_node.edge_to(dep.to, var, label='prev('+str(var)+')')
            except KeyError:
                pass
        # handle fail args
        if guard_op.getfailargs():
            for arg in guard_op.getfailargs():
                try:
                    for at in tracker.redefintions(arg):
                        # later redefinitions are prohibited
                        if at.is_before(guard_node):
                            at.edge_to(guard_node, arg, label="fail")
                except KeyError:
                    assert False
        #
        # guards check overflow or raise are directly dependent
        # find the first non guard operation
        prev_op_idx = guard_node.opidx - 1
        while prev_op_idx > 0:
            prev_node = self.nodes[prev_op_idx]
            if prev_node.op.is_guard():
                prev_op_idx -= 1
            else:
                break
        prev_node = self.nodes[prev_op_idx]
        guard_op = guard_node.getoperation()
        prev_op = prev_node.getoperation()
        if guard_op.is_guard_exception() and prev_op.can_raise():
            self.guard_inhert(prev_node, guard_node)
        elif guard_op.is_guard_overflow() and prev_op.is_ovf():
            self.guard_inhert(prev_node, guard_node)
        elif guard_op.getopnum() == rop.GUARD_NOT_FORCED and prev_op.can_raise():
            self.guard_inhert(prev_node, guard_node)
        elif guard_op.getopnum() == rop.GUARD_NOT_FORCED_2 and prev_op.can_raise():
            self.guard_inhert(prev_node, guard_node)

    def guard_inhert(self, at, to):
        at.edge_to(to, None, label='inhert')
        for dep in at.provides():
            if to.is_before(dep.to):
                to.edge_to(dep.to, None, label='inhert')

    def _build_non_pure_dependencies(self, node, tracker):
        op = node.op
        if node.loads_from_complex_object():
            # If this complex object load operation loads an index that has been
            # modified, the last modification should be used to put a def-use edge.
            for opnum, i, j in unrolling_iterable(LOAD_COMPLEX_OBJ):
                if opnum == op.getopnum():
                    cobj = op.getarg(i)
                    index_var = op.getarg(j)
                    tracker.depends_on_arg(cobj, node, index_var)
                    tracker.depends_on_arg(index_var, node)
        else:
            for arg, argcell, destroyed in node.side_effect_arguments():
                if argcell is not None:
                    # tracks the exact cell that is modified
                    tracker.depends_on_arg(arg, node, argcell)
                    tracker.depends_on_arg(argcell, node)
                else:
                    if destroyed:
                        # cannot be sure that only a one cell is modified
                        # assume all cells are (equivalent to a redefinition)
                        try:
                            # A trace is not entirely in SSA form. complex object
                            # modification introduces WAR/WAW dependencies
                            def_node = tracker.definition(arg)
                            for dep in def_node.provides():
                                if dep.to != node:
                                    dep.to.edge_to(node, argcell, label='war')
                            def_node.edge_to(node, argcell)
                        except KeyError:
                            pass
                    else:
                        # not destroyed, just a normal use of arg
                        tracker.depends_on_arg(arg, node)
                if destroyed:
                    tracker.define(arg, node, argcell=argcell)

    def __repr__(self):
        graph = "graph([\n"
        for node in self.nodes:
            graph += "       " + str(node.opidx) + ": "
            for dep in node.provides():
                graph += "=>" + str(dep.to.opidx) + ","
            graph += " | "
            for dep in node.depends():
                graph += "<=" + str(dep.to.opidx) + ","
            graph += "\n"
        return graph + "      ])"

    def as_dot(self):
        if not we_are_translated():
            dot = "digraph dep_graph {\n"
            for node in self.nodes:
                op = node.getoperation()
                op_str = str(op)
                if op.is_guard():
                    op_str += " " + str(op.getfailargs())
                dot += " n%d [label=\"[%d]: %s\"];\n" % (node.getindex(),node.getindex(),op_str)
            dot += "\n"
            for node in self.nodes:
                for dep in node.provides():
                    label = ''
                    if getattr(dep, 'label', None):
                        label = '[label="%s"]' % dep.label
                    dot += " n%d -> n%d %s;\n" % (node.getindex(),dep.to_index(),label)
            dot += "\n}\n"
            return dot
        raise NotImplementedError("dot cannot built at runtime")

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
            print "sched"
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
            self.graph.remove_dependency_by_index(node, dep.idx_to)
            self.graph.remove_dependency_by_index(dep.idx_to, node)
            print "remove", node, "<=>", dep.idx_to
            if self.is_schedulable(dep.idx_to):
                print "sched", dep.idx_to
                self.schedulable_nodes.append(dep.idx_to)
        #
        # TODO for dep in self.graph.provides(node):
        #    candidate = dep.idx_to
        node.clear_dependencies()

    def is_schedulable(self, idx):
        print "is sched", idx, "count:", self.graph.depends_count(idx), self.graph.adjacent_list[idx]
        return self.graph.depends_count(idx) == 0

class IntegralForwardModification(object):
    """ Calculates integral modifications on an integer box. """
    def __init__(self, memory_refs, index_vars):
        self.index_vars = index_vars
        self.memory_refs = memory_refs

    def is_const_integral(self, box):
        if isinstance(box, ConstInt):
            return True
        return False

    def get_or_create(self, arg):
        var = self.index_vars.get(arg)
        if not var:
            var = self.index_vars[arg] = IndexVar(arg)
        return var

    additive_func_source = """
    def operation_{name}(self, node):
        op = node.op
        box_r = op.result
        if not box_r:
            return
        box_a0 = op.getarg(0)
        box_a1 = op.getarg(1)
        if self.is_const_integral(box_a0) and self.is_const_integral(box_a1):
            idx_ref = IndexVar(box_r)
            idx_ref.constant = box_a0.getint() {op} box_a1.getint()
            self.index_vars[box_r] = idx_ref 
        elif self.is_const_integral(box_a0):
            idx_ref = self.get_or_create(box_a1)
            idx_ref = idx_ref.clone()
            idx_ref.constant {op}= box_a0.getint()
            self.index_vars[box_r] = idx_ref
        elif self.is_const_integral(box_a1):
            idx_ref = self.get_or_create(box_a0)
            idx_ref = idx_ref.clone()
            idx_ref.constant {op}= box_a1.getint()
            self.index_vars[box_r] = idx_ref
    """
    exec py.code.Source(additive_func_source
            .format(name='INT_ADD', op='+')).compile()
    exec py.code.Source(additive_func_source
            .format(name='INT_SUB', op='-')).compile()
    del additive_func_source

    multiplicative_func_source = """
    def operation_{name}(self, node):
        op = node.op
        box_r = op.result
        if not box_r:
            return
        box_a0 = op.getarg(0)
        box_a1 = op.getarg(1)
        if self.is_const_integral(box_a0) and self.is_const_integral(box_a1):
            idx_ref = IndexVar(box_r)
            idx_ref.constant = box_a0.getint() {cop} box_a1.getint()
            self.index_vars[box_r] = idx_ref 
        elif self.is_const_integral(box_a0):
            idx_ref = self.get_or_create(box_a1)
            idx_ref = idx_ref.clone()
            idx_ref.coefficient_{tgt} *= box_a0.getint()
            idx_ref.constant {cop}= box_a0.getint()
            self.index_vars[box_r] = idx_ref
        elif self.is_const_integral(box_a1):
            idx_ref = self.get_or_create(box_a0)
            idx_ref = idx_ref.clone()
            idx_ref.coefficient_{tgt} {op}= box_a1.getint()
            idx_ref.constant {cop}= box_a1.getint()
            self.index_vars[box_r] = idx_ref
    """
    exec py.code.Source(multiplicative_func_source
            .format(name='INT_MUL', op='*', tgt='mul', cop='*')).compile()
    exec py.code.Source(multiplicative_func_source
            .format(name='INT_FLOORDIV', op='*', tgt='div', cop='/')).compile()
    exec py.code.Source(multiplicative_func_source
            .format(name='UINT_FLOORDIV', op='*', tgt='div', cop='/')).compile()
    del multiplicative_func_source

    array_access_source = """
    def operation_{name}(self, node):
        op = node.getoperation()
        descr = op.getdescr()
        idx_ref = self.get_or_create(op.getarg(1))
        node.memory_ref = MemoryRef(op, idx_ref, {raw_access})
        self.memory_refs[node] = node.memory_ref
    """
    exec py.code.Source(array_access_source
           .format(name='RAW_LOAD',raw_access=True)).compile()
    exec py.code.Source(array_access_source
           .format(name='RAW_STORE',raw_access=True)).compile()
    exec py.code.Source(array_access_source
           .format(name='GETARRAYITEM_GC',raw_access=False)).compile()
    exec py.code.Source(array_access_source
           .format(name='SETARRAYITEM_GC',raw_access=False)).compile()
    exec py.code.Source(array_access_source
           .format(name='GETARRAYITEM_RAW',raw_access=False)).compile()
    exec py.code.Source(array_access_source
           .format(name='SETARRAYITEM_RAW',raw_access=False)).compile()
    del array_access_source
integral_dispatch_opt = make_dispatcher_method(IntegralForwardModification, 'operation_')
IntegralForwardModification.inspect_operation = integral_dispatch_opt
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

    def clone(self):
        c = IndexVar(self.var)
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
    """ a memory reference to an array object. IntegralForwardModification is able
    to propagate changes to this object if applied in backwards direction.
    Example:

    i1 = int_add(i0,1)
    i2 = int_mul(i1,2)
    setarrayitem_gc(p0, i2, 1, ...)

    will result in the linear combination i0 * (2/1) + 2
    """
    def __init__(self, op, index_var, raw_access=False):
        assert op.getdescr() is not None
        self.array = op.getarg(0)
        self.descr = op.getdescr()
        self.index_var = index_var
        self.raw_access = raw_access

    def is_adjacent_to(self, other):
        """ this is a symmetric relation """
        stride = self.stride()
        if self.match(other):
            return abs(self.index_var.diff(other.index_var)) - stride == 0
        return False

    def match(self, other):
        assert isinstance(other, MemoryRef)
        if self.array == other.array and self.descr == other.descr:
            return self.index_var.same_variable(other.index_var)
        return False

    def stride(self):
        """ the stride in bytes """
        if not self.raw_access:
            return 1
        return self.descr.get_item_size_in_bytes()

    def is_adjacent_after(self, other):
        """ the asymetric relation to is_adjacent_to """
        stride = self.stride()
        if self.match(other):
            return other.index_var.diff(self.index_var) == stride
        return False

    def indices_can_alias(self, other):
        """ can to array indices alias? they can alias iff 
        self.origin != other.origin, or their
        linear combination point to the same element.
        """
        assert other is not None
        if not self.index_var.same_variable(other.index_var):
            return True
        stride = self.stride()
        if self.match(other):
            diff = self.index_var.diff(other.index_var)
            return abs(diff) < stride
        return False

    def __eq__(self, other):
        if self.match(other):
            return self.index_var.diff(other.index_var) == 0
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'MemRef(%s,%s)' % (self.array, self.index_var)
