from pypy.annotation.model import setunion
from pypy.objspace.flow.model import Variable, Constant
from pypy.rpython.lltypesystem import lltype
from pypy.translator.simplify import get_graph
from pypy.rpython.rmodel import inputconst

class CreationPoint(object):
    def __init__(self, creation_method="?"):
        self.changes = False
        self.escapes = False
        self.creation_method = creation_method
        if creation_method == "constant":
            self.changes = True
            self.escapes = True
            self.malloced = False

    def __repr__(self):
        return ("CreationPoint(<%s>, %s, esc=%s, cha=%s)" %
                (id(self), self.creation_method, self.escapes, self.changes))

class VarState(object):
    def __init__(self, crep=None):
        self.creation_points = {}
        if crep is not None:
            self.creation_points[crep] = True

    def contains(self, other):
        for crep in other.creation_points:
            if crep not in self.creation_points:
                return False
        return True

    def merge(self, other):
        newstate = VarState()
        creation_points = setunion(self.creation_points, other.creation_points)
        newstate = VarState()
        newstate.creation_points = creation_points
        return newstate

    def setescapes(self):
        changed = []
        for crep in self.creation_points:
            if not crep.escapes:
                changed.append(crep)
                crep.escapes = True
        return changed

    def setchanges(self):
        changed = []
        for crep in self.creation_points:
            if not crep.changes:
                changed.append(crep)
                crep.changes = True
        return changed
    
    def does_escape(self):
        for crep in self.creation_points:
            if crep.escapes:
                return True
        return False

    def does_change(self):
        for crep in self.creation_points:
            if crep.changes:
                return True
        return False
    
    def __repr__(self):
        crepsrepr = (", ".join([repr(crep) for crep in self.creation_points]), )
        return "VarState({%s})" % crepsrepr

class AbstractDataFlowInterpreter(object):
    def __init__(self, translation_context):
        self.translation_context = translation_context
        self.scheduled = {} # block: graph containing it
        self.varstates = {} # var-or-const: state
        self.creationpoints = {} # var: creationpoint
        self.constant_cps = {} # const: creationpoint
        self.dependencies = {} # creationpoint: {block: graph containing it}
        self.functionargs = {} # graph: list of state of args
        self.flown_blocks = {} # block: True
    
    def getstate(self, var_or_const):
        if not isonheap(var_or_const):
            return None
        if var_or_const in self.varstates:
            return self.varstates[var_or_const]
        if isinstance(var_or_const, Variable):
            varstate = VarState()
        else:
            if var_or_const not in self.constant_cps:
                crep = CreationPoint("constant")
                self.constant_cps[var_or_const] = crep
            else:
                crep = self.constant_cps[var_or_const]
            varstate = VarState(crep)
        self.varstates[var_or_const] = varstate
        return varstate
            
    def getstates(self, varorconstlist):
        return [self.getstate(var) for var in varorconstlist]
    
    def setstate(self, var, state):
        self.varstates[var] = state
    
    def get_creationpoint(self, var, method="?"):
        if var in self.creationpoints:
            return self.creationpoints[var]
        crep = CreationPoint(method)
        self.creationpoints[var] = crep
        return crep
    
    def schedule_function(self, graph):
        print "scheduling function:", graph.name
        startblock = graph.startblock
        if graph in self.functionargs:
            args = self.functionargs[graph]
        else:
            args = []
            for var in startblock.inputargs:
                if not isonheap(var):
                    varstate = None
                else:
                    crep = self.get_creationpoint(var, "arg")
                    varstate = VarState(crep)
                    self.setstate(var, varstate)
                args.append(varstate)
            self.scheduled[startblock] = graph
        resultstate = self.getstate(graph.returnblock.inputargs[0])
        return resultstate, args

    def flow_block(self, block, graph):
        print "flowing in block %s of function %s" % (block, graph.name)
        self.flown_blocks[block] = True
        if block is graph.returnblock:
            if isonheap(block.inputargs[0]):
                changed = self.getstate(block.inputargs[0]).setescapes()
                self.handle_changed(changed)
            return
        if block is graph.exceptblock:
            if isonheap(block.inputargs[0]):
                changed = self.getstate(block.inputargs[0]).setescapes()
                self.handle_changed(changed)
            if isonheap(block.inputargs[0]):
                changed = self.getstate(block.inputargs[1]).setescapes()
                self.handle_changed(changed)
            return
        self.curr_block = block
        self.curr_graph = graph
        print "inputargs", self.getstates(block.inputargs)
        
        for op in block.operations:
            self.flow_operation(op)
        print "checking exits..."
        for exit in block.exits:
            print "exit", exit
            args = self.getstates(exit.args)
            targetargs = self.getstates(exit.target.inputargs)
            print "   newargs", args
            print "   targetargs", targetargs
            # flow every block at least once:
            if (multicontains(targetargs, args) and
                exit.target in self.flown_blocks):
                print "   not necessary"
                continue
            else:
                print "   scheduling for flowin"
            for prevstate, origstate, var in zip(args, targetargs,
                                                exit.target.inputargs):
                if not isonheap(var):
                    continue
                newstate = prevstate.merge(origstate)
                self.setstate(var, newstate)
            print "   args", self.getstates(exit.target.inputargs)
            self.scheduled[exit.target] = graph

    def flow_operation(self, op):
        print "handling", op
        args = self.getstates(op.args)
        print "args:", args
        opimpl = getattr(self, op.opname, None)
        if opimpl is None:
            if isonheap(op.result) or filter(None, args):
                raise NotImplementedError("can't handle %s" % (op.opname, ))
            print "assuming that '%s' is irrelevant" % op
            return
        res = opimpl(op, *args)
        self.setstate(op.result, res)
        
    def complete(self):
        while self.scheduled:
            block = self.scheduled.iterkeys().next()
            graph = self.scheduled.pop(block)
            self.flow_block(block, graph)

    def handle_changed(self, changed):
        for crep in changed:
            if crep not in self.dependencies:
                continue
            for block, graph in self.dependencies[crep].iteritems():
                self.scheduled[block] = graph

    def register_block_dependency(self, state, block=None, graph=None):
        if block is None:
            block = self.curr_block
            graph = self.curr_graph
        for crep in state.creation_points:
            self.dependencies.setdefault(crep, {})[block] = graph

    def register_state_dependency(self, state1, state2):
        "state1 depends on state2: if state2 does escape/change, so does state1"
        # change state1 according to how state2 is now
        escapes = state2.does_escape()
        if escapes and not state1.does_escape():
            changed = state1.setescapes()
            self.handle_changed(changed)
        changes = state2.does_change()
        if changes and not state1:
            changed = state1.setchanges()
            self.handle_changed(changed)
        # register a dependency of the current block on state2:
        # that means that if state2 changes the current block will be reflown
        # triggering this function again and thus updating state1
        self.register_block_dependency(state2)

    # _____________________________________________________________________
    # operation implementations

    def malloc(self, op, typestate):
        return VarState(self.get_creationpoint(op.result, "malloc"))

    def malloc_varsize(self, op, typestate, lengthstate):
        return VarState(self.get_creationpoint(op.result, "malloc_varsize"))

    def cast_pointer(self, op, state):
        return state
    
    def setfield(self, op, objstate, fieldname, valuestate):
        changed = objstate.setchanges()
        self.handle_changed(changed)
        if valuestate is not None:
            # be pessimistic for now:
            # everything that gets stored into a structure escapes and changes
            self.handle_changed(changed)
            changed = valuestate.setchanges()
            self.handle_changed(changed)
            changed = valuestate.setescapes()
            self.handle_changed(changed)
        return None

    def setarrayitem(self, op, objstate, indexstate, valuestate):
        changed = objstate.setchanges()
        self.handle_changed(changed)
        if valuestate is not None:
            # everything that gets stored into a structure escapes and changes
            self.handle_changed(changed)
            changed = valuestate.setchanges()
            self.handle_changed(changed)
            changed = valuestate.setescapes()
            self.handle_changed(changed)
        return None

    def getarrayitem(self, op, objstate, indexstate):
        if isonheap(op.result):
            return VarState(self.get_creationpoint(op.result, "getarrayitem"))
    
    def getfield(self, op, objstate, fieldname):
        if isonheap(op.result):
            # assume that getfield creates a new value
            return VarState(self.get_creationpoint(op.result, "getfield"))

    def getsubstruct(self, op, objstate, fieldname):
        # since this is really an embedded struct, it has the same
        # state, the same creationpoints, etc.
        return objstate

    def getarraysize(self, op, arraystate):
        pass

    def direct_call(self, op, function, *args):
        graph = get_graph(op.args[0], self.translation_context)
        if graph is None:
            for arg in args:
                if arg is None:
                    continue
                # an external function can change every parameter:
                changed = arg.setchanges()
                self.handle_changed(changed)
            funcargs = [None] * len(args)
        else:
            result, funcargs = self.schedule_function(graph)
        assert len(args) == len(funcargs)
        for localarg, funcarg in zip(args, funcargs):
            if localarg is None:
                assert funcarg is None
                continue
            if funcarg is not None:
                self.register_state_dependency(localarg, funcarg)
        if isonheap(op.result):
            # assume that a call creates a new value
            return VarState(self.get_creationpoint(op.result, "direct_call"))

    def indirect_call(self, op, function, *args):
        graphs = op.args[-1].value
        args = args[:-1]
        for graph in graphs:
            result, funcargs = self.schedule_function(graph)
            assert len(args) == len(funcargs)
            for localarg, funcarg in zip(args, funcargs):
                if localarg is None:
                    assert funcarg is None
                    continue
                self.register_state_dependency(localarg, funcarg)
        if isonheap(op.result):
            # assume that a call creates a new value
            return VarState(self.get_creationpoint(op.result, "indirect_call"))

    def ptr_iszero(self, op, ptrstate):
        return None

    cast_ptr_to_int = keepalive = ptr_nonzero = ptr_iszero

    def ptr_eq(self, op, ptr1state, ptr2state):
        return None

    def same_as(self, op, objstate):
        return objstate

def isonheap(var_or_const):
    return isinstance(var_or_const.concretetype, lltype.Ptr)

def multicontains(l1, l2):
    assert len(l1) == len(l2)
    for a, b in zip(l1, l2):
        if a is None:
            assert b is None
        elif not a.contains(b):
            return False
    return True

def find_backedges(graph):
    """finds the backedges in the flow graph"""
    scheduled = [graph.startblock]
    seen = {}
    backedges = []
    while scheduled:
        current = scheduled.pop()
        seen[current] = True
        for link in current.exits:
            if link.target in seen:
                backedges.append(link)
            else:
                scheduled.append(link.target)
    return backedges

def compute_reachability(graph):
    reachable = {}
    for block in graph.iterblocks():
        reach = {}
        scheduled = [block]
        while scheduled:
            current = scheduled.pop()
            for link in current.exits:
                if link.target in reachable:
                    reach = setunion(reach, reachable[link.target])
                    continue
                if link.target not in reach:
                    reach[link.target] = True
        reachable[block] = reach
    return reachable

def find_loop_blocks(graph):
    """find the blocks in a graph that are part of a loop"""
    loop = {}
    reachable = compute_reachability(graph)
    for backedge in find_backedges(graph):
        start = backedge.target
        end = backedge.prevblock
        loop[start] = start
        loop[end] = start
        scheduled = [start]
        seen = {}
        while scheduled:
            current = scheduled.pop()
            connects = end in reachable[current]
            seen[current] = True
            if connects:
                loop[current] = start
            for link in current.exits:
                if link.target not in seen:
                    scheduled.append(link.target)
    return loop

def malloc_to_stack(t):
    aib = AbstractDataFlowInterpreter(t)
    for graph in t.graphs:
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'malloc':
                    if graph.startblock not in aib.flown_blocks:
                        aib.schedule_function(graph)
                        aib.complete()
                    varstate = aib.getstate(op.result)
                    assert len(varstate.creation_points) == 1
                    crep = varstate.creation_points.keys()[0]
                    if not crep.escapes:
                        print "moving object from heap to stack %s in %s" % (op, graph.name)
                        op.opname = 'flavored_malloc'
                        op.args.insert(0, inputconst(lltype.Void, 'stack'))
