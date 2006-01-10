from pypy.annotation.model import setunion
from pypy.objspace.flow.model import Variable, Constant
from pypy.rpython.lltypesystem import lltype
from pypy.translator.simplify import get_graph

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
                changed = self.gestate(block.inputargs[1]).setescapes()
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
            if multicontains(targetargs, args):
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
        escapes = state2.does_escape()
        if escapes and not state1.does_escape():
            changed = state1.setescapes()
            self.handle_changed(changed)
        changes = state2.does_change()
        if changes and not state1:
            changed = state1.setchanges()
            self.handle_changed(changed)
        self.register_block_dependency(state2)

    # _____________________________________________________________________
    # operation implementations

    def malloc(self, op, type):
        return VarState(self.get_creationpoint(op.result, "malloc"))

    def cast_pointer(self, op, state):
        return state
    
    def setfield(self, op, objstate, fieldname, valuestate):
        changed = objstate.setchanges()
        if valuestate is not None:
            # be pessimistic for now:
            # everything that gets stored into a structure escapes and changes
            self.handle_changed(changed)
            changed = valuestate.setchanges()
            self.handle_changed(changed)
            changed = valuestate.setescapes()
            self.handle_changed(changed)
        return None
    
    def getfield(self, op, objstate, fieldname):
        if isonheap(op.result):
            # assume that getfield creates a new value
            return VarState(self.get_creationpoint(op.result, "getfield"))

    def direct_call(self, op, function, *args):
        graph = get_graph(op.args[0], self.translation_context)
        result, funcargs = self.schedule_function(graph)
        assert len(args) == len(funcargs)
        for localarg, funcarg in zip(args, funcargs):
            if localarg is None:
                assert funcarg is None
                continue
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

    def ptr_iszero(self, op, ptr):
        return None
 
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
