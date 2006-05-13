from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rgenop
from pypy.tool.uid import Hashable

class AVariable(object):
    def __init__(self, T, genvar=None):
        self.concretetype = T
        self.genvar = genvar

    def getgenvar(self, builder):
        return self.genvar
    
class AConstant(Hashable):
    def __init__(self, value, T=None, genvar=None):
        Hashable.__init__(self, value)   
        self.concretetype = T or lltype.typeOf(value)
        self.genvar = genvar
        if T is lltype.Void and self.genvar is None:
            self.genvar = rgenop.placeholder(value)
        
    def getgenvar(self, builder):
        if self.genvar is None:
            self.genvar = builder.genconst(self.value)
        return self.genvar

class LLAbstractValue(object):
    """An abstract value, propagated through the blocks of the low-level
    flow graphs and recording what the value will concretely be at run-time.
    """
    # Instances of LLAbstractValue are either runtime values (where they
    # stand for a Variable or Constant in the generated flow graph) or
    # virtual values (where they stand for a pointer to a structure or
    # array that is not yet built in memory).  See __repr__() for how the
    # various combinations of 'runtimevar' and 'content' encode the various
    # states.

    concrete = False   # concrete constants propagate eagerly

    def __init__(self, runtimevar=None, content=None):
        self.runtimevar = runtimevar    # None or a AVariable or a AConstant
        self.content    = content       # None or an LLAbstractContainer
        self.origin     = []  # list of frozen values: the sources that did or
                              # could allow 'self' to be computed as a constant
        
    def __repr__(self):
        if self.runtimevar is None:
            if self.content is None:
                return '<dummy>'
            else:
                return '<virtual %s>' % (self.content,)
        else:
            # runtime value -- display more precisely if it's a
            # Variable or a Constant
            if isinstance(self.runtimevar, AVariable):
                kind = 'runtime'
            elif self.concrete:
                kind = 'concrete'
            else:
                kind = 'constant'
            return '<%s %s>' % (kind, self.runtimevar)

    def freeze(self, memo):
        # turn a run-time value into a frozen value
        if self.runtimevar is not None:
            if self.concrete:
                return LLFrozenConcreteValue(self)
            else:
                # don't use 'memo' here: for now, shared LLAbstractValues
                # need to become distinct LLFrozenRuntimeValues.
                return LLFrozenRuntimeValue(self)
        elif self.content is not None:
            # virtual container: preserve sharing
            if self in memo.seen:
                return memo.seen[self]    # already seen
            else:
                result = LLFrozenVirtualValue()
                memo.seen[self] = result
                result.fz_content = self.content.freeze(memo)
                return result
        else:
            return frozen_dummy_value   # dummy

    def getconcretetype(self):
        if self.runtimevar is not None:
            return self.runtimevar.concretetype
        elif self.content is not None:
            return lltype.Ptr(self.content.T)
        else:
            raise ValueError("ll_dummy_value.getconcretetype()")

    def forcevarorconst(self, builder):
        if self.runtimevar is None:
            if self.content is None:
                raise ValueError("ll_dummy_value.forcevarorconst()")
            genvar = self.content.build_runtime_container(builder)
            # sanity check violating encapsulation
            var = rgenop.reveal(genvar)
            assert self.content.T == var.concretetype.TO
            self.runtimevar = AVariable(lltype.Ptr(self.content.T), genvar=genvar)
            self.content = None
        return self.runtimevar

    def forcegenvarorconst(self, builder):
        return self.forcevarorconst(builder).getgenvar(builder)
    
    def maybe_get_constant(self):
        if isinstance(self.runtimevar, AConstant):
            return self.runtimevar
        else:
            return None

    def flatten(self, memo):
        """Recursively flatten the LLAbstractValue into a list of run-time
        LLAbstractValues.
        """
        if self.runtimevar is not None:
            if not self.concrete:   # skip concrete values, they don't need
                                    # to be present in the residual graph at all
                memo.result.append(self)
        elif self.content is not None:
            if self not in memo.seen:
                memo.seen[self] = True
                self.content.flatten(memo)
        else:
            pass    # dummy

# _____________________________________________________________


class LLFrozenValue(object):
    """An abstract value frozen in a saved state.
    """
    # When the end of a block is reached, the LLAbstractValues are
    # frozen by creating LLFrozenValues of the same shape.  In the
    # frozen values, the Variable is forgotten, because it was only
    # relevant in the finished block.


class LLFrozenDummyValue(LLFrozenValue):

    def flatten(self, memo):
        pass

    def unfreeze(self, memo, block):
        return ll_dummy_value

    def match(self, a_value, memo):
        return True    # a dummy matches anything


class LLFrozenConcreteValue(LLFrozenValue):

    def __init__(self, a_source):
        self.a_source = a_source

    def flatten(self, memo):
        """Recursively flatten the frozen value into a list of frozen values.
        """
        pass

    def unfreeze(self, memo, block):
        """Create an un-frozen copy of a frozen value recursively,
        creating fresh Variables.
        """
        return self.a_source    # we can keep the same LLAbstractValue around

    def match(self, a_value, memo):
        """Check if a frozen state is a suitable match for a live state
        reaching the same point.  This checks if freezing the live 'a_value'
        would basically result in the same state as 'self'.
        """
        return (a_value.concrete and
                a_value.runtimevar == self.a_source.runtimevar)


class LLFrozenRuntimeValue(LLFrozenValue):

    fixed = False      # Describes what this frozen value will become in
                       # the next block.  Set to True by hint() to force a
                       # Constant to stay a Constant.

    def __init__(self, a_value):
        # get the necessary information from the a_value
        self.concretetype = a_value.getconcretetype()
        self.origin = a_value.origin

    def flatten(self, memo):
        """Recursively flatten the frozen value into a list of frozen values.
        """
        memo.result.append(self)

    def unfreeze(self, memo, block):
        """Create an un-frozen copy of a frozen value recursively,
        creating fresh Variables.
        """
        # no need to worry about sharing here: LLFrozenRuntimeValues are
        # never shared
        propagateconst = memo.propagateconsts.next()
        if isinstance(propagateconst, AConstant):
            c = propagateconst        # allowed to propagate as a Constant
            assert c.concretetype == self.concretetype
            result = LLAbstractValue(c)
        else:
            gen_v = rgenop.geninputarg(block, rgenop.constTYPE(self.concretetype))
            result = LLAbstractValue(AVariable(self.concretetype, genvar=gen_v))
        result.origin.append(self)
        return result

    def match(self, a_value, memo):
        """Check if a frozen state is a suitable match for a live state
        reaching the same point.  This checks if freezing the live 'a_value'
        would basically result in the same state as 'self'.
        """
        # any two non-concrete run-time values match
        memo.dependencies.append((self, a_value))
        return a_value.runtimevar is not None and not a_value.concrete


class LLFrozenVirtualValue(LLFrozenValue):
    # fz_content must be initialized to a frozen LLAbstractContainer

    def flatten(self, memo):
        """Recursively flatten the frozen value into a list of frozen values.
        """
        if self not in memo.seen:
            memo.seen[self] = True
            self.fz_content.flatten(memo)

    def unfreeze(self, memo, block):
        """Create an un-frozen copy of a frozen value recursively,
        creating fresh Variables.
        """
        # virtual container: preserve sharing
        if self in memo.seen:
            return memo.seen[self]    # already seen
        else:
            a = LLAbstractValue()
            memo.seen[self] = a
            a.content = self.fz_content.unfreeze(memo, block)
            return a

    def match(self, a_value, memo):
        """Check if a frozen state is a suitable match for a live state
        reaching the same point.  This checks if freezing the live 'a_value'
        would basically result in the same state as 'self'.
        """
        # check virtual values recursively
        return (a_value.content is not None and
                self.fz_content.match(a_value.content, memo))

# ____________________________________________________________

class FlattenMemo:
    def __init__(self):
        self.seen = {}
        self.result = []

class MatchMemo:
    def __init__(self):
        self.dependencies = []
        self.self_alias = {}
        self.live_alias = {}

class FreezeMemo:
    def __init__(self):
        self.seen = {}

class UnfreezeMemo:
    def __init__(self, propagateconsts):
        self.propagateconsts = iter(propagateconsts)
        self.seen            = {}

# ____________________________________________________________

def const(value, T=None):
    c = Constant(value)
    c.concretetype = T or lltype.typeOf(value)
    return c

ll_no_return_value = LLAbstractValue(AConstant(None, lltype.Void))
ll_dummy_value = LLAbstractValue()
frozen_dummy_value = LLFrozenDummyValue()
