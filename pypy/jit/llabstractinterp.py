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

orig_v = Constant(None)
orig_v.concretetype = lltype.Void
ll_no_return_value = LLRuntimeValue(orig_v)
del orig_v


class BlockState(object):
    """Entry state of a block, as a combination of LLAbstractValues
    for its input arguments."""

    def __init__(self, origblock, args_a):
        assert len(args_a) == len(origblock.inputargs)
        self.args_a = args_a
        self.origblock = origblock
        self.copyblock = None

    def match(self, args_a):
        # simple for now
        for a1, a2 in zip(self.args_a, args_a):
            if not a1.match(a2):
                return False
        else:
            return True

    def resolveblock(self, newblock):
        #print "RESOLVING BLOCK", newblock
        self.copyblock = newblock


class GraphState(object):
    """Entry state of a graph."""

    def __init__(self, origgraph, args_a):
        super(GraphState, self).__init__(args_a)
        self.origgraph = origgraph
        self.copygraph = FunctionGraph(origgraph.name, Block([]))   # grumble
        for orig_v, copy_v in [(origgraph.getreturnvar(),
                                self.copygraph.getreturnvar()),
                               (origgraph.exceptblock.inputargs[0],
                                self.copygraph.exceptblock.inputargs[0]),
                               (origgraph.exceptblock.inputargs[1],
                                self.copygraph.exceptblock.inputargs[1])]:
            if hasattr(orig_v, 'concretetype'):
                copy_v.concretetype = orig_v.concretetype
        self.a_return = None
        self.state = "before"

    def settarget(self, block):
        block.isstartblock = True
        self.copygraph.startblock = block

    def complete(self, interp):
        assert self.state != "during"
        if self.state == "before":
            builderframe = LLAbstractFrame(interp, self)
            builderframe.complete()
            self.state = "after"

# ____________________________________________________________

class LLAbstractInterp(object):

    def __init__(self):
        self.graphs = {}          # {origgraph: {BlockState: GraphState}}
        self.pendingstates = {}   # {Link-or-GraphState: next-BlockState}

    def itercopygraphs(self):
        for d in self.graphs.itervalues():
            for graphstate in d.itervalues():
                yield graphstate.copygraph

    def eval(self, origgraph, hints):
        # for now, 'hints' means "I'm absolutely sure that the
        # given variables will have the given ll value"
        self.hints = hints
        self.blocks = {}   # {origblock: list-of-LLStates}
        args_a = [LLRuntimeValue(orig_v=v) for v in origgraph.getargs()]
        graphstate, args_a = self.schedule_graph(args_a, origgraph)
        graphstate.complete(self)
        return graphstate.copygraph

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
            d = self.graphs.setdefault(origgraph, {})
            d[state] = graphstate
            self.pendingstates[graphstate] = state
        #print "SCHEDULE_GRAPH", graphstate
        return graphstate, args_a

    def schedule(self, args_a, origblock):
        #print "SCHEDULE", args_a, origblock
        # args_a: [a_value for v in origblock.inputargs]
        state, args_a = self.schedule_getstate(args_a, origblock)
        args_v = [a.getvarorconst() for a in args_a
                  if not isinstance(a, LLConcreteValue)]
        newlink = Link(args_v, None)
        self.pendingstates[newlink] = state
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
            return state, args_a


class LLAbstractFrame(object):

    def __init__(self, interp, graphstate):
        self.interp = interp
        self.graphstate = graphstate

    def complete(self):
        graph = self.graphstate.copygraph
        interp = self.interp
        pending = [self.graphstate]
        seen = {}
        # follow all possible links, forcing the blocks along the way to be
        # computed
        while pending:
            next = pending.pop()
            state = interp.pendingstates[next]
            if state.copyblock is None:
                self.flowin(state)
            next.settarget(state.copyblock)
            for link in state.copyblock.exits:
                if link not in seen:
                    seen[link] = True
                    if link.target is None or link.target.operations != ():
                        pending.append(link)
                    else:
                        # link.target is a return or except block; make sure
                        # that it is really the one from 'graph' -- by patching
                        # 'graph' if necessary.
                        if len(link.target.inputargs) == 1:
                            graph.returnblock = link.target
                        elif len(link.target.inputargs) == 2:
                            graph.exceptblock = link.target
                        else:
                            raise Exception("uh?")
        # the graph should be complete now; sanity-check
        checkgraph(graph)

    def flowin(self, state):
        # flow in the block
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
        print
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

        if origblock.operations != ():
            # build exit links and schedule their target for later completion
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
                newlink = self.interp.schedule(args_a, origlink.target)
                newlinks.append(newlink)
        else:
            # copies of return and except blocks are *normal* blocks currently;
            # they are linked to the official return or except block of the
            # copygraph.  If needed, LLConcreteValues are turned into Constants.
            if len(origblock.inputargs) == 1:
                self.graphstate.a_return = bindings[origblock.inputargs[0]]
                target = self.graphstate.copygraph.returnblock
            else:
                XXX_later
                target = self.graphstate.copygraph.exceptblock
            args_v = [binding(v).getvarorconst() for v in origblock.inputargs]
            newlinks = [Link(args_v, target)]
        #print "CLOSING"
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
        print 'fold:', constant_op, concretevalues
        concreteresult = constant_op(*concretevalues)
        if any_concrete:
            return LLConcreteValue(concreteresult)
        else:
            c = Constant(concreteresult)
            c.concretetype = typeOf(concreteresult)
            return LLRuntimeValue(c)

    def residual(self, opname, args_a, a_result):
        v_result = a_result.getvarorconst()
        if isinstance(v_result, Constant):
            v = Variable()
            v.concretetype = v_result.concretetype
            v_result = v
        op = SpaceOperation(opname,
                            [a.getvarorconst() for a in args_a],
                            v_result)
        print 'keep:', op
        self.residual_operations.append(op)

    def residualize(self, op, args_a, constant_op=None):
        if constant_op:
            RESULT = op.result.concretetype
            if RESULT is lltype.Void:
                return ll_no_return_value
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

    def op_int_and(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.and_)

    def op_int_rshift(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.rshift)

    def op_int_neg(self, op, a1):
        return self.residualize(op, [a1], operator.neg)

    def op_int_gt(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.gt)

    def op_int_lt(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.lt)

    def op_int_ge(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.ge)

    def op_int_le(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.le)

    def op_int_eq(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.eq)

    def op_int_ne(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.ne)

    def op_cast_char_to_int(self, op, a):
        return self.residualize(op, [a], ord)

    def op_same_as(self, op, a):
        return a

    def op_direct_call(self, op, a_func, *args_a):
        a_result = LLRuntimeValue(op.result)
        v_func = a_func.getvarorconst()
        if isinstance(v_func, Constant):
            fnobj = v_func.value._obj
            if hasattr(fnobj, 'graph'):
                origgraph = fnobj.graph
                graphstate, args_a = self.interp.schedule_graph(
                    args_a, origgraph)
                if graphstate.state != "during":
                    graphstate.complete(self.interp)
                    if isinstance(graphstate.a_return, LLConcreteValue):
                        a_result = graphstate.a_return
                
                origfptr = v_func.value
                ARGS = []
                new_args_a = []
                for a in args_a:
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
        self.residual("direct_call", [a_func] + args_a, a_result) 
        return a_result

    def op_getfield(self, op, a_ptr, a_attrname):
        constant_op = None
        T = a_ptr.getconcretetype().TO
        if T._hints.get('immutable', False):
            constant_op = getattr
        return self.residualize(op, [a_ptr, a_attrname], constant_op)

    def op_getsubstruct(self, op, a_ptr, a_attrname):
        return self.residualize(op, [a_ptr, a_attrname], getattr)

    def op_getarraysize(self, op, a_ptr):
        return self.residualize(op, [a_ptr], len)

    def op_getarrayitem(self, op, a_ptr, a_index):
        constant_op = None
        T = a_ptr.getconcretetype().TO
        if T._hints.get('immutable', False):
            constant_op = operator.getitem
        return self.residualize(op, [a_ptr, a_index], constant_op)

    def op_malloc(self, op, a_T):
        return self.residualize(op, [a_T])

    def op_malloc_varsize(self, op, a_T, a_size):
        return self.residualize(op, [a_T, a_size])

    def op_setfield(self, op, a_ptr, a_attrname, a_value):
        return self.residualize(op, [a_ptr, a_attrname, a_value])

    def op_setarrayitem(self, op, a_ptr, a_index, a_value):
        return self.residualize(op, [a_ptr, a_index, a_value])
