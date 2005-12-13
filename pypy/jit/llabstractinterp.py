import operator
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import Block, Link, FunctionGraph
from pypy.objspace.flow.model import checkgraph, c_last_exception
from pypy.rpython.lltypesystem import lltype
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks


def const(value, T=None):
    c = Constant(value)
    c.concretetype = T or lltype.typeOf(value)
    return c

def newvar(T):
    v = Variable()
    v.concretetype = T
    return v


class LLAbstractValue(object):
    pass

class LLConcreteValue(LLAbstractValue):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '<concrete %r>' % (self.value,)

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

    def forcevarorconst(self, builder):
        return const(self.value)

    def getruntimevars(self, memo):
        return []

    def maybe_get_constant(self):
        return const(self.value)

    def with_fresh_variables(self, memo):
        return self

    def match(self, other, memo):
        return isinstance(other, LLConcreteValue) and self.value == other.value


class LLRuntimeValue(LLAbstractValue):

    def __init__(self, orig_v):
        if isinstance(orig_v, Variable):
            self.copy_v = Variable(orig_v)
            self.copy_v.concretetype = orig_v.concretetype
        elif isinstance(orig_v, Constant):
            # we can share the Constant()
            self.copy_v = orig_v
        elif isinstance(orig_v, lltype.LowLevelType):
            # hackish interface :-(  we accept a type too
            self.copy_v = newvar(orig_v)
        else:
            raise TypeError(repr(orig_v))

    def __repr__(self):
        return '<runtime %r>' % (self.copy_v,)

    def getconcretetype(self):
        return self.copy_v.concretetype

    def forcevarorconst(self, builder):
        return self.copy_v

    def getruntimevars(self, memo):
        if (isinstance(self.copy_v, Variable) or
            self not in memo.propagate_as_constants):
            return [self.copy_v]
        else:
            return []   # we propagate this constant as a constant

    def maybe_get_constant(self):
        if isinstance(self.copy_v, Constant):
            return self.copy_v
        else:
            return None

    def with_fresh_variables(self, memo):
        # don't use memo.seen here: shared variables must become distinct
        if (isinstance(self.copy_v, Variable) or
            self not in memo.propagate_as_constants):
            return LLRuntimeValue(self.getconcretetype())
        else:
            return self   # we are allowed to propagate this constant

    def match(self, other, memo):
        if not isinstance(other, LLRuntimeValue):
            return False
        if isinstance(self.copy_v, Variable):
            return True
        if self.copy_v == other.copy_v:
            memo.propagate_as_constants[other] = True   # exact match
        else:
            memo.exact_match = False
        return True

ll_no_return_value = LLRuntimeValue(const(None, lltype.Void))


class LLVirtualContainer(LLAbstractValue):

    parent = None
    parentindex = None

    def __init__(self, T, a_length=None):
        assert (a_length is not None) == T._is_varsize()
        self.T = T
        self.a_length = a_length
        self.names = self.getnames()
        self.fields = {}

    def getconcretetype(self):
        return lltype.Ptr(self.T)

    def maybe_get_constant(self):
        return None

    def setparent(self, parent, parentindex):
        self.parent = parent
        self.parentindex = parentindex

    def topmostparent(self):
        obj = self
        while obj.parent is not None:
            obj = obj.parent
        return obj

    def getfield(self, name):
        try:
            return self.fields[name]
        except KeyError:
            T = self.fieldtype(name)
            if isinstance(T, lltype.ContainerType):
                # reading a substructure
                if T._is_varsize():
                    a_length = self.a_length
                else:
                    a_length = None
                a_sub = virtualcontainer(T, a_length)
                a_sub.setparent(self, name)
                self.fields[name] = a_sub
                return a_sub
            else:
                # no value ever set, return a default
                return LLRuntimeValue(const(T._defl()))

    def setfield(self, name, a_value):
        self.fields[name] = a_value

    def with_fresh_variables(self, memo):
        if self in memo.seen:
            return memo.seen[self]    # already seen
        else:
            result = virtualcontainer(self.T, self.a_length)
            memo.seen[self] = result
            if self.parent is not None:
                # build the parent first -- note that
                # parent.with_fresh_variables() will pick up 'result' again,
                # because it is already in the memo
                result.setparent(self.parent.with_fresh_variables(memo),
                                 self.parentindex)

            # cannot keep lazy fields around: the copy is expected to have
            # only variables, not constants
            for name in self.names:
                a = self.getfield(name).with_fresh_variables(memo)
                result.fields[name] = a
            return result

    def forcevarorconst(self, builder):
        v_result = newvar(lltype.Ptr(self.T))
        if self.parent is not None:
            v_parent = self.parent.forcevarorconst(builder)
            op = SpaceOperation('getsubstruct', [v_parent,
                                                 const(self.parentindex,
                                                       lltype.Void)],
                                v_result)
            print 'force:', op
            builder.residual_operations.append(op)
        else:
            if self.T._is_varsize():
                op = SpaceOperation('malloc_varsize', [
                                        const(self.T, lltype.Void),
                                        self.a_length.forcevarorconst(builder)],
                                    v_result)
            else:
                op = SpaceOperation('malloc', [const(self.T, lltype.Void)],
                                    v_result)
            print 'force:', op
            builder.residual_operations.append(op)
            self.buildcontent(builder, v_result)
        self.__class__ = LLRuntimeValue
        self.__dict__ = {'copy_v': v_result}
        return v_result

    def buildcontent(self, builder, v_target):
        # initialize all fields
        for name in self.names:
            if name in self.fields:
                a_value = self.fields[name]
                T = self.fieldtype(name)
                if isinstance(T, lltype.ContainerType):
                    # initialize the substructure/subarray
                    v_subptr = newvar(lltype.Ptr(T))
                    op = SpaceOperation('getsubstruct',
                                        [v_target, const(name, lltype.Void)],
                                        v_subptr)
                    print 'force:', op
                    builder.residual_operations.append(op)
                    assert isinstance(a_value, LLVirtualStruct)
                    a_value.buildcontent(builder, v_subptr)
                else:
                    v_value = a_value.forcevarorconst(builder)
                    op = self.setop(v_target, name, v_value)
                    print 'force:', op
                    builder.residual_operations.append(op)

    def getruntimevars(self, memo):
        result = []
        if self not in memo.seen:
            memo.seen[self] = True
            if self.parent is not None:
                result.extend(self.parent.getruntimevars(memo))
            for name in self.names:
                result.extend(self.getfield(name).getruntimevars(memo))
        return result

    def match(self, other, memo):
        if self.__class__ is not other.__class__:
            return False

        if self in memo.self_alias:
            return other is memo.self_alias[self]
        if other in memo.other_alias:
            return self is memo.other_alias[other]
        memo.self_alias[self] = other
        memo.other_alias[other] = self

        assert self.T == other.T
        if self.a_length is not None:
            if not self.a_length.match(other.a_length, memo):
                return False
        for name in self.names:
            a1 = self.getfield(name)
            a2 = other.getfield(name)
            if not a1.match(a2, memo):
                return False
        else:
            return True


class LLVirtualStruct(LLVirtualContainer):
    """Stands for a pointer to a malloc'ed structure; the structure is not
    malloc'ed so far, but we record which fields have which value.
    """
    def getnames(self):
        return self.T._names

    def fieldtype(self, name):
        return getattr(self.T, name)

    def setop(self, v_target, name, v_value):
        return SpaceOperation('setfield', [v_target,
                                           const(name, lltype.Void),
                                           v_value],
                              newvar(lltype.Void))

class LLVirtualArray(LLVirtualContainer):
    """Stands for a pointer to a malloc'ed array; the array is not
    malloc'ed so far, but we record which fields have which value -- here
    a field is an item, indexed by an integer instead of a string field name.
    """
    def getnames(self):
        c = self.a_length.maybe_get_constant()
        assert c is not None
        return range(c.value)

    def fieldtype(self, index):
        return self.T.OF

    def setop(self, v_target, name, v_value):
        return SpaceOperation('setarrayitem', [v_target,
                                               const(name, lltype.Signed),
                                               v_value],
                              newvar(lltype.Void))

def virtualcontainer(T, a_length=None):
    if isinstance(T, lltype.Struct):
        cls = LLVirtualStruct
    elif isinstance(T, lltype.Array):
        cls = LLVirtualArray
    else:
        raise TypeError("unsupported container type %r" % (T,))
    return cls(T, a_length)

# ____________________________________________________________

class LLState(LLAbstractValue):
    """Entry state of a block, as a combination of LLAbstractValues
    for its input arguments.  Abstract base class."""
    generalized_by = None

    def __init__(self, a_back, args_a, origblock):
        self.a_back = a_back
        self.args_a = args_a
        self.origblock = origblock
        self.copyblock = None
        assert len(args_a) == len(self.getlivevars())

    def key(self):
        # two LLStates should return different keys if they cannot match().
        result = self.localkey()
        if self.a_back is not None:
            result += self.a_back.key()
        return result

    def getruntimevars(self, memo):
        if self.a_back is None:
            result = []
        else:
            result = self.a_back.getruntimevars(memo)
        for a in self.args_a:
            result.extend(a.getruntimevars(memo))
        return result

    def maybe_get_constant(self):
        return None

    def with_fresh_variables(self, memo):
        if self.a_back is not None:
            new_a_back = self.a_back.with_fresh_variables(memo)
        else:
            new_a_back = None
        new_args_a = []
        for v, a in zip(self.getlivevars(), self.args_a):
            a = a.with_fresh_variables(memo)
            # try to preserve the name
            if isinstance(a, LLRuntimeValue) and isinstance(a.copy_v, Variable):
                a.copy_v.rename(v)
            new_args_a.append(a)
        return self.__class__(new_a_back, new_args_a, *self.localkey())

    def match(self, other, memo):
        assert self.__class__ is other.__class__
        if self.localkey() != other.localkey():
            return False
        if self.a_back is None:
            if other.a_back is not None:
                return False
        else:
            if other.a_back is None:
                return False
            if not self.a_back.match(other.a_back, memo):
                return False
        for a1, a2 in zip(self.args_a, other.args_a):
            if not a1.match(a2, memo):
                return False
        else:
            return True

    def resolveblock(self, newblock):
        #print "RESOLVING BLOCK", newblock
        if self.copyblock is not None:
            # uncommon case: must patch the existing Block
            assert len(self.copyblock.inputargs) == len(newblock.inputargs)
            self.copyblock.inputargs  = newblock.inputargs
            self.copyblock.operations = newblock.operations
            self.copyblock.exitswitch = newblock.exitswitch
            self.copyblock.recloseblock(*newblock.exits)
        else:
            self.copyblock = newblock

    def getbindings(self):
        return dict(zip(self.getlivevars(), self.args_a))


class LLBlockState(LLState):
    """Entry state of a block, as a combination of LLAbstractValues
    for its input arguments."""
    propagate_as_constants = {}

    def localkey(self):
        return (self.origblock,)

    def getlivevars(self):
        return self.origblock.inputargs


class LLSuspendedBlockState(LLBlockState):
    """Block state in the middle of the execution of one instruction
    (typically a direct_call() that is causing inlining)."""

    def __init__(self, a_back, args_a, origblock, origposition):
        self.origposition = origposition
        super(LLSuspendedBlockState, self).__init__(a_back, args_a, origblock)

    def localkey(self):
        return (self.origblock, self.origposition)

    def getlivevars(self):
        return live_variables(self.origblock, self.origposition)


# ____________________________________________________________

class Policy(object):
    def __init__(self, inlining=False, const_propagate=False):
        self.inlining = inlining
        self.const_propagate = const_propagate

best_policy = Policy(inlining=True, const_propagate=True)


class LLAbstractInterp(object):

    def __init__(self, policy=best_policy):
        self.graphs = []
        self.graphstates = {}     # {origgraph: {BlockState: GraphState}}
        self.pendingstates = {}   # {Link-or-GraphState: next-BlockState}
        self.blocks = {}          # {BlockState.key(): list-of-LLBlockStates}
        self.policy = policy

    def itercopygraphs(self):
        return self.graphs

    def eval(self, origgraph, arghints):
        # 'arghints' maps argument index to a given ll value
        args_a = []
        for i, v in enumerate(origgraph.getargs()):
            if i in arghints:
                a = LLConcreteValue(arghints[i])
            else:
                a = LLRuntimeValue(orig_v=v)
            args_a.append(a)
        graphstate = self.schedule_graph(args_a, origgraph)
        graphstate.complete()
        return graphstate.copygraph

    def schedule_graph(self, args_a, origgraph):
        inputstate = LLBlockState(None, args_a, origgraph.startblock)
        state = self.schedule_getstate(inputstate)
        try:
            graphstate = self.graphstates[origgraph][state]
        except KeyError:
            d = self.graphstates.setdefault(origgraph, {})
            graphstate = GraphState(self, origgraph, inputstate, n=len(d))
            d[state] = graphstate
            self.pendingstates[graphstate] = state
        #print "SCHEDULE_GRAPH", graphstate
        return graphstate

    def schedule(self, inputstate):
        #print "SCHEDULE", args_a, origblock
        state = self.schedule_getstate(inputstate)
        memo = VarMemo(state.propagate_as_constants)
        args_v = inputstate.getruntimevars(memo)
        newlink = Link(args_v, None)
        self.pendingstates[newlink] = state
        return newlink

    def schedule_getstate(self, inputstate):
        # NOTA BENE: copyblocks can get shared between different copygraphs!
        pendingstates = self.blocks.setdefault(inputstate.key(), [])
        # try to match the input state with an existing one
        for i, state in enumerate(pendingstates):
            memo = MatchMemo()
            if state.match(inputstate, memo):
                # already matched
                if memo.exact_match:
                    return state    # exact match
                if not self.policy.const_propagate:
                    return state    # all constants will be generalized anyway
                # partial match: in the old state, some constants need to
                # be turned into variables.
                inputstate.propagate_as_constants = memo.propagate_as_constants
                # The generalized state replaces the existing one.
                pendingstates[i] = inputstate
                state.generalized_by = inputstate
                return inputstate
        else:
            # cache and return this new state
            if self.policy.const_propagate:
                inputstate.propagate_as_constants = ALL
            pendingstates.append(inputstate)
            return inputstate


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
        self.a_return = None
        self.state = "before"

    def settarget(self, block):
        block.isstartblock = True
        self.copygraph.startblock = block

    def complete(self):
        assert self.state != "during"
        if self.state == "after":
            return
        self.state = "during"
        graph = self.copygraph
        interp = self.interp
        pending = [self]
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
                if link.target is None or link.target.operations != ():
                    if link not in seen:
                        seen[link] = True
                        pending.append(link)
                else:
                    # link.target is a return or except block; make sure
                    # that it is really the one from 'graph' -- by patching
                    # 'graph' if necessary.
                    if len(link.target.inputargs) == 1:
                        self.a_return = state.args_a[0]
                        graph.returnblock = link.target
                    elif len(link.target.inputargs) == 2:
                        graph.exceptblock = link.target
                    else:
                        raise Exception("uh?")

        if interp.policy.const_propagate:
            self.compactify(seen)

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

    def compactify(self, links):
        # remove the parts of the graph that use constants that were later
        # generalized
        interp = self.interp
        for link in links:
            oldstate = interp.pendingstates[link]
            if oldstate.generalized_by is not None:
                newstate = oldstate.generalized_by
                while newstate.generalized_by:
                    newstate = newstate.generalized_by
                # Patch oldstate.block to point to the new state,
                # as in the flow object space
                builder = BlockBuilder(self, oldstate)
                memo = VarMemo(newstate.propagate_as_constants)
                args_v = builder.runningstate.getruntimevars(memo)
                oldlink = Link(args_v, newstate.copyblock)
                oldblock = builder.buildblock(None, [oldlink])
                oldstate.resolveblock(oldblock)

    def flowin(self, state):
        # flow in the block
        assert isinstance(state, LLBlockState)
        origblock = state.origblock
        origposition = 0
        builder = BlockBuilder(self.interp, state)
        newexitswitch = None
        print
        try:
            if origblock.operations == ():
                if state.a_back is None:
                    # copies of return and except blocks are *normal* blocks
                    # currently; they are linked to the official return or
                    # except block of the copygraph.  If needed,
                    # LLConcreteValues are turned into Constants.
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
                        builder.runningstate = builder.runningstate.a_back
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
                nextinputstate = LLBlockState(builder.runningstate.a_back,
                                              args_a, origlink.target)
                newlink = self.interp.schedule(nextinputstate)
                if newexitswitch is not None:
                    newlink.exitcase = origlink.exitcase
                    newlink.llexitcase = origlink.llexitcase
                newlinks.append(newlink)

        newblock = builder.buildblock(newexitswitch, newlinks)
        state.resolveblock(newblock)


class BlockBuilder(object):

    def __init__(self, interp, initialstate):
        self.interp = interp
        memo = VarMemo(initialstate.propagate_as_constants)
        self.runningstate = initialstate.with_fresh_variables(memo)
        memo = VarMemo(initialstate.propagate_as_constants)
        self.newinputargs = self.runningstate.getruntimevars(memo)
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
            return LLRuntimeValue(orig_v=v)
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
            any_concrete = any_concrete or isinstance(a, LLConcreteValue)
        # can constant-fold
        print 'fold:', constant_op, concretevalues
        concreteresult = constant_op(*concretevalues)
        if any_concrete:
            return LLConcreteValue(concreteresult)
        else:
            return LLRuntimeValue(const(concreteresult))

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
        a_result = LLRuntimeValue(op.result)
        self.residual(op.opname, args_a, a_result)
        return a_result

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

    def op_cast_char_to_int(self, op, a):
        return self.residualize(op, [a], ord)

    def op_same_as(self, op, a):
        return a

    def op_direct_call(self, op, *args_a):
        a_result = self.handle_call(op, *args_a)
        if a_result is None:
            a_result = self.residualize(op, args_a)
        return a_result

    def handle_call(self, op, a_func, *args_a):
        v_func = a_func.maybe_get_constant()
        if v_func is None:
            return None
        fnobj = v_func.value._obj
        if not hasattr(fnobj, 'graph'):
            return None
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
        parentstate = LLSuspendedBlockState(self.runningstate.a_back, alive_a,
                                            origblock, origposition)
        nextstate = LLBlockState(parentstate, args_a, origgraph.startblock)
        raise InsertNextLink(self.interp.schedule(nextstate))

    def handle_call_residual(self, op, origgraph, *args_a):
        # residual call: for now we need to force all arguments
        any_concrete = False
        for a in args_a:
            a.forcevarorconst(self)
            any_concrete = any_concrete or isinstance(a,LLConcreteValue)
        if not any_concrete:
            return None

        a_result = LLRuntimeValue(op.result)
        graphstate = self.interp.schedule_graph(args_a, origgraph)
        #print 'SCHEDULE_GRAPH', args_a, '==>', graphstate.copygraph.name
        if graphstate.state != "during":
            print 'ENTERING', graphstate.copygraph.name, args_a
            graphstate.complete()
            if (graphstate.a_return is not None and
                graphstate.a_return.maybe_get_constant() is not None):
                a_result = graphstate.a_return
            print 'LEAVING', graphstate.copygraph.name, graphstate.a_return

        ARGS = []
        new_args_a = []
        for a in args_a:
            if not isinstance(a, LLConcreteValue):
                ARGS.append(a.getconcretetype())
                new_args_a.append(a)
        args_a = new_args_a
        TYPE = lltype.FuncType(ARGS, a_result.getconcretetype())
        fptr = lltype.functionptr(
           TYPE, graphstate.copygraph.name, graph=graphstate.copygraph)
        a_func = LLRuntimeValue(const(fptr))
        self.residual("direct_call", [a_func] + args_a, a_result) 
        return a_result

    def op_getfield(self, op, a_ptr, a_attrname):
        if isinstance(a_ptr, LLVirtualStruct):
            c_attrname = a_attrname.maybe_get_constant()
            assert c_attrname is not None
            return a_ptr.getfield(c_attrname.value)
        constant_op = None
        T = a_ptr.getconcretetype().TO
        if T._hints.get('immutable', False):
            constant_op = getattr
        return self.residualize(op, [a_ptr, a_attrname], constant_op)

    def op_getsubstruct(self, op, a_ptr, a_attrname):
        if isinstance(a_ptr, LLVirtualContainer):
            c_attrname = a_attrname.maybe_get_constant()
            assert c_attrname is not None
            # this should return new LLVirtualContainer as well
            return a_ptr.getfield(c_attrname.value)
        return self.residualize(op, [a_ptr, a_attrname], getattr)

    def op_getarraysize(self, op, a_ptr):
        if isinstance(a_ptr, LLVirtualArray):
            return a_ptr.a_length
        return self.residualize(op, [a_ptr], len)

    def op_getarrayitem(self, op, a_ptr, a_index):
        if isinstance(a_ptr, LLVirtualArray):
            c_index = a_index.maybe_get_constant()
            if c_index is not None:
                return a_ptr.getfield(c_index.value)
        constant_op = None
        T = a_ptr.getconcretetype().TO
        if T._hints.get('immutable', False):
            constant_op = operator.getitem
        return self.residualize(op, [a_ptr, a_index], constant_op)

    def op_malloc(self, op, a_T):
        c_T = a_T.maybe_get_constant()
        assert c_T is not None
        return LLVirtualStruct(c_T.value)

    def op_malloc_varsize(self, op, a_T, a_size):
        if a_size.maybe_get_constant() is not None:
            c_T = a_T.maybe_get_constant()
            assert c_T is not None
            return virtualcontainer(c_T.value, a_length=a_size)
        return self.residualize(op, [a_T, a_size])

    def op_setfield(self, op, a_ptr, a_attrname, a_value):
        if isinstance(a_ptr, LLVirtualStruct):
            c_attrname = a_attrname.maybe_get_constant()
            assert c_attrname is not None
            a_ptr.setfield(c_attrname.value, a_value)
            return ll_no_return_value
        return self.residualize(op, [a_ptr, a_attrname, a_value])

    def op_setarrayitem(self, op, a_ptr, a_index, a_value):
        if isinstance(a_ptr, LLVirtualArray):
            c_index = a_index.maybe_get_constant()
            if c_index is not None:
                a_ptr.setfield(c_index.value, a_value)
                return ll_no_return_value
        return self.residualize(op, [a_ptr, a_index, a_value])

    def op_cast_pointer(self, op, a_ptr):
        if isinstance(a_ptr, LLVirtualStruct):
            down_or_up = lltype.castable(op.result.concretetype,
                                         a_ptr.getconcretetype())
            a = a_ptr
            if down_or_up >= 0:
                for n in range(down_or_up):
                    a = a.getfield(a.T._names[0])
            else:
                for n in range(-down_or_up):
                    a = a.parent
            return a
        def constant_op(ptr):
            return lltype.cast_pointer(op.result.concretetype, ptr)
        return self.residualize(op, [a_ptr], constant_op)

    def op_keepalive(self, op, a_ptr):
        if isinstance(a_ptr, LLVirtualStruct):
            for v in a_ptr.getruntimevars(VarMemo()):
                if isinstance(v, Variable) and not v.concretetype._is_atomic():
                    op = SpaceOperation('keepalive', [v], newvar(lltype.Void))
                    print 'virtual:', op
                    self.residual_operations.append(op)
            return ll_no_return_value
        return self.residualize(op, [a_ptr])


class InsertNextLink(Exception):
    def __init__(self, link):
        self.link = link

class MatchMemo(object):
    def __init__(self):
        self.exact_match = True
        self.propagate_as_constants = {}
        self.self_alias = {}
        self.other_alias = {}

class VarMemo(object):
    def __init__(self, propagate_as_constants={}):
        self.seen = {}
        self.propagate_as_constants = propagate_as_constants

class ALL(object):
    def __contains__(self, other):
        return True
ALL = ALL()


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
