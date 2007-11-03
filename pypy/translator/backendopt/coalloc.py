from pypy.annotation.model import setunion
from pypy.objspace.flow.model import Variable, Constant
from pypy.rpython.lltypesystem import lltype
from pypy.translator.simplify import get_graph
from pypy.rpython.rmodel import inputconst
from pypy.translator.backendopt import support
from pypy.tool.uid import uid

class CreationPoint(object):
    def __init__(self, creation_method, TYPE):
        self.creation_method = creation_method
        self.TYPE = TYPE

    def __repr__(self):
        return ("CreationPoint(<0x%x>, %r)" %
                (uid(self), self.TYPE))

class VarState(object):
    def __init__(self, crep=None):
        self.creation_points = {}
        if crep is not None:
            self.creation_points[crep] = True
        self.returned = False

    def contains(self, other):
        for crep in other.creation_points:
            if crep not in self.creation_points:
                return False
        return True

    def merge(self, other):
        creation_points = setunion(self.creation_points, other.creation_points)
        newstate = VarState()
        newstate.creation_points = creation_points
        return newstate

    def __repr__(self):
        crepsrepr = (", ".join([repr(crep) for crep in self.creation_points]), )
        return "VarState({%s})" % crepsrepr

class GraphState(object):
    def __init__(self, graph):
        self.graph = graph


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
                crep = CreationPoint("constant", var_or_const.concretetype)
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
        crep = CreationPoint(method, var.concretetype)
        self.creationpoints[var] = crep
        return crep
    
    def schedule_function(self, graph):
        #print "scheduling function:", graph.name
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
            self.functionargs[graph] = args
        resultstate = self.getstate(graph.returnblock.inputargs[0])
        return resultstate, args

    def flow_block(self, block, graph):
        #print "flowing in block %s of function %s" % (block, graph.name)
        self.flown_blocks[block] = True
        if block is graph.returnblock:
            if isonheap(block.inputargs[0]):
                self.getstate(block.inputargs[0]).returned = True
            return
        if block is graph.exceptblock:
            return
        self.curr_block = block
        self.curr_graph = graph
        #print "inputargs", self.getstates(block.inputargs)
        
        for op in block.operations:
            self.flow_operation(op)
        #print "checking exits..."
        for exit in block.exits:
            #print "exit", exit
            args = self.getstates(exit.args)
            targetargs = self.getstates(exit.target.inputargs)
            #print "   newargs", args
            #print "   targetargs", targetargs
            # flow every block at least once:
            if (multicontains(targetargs, args) and
                exit.target in self.flown_blocks):
                #print "   not necessary"
                continue
            #else:
                #print "   scheduling for flowin"
            for prevstate, origstate, var in zip(args, targetargs,
                                                exit.target.inputargs):
                if not isonheap(var):
                    continue
                newstate = prevstate.merge(origstate)
                self.setstate(var, newstate)
            #print "   args", self.getstates(exit.target.inputargs)
            self.scheduled[exit.target] = graph

    def flow_operation(self, op):
        #print "handling", op
        args = self.getstates(op.args)
        #print "args:", args
        opimpl = getattr(self, 'op_'+op.opname, None)
        if opimpl is not None:
            res = opimpl(op, *args)
            if res is not NotImplemented:
                self.setstate(op.result, res)
                return
            
        if isonheap(op.result) or filter(None, args):
            raise NotImplementedError("can't handle %s" % (op.opname, ))
            #print "assuming that '%s' is irrelevant" % op
        
    def complete(self):
        while self.scheduled:
            block, graph = self.scheduled.popitem()
            self.flow_block(block, graph)

    def handle_changed(self, changed):
        for crep in changed:
            if crep not in self.dependencies:
                continue
            self.scheduled.update(self.dependencies[crep])

    def register_block_dependency(self, state, block=None, graph=None):
        if block is None:
            block = self.curr_block
            graph = self.curr_graph
        for crep in state.creation_points:
            self.dependencies.setdefault(crep, {})[block] = graph

    def register_state_dependency(self, state1, state2):
        "state1 depends on state2: if state2 does escape/change, so does state1"
        # change state1 according to how state2 is now
        #print "registering dependency of %s on %s" % (state1, state2)
        if state2.does_escape():
            changed = state1.setescapes()  # mark all crep's as escaping
            self.handle_changed(changed)
        if state2.does_change():
            changed = state1.setchanges()  # mark all crep's as changing
            self.handle_changed(changed)
        # register a dependency of the current block on state2:
        # that means that if state2 changes the current block will be reflown
        # triggering this function again and thus updating state1
        self.register_block_dependency(state2)

    # _____________________________________________________________________
    # operation implementations

    def op_malloc(self, op, typestate, flagsstate):
        assert flagsstate is None
        flags = op.args[1].value
        if flags != {'flavor': 'gc'}:
            return NotImplemented
        return VarState(self.get_creationpoint(op.result, "malloc"))

    def op_malloc_varsize(self, op, typestate, flagsstate, lengthstate):
        assert flagsstate is None
        flags = op.args[1].value
        if flags != {'flavor': 'gc'}:
            return NotImplemented
        return VarState(self.get_creationpoint(op.result, "malloc_varsize"))

    def op_keepalive(self, op, state):
        return None

    def op_cast_pointer(self, op, state):
        return state
    
    def op_getfield(self, op, objstate, fieldname):
        # connectivity-wise the field within is identical to the containing
        # structure
        return objstate
    op_getarrayitem = op_getinteriorfield = op_getfield

    def op_getarraysize(self, op, arraystate):
        pass

    def op_setfield(self, op, objstate, fieldname, valuestate):
        pass
    op_setarrayitem = op_setinteriorfield = op_setfield

    def op_direct_call(self, op, function, *args):
#        graph = get_graph(op.args[0], self.translation_context)
#        if graph is None:
#            for arg in args:
#                if arg is None:
#                    continue
#                # an external function can change every parameter:
#                changed = arg.setchanges()
#                self.handle_changed(changed)
#            funcargs = [None] * len(args)
#        else:
#            result, funcargs = self.schedule_function(graph)
#        assert len(args) == len(funcargs)
#        for localarg, funcarg in zip(args, funcargs):
#            if localarg is None:
#                assert funcarg is None
#                continue
#            if funcarg is not None:
#                self.register_state_dependency(localarg, funcarg)
        if isonheap(op.result):
            # for now assume that a call always creates a new value
            return VarState(self.get_creationpoint(op.result, "direct_call"))

    def op_indirect_call(self, op, function, *args):
#        graphs = op.args[-1].value
#        args = args[:-1]
#        if graphs is None:
#            for localarg in args:
#                if localarg is None:
#                    continue
#                changed = localarg.setescapes()
#                self.handle_changed(changed)
#                changed = localarg.setchanges()
#                self.handle_changed(changed)
#        else:
#            for graph in graphs:
#                result, funcargs = self.schedule_function(graph)
#                assert len(args) == len(funcargs)
#                for localarg, funcarg in zip(args, funcargs):
#                    if localarg is None:
#                        assert funcarg is None
#                        continue
#                    self.register_state_dependency(localarg, funcarg)
        if isonheap(op.result):
            # for now assume that a call always creates a new value
            return VarState(self.get_creationpoint(op.result, "indirect_call"))

    def op_ptr_iszero(self, op, ptrstate):
        return None

    op_cast_ptr_to_int = op_keepalive = op_ptr_nonzero = op_ptr_iszero

    def op_ptr_eq(self, op, ptr1state, ptr2state):
        return None

    op_ptr_ne = op_ptr_eq

    def op_same_as(self, op, objstate):
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

def malloc_to_coalloc(t):
    adi = AbstractDataFlowInterpreter(t)
    for graph in t.graphs:
        if graph.startblock not in adi.flown_blocks:
            adi.schedule_function(graph)
            adi.complete()
    return adi
