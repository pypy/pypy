from rpython.jit.metainterp.resoperation import rop
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import BoxPtr, ConstPtr, ConstInt, BoxInt
from rpython.rtyper.lltypesystem import llmemory
from rpython.rlib.unroll import unrolling_iterable

MODIFY_COMPLEX_OBJ = [ (rop.SETARRAYITEM_GC, 0)
                     , (rop.SETARRAYITEM_RAW, 0)
                     , (rop.RAW_STORE, 0)
                     , (rop.SETINTERIORFIELD_GC, 0)
                     , (rop.SETINTERIORFIELD_RAW, 0)
                     , (rop.SETFIELD_GC, 0)
                     , (rop.SETFIELD_RAW, 0)
                     , (rop.ZERO_PTR_FIELD, 0)
                     , (rop.ZERO_PTR_FIELD, 0)
                     , (rop.ZERO_ARRAY, 0)
                     , (rop.STRSETITEM, 0)
                     , (rop.UNICODESETITEM, 0)
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
    """
    def __init__(self, operations):
        self.operations = operations
        self.adjacent_list = [ [] for i in range(len(self.operations)) ]

        self.build_dependencies(self.operations)

    def build_dependencies(self, operations):
        """ This is basically building the definition-use chain and saving this
            information in a graph structure. This is the same as calculating
            the reaching definitions and the 'looking back' whenever it is used.

            Write After Read, Write After Write dependencies are not possible,
            the operations are in SSA form
        """
        defining_indices = {}

        for i,op in enumerate(operations):
            # the label operation defines all operations at the
            # beginning of the loop
            if op.getopnum() == rop.LABEL:
                for arg in op.getarglist():
                    defining_indices[arg] = 0
                continue # prevent adding edge to the label itself

            # TODO what about a JUMP operation? it often has many parameters
            # (10+) and uses  nearly every definition in the trace (for loops).
            # Maybe we can skip this operation and let jump NEVER move...

            if op.result is not None:
                # the trace is always in SSA form, thus it is neither possible to have a WAR
                # not a WAW dependency
                defining_indices[op.result] = i

            for arg in op.getarglist():
                if arg in defining_indices:
                    idx = defining_indices[arg]
                    self._put_edge(idx, i, arg)

            if op.getfailargs():
                for arg in op.getfailargs():
                    if arg in defining_indices:
                        idx = defining_indices[arg]
                        self._put_edge(idx, i, arg)

            # a trace has store operations on complex operations
            # (e.g. setarrayitem). in general only once cell is updated,
            # and in theroy it could be tracked but for simplicity, the
            # whole is marked as redefined, thus any later usage sees
            # only this definition.
            self._redefine_if_complex_obj_is_modified(op, i, defining_indices)
            if op.is_guard() and i > 0:
                self._guard_dependency(op, i, operations, defining_indices)

    def _redefine_if_complex_obj_is_modified(self, op, index, defining_indices):
        if not op.has_no_side_effect():
            for arg in self._destroyed_arguments(op):
                try:
                    # put an edge from the definition and all later uses until this
                    # instruction to this instruction
                    def_idx = defining_indices[arg]
                    for dep in self.instr_dependencies(def_idx):
                        if dep.idx_to >= index:
                            break
                        self._put_edge(dep.idx_to, index, arg)
                    self._put_edge(def_idx, index, arg)
                except KeyError:
                    pass

    def _destroyed_arguments(self, op):
        # conservative, if an item in array p0 is modified or a call
        # contains a boxptr parameter, it is assumed that this is a
        # new definition.
        args = []
        if op.is_call() and op.getopnum() != rop.CALL_ASSEMBLER:
            # free destroys an argument -> connect all uses & def with it
            descr = op.getdescr()
            extrainfo = descr.get_extra_info()
            if extrainfo.oopspecindex == EffectInfo.OS_RAW_FREE:
                args.append(op.getarg(1))
        else:
            for opnum, i in unrolling_iterable(MODIFY_COMPLEX_OBJ):
                if op.getopnum() == opnum:
                    arg = op.getarg(i)
                    args.append(arg)
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
        print("puttin", idx_from, idx_to)
        dep = self.instr_dependency(idx_from, idx_to)
        if dep is None:
            dep = Dependency(idx_from, idx_to, arg)
            self.adjacent_list[idx_from].append(dep)
            self.adjacent_list[idx_to].append(dep)
        else:
            if arg not in dep.args:
                dep.args.append(arg)

    def get_uses(self, idx):
        deps = []
        for dep in self.adjacent_list[idx]:
            if idx < dep.idx_to:
                deps.append(dep)
        return deps

    def get_defs(self, idx):
        deps = []
        for dep in self.adjacent_list[idx]:
            if idx > dep.idx_from:
                deps.append(dep)
        return deps

    def instr_dependencies(self, idx):
        edges = self.adjacent_list[idx]
        return edges

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
        for edge in self.instr_dependencies(from_instr_idx):
            if edge.idx_to == to_instr_idx:
                return edge
        return None 

    def __repr__(self):
        graph = "graph([\n"

        for l in self.adjacent_list:
            graph += "       " + str([d.idx_to for d in l]) + "\n"

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


