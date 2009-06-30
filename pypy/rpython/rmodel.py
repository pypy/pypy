from pypy.tool.pairtype import pairtype, extendabletype, pair
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem.lltype import \
     Void, Bool, Float, Signed, Char, UniChar, \
     typeOf, LowLevelType, Ptr, PyObject, isCompatibleType
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.error import TyperError, MissingRTypeOperation 

# initialization states for Repr instances 

class setupstate: 
    NOTINITIALIZED = 0 
    INPROGRESS = 1
    BROKEN = 2 
    FINISHED = 3
    DELAYED = 4

class Repr:
    """ An instance of Repr is associated with each instance of SomeXxx.
    It defines the chosen representation for the SomeXxx.  The Repr subclasses
    generally follows the SomeXxx subclass hierarchy, but there are numerous
    exceptions.  For example, the annotator uses SomeIter for any iterator, but
    we need different representations according to the type of container we are
    iterating over.
    """
    __metaclass__ = extendabletype
    _initialized = setupstate.NOTINITIALIZED 

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.lowleveltype)

    def compact_repr(self):
        return '%s %s' % (self.__class__.__name__.replace('Repr','R'), self.lowleveltype._short_name())

    def setup(self): 
        """ call _setup_repr() and keep track of the initializiation
            status to e.g. detect recursive _setup_repr invocations.
            the '_initialized' attr has four states: 
        """
        if self._initialized == setupstate.FINISHED: 
            return 
        elif self._initialized == setupstate.BROKEN: 
            raise BrokenReprTyperError(
                "cannot setup already failed Repr: %r" %(self,))
        elif self._initialized == setupstate.INPROGRESS: 
            raise AssertionError(
                "recursive invocation of Repr setup(): %r" %(self,))
        elif self._initialized == setupstate.DELAYED:
            raise AssertionError(
                "Repr setup() is delayed and cannot be called yet: %r" %(self,))
        assert self._initialized == setupstate.NOTINITIALIZED 
        self._initialized = setupstate.INPROGRESS 
        try: 
            self._setup_repr() 
        except TyperError, e: 
            self._initialized = setupstate.BROKEN 
            raise 
        else: 
            self._initialized = setupstate.FINISHED 

    def _setup_repr(self):
        "For recursive data structure, which must be initialized in two steps."

    def setup_final(self):
        """Same as setup(), called a bit later, for effects that are only
        needed after the typer finished (as opposed to needed for other parts
        of the typer itself)."""
        if self._initialized == setupstate.BROKEN: 
            raise BrokenReprTyperError("cannot perform setup_final_touch "
                             "on failed Repr: %r" %(self,))
        assert self._initialized == setupstate.FINISHED, (
                "setup_final() on repr with state %s: %r" %
                (self._initialized, self))
        self._setup_repr_final() 

    def _setup_repr_final(self): 
        pass

    def is_setup_delayed(self):
        return self._initialized == setupstate.DELAYED

    def set_setup_delayed(self, flag):
        assert self._initialized in (setupstate.NOTINITIALIZED,
                                     setupstate.DELAYED)
        if flag:
            self._initialized = setupstate.DELAYED
        else:
            self._initialized = setupstate.NOTINITIALIZED

    def set_setup_maybe_delayed(self):
        if self._initialized == setupstate.NOTINITIALIZED:
            self._initialized = setupstate.DELAYED
        return self._initialized == setupstate.DELAYED

    def __getattr__(self, name):
        # Assume that when an attribute is missing, it's because setup() needs
        # to be called
        if not (name[:2] == '__' == name[-2:]): 
            if self._initialized == setupstate.NOTINITIALIZED: 
                self.setup()
                try:
                    return self.__dict__[name]
                except KeyError:
                    pass
        raise AttributeError("%s instance has no attribute %s" % (
            self.__class__.__name__, name))

    def _freeze_(self):
        return True

    def convert_desc_or_const(self, desc_or_const):
        if isinstance(desc_or_const, description.Desc):
            return self.convert_desc(desc_or_const)
        elif isinstance(desc_or_const, Constant):
            return self.convert_const(desc_or_const.value)
        else:
            raise TyperError("convert_desc_or_const expects a Desc"
                             "or Constant: %r" % desc_or_const)
                            
    def convert_const(self, value):
        "Convert the given constant value to the low-level repr of 'self'."
        if self.lowleveltype is not Void:
            try:
                realtype = typeOf(value)
            except (AssertionError, AttributeError, TypeError):
                realtype = '???'
            if realtype != self.lowleveltype:
                raise TyperError("convert_const(self = %r, value = %r)" % (
                    self, value))
        return value

    def get_ll_eq_function(self):
        """Return an eq(x,y) function to use to compare two low-level
        values of this Repr.
        This can return None to mean that simply using '==' is fine.
        """
        raise TyperError, 'no equality function for %r' % self

    def get_ll_hash_function(self):
        """Return a hash(x) function for low-level values of this Repr.
        """
        raise TyperError, 'no hashing function for %r' % self

    def get_ll_fasthash_function(self):
        """Return a 'fast' hash(x) function for low-level values of this
        Repr.  The function can assume that 'x' is already stored as a
        key in a dict.  get_ll_fasthash_function() should return None if
        the hash should rather be cached in the dict entry.
        """
        return None

    def can_ll_be_null(self, s_value):
        """Check if the low-level repr can take the value 0/NULL.
        The annotation s_value is provided as a hint because it may
        contain more information than the Repr.
        """
        return True   # conservative

    def get_ll_dummyval_obj(self, rtyper, s_value):
        """A dummy value is a special low-level value, not otherwise
        used.  It should not be the NULL value even if it is special.
        This returns either None, or a hashable object that has a
        (possibly lazy) attribute 'll_dummy_value'.
        The annotation s_value is provided as a hint because it may
        contain more information than the Repr.
        """
        T = self.lowleveltype
        if (isinstance(T, lltype.Ptr) and
            isinstance(T.TO, (lltype.Struct,
                              lltype.Array,
                              lltype.ForwardReference))):
            assert T.TO._gckind != 'cpy'
            return DummyValueBuilder(rtyper, T.TO)
        else:
            return None

    def rtype_bltn_list(self, hop):
        raise TyperError, 'no list() support for %r' % self

    def rtype_unichr(self, hop):
        raise TyperError, 'no unichr() support for %r' % self

    # default implementation of some operations

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            s_obj = hop.args_s[0]
            if s_obj.find_method(attr) is None:
                raise TyperError("no method %s on %r" % (attr, s_obj))
            else:
                # implement methods (of a known name) as just their 'self'
                return hop.inputarg(self, arg=0)
        else:
            raise TyperError("getattr() with a non-constant attribute name")

    def rtype_str(self, hop):
        [v_self] = hop.inputargs(self)
        return hop.gendirectcall(self.ll_str, v_self)

    def rtype_nonzero(self, hop):
        return self.rtype_is_true(hop)   # can call a subclass' rtype_is_true()

    def rtype_is_true(self, hop):
        try:
            vlen = self.rtype_len(hop)
        except MissingRTypeOperation:
            if not hop.s_result.is_constant():
                raise TyperError("rtype_is_true(%r) not implemented" % (self,))
            return hop.inputconst(Bool, hop.s_result.const)
        else:
            return hop.genop('int_is_true', [vlen], resulttype=Bool)

    def rtype_hash(self, hop):
        ll_hash = self.get_ll_hash_function()
        v, = hop.inputargs(self)
        return hop.gendirectcall(ll_hash, v)

    def rtype_iter(self, hop):
        r_iter = self.make_iterator_repr()
        return r_iter.newiter(hop)

    def make_iterator_repr(self, *variant):
        raise TyperError("%s is not iterable" % (self,))

    def rtype_hint(self, hop):
        return hop.inputarg(hop.r_result, arg=0)

    # hlinvoke helpers

    def get_r_implfunc(self):
        raise TyperError("%s has no corresponding implementation function representation" % (self,))

    def get_s_callable(self):
        raise TyperError("%s is not callable or cannot reconstruct a pbc annotation for itself" % (self,))

def ll_hash_void(v):
    return 0


class CanBeNull(object):
    """A mix-in base class for subclasses of Repr that represent None as
    'null' and true values as non-'null'.
    """
    def rtype_is_true(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(Bool, hop.s_result.const)
        else:
            return hop.rtyper.type_system.check_null(self, hop)


class IteratorRepr(Repr):
    """Base class of Reprs of any kind of iterator."""

    def rtype_iter(self, hop):    #   iter(iter(x))  <==>  iter(x)
        v_iter, = hop.inputargs(self)
        return v_iter

    def rtype_method_next(self, hop):
        return self.rtype_next(hop)


class __extend__(annmodel.SomeIterator):
    # NOTE: SomeIterator is for iterators over any container, not just list
    def rtyper_makerepr(self, rtyper):
        r_container = rtyper.getrepr(self.s_container)
        return r_container.make_iterator_repr(*self.variant)
    def rtyper_makekey_ex(self, rtyper):
        return self.__class__, rtyper.makekey(self.s_container), self.variant

class __extend__(annmodel.SomeImpossibleValue):
    def rtyper_makerepr(self, rtyper):
        return impossible_repr
    def rtyper_makekey(self):
        return self.__class__,

# ____ generic binary operations _____________________________


class __extend__(pairtype(Repr, Repr)):
    
    def rtype_is_((robj1, robj2), hop):
        if hop.s_result.is_constant():
            return inputconst(Bool, hop.s_result.const)
        return hop.rtyper.type_system.generic_is(robj1, robj2, hop)

    # default implementation for checked getitems
    
    def rtype_getitem_idx_key((r_c1, r_o1), hop):
        return pair(r_c1, r_o1).rtype_getitem(hop)

    rtype_getitem_idx = rtype_getitem_idx_key
    rtype_getitem_key = rtype_getitem_idx_key

# ____________________________________________________________


def make_missing_op(rcls, opname):
    attr = 'rtype_' + opname
    if not hasattr(rcls, attr):
        def missing_rtype_operation(self, hop):
            raise MissingRTypeOperation("unimplemented operation: "
                                        "'%s' on %r" % (opname, self))
        setattr(rcls, attr, missing_rtype_operation)

for opname in annmodel.UNARY_OPERATIONS:
    make_missing_op(Repr, opname)

for opname in annmodel.BINARY_OPERATIONS:
    make_missing_op(pairtype(Repr, Repr), opname)

# not in BINARY_OPERATIONS
make_missing_op(pairtype(Repr, Repr), 'contains')

class __extend__(pairtype(Repr, Repr)):
    def convert_from_to((r_from, r_to), v, llops):
        return NotImplemented

# ____________________________________________________________
# Primitive Repr classes, in the same hierarchical order as
# the corresponding SomeObjects

class FloatRepr(Repr):
    lowleveltype = Float

class IntegerRepr(FloatRepr):
    def __init__(self, lowleveltype, opprefix):
        self.lowleveltype = lowleveltype
        self._opprefix = opprefix
        self.as_int = self

    def _get_opprefix(self):
        if self._opprefix is None:
            raise TyperError("arithmetic not supported on %r" %
                             self.lowleveltype)
        return self._opprefix

    opprefix =property(_get_opprefix)
    
class BoolRepr(IntegerRepr):
    lowleveltype = Bool
    # NB. no 'opprefix' here.  Use 'as_int' systematically.
    def __init__(self):
        from pypy.rpython.rint import signed_repr
        self.as_int = signed_repr

class VoidRepr(Repr):
    lowleveltype = Void
    def get_ll_eq_function(self): return None
    def get_ll_hash_function(self): return ll_hash_void
    get_ll_fasthash_function = get_ll_hash_function
    def ll_str(self, nothing): raise AssertionError("unreachable code")
impossible_repr = VoidRepr()

class SimplePointerRepr(Repr):
    "Convenience Repr for simple ll pointer types with no operation on them."

    def __init__(self, lowleveltype):
        self.lowleveltype = lowleveltype

    def convert_const(self, value):
        if value is not None:
            raise TyperError("%r only supports None as prebuilt constant, "
                             "got %r" % (self, value))
        return lltype.nullptr(self.lowleveltype.TO)

# ____________________________________________________________

def inputdesc(reqtype, desc):
    """Return a Constant for the given desc, of the requested type,
    which can only be a Repr.
    """
    assert isinstance(reqtype, Repr)
    value = reqtype.convert_desc(desc)
    lltype = reqtype.lowleveltype
    c = Constant(value)
    c.concretetype = lltype
    return c

def inputconst(reqtype, value):
    """Return a Constant with the given value, of the requested type,
    which can be a Repr instance or a low-level type.
    """
    if isinstance(reqtype, Repr):
        value = reqtype.convert_const(value)
        lltype = reqtype.lowleveltype
    elif isinstance(reqtype, LowLevelType):
        lltype = reqtype
    else:
        raise TypeError(repr(reqtype))
    # Void Constants can hold any value;
    # non-Void Constants must hold a correctly ll-typed value
    if lltype is not Void:
        try:
            realtype = typeOf(value)
        except (AssertionError, AttributeError):
            realtype = '???'
        if not isCompatibleType(realtype, lltype):
            raise TyperError("inputconst(reqtype = %s, value = %s):\n"
                             "expected a %r,\n"
                             "     got a %r" % (reqtype, value,
                                                lltype, realtype))
    c = Constant(value)
    c.concretetype = lltype
    return c

class BrokenReprTyperError(TyperError): 
    """ raised when trying to setup a Repr whose setup 
        has failed already. 
    """

def mangle(prefix, name):
    """Make a unique identifier from the prefix and the name.  The name
    is allowed to start with $."""
    if name.startswith('$'):
        return '%sinternal_%s' % (prefix, name[1:])
    else:
        return '%s_%s' % (prefix, name)

# __________ utilities __________
PyObjPtr = Ptr(PyObject)

def getgcflavor(classdef):
    classdesc = classdef.classdesc
    alloc_flavor = classdesc.read_attribute('_alloc_flavor_',
                                            Constant('gc')).value
    return alloc_flavor

def externalvsinternal(rtyper, item_repr): # -> external_item_repr, (internal_)item_repr
    from pypy.rpython import rclass
    if (isinstance(item_repr, rclass.AbstractInstanceRepr) and
        getattr(item_repr, 'gcflavor', 'gc') == 'gc'):
        return item_repr, rclass.getinstancerepr(rtyper, None)
    else:
        return item_repr, item_repr


class DummyValueBuilder(object):

    def __init__(self, rtyper, TYPE):
        self.rtyper = rtyper
        self.TYPE = TYPE

    def _freeze_(self):
        return True

    def __hash__(self):
        return hash(self.TYPE)

    def __eq__(self, other):
        return (isinstance(other, DummyValueBuilder) and
                self.rtyper is other.rtyper and
                self.TYPE == other.TYPE)

    def __ne__(self, other):
        return not (self == other)

    def build_ll_dummy_value(self):
        TYPE = self.TYPE
        try:
            return self.rtyper.cache_dummy_values[TYPE]
        except KeyError:
            # generate a dummy ptr to an immortal placeholder struct/array
            if TYPE._is_varsize():
                p = lltype.malloc(TYPE, 1, immortal=True)
            else:
                p = lltype.malloc(TYPE, immortal=True)
            self.rtyper.cache_dummy_values[TYPE] = p
            return p

    ll_dummy_value = property(build_ll_dummy_value)


# logging/warning

import py
from pypy.tool.ansi_print import ansi_log

log = py.log.Producer("rtyper")
py.log.setconsumer("rtyper", ansi_log)
py.log.setconsumer("rtyper translating", None)
py.log.setconsumer("rtyper debug", None)

def warning(msg):
    log.WARNING(msg)



