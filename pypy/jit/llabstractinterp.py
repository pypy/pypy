import operator
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import Block, Link, FunctionGraph
from pypy.objspace.flow.model import checkgraph, last_exception
from pypy.rpython.lltypesystem import lltype


class LLAbstractValue(object):
    pass

class LLConcreteValue(LLAbstractValue):

    def __init__(self, value):
        self.value = value

#    def __eq__(self, other):
#        return self.__class__ is other.__class__ and self.value == other.value
#
#    def __ne__(self, other):
#        return not (self == other)
#
#    def __hash__(self):
#        return hash(self.value)

    def getconcretetype(self):
        return lltype.typeOf(self.value)

    def getvarorconst(self):
        c = Constant(self.value)
        c.concretetype = self.getconcretetype()
        return c

    def match(self, other):
        return isinstance(other, LLConcreteValue) and self.value == other.value


class LLRuntimeValue(LLAbstractValue):

    def __init__(self, orig_v):
        if isinstance(orig_v, Variable):
            self.copy_v = Variable(orig_v)
            self.copy_v.concretetype = orig_v.concretetype
        else:
            # we can share the Constant()
            self.copy_v = orig_v

    def getconcretetype(self):
        return self.copy_v.concretetype

    def getvarorconst(self):
        return self.copy_v

    def match(self, other):
        return isinstance(other, LLRuntimeValue)  # XXX and ...


class LLState(object):
    """Entry state of a block or a graph, as a combination of LLAbstractValues
    for its input arguments."""

    def __init__(self, args_a):
        self.args_a = args_a

    def match(self, args_a):
        # simple for now
        for a1, a2 in zip(self.args_a, args_a):
            if not a1.match(a2):
                return False
        else:
            return True


class BlockState(LLState):
    """Entry state of a block."""

    def __init__(self, origblock, args_a):
        assert len(args_a) == len(origblock.inputargs)
        super(BlockState, self).__init__(args_a)
        self.origblock = origblock
        self.copyblock = None
        self.pendingsources = []

    def patchsource(self, source):
        if self.copyblock is None:
            print 'PENDING', self, hex(id(source))
            self.pendingsources.append(source)
        else:
            # XXX nice interface required!
            print 'LINKING', self, id(source), self.copyblock
            source.settarget(self.copyblock)

    def resolveblock(self, newblock):
        print "RESOLVING BLOCK", newblock
        self.copyblock = newblock
        for source in self.pendingsources:
            self.patchsource(source)
        del self.pendingsources[:]


class GraphState(LLState):
    """Entry state of a graph."""

    def __init__(self, origgraph, args_a):
        super(GraphState, self).__init__(args_a)
        self.origgraph = origgraph
        self.copygraph = FunctionGraph(origgraph.name, Block([]))   # grumble

    def settarget(self, block):
        block.isstartblock = True
        self.copygraph.startblock = block

# ____________________________________________________________

class LLAbstractInterp(object):

    def __init__(self):
        self.graphs = {}   # {origgraph: {BlockState: GraphState}}
        self.fixreturnblocks = []

    def itercopygraphs(self):
        for d in self.graphs.itervalues():
            for graphstate in d.itervalues():
                yield graphstate.copygraph

    def eval(self, origgraph, hints):
        # for now, 'hints' means "I'm absolutely sure that the
        # given variables will have the given ll value"
        self.allpendingstates = []
        self.hints = hints
        self.blocks = {}   # {origblock: list-of-LLStates}
        args_a = [LLRuntimeValue(orig_v=v) for v in origgraph.getargs()]
        graphstate = self.schedule_graph(args_a, origgraph)
        self.complete()
        self.fixgraphs()
        return graphstate.copygraph

    def fixgraphs(self):
        # add the missing '.returnblock' attribute
        for graph in self.fixreturnblocks:
            for block in graph.iterblocks():
                if block.operations == () and len(block.inputargs) == 1:
                    # here it is :-)
                    graph.returnblock = block
                    break
            else:
                # no return block...
                graph.getreturnvar().concretevalue = lltype.Void
            checkgraph(graph)   # sanity-check
        del self.fixreturnblocks

    def applyhint(self, args_a, origblock):
        result_a = []
        if origblock.operations == ():
            # make sure args_s does *not* contain LLConcreteValues
            for a in args_a:
                if isinstance(a, LLConcreteValue):
                    a = LLRuntimeValue(orig_v=a.getvarorconst())
                result_a.append(a)
        else:
            # apply the hints to make more LLConcreteValues
            for a, origv in zip(args_a, origblock.inputargs):
                if origv in self.hints:
                    # use the hint, ignore the source binding
                    a = LLConcreteValue(self.hints[origv])
                result_a.append(a)
        return result_a

    def schedule_graph(self, args_a, origgraph):
        origblock = origgraph.startblock
        state, args_a = self.schedule_getstate(args_a, origblock)
        try:
            graphstate = self.graphs[origgraph][state]
        except KeyError:
            graphstate = GraphState(origgraph, args_a)
            self.fixreturnblocks.append(graphstate.copygraph)
            d = self.graphs.setdefault(origgraph, {})
            d[state] = graphstate
        print "SCHEDULE_GRAPH", graphstate
        state.patchsource(graphstate)
        return graphstate

    def schedule(self, args_a, origblock):
        print "SCHEDULE", args_a, origblock
        # args_a: [a_value for v in origblock.inputargs]
        state, args_a = self.schedule_getstate(args_a, origblock)
        args_v = [a.getvarorconst() for a in args_a
                  if not isinstance(a, LLConcreteValue)]
        newlink = Link(args_v, None)
        state.patchsource(newlink)
        return newlink

    def schedule_getstate(self, args_a, origblock):
        # NOTA BENE: copyblocks can get shared between different copygraphs!
        args_a = self.applyhint(args_a, origblock)
        pendingstates = self.blocks.setdefault(origblock, [])
        # try to match this new state with an existing one
        for state in pendingstates:
            if state.match(args_a):
                # already matched
                return state, args_a
        else:
            # schedule this new state
            state = BlockState(origblock, args_a)
            pendingstates.append(state)
            self.allpendingstates.append(state)
            return state, args_a

    def complete(self):
        while self.allpendingstates:
            state = self.allpendingstates.pop()
            print 'CONSIDERING', state
            self.flowin(state)

    def flowin(self, state):
        # flow in the block
        assert state.copyblock is None
        origblock = state.origblock
        bindings = {}   # {Variables-of-origblock: a_value}
        def binding(v):
            if isinstance(v, Constant):
                return LLRuntimeValue(orig_v=v)
            else:
                return bindings[v]
        for v, a in zip(origblock.inputargs, state.args_a):
            if not isinstance(a, LLConcreteValue):
                a = LLRuntimeValue(orig_v=v)
            bindings[v] = a
        if origblock.operations == ():
            self.residual_operations = ()
        else:
            self.residual_operations = []
            for op in origblock.operations:
                handler = getattr(self, 'op_' + op.opname)
                a_result = handler(op, *[binding(v) for v in op.args])
                bindings[op.result] = a_result
        inputargs = []
        for v in origblock.inputargs:
            a = bindings[v]
            if not isinstance(a, LLConcreteValue):
                inputargs.append(a.getvarorconst())
        newblock = Block(inputargs)
        newblock.operations = self.residual_operations
        del self.residual_operations   # just in case
        if origblock.exitswitch is None:
            links = origblock.exits
        elif origblock.exitswitch == Constant(last_exception):
            XXX
        else:
            v = bindings[origblock.exitswitch].getvarorconst()
            if isinstance(v, Variable):
                newblock.exitswitch = v
                links = origblock.exits
            else:
                links = [link for link in origblock.exits
                              if link.llexitcase == v.value]
        newlinks = []
        for origlink in links:
            args_a = [binding(v) for v in origlink.args]
            newlink = self.schedule(args_a, origlink.target)
            newlinks.append(newlink)
        print "CLOSING"
        newblock.closeblock(*newlinks)
        state.resolveblock(newblock)

    def constantfold(self, constant_op, args_a):
        concretevalues = []
        any_concrete = False
        for a in args_a:
            v = a.getvarorconst()
            if isinstance(v, Constant):
                concretevalues.append(v.value)
            else:
                return None    # cannot constant-fold
            any_concrete = any_concrete or isinstance(a, LLConcreteValue)
        # can constant-fold
        concreteresult = constant_op(*concretevalues)
        if any_concrete:
            return LLConcreteValue(concreteresult)
        else:
            c = Constant(concreteresult)
            c.concretetype = typeOf(concreteresult)
            return LLRuntimeValue(c)

    def residual(self, opname, args_a, a_result):
        op = SpaceOperation(opname,
                            [a.getvarorconst() for a in args_a],
                            a_result.getvarorconst())
        self.residual_operations.append(op)

    def residualize(self, op, args_a, constant_op=None):
        RESULT = op.result.concretetype
        if RESULT is lltype.Void:
            return XXX_later
        if constant_op:
            a_result = self.constantfold(constant_op, args_a)
            if a_result is not None:
                return a_result
        a_result = LLRuntimeValue(op.result)
        self.residual(op.opname, args_a, a_result)
        return a_result

    # ____________________________________________________________

    def op_int_is_true(self, op, a):
        return self.residualize(op, [a], operator.truth)

    def op_int_add(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.add)

    def op_int_sub(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.sub)

    def op_int_mul(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.mul)

    def op_int_gt(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.gt)

    def op_int_lt(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.lt)

    def op_cast_char_to_int(self, op, a):
        return self.residualize(op, [a], ord)

    def op_same_as(self, op, a):
        return a

    def op_direct_call(self, op, a_func, *args_a):
        v_func = a_func.getvarorconst()
        if isinstance(v_func, Constant):
            fnobj = v_func.value._obj
            if hasattr(fnobj, 'graph'):
                origgraph = fnobj.graph
                graphstate = self.schedule_graph(args_a, origgraph)
                origfptr = v_func.value
                ARGS = []
                new_args_a = []
                for a in graphstate.args_a:
                    if not isinstance(a, LLConcreteValue):
                        ARGS.append(a.getconcretetype())
                        new_args_a.append(a)
                args_a = new_args_a
                TYPE = lltype.FuncType(
                   ARGS, lltype.typeOf(origfptr).TO.RESULT)
                fptr = lltype.functionptr(
                   TYPE, fnobj._name, graph=graphstate.copygraph)
                fconst = Constant(fptr)
                fconst.concretetype = lltype.typeOf(fptr)
                a_func = LLRuntimeValue(fconst)
        a_result = LLRuntimeValue(op.result)
        self.residual("direct_call", [a_func] + args_a, a_result) 
        return a_result

    def op_getfield(self, op, a_ptr, a_attrname):
        constant_op = None
        T = a_ptr.getconcretetype().TO
        v_ptr = a_ptr.getvarorconst()
        if isinstance(v_ptr, Constant):
            if T._hints.get('immutable', False):
                constant_op = getattr
        return self.residualize(op, [a_ptr, a_attrname], constant_op)
    op_getsubstruct = op_getfield

    def op_getarraysize(self, op, a_ptr):
        constant_op = None
        T = a_ptr.getconcretetype().TO
        v_ptr = a_ptr.getvarorconst()
        if isinstance(v_ptr, Constant):
            if T._hints.get('immutable', False):
                constant_op = len
        return self.residualize(op, [a_ptr], constant_op)

    def op_getarrayitem(self, op, a_ptr, a_index):
        constant_op = None
        T = a_ptr.getconcretetype().TO
        v_ptr = a_ptr.getvarorconst()
        if isinstance(v_ptr, Constant):
            if T._hints.get('immutable', False):
                constant_op = operator.getitem
        return self.residualize(op, [a_ptr, a_index], constant_op)

        
