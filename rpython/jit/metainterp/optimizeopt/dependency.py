import py

from rpython.jit.metainterp import compile
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import (rop, GuardResOp, ResOperation)
from rpython.jit.metainterp.resume import Snapshot
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import (BoxPtr, ConstPtr, ConstInt, BoxInt,
    Box, Const, BoxFloat, AbstractValue)
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
                   ]

class Path(object):
    def __init__(self,path):
        self.path = path

    def second(self):
        if len(self.path) <= 1:
            return None
        return self.path[1]

    def last_but_one(self):
        if len(self.path) < 2:
            return None
        return self.path[len(self.path)-2]

    def has_no_side_effects(self, exclude_first=False, exclude_last=False):
        last = len(self.path)-1
        count = len(self.path)
        i = 0
        if exclude_first:
            i += 1
        if exclude_last:
            count -= 1
        while i < count: 
            op = self.path[i].getoperation()
            if op.getopnum() != rop.GUARD_EARLY_EXIT and not op.is_always_pure():
                return False
            i += 1
        return True

    def set_schedule_priority(self, p):
        for node in self.path:
            node.setpriority(p)

    def walk(self, node):
        self.path.append(node)

    def cut_off_at(self, index):
        self.path = self.path[:index]

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
        self.pack_position = -1
        self.emitted = False
        self.schedule_position = -1
        self.priority = 0
        # save the operation that produces the result for the first argument
        # only for guard_true/guard_false
        self.guard_bool_bool_node = None

    def getoperation(self):
        return self.op
    def getindex(self):
        return self.opidx

    def getopnum(self):
        return self.op.getopnum()
    def getopname(self):
        return self.op.getopname()

    def setpriority(self, value):
        self.priority = value

    def can_be_relaxed(self):
        return self.op.getopnum() in (rop.GUARD_TRUE, rop.GUARD_FALSE)

    def edge_to(self, to, arg=None, failarg=False, label=None):
        if self is to:
            return
        dep = self.depends_on(to)
        if not dep:
            #if force or self.independent(idx_from, idx_to):
            dep = Dependency(self, to, arg, failarg)
            self.adjacent_list.append(dep)
            dep_back = Dependency(to, self, arg, failarg)
            dep.backward = dep_back
            to.adjacent_list_back.append(dep_back)
            if not we_are_translated():
                if label is None:
                    label = ''
                dep.label = label
        else:
            if not dep.because_of(arg):
                dep.add_dependency(self,to,arg)
            # if a fail argument is overwritten by another normal
            # dependency it will remove the failarg flag
            if not (dep.is_failarg() and failarg):
                dep.set_failarg(False)
            if not we_are_translated() and label is not None:
                _label = getattr(dep, 'label', '')
                dep.label = _label + ", " + label
        return dep

    def clear_dependencies(self):
        self.adjacent_list = []
        self.adjacent_list_back = []

    def exits_early(self):
        if self.op.is_guard():
            descr = self.op.getdescr()
            return isinstance(descr, compile.ResumeAtLoopHeaderDescr) or \
                   isinstance(descr, compile.CompileLoopVersionDescr)
        return False

    def is_guard_early_exit(self):
        return self.op.getopnum() == rop.GUARD_EARLY_EXIT

    def loads_from_complex_object(self):
        return rop._ALWAYS_PURE_LAST <= self.op.getopnum() <= rop.GETINTERIORFIELD_GC

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
                # if it is a constant argument it cannot be destroyed.
                # neither can a box float be destroyed. BoxInt can
                # contain a reference thus it is assumed to be destroyed
                if isinstance(arg, Const) or isinstance(arg, BoxFloat):
                    args.append((arg, None, False))
                else:
                    args.append((arg, None,True))
        return args

    def provides_count(self):
        return len(self.adjacent_list)

    def provides(self):
        return self.adjacent_list

    def depends_count(self):
        return len(self.adjacent_list_back)

    def depends(self):
        return self.adjacent_list_back

    def depends_on(self, to):
        """ Does there exist a dependency from the instruction to another?
            Returns None if there is no dependency or the Dependency object in
            any other case.
        """
        for edge in self.adjacent_list:
            if edge.to is to:
                return edge
        return None 

    def dependencies(self):
        return self.adjacent_list[:] + self.adjacent_list_back[:] # COPY

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
                if dep.to.is_after(other):
                    continue
                if dep.points_to(other):
                    # dependent. There is a path from self to other
                    return False
                worklist.append(dep.to)
        # backward
        worklist = [self]
        while len(worklist) > 0:
            node = worklist.pop()
            for dep in node.depends():
                if dep.to.is_before(other):
                    continue
                if dep.points_to(other):
                    # dependent. There is a path from self to other
                    return False
                worklist.append(dep.to)
        return True

    def iterate_paths(self, to, backwards=False, path_max_len=-1):
        """ yield all nodes from self leading to 'to' """
        if self == to:
            return
        path = Path([self])
        worklist = [(0, self, 1)]
        while len(worklist) > 0:
            index,node,pathlen = worklist.pop()
            if backwards:
                iterdir = node.depends()
            else:
                iterdir = node.provides()
            if index >= len(iterdir):
                continue
            else:
                next_dep = iterdir[index]
                next_node = next_dep.to
                index += 1
                if index < len(iterdir):
                    worklist.append((index, node, pathlen))
                path.cut_off_at(pathlen)
                path.walk(next_node)
                pathlen += 1

                if next_node is to or (path_max_len > 0 and pathlen >= path_max_len):
                    yield path
                else:
                    worklist.append((0, next_node, pathlen))

    def remove_edge_to(self, node):
        i = 0
        while i < len(self.adjacent_list):
            dep = self.adjacent_list[i]
            if dep.to == node:
                del self.adjacent_list[i]
                break
            i += 1
        i = 0
        while i < len(node.adjacent_list_back):
            dep = node.adjacent_list_back[i]
            if dep.to == self:
                del node.adjacent_list_back[i]
                break
            i += 1

    def getedge_to(self, other):
        for dep in self.adjacent_list:
            if dep.to == other:
                return dep
        return None

    def __repr__(self):
        pack = ''
        if self.pack:
            pack = "p: %d" % self.pack.opcount()
        return "Node(%s,%s i: %d)" % (self.op.getopname(), pack, self.opidx)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if other is None:
            return False
        assert isinstance(other, Node)
        return self.opidx == other.opidx


class Dependency(object):
    def __init__(self, at, to, arg, failarg=False):
        assert at != to
        self.args = [] 
        if arg is not None:
            self.add_dependency(at, to, arg)
        self.at = at
        self.to = to
        self.failarg = failarg
        self.backward = None

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

    def set_failarg(self, value):
        self.failarg = value
        if self.backward:
            self.backward.failarg = value

    def is_failarg(self):
        return self.failarg

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
        self.non_pure = []

    def add_non_pure(self, node):
        self.non_pure.append(node)

    def define(self, arg, node, argcell=None):
        if isinstance(arg, Const):
            return
        if arg in self.defs:
            self.defs[arg].append((node,argcell))
        else:
            self.defs[arg] = [(node,argcell)]

    def redefinitions(self, arg):
        for _def in self.defs[arg]:
            yield _def[0]

    def definition(self, arg, node=None, argcell=None):
        def_chain = self.defs[arg]
        if len(def_chain) == 1:
            return def_chain[0][0]
        else:
            if not argcell:
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
    def __init__(self, loop):
        self.loop = loop
        self.nodes = [ Node(op,i) for i,op in enumerate(loop.operations) ]
        self.invariant_vars = {}
        self.update_invariant_vars()
        self.memory_refs = {}
        self.schedulable_nodes = []
        self.index_vars = {}
        self.comparison_vars = {}
        self.guards = []
        self.build_dependencies()

    def getnode(self, i):
        return self.nodes[i]

    def update_invariant_vars(self):
        label_op = self.nodes[0].getoperation()
        jump_op = self.nodes[-1].getoperation()
        assert label_op.numargs() == jump_op.numargs()
        for i in range(label_op.numargs()):
            label_box = label_op.getarg(i)
            jump_box = jump_op.getarg(i)
            if label_box == jump_box:
                self.invariant_vars[label_box] = None

    def box_is_invariant(self, box):
        return box in self.invariant_vars

    def build_dependencies(self):
        """ This is basically building the definition-use chain and saving this
            information in a graph structure. This is the same as calculating
            the reaching definitions and the 'looking back' whenever it is used.

            Write After Read, Write After Write dependencies are not possible,
            the operations are in SSA form
        """
        tracker = DefTracker(self)
        #
        label_pos = 0
        jump_pos = len(self.nodes)-1
        intformod = IntegralForwardModification(self.memory_refs, self.index_vars,
                                                self.comparison_vars, self.invariant_vars)
        # pass 1
        for i,node in enumerate(self.nodes):
            op = node.op
            if op.is_always_pure():
                node.setpriority(1)
            if op.is_guard():
                node.setpriority(2)
            # the label operation defines all operations at the
            # beginning of the loop
            if op.getopnum() == rop.LABEL and i != jump_pos:
                node.setpriority(100)
                label_pos = i
                for arg in op.getarglist():
                    tracker.define(arg, node)
                continue # prevent adding edge to the label itself
            elif node.is_guard_early_exit():
                label_node = self.nodes[label_pos]
                label_node.edge_to(node,None,label='L->EE')
                for arg in label_node.getoperation().getarglist():
                    tracker.define(arg, node)
                continue
            intformod.inspect_operation(op,node)
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
                if node.exits_early():
                    pass
                else:
                    # consider cross iterations?
                    if len(self.guards) > 0:
                        last_guard = self.guards[-1]
                        last_guard.edge_to(node, failarg=True, label="guardorder")
                    for nonpure in tracker.non_pure:
                        nonpure.edge_to(node, failarg=True, label="nonpure")
                    tracker.non_pure = []
                self.guards.append(node)
            else:
                self.build_non_pure_dependencies(node, tracker)
        # pass 2 correct guard dependencies
        for guard_node in self.guards:
            self.build_guard_dependencies(guard_node, tracker)
        # pass 3 find schedulable nodes
        jump_node = self.nodes[jump_pos]
        label_node = self.nodes[label_pos]
        for node in self.nodes:
            if node != jump_node:
                if node.depends_count() == 0:
                    self.schedulable_nodes.insert(0, node)
                # every leaf instruction points to the jump_op. in theory every instruction
                # points to jump_op. this forces the jump/finish op to be the last operation
                if node.provides_count() == 0:
                    node.edge_to(jump_node, None, label='jump')

    def guard_argument_protection(self, guard_node, tracker):
        """ the parameters the guard protects are an indicator for
            dependencies. Consider the example:
            i3 = ptr_eq(p1,p2)
            guard_true(i3) [...]

            guard_true|false are exceptions because they do not directly
            protect the arguments, but a comparison function does.
        """
        guard_op = guard_node.getoperation()
        guard_opnum = guard_op.getopnum()
        if guard_opnum in (rop.GUARD_TRUE, rop.GUARD_FALSE):
            for dep in guard_node.depends():
                op = dep.to.getoperation()
                if op.returns_bool_result() and op.result == guard_op.getarg(0):
                    guard_node.guard_bool_bool_node = dep.to
                    for arg in op.getarglist():
                        if isinstance(arg, Box):
                            self.guard_exit_dependence(guard_node, arg, tracker)
                    break
            else:
                # in this case the guard protects an integer
                # example:
                # i = int_and(j, 255)
                # guard_true(i) [...]
                pass

        elif guard_op.is_foldable_guard():
            # these guards carry their protected variables directly as a parameter
            for arg in guard_node.getoperation().getarglist():
                if isinstance(arg, Box):
                    self.guard_exit_dependence(guard_node, arg, tracker)
        elif guard_opnum == rop.GUARD_NOT_FORCED_2:
            # must be emitted before finish, thus delayed the longest
            guard_node.setpriority(-10)
        elif guard_opnum in (rop.GUARD_OVERFLOW, rop.GUARD_NO_OVERFLOW):
            # previous operation must be an ovf_operation
            guard_node.setpriority(100)
            i = guard_node.getindex()-1
            while i >= 0:
                node = self.nodes[i]
                op = node.getoperation()
                if op.is_ovf():
                    break
                i -= 1
            else:
                raise AssertionError("(no)overflow: no overflowing op present")
            node.edge_to(guard_node, None, label='overflow')
        elif guard_opnum in (rop.GUARD_NO_EXCEPTION, rop.GUARD_EXCEPTION, rop.GUARD_NOT_FORCED):
            # previous op must be one that can raise or a not forced guard
            guard_node.setpriority(100)
            i = guard_node.getindex() - 1
            while i >= 0:
                node = self.nodes[i]
                op = node.getoperation()
                if op.can_raise():
                    node.edge_to(guard_node, None, label='exception/notforced')
                    break
                if op.is_guard():
                    node.edge_to(guard_node, None, label='exception/notforced')
                    break
                i -= 1
            else:
                raise AssertionError("(no)exception/not_forced: not op raises for them")
        else:
            pass # not invalidated, early exit, future condition!

    def guard_exit_dependence(self, guard_node, var, tracker):
        def_node = tracker.definition(var)
        for dep in def_node.provides():
            if guard_node.is_before(dep.to) and dep.because_of(var):
                guard_node.edge_to(dep.to, var, label='guard_exit('+str(var)+')')

    def build_guard_dependencies(self, guard_node, tracker):
        guard_op = guard_node.op
        if guard_op.getopnum() >= rop.GUARD_FUTURE_CONDITION:
            # ignore invalidated & future condition guard & early exit
            return
        # true dependencies
        for arg in guard_op.getarglist():
            tracker.depends_on_arg(arg, guard_node)
        # dependencies to uses of arguments it protects
        self.guard_argument_protection(guard_node, tracker)
        #
        descr = guard_op.getdescr()
        if isinstance(descr, compile.ResumeAtLoopHeaderDescr) or \
           isinstance(descr, compile.CompileLoopVersionDescr):
            return
        # handle fail args
        if guard_op.getfailargs():
            for arg in guard_op.getfailargs():
                if arg is None:
                    continue
                try:
                    for at in tracker.redefinitions(arg):
                        # later redefinitions are prohibited
                        if at.is_before(guard_node):
                            at.edge_to(guard_node, arg, failarg=True, label="fail")
                except KeyError:
                    assert False

    def build_non_pure_dependencies(self, node, tracker):
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
            # it must be assumed that a side effect operation must not be executed
            # before the last guard operation
            if len(self.guards) > 0:
                last_guard = self.guards[-1]
                last_guard.edge_to(node, label="sideeffect")
            # and the next guard instruction
            tracker.add_non_pure(node)

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
                    op_str += " " + ','.join([str(arg) for arg in op.getfailargs()])
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
        raise NotImplementedError("dot only for debug purpose")

class IntegralForwardModification(object):
    """ Calculates integral modifications on integer boxes. """
    def __init__(self, memory_refs, index_vars, comparison_vars, invariant_vars):
        self.index_vars = index_vars
        self.comparison_vars = comparison_vars
        self.memory_refs = memory_refs
        self.invariant_vars = invariant_vars

    def is_const_integral(self, box):
        if isinstance(box, ConstInt):
            return True
        return False

    def get_or_create(self, arg):
        var = self.index_vars.get(arg, None)
        if not var:
            var = self.index_vars[arg] = IndexVar(arg)
        return var

    additive_func_source = """
    def operation_{name}(self, op, node):
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
    def operation_{name}(self, op, node):
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
    def operation_{name}(self, op, node):
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
           .format(name='GETARRAYITEM_RAW',raw_access=False)).compile()
    exec py.code.Source(array_access_source
           .format(name='SETARRAYITEM_RAW',raw_access=False)).compile()
    del array_access_source
integral_dispatch_opt = make_dispatcher_method(IntegralForwardModification, 'operation_')
IntegralForwardModification.inspect_operation = integral_dispatch_opt
del integral_dispatch_opt

class IndexVar(AbstractValue):
    """ IndexVar is an AbstractValue only to ensure that a box can be assigned
        to the same variable as an index var.
    """
    def __init__(self, var):
        self.var = var
        self.coefficient_mul = 1
        self.coefficient_div = 1
        self.constant = 0
        # saves the next modification that uses a variable
        self.next_nonconst = None
        self.current_end = None
        self.opnum = 0

    def stride_const(self):
        return self.next_nonconst is None

    def add_const(self, number):
        if self.current_end is None:
            self.constant += number
        else:
            self.current_end.constant += number

    def set_next_nonconst_mod(self, idxvar):
        if self.current_end is None:
            self.next_nonconst = idxvar
        else:
            self.current_end.next_nonconst = idxvar
        self.current_end = idxvar

    def getvariable(self):
        return self.var

    def is_identity(self):
        return self.coefficient_mul == 1 and \
               self.coefficient_div == 1 and \
               self.constant == 0

    def __eq__(self, other):
        if self.same_variable(other):
            return self.diff(other) == 0
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def less(self, other):
        if self.same_variable(other):
            return self.diff(other) < 0
        return False

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

    def emit_operations(self, opt, result_box=None):
        box = self.var
        if self.is_identity():
            return box
        last_op = None
        if self.coefficient_mul != 1:
            box_result = box.clonebox()
            last_op = ResOperation(rop.INT_MUL, [box, ConstInt(self.coefficient_mul)], box_result)
            opt.emit_operation(last_op)
            box = box_result
        if self.coefficient_div != 1:
            box_result = box.clonebox()
            last_op = ResOperation(rop.INT_FLOORDIV, [box, ConstInt(self.coefficient_div)], box_result)
            opt.emit_operation(last_op)
            box = box_result
        if self.constant > 0:
            box_result = box.clonebox()
            last_op = ResOperation(rop.INT_ADD, [box, ConstInt(self.constant)], box_result)
            opt.emit_operation(last_op)
            box = box_result
        if self.constant < 0:
            box_result = box.clonebox()
            last_op = ResOperation(rop.INT_SUB, [box, ConstInt(self.constant)], box_result)
            opt.emit_operation(last_op)
            box = box_result
        if result_box is not None:
            last_op.result = box = result_box
        return box

    def compare(self, other):
        """ returns if the two are compareable as a first result
            and a number (-1,0,1) of the ordering
        """
        v1 = (self.coefficient_mul // self.coefficient_div) + self.constant
        v2 = (other.coefficient_mul // other.coefficient_div) + other.constant
        c = (v1 - v2)
        if self.var.same_box(other.var):
            #print "cmp(",self,",",other,") =>", (v1 - v2)
            return True, (v1 - v2)
        return False, 0

    def __repr__(self):
        if self.is_identity():
            return 'IndexVar(%s+%s)' % (self.var, repr(self.next_nonconst))

        return 'IndexVar((%s*(%s/%s)+%s) + %s)' % (self.var, self.coefficient_mul,
                                            self.coefficient_div, self.constant,
                                            repr(self.next_nonconst))

    def adapt_operation(self, op):
        # TODO
        if self.coefficient_mul == 1 and \
           self.coefficient_div == 1 and \
           op.getopnum() == rop.INT_ADD:
           if isinstance(op.getarg(0), Box) and isinstance(op.getarg(1), Const):
               op.setarg(0, self.var)
               op.setarg(1, ConstInt(self.constant))
           elif isinstance(op.getarg(1), Box) and isinstance(op.getarg(0), Const):
               op.setarg(1, self.var)
               op.setarg(0, ConstInt(self.constant))

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
