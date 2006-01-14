import operator
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import Block, Link, FunctionGraph
from pypy.objspace.flow.model import checkgraph, c_last_exception
from pypy.rpython.lltypesystem import lltype
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks
from pypy.jit.llvalue import LLAbstractValue, const, newvar, dupvar
from pypy.jit.llvalue import ll_no_return_value
from pypy.jit.llvalue import FlattenMemo, MatchMemo, FreezeMemo, UnfreezeMemo
from pypy.jit.llcontainer import LLAbstractContainer, virtualcontainervalue
from pypy.jit.llcontainer import hasllcontent

# ____________________________________________________________

class LLState(LLAbstractContainer):
    """Entry state of a block, as a combination of LLAbstractValues
    for its input arguments.  Abstract base class."""

    frozen = False   # for debugging

    def __init__(self, back, args_a, origblock):
        self.back = back
        self.args_a = args_a
        self.origblock = origblock
        self.copyblocks = {}
        assert len(args_a) == len(self.getlivevars())

    def key(self):
        # two LLStates should return different keys if they cannot match().
        result = self.localkey()
        if self.back is not None:
            result += self.back.key()
        return result

    def enum_fixed_constants(self, incoming_link_args=None):
        assert self.frozen, "enum_fixed_constants(): only for frozen states"
        selfvalues = self.flatten()
        if incoming_link_args is None:
            for a in selfvalues:
                yield None   # no incoming args provided, so no fixed constants
        else:
            assert len(incoming_link_args) == len(selfvalues)
            for linkarg, fr in zip(incoming_link_args, selfvalues):
                if fr.fixed:
                    assert isinstance(linkarg, Constant), (
                        "unexpected Variable %r reaching the fixed input arg %r"
                        % (linkarg, fr))
                    yield linkarg
                else:
                    yield None

    def getruntimevars(self):
        assert not self.frozen, "getruntimevars(): not for frozen states"
        return [a.runtimevar for a in self.flatten()]

    def flatten(self, memo=None):
        if memo is None:
            memo = FlattenMemo()
        if self.back is not None:
            self.back.flatten(memo)
        for a in self.args_a:
            a.flatten(memo)
        return memo.result

    def match(self, other, memo):
        assert self.frozen, "match(): 1st state must be frozen"
        assert not other.frozen, "match(): 2nd state must not be frozen"
        assert self.__class__ is other.__class__
        if self.localkey() != other.localkey():
            return False
        if self.back is None:
            if other.back is not None:
                return False
        else:
            if other.back is None:
                return False
            if not self.back.match(other.back, memo):
                return False
        for a1, a2 in zip(self.args_a, other.args_a):
            if not a1.match(a2, memo):
                return False
        else:
            return True

    def freeze(self, memo):
        assert not self.frozen, "freeze(): state already frozen"
        if self.back is not None:
            new_back = self.back.freeze(memo)
        else:
            new_back = None
        new_args_a = [a.freeze(memo) for a in self.args_a]
        result = self.__class__(new_back, new_args_a, *self.localkey())
        result.frozen = True    # for debugging
        return result

    def unfreeze(self, memo):
        assert self.frozen, "unfreeze(): state not frozen"
        if self.back is not None:
            new_back = self.back.unfreeze(memo)
        else:
            new_back = None
        new_args_a = []
        for v, a in zip(self.getlivevars(), self.args_a):
            a = a.unfreeze(memo)
            # try to preserve the name
            if isinstance(a.runtimevar, Variable):
                a.runtimevar.rename(v)
            new_args_a.append(a)
        return self.__class__(new_back, new_args_a, *self.localkey())

    def getbindings(self):
        return dict(zip(self.getlivevars(), self.args_a))


class LLBlockState(LLState):
    """Entry state of a block, as a combination of LLAbstractValues
    for its input arguments."""

    def localkey(self):
        return (self.origblock,)

    def getlivevars(self):
        return self.origblock.inputargs


class LLSuspendedBlockState(LLBlockState):
    """Block state in the middle of the execution of one instruction
    (typically a direct_call() that is causing inlining)."""

    def __init__(self, back, args_a, origblock, origposition):
        self.origposition = origposition
        super(LLSuspendedBlockState, self).__init__(back, args_a, origblock)

    def localkey(self):
        return (self.origblock, self.origposition)

    def getlivevars(self):
        return live_variables(self.origblock, self.origposition)


# ____________________________________________________________


class Policy(object):
    def __init__(self, inlining=False, const_propagate=False,
                       concrete_propagate=True, concrete_args=True,
                       oopspec=False):
        self.inlining = inlining
        self.const_propagate = const_propagate
        self.concrete_propagate = concrete_propagate
        self.concrete_args = concrete_args
        self.oopspec = oopspec

# hint-driven policy
best_policy = Policy(inlining=True, const_propagate=True, concrete_args=False)


class LLAbstractInterp(object):

    def __init__(self, policy=best_policy):
        self.graphs = []
        self.graphstates = {}     # {origgraph: {BlockState: GraphState}}
        self.pendingstates = {}   # {Link-or-GraphState: next-BlockState}
        self.blocks = {}          # {BlockState.key(): list-of-LLBlockStates}
        self.policy = policy

    def itercopygraphs(self):
        return iter(self.graphs)

    def eval(self, origgraph, arghints):
        # 'arghints' maps argument index to a given ll value
        args_a = []
        for i, v in enumerate(origgraph.getargs()):
            if i in arghints:
                a = LLAbstractValue(const(arghints[i]))
                a.concrete = self.policy.concrete_args
            else:
                a = LLAbstractValue(dupvar(v))
            args_a.append(a)
        graphstate = self.schedule_graph(args_a, origgraph)
        graphstate.complete()
        return graphstate.copygraph

    def schedule_graph(self, args_a, origgraph):
        inputstate = LLBlockState(None, args_a, origgraph.startblock)
        frozenstate = self.schedule_getstate(inputstate)
        try:
            graphstate = self.graphstates[origgraph][frozenstate]
        except KeyError:
            d = self.graphstates.setdefault(origgraph, {})
            graphstate = GraphState(self, origgraph, inputstate, n=len(d))
            d[frozenstate] = graphstate
            self.pendingstates[graphstate] = frozenstate
        #print "SCHEDULE_GRAPH", graphstate
        return graphstate

    def schedule(self, inputstate):
        #print "SCHEDULE", args_a, origblock
        frozenstate = self.schedule_getstate(inputstate)
        args_v = inputstate.getruntimevars()
        newlink = Link(args_v, None)
        self.pendingstates[newlink] = frozenstate
        return newlink

    def schedule_getstate(self, inputstate):
        # NOTA BENE: copyblocks can get shared between different copygraphs!
        pendingstates = self.blocks.setdefault(inputstate.key(), [])
        # try to match the input state with an existing one
        for i, savedstate in enumerate(pendingstates):
            memo = MatchMemo()
            if savedstate.match(inputstate, memo):
                # already matched
                must_restart = False
                for statevar, inputvar in memo.dependencies:
                    if statevar.fixed:
                        # the saved state says that this new incoming
                        # variable must be forced to a constant
                        self.hint_needs_constant(inputvar)
                        # we'll have to restart if we are trying to turn
                        # a variable into a constant
                        if inputvar.maybe_get_constant() is None:
                            must_restart = True
                if must_restart:
                    raise RestartCompleting
                # The new inputstate is merged into the existing saved state.
                # Record this inputstate's variables in the possible origins
                # of the saved state's variables.
                for statevar, inputvar in memo.dependencies:
                    statevar.origin.extend(inputvar.origin)
                return savedstate
        else:
            # freeze and return this new state
            frozenstate = inputstate.freeze(FreezeMemo())
            pendingstates.append(frozenstate)
            return frozenstate

    def hint_needs_constant(self, a):
        # Force the given LLAbstractValue to be a fixed constant.
        fix_me = list(a.origin)
        progress = False
        while fix_me:
            fr = fix_me.pop()
            if fr.fixed:
                continue    # already fixed
            if not fr.fixed:
                print 'fixing:', fr
                fr.fixed = True
                progress = True
                fix_me.extend(fr.origin)
        if not progress and a.maybe_get_constant() is None:
            raise HintError("cannot trace the origin of %r" % (a,))


class GraphState(object):
    """Entry state of a graph."""

    def __init__(self, interp, origgraph, inputstate, n):
        self.interp = interp
        self.origgraph = origgraph
        name = '%s_%d' % (origgraph.name, n)
        self.copygraph = FunctionGraph(name, Block([]))   # grumble
        interp.graphs.append(self.copygraph)
        for orig_v, copy_v in [(origgraph.getreturnvar(),
                                self.copygraph.getreturnvar()),
                               (origgraph.exceptblock.inputargs[0],
                                self.copygraph.exceptblock.inputargs[0]),
                               (origgraph.exceptblock.inputargs[1],
                                self.copygraph.exceptblock.inputargs[1])]:
            if hasattr(orig_v, 'concretetype'):
                copy_v.concretetype = orig_v.concretetype
        # The 'args' attribute is needed by try_to_complete(),
        # which looks for it on either a GraphState or a Link
        self.args = inputstate.getruntimevars()
        #self.a_return = None
        self.state = "before"

    def settarget(self, block):
        block.isstartblock = True
        self.copygraph.startblock = block

    def complete(self):
        assert self.state != "during"
        if self.state == "after":
            return
        self.state = "during"
        while True:
            try:
                self.try_to_complete()
                break
            except RestartCompleting:
                print '--- restarting ---'
                continue

    def try_to_complete(self):
        graph = self.copygraph
        interp = self.interp
        pending = [self]
        seen = {}
        did_any_generalization = False
        # follow all possible links, forcing the blocks along the way to be
        # computed
        while pending:
            next = pending.pop()
            state = interp.pendingstates[next]

            # debugging: print the current call stack
            print
            st = state
            stlist = []
            while st.back is not None:
                st = st.back
                stlist.append(st)
            stlist.reverse()
            for st in stlist:
                op = st.origblock.operations[st.origposition]
                if op.opname == 'direct_call':
                    v = op.args[0].value
                elif op.opname == 'indirect_call':
                    v = op.args[0]
                else:
                    v = '?'
                print 'In %r:' % (v,)

            # Before computing each block, we compute a 'key' which is
            # derived from the current state's fixed constants.  Instead
            # of only one residual block per state, there is one residual
            # block per 'key'.  The residual block in question has
            # inputargs that are constants -- at least for each fixed
            # constant, but possibly for more, if policy.const_propagate
            # is True.
            #
            # When we consider a link that should go to a given block, we
            # compute the 'key' and check if there is already a
            # corresponding residual block; if so, we check the constants
            # that have been put in the inputargs.  If they don't match
            # the new link's constants, we throw away the existing
            # residual block and compute a new one with less constants in
            # its inputargs.
            #
            # These recomputations are based on the official 'key', so
            # that links with different *fixed* constants don't interfere
            # with each other.

            key = tuple(state.enum_fixed_constants(next.args))
            try:
                block = state.copyblocks[key]
            except KeyError:
                if interp.policy.const_propagate:
                    # originally, propagate all constants from next.args
                    # optimistically to the new block
                    initial_key = next.args
                else:
                    # don't propagate anything more than required ('fixed')
                    initial_key = key
                print 'flowin() with initial key', initial_key
                block = self.flowin(state, initial_key)
                state.copyblocks[key] = block
            else:
                # check if the tentative constants of the existing block
                # are compatible with the ones specified by the new link
                merged_key = []
                recompute = False
                for c1, c2 in zip(block.inputargs, next.args):
                    if isinstance(c1, Constant) and c1 != c2:
                        # incompatibility
                        merged_key.append(None)  # force a Variable
                        recompute = True
                    else:
                        merged_key.append(c1)    # unmodified
                if recompute:
                    print 'flowin() merged as', merged_key
                    block = self.flowin(state, merged_key)
                    state.copyblocks[key] = block
                    did_any_generalization = True
            next.settarget(block)
            for link in block.exits:
                if link.target is None or link.target.operations != ():
                    if link not in seen:
                        seen[link] = True
                        pending.append(link)
                else:
                    # link.target is a return or except block; make sure
                    # that it is really the one from 'graph' -- by patching
                    # 'graph' if necessary.
                    if len(link.target.inputargs) == 1:
                        #self.a_return = state.args_a[0]
                        graph.returnblock = link.target
                    elif len(link.target.inputargs) == 2:
                        graph.exceptblock = link.target
                    else:
                        raise Exception("uh?")

        if did_any_generalization:
            raise RestartCompleting

        remove_constant_inputargs(graph)

        # the graph should be complete now; sanity-check
        try:
            checkgraph(graph)
        except Exception, e:
            print 'INVALID GRAPH:'
            import traceback
            traceback.print_exc()
            print 'graph.show()...'
            graph.show()
            raise
        eliminate_empty_blocks(graph)
        join_blocks(graph)
        self.state = "after"

    def flowin(self, state, key):
        # flow in the block
        assert isinstance(state, LLBlockState)
        origblock = state.origblock
        origposition = 0
        builder = BlockBuilder(self.interp, state, key)
        newexitswitch = None
        # debugging print
        arglist = []
        if key:
            for a1, a2, k in zip(state.flatten(),
                                 builder.runningstate.flatten(),
                                 key):
                if isinstance(k, Constant):
                    arglist.append('%s => %s' % (a1, k))
                else:
                    arglist.append('%s => %s' % (a1, a2))
        print
        print '--> %s [%s]' % (origblock, ', '.join(arglist))
        for op in origblock.operations:
            print '\t\t', op
        # end of debugging print
        try:
            if origblock.operations == ():
                if state.back is None:
                    # copies of return and except blocks are *normal* blocks
                    # currently; they are linked to the official return or
                    # except block of the copygraph.
                    if len(origblock.inputargs) == 1:
                        target = self.copygraph.returnblock
                    else:
                        target = self.copygraph.exceptblock
                    args_v = [builder.binding(v).forcevarorconst(builder)
                              for v in origblock.inputargs]
                    raise InsertNextLink(Link(args_v, target))
                else:
                    # finishing a handle_call_inlining(): link back to
                    # the parent, passing the return value
                    # XXX GENERATE KEEPALIVES HERE
                    if len(origblock.inputargs) == 1:
                        a_result = builder.binding(origblock.inputargs[0])
                        builder.runningstate = builder.runningstate.back
                        origblock = builder.runningstate.origblock
                        origposition = builder.runningstate.origposition
                        builder.bindings = builder.runningstate.getbindings()
                        op = origblock.operations[origposition]
                        builder.bindings[op.result] = a_result
                        origposition += 1
                    else:
                        XXX_later

            # flow the actual operations of the block
            for i in range(origposition, len(origblock.operations)):
                op = origblock.operations[i]
                builder.enter(origblock, i)
                try:
                    builder.dispatch(op)
                finally:
                    builder.leave()
            # done

        except InsertNextLink, e:
            # the current operation forces a jump to another block
            newlinks = [e.link]

        else:
            # normal path: build exit links and schedule their target for
            # later completion
            if origblock.exitswitch is None:
                links = origblock.exits
            elif origblock.exitswitch == c_last_exception:
                XXX
            else:
                a = builder.bindings[origblock.exitswitch]
                v = a.forcevarorconst(builder)
                if isinstance(v, Variable):
                    newexitswitch = v
                    links = origblock.exits
                else:
                    links = [link for link in origblock.exits
                                  if link.llexitcase == v.value]
            newlinks = []
            for origlink in links:
                args_a = [builder.binding(v) for v in origlink.args]
                nextinputstate = LLBlockState(builder.runningstate.back,
                                              args_a, origlink.target)
                newlink = self.interp.schedule(nextinputstate)
                if newexitswitch is not None:
                    newlink.exitcase = origlink.exitcase
                    newlink.llexitcase = origlink.llexitcase
                newlinks.append(newlink)

        newblock = builder.buildblock(newexitswitch, newlinks)
        return newblock


class BlockBuilder(object):

    def __init__(self, interp, initialstate, key):
        self.interp = interp
        memo = UnfreezeMemo(key)
        self.runningstate = initialstate.unfreeze(memo)
        assert list(memo.propagateconsts) == []   # all items consumed
        self.newinputargs = self.runningstate.getruntimevars()
        assert len(self.newinputargs) == len(key)
        # {Variables-of-origblock: a_value}
        self.bindings = self.runningstate.getbindings()
        self.residual_operations = []

    def buildblock(self, newexitswitch, newlinks):
        b = Block(self.newinputargs)
        b.operations = self.residual_operations
        b.exitswitch = newexitswitch
        b.closeblock(*newlinks)
        return b

    def binding(self, v):
        if isinstance(v, Constant):
            return LLAbstractValue(v)
        else:
            return self.bindings[v]

    def dispatch(self, op):
        handler = getattr(self, 'op_' + op.opname)
        a_result = handler(op, *[self.binding(v) for v in op.args])
        self.bindings[op.result] = a_result

    def enter(self, origblock, origposition):
        self.blockpos = origblock, origposition

    def leave(self):
        del self.blockpos

    # ____________________________________________________________
    # Utilities

    def constantfold(self, constant_op, args_a):
        concretevalues = []
        any_concrete = False
        for a in args_a:
            v = a.maybe_get_constant()
            if v is None:
                return None    # cannot constant-fold
            concretevalues.append(v.value)
            any_concrete = any_concrete or a.concrete
        # can constant-fold
        print 'fold:', constant_op.__name__, concretevalues
        concreteresult = constant_op(*concretevalues)
        a_result = LLAbstractValue(const(concreteresult))
        if any_concrete and self.interp.policy.concrete_propagate:
            a_result.concrete = True
        else:
            self.record_origin(a_result, args_a)
        return a_result

    def residual(self, opname, args_a, a_result):
        v_result = a_result.forcevarorconst(self)
        if isinstance(v_result, Constant):
            v_result = newvar(v_result.concretetype)
        op = SpaceOperation(opname,
                            [a.forcevarorconst(self) for a in args_a],
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
        a_result = LLAbstractValue(dupvar(op.result))
        if constant_op:
            self.record_origin(a_result, args_a)
        self.residual(op.opname, args_a, a_result)
        return a_result

    def record_origin(self, a_result, args_a):
        origin = a_result.origin
        for a in args_a:
            if not a.concrete:
                origin.extend(a.origin)

    # ____________________________________________________________
    # Operation handlers

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

    op_char_eq = op_int_eq
    op_char_ne = op_int_ne

    def op_cast_char_to_int(self, op, a):
        return self.residualize(op, [a], ord)

    def op_cast_bool_to_int(self, op, a):
        return self.residualize(op, [a], int)

    def op_same_as(self, op, a):
        return a

    def op_hint(self, op, a, a_hints):
        c_hints = a_hints.maybe_get_constant()
        assert c_hints is not None, "hint dict not constant"
        hints = c_hints.value
        if hints.get('concrete'):
            # turn this 'a' into a concrete value
            a.forcevarorconst(self)
            if not a.concrete:
                self.interp.hint_needs_constant(a)
                c = a.maybe_get_constant()
                if c is None:
                    # Oups! it's not a constant.  But hint_needs_constant()
                    # traced it back to a constant that was turned into a
                    # variable by a link.  This constant has been marked as
                    # 'fixed', so if we restart now, op_hint() should receive
                    # a constant the next time.
                    raise RestartCompleting
                a = LLAbstractValue(c)
                a.concrete = True
        if hints.get('nonvirtual'):
            a.forcevarorconst(self)   # for testing only
        return a

    def op_direct_call(self, op, *args_a):
        a_result = self.handle_call(op, *args_a)
        if a_result is None:
            a_result = self.residualize(op, args_a)
        return a_result

    def op_indirect_call(self, op, *args_a):
        # XXX not really sure what the right thing to do is:
        # right now there is no test that produces indirect_call
        # the slight ugliness involved is, that it is necessary to
        # change the operation from an indirect_call to a direct_call
        # when the first argument of the indirect_call is discovered to be
        # constant
        assert 0, "XXX"

    def handle_call(self, op, a_func, *args_a):
        v_func = a_func.maybe_get_constant()
        if v_func is None:
            return None
        fnobj = v_func.value._obj
        if not hasattr(fnobj, 'graph'):
            return None

        if self.interp.policy.oopspec and hasattr(fnobj._callable, 'oopspec'):
            a_result = self.handle_highlevel_operation(op, fnobj._callable,
                                                       *args_a)
            if a_result is not None:
                return a_result

        if getattr(fnobj._callable, 'suggested_primitive', False):
            return None

        origgraph = fnobj.graph
        if self.interp.policy.inlining:
            return self.handle_call_inlining(op, origgraph, *args_a)
        else:
            return self.handle_call_residual(op, origgraph, *args_a)

    def handle_call_inlining(self, op, origgraph, *args_a):
        origblock, origposition = self.blockpos
        alive_a = []
        for v in live_variables(origblock, origposition):
            alive_a.append(self.bindings[v])
        parentstate = LLSuspendedBlockState(self.runningstate.back, alive_a,
                                            origblock, origposition)
        nextstate = LLBlockState(parentstate, args_a, origgraph.startblock)
        raise InsertNextLink(self.interp.schedule(nextstate))

    def handle_call_residual(self, op, origgraph, *args_a):
        # residual call: for now we need to force all arguments
        any_concrete = False
        for a in args_a:
            a.forcevarorconst(self)
            any_concrete = any_concrete or a.concrete
        if not any_concrete:
            return None

        a_result = LLAbstractValue(dupvar(op.result))
        a_real_result = a_result
        graphstate = self.interp.schedule_graph(args_a, origgraph)
        #print 'SCHEDULE_GRAPH', args_a, '==>', graphstate.copygraph.name
        if graphstate.state != "during":
            print 'ENTERING', graphstate.copygraph.name, args_a
            graphstate.complete()
            #if graphstate.a_return is not None:
            #    a = graphstate.a_return.unfreeze(UnfreezeMemo())
            #    if a.maybe_get_constant() is not None:
            #        a_real_result = a    # propagate a constant result
            print 'LEAVING', graphstate.copygraph.name#, graphstate.a_return

        ARGS = []
        new_args_a = []
        for a in args_a:
            if not a.concrete:
                ARGS.append(a.getconcretetype())
                new_args_a.append(a)
        args_a = new_args_a
        TYPE = lltype.FuncType(ARGS, a_result.getconcretetype())
        fptr = lltype.functionptr(
           TYPE, graphstate.copygraph.name, graph=graphstate.copygraph)
        a_func = LLAbstractValue(const(fptr))
        self.residual("direct_call", [a_func] + args_a, a_result) 
        return a_real_result

    def op_getfield(self, op, a_ptr, a_attrname):
        if hasllcontent(a_ptr):
            c_attrname = a_attrname.maybe_get_constant()
            assert c_attrname is not None
            return a_ptr.content.getfield(c_attrname.value)
        constant_op = None
        T = a_ptr.getconcretetype().TO
        if T._hints.get('immutable', False):
            constant_op = getattr
        return self.residualize(op, [a_ptr, a_attrname], constant_op)

    def op_getsubstruct(self, op, a_ptr, a_attrname):
        if hasllcontent(a_ptr):
            c_attrname = a_attrname.maybe_get_constant()
            assert c_attrname is not None
            # the difference with op_getfield() is only that the following
            # line always returns a LLAbstractValue with content != None
            return a_ptr.content.getfield(c_attrname.value)
        return self.residualize(op, [a_ptr, a_attrname], getattr)

    def op_getarraysize(self, op, a_ptr):
        if hasllcontent(a_ptr):
            return LLAbstractValue(const(a_ptr.content.length))
        return self.residualize(op, [a_ptr], len)

    def op_getarrayitem(self, op, a_ptr, a_index):
        if hasllcontent(a_ptr):
            c_index = a_index.maybe_get_constant()
            if c_index is not None:
                return a_ptr.content.getfield(c_index.value)
        constant_op = None
        T = a_ptr.getconcretetype().TO
        if T._hints.get('immutable', False):
            constant_op = operator.getitem
        return self.residualize(op, [a_ptr, a_index], constant_op)

    def op_malloc(self, op, a_T):
        c_T = a_T.maybe_get_constant()
        assert c_T is not None
        return virtualcontainervalue(c_T.value)

    def op_malloc_varsize(self, op, a_T, a_size):
        c_size = a_size.maybe_get_constant()
        if c_size is not None:
            c_T = a_T.maybe_get_constant()
            assert c_T is not None
            return virtualcontainervalue(c_T.value, c_size.value)
        return self.residualize(op, [a_T, a_size])

    def op_setfield(self, op, a_ptr, a_attrname, a_value):
        if hasllcontent(a_ptr):
            c_attrname = a_attrname.maybe_get_constant()
            assert c_attrname is not None
            a_ptr.content.setfield(c_attrname.value, a_value)
            return ll_no_return_value
        return self.residualize(op, [a_ptr, a_attrname, a_value])

    def op_setarrayitem(self, op, a_ptr, a_index, a_value):
        if hasllcontent(a_ptr):
            c_index = a_index.maybe_get_constant()
            if c_index is not None:
                a_ptr.content.setfield(c_index.value, a_value)
                return ll_no_return_value
        return self.residualize(op, [a_ptr, a_index, a_value])

    def op_cast_pointer(self, op, a_ptr):
        if hasllcontent(a_ptr):
            down_or_up = lltype.castable(op.result.concretetype,
                                         a_ptr.content.getconcretetype())
            # the following works because if a structure is virtual, then
            # all its parent and inlined substructures are also virtual
            a = a_ptr
            if down_or_up >= 0:
                for n in range(down_or_up):
                    a = a.content.getfield(a.content.T._names[0])
            else:
                for n in range(-down_or_up):
                    a = a.content.a_parent
            return a
        def constant_op(ptr):
            return lltype.cast_pointer(op.result.concretetype, ptr)
        return self.residualize(op, [a_ptr], constant_op)

    def op_keepalive(self, op, a_ptr):
        memo = FlattenMemo()
        a_ptr.flatten(memo)
        for a in memo.result:
            v = a.runtimevar
            if isinstance(v, Variable) and not v.concretetype._is_atomic():
                op = SpaceOperation('keepalive', [v], newvar(lltype.Void))
                print 'virtual:', op
                self.residual_operations.append(op)
        return ll_no_return_value

    # High-level operation dispatcher
    def handle_highlevel_operation(self, op, ll_func, *args_a):
        # parse the oopspec and fill in the arguments
        operation_name, args = ll_func.oopspec.split('(', 1)
        assert args.endswith(')')
        args = args[:-1] + ','     # trailing comma to force tuple syntax
        argnames = ll_func.func_code.co_varnames[:len(args_a)]
        d = dict(zip(argnames, args_a))
        argtuple = eval(args, d)
        args_a = []
        for a in argtuple:
            if not isinstance(a, LLAbstractValue):
                a = LLAbstractValue(const(a))
            args_a.append(a)
        # end of rather XXX'edly hackish parsing

        if operation_name == 'newlist':
            from pypy.jit.vlist import oop_newlist
            handler = oop_newlist
        else:
            # dispatch on the 'self' argument if it is virtual
            a_self = args_a[0]
            args_a = args_a[1:]
            if not isinstance(a_self, LLAbstractContainer):
                return None
            type_name, operation_name = operation_name.split('.')
            if a_self.type_name != type_name:
                return None
            try:
                handler = getattr(a_self, 'oop_' + operation_name)
            except AttributeError:
                print 'MISSING HANDLER: oop_%s' % (operation_name,)
                return None
        try:
            a_result = handler(op, *args_a)
        except NotImplementedError:
            return None
        if a_result is None:
            a_result = ll_no_return_value
        assert op.result.concretetype == a_result.getconcretetype(), (
            "type mismatch: %s\nreturned %s\nexpected %s" % (
            handler, a_result.getconcretetype(), op.result.concretetype))
        return a_result


class InsertNextLink(Exception):
    def __init__(self, link):
        self.link = link

class RestartCompleting(Exception):
    pass

class HintError(Exception):
    pass


def live_variables(block, position):
    # return a list of all variables alive in the block at the beginning of
    # the given 'position', in the order of creation.
    used = {block.exitswitch: True}
    for op in block.operations[position:]:
        for v in op.args:
            used[v] = True
    for link in block.exits:
        for v in link.args:
            used[v] = True
    result = []
    for v in block.inputargs:
        if v in used:
            result.append(v)
    for op in block.operations[:position]:
        if op.result in used:
            result.append(op.result)
    return result

def remove_constant_inputargs(graph):
    # for simplicity, the logic in GraphState produces graphs that can
    # pass constants from one block to the next explicitly, via a
    # link.args -> block.inputargs.  Remove them now.
    for link in graph.iterlinks():
        i = 0
        for v in link.target.inputargs:
            if isinstance(v, Constant):
                del link.args[i]
            else:
                i += 1
    for block in graph.iterblocks():
        i = 0
        for v in block.inputargs[:]:
            if isinstance(v, Constant):
                del block.inputargs[i]
            else:
                i += 1
