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

    def __init__(self, origblock, args_a):
        assert len(args_a) == len(origblock.inputargs)
        self.args_a = args_a
        self.origblock = origblock
        self.copyblock = None
        self.pendinglinks = []

    def patchlink(self, copylink):
        if self.copyblock is None:
            print 'PENDING', self, id(copylink)
            self.pendinglinks.append(copylink)
        else:
            # XXX nice interface required!
            print 'LINKING', self, id(copylink), self.copyblock
            copylink.settarget(self.copyblock)

    def resolveblock(self, newblock):
        self.copyblock = newblock
        for copylink in self.pendinglinks:
            self.patchlink(copylink)
        del self.pendinglinks[:]

    def match(self, args_a):
        # simple for now
        for a1, a2 in zip(self.args_a, args_a):
            if not a1.match(a2):
                return False
        else:
            return True

# ____________________________________________________________

class GotReturnValue(Exception):
    def __init__(self, returnstate):
        self.returnstate = returnstate


class LLAbstractInterp(object):

    def __init__(self):
        pass

    def eval(self, origgraph, hints):
        # for now, 'hints' means "I'm absolutely sure that the
        # given variables will have the given ll value"
        self.allpendingstates = []
        self.hints = hints
        self.blocks = {}   # {origblock: list-of-LLStates}
        args_a = [LLRuntimeValue(orig_v=v) for v in origgraph.getargs()]
        newstartlink = self.schedule(args_a, origgraph.startblock)

        return_a = LLRuntimeValue(orig_v=origgraph.getreturnvar())
        returnstate = LLState(origgraph.returnblock, [return_a])
        self.allpendingstates.append(returnstate)
        self.blocks[origgraph.returnblock] = [returnstate]
        self.complete(returnstate)

        copygraph = FunctionGraph(origgraph.name, newstartlink.target)
        # XXX messy -- what about len(returnlink.args) == 0 ??
        copygraph.getreturnvar().concretetype = (
            origgraph.getreturnvar().concretetype)
        returnstate.resolveblock(copygraph.returnblock)
        checkgraph(copygraph)   # sanity-check
        return copygraph

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

    def schedule(self, args_a, origblock):
        print "SCHEDULE", args_a, origblock
        # args_a: [a_value for v in origblock.inputargs]
        args_a = self.applyhint(args_a, origblock)
        args_v = [a.getvarorconst() for a in args_a
                  if not isinstance(a, LLConcreteValue)]
        newlink = Link(args_v, None)
        # try to match this new state with an existing one
        pendingstates = self.blocks.setdefault(origblock, [])
        for state in pendingstates:
            if state.match(args_a):
                # already matched
                break
        else:
            # schedule this new state
            state = LLState(origblock, args_a)
            pendingstates.append(state)
            self.allpendingstates.append(state)
        state.patchlink(newlink)
        return newlink

    def complete(self, returnstate):
        while self.allpendingstates:
            state = self.allpendingstates.pop()
            print 'CONSIDERING', state
            try:
                self.flowin(state)
            except GotReturnValue, e:
                assert e.returnstate is returnstate

    def flowin(self, state):
        # flow in the block
        assert state.copyblock is None
        origblock = state.origblock
        if origblock.operations == ():
            if len(origblock.inputargs) == 1:
                # return block
                raise GotReturnValue(state)
            elif len(origblock.inputargs) == 2:
                # except block
                XXX
            else:
                raise Exception("uh?")
        self.residual_operations = []
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

    def op_int_gt(self, op, a1, a2):
        return self.residualize(op, [a1, a2], operator.gt)

    def op_same_as(self, op, a):
        return a
