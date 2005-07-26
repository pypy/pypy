from pypy.annotation.pairtype import pair, pairtype, extendabletype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import Void, Bool, Float, Signed, Char, UniChar
from pypy.rpython.lltype import typeOf, LowLevelType, Ptr, PyObject
from pypy.rpython.lltype import FuncType, functionptr
from pypy.tool.ansi_print import ansi_print
from pypy.rpython.error import TyperError, MissingRTypeOperation 

# initialization states for Repr instances 

class setupstate: 
    NOTINITIALIZED = 0 
    INPROGRESS = 1
    BROKEN = 2 
    FINISHED = 3 

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

    def convert_const(self, value):
        "Convert the given constant value to the low-level repr of 'self'."
        if self.lowleveltype != Void:
            try:
                realtype = typeOf(value)
            except (AssertionError, AttributeError):
                realtype = '???'
            if realtype != self.lowleveltype:
                raise TyperError("convert_const(self = %r, value = %r)" % (
                    self, value))
        return value

    def get_ll_eq_function(self): 
        raise TyperError, 'no equality function for %r' % self

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
            try:
                s_obj.find_method(attr)   # just to check it is here
            except AttributeError:
                raise TyperError("no method %s on %r" % (attr, s_obj))
            else:
                # implement methods (of a known name) as just their 'self'
                return hop.inputarg(self, arg=0)
        else:
            raise TyperError("getattr() with a non-constant attribute name")

    def rtype_str(self, hop):
        vrepr = inputconst(Void, self)
        return hop.gendirectcall(self.ll_str, hop.args_v[0], vrepr)

    def rtype_nonzero(self, hop):
        return self.rtype_is_true(hop)   # can call a subclass' rtype_is_true()

    def rtype_is_true(self, hop):
        try:
            vlen = self.rtype_len(hop)
        except MissingRTypeOperation:
            return hop.inputconst(Bool, True)
        else:
            return hop.genop('int_is_true', [vlen], resulttype=Bool)

    def rtype_id(self, hop):
        if not isinstance(self.lowleveltype, Ptr):
            raise TyperError('id() of an instance of the non-pointer %r' % (
                self,))
        vobj, = hop.inputargs(self)
        # XXX
        return hop.genop('cast_ptr_to_int', [vobj], resulttype=Signed)

    def rtype_iter(self, hop):
        r_iter = self.make_iterator_repr()
        return r_iter.newiter(hop)

    def make_iterator_repr(self):
        raise TyperError("%s is not iterable" % (self,))

class __extend__(annmodel.SomeIterator):
    # NOTE: SomeIterator is for iterators over any container, not just list
    def rtyper_makerepr(self, rtyper):
        r_container = rtyper.getrepr(self.s_container)
        return r_container.make_iterator_repr()
    def rtyper_makekey(self):
        return self.__class__, self.s_container.rtyper_makekey()

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
        if robj1.lowleveltype == Void:
            robj1 = robj2
        elif robj2.lowleveltype == Void:
            robj2 = robj1
        if (not isinstance(robj1.lowleveltype, Ptr) or
            not isinstance(robj2.lowleveltype, Ptr)):
            raise TyperError('is of instances of the non-pointers: %r, %r' % (
                robj1, robj2))
        if robj1.lowleveltype != robj2.lowleveltype:
            raise TyperError('is of instances of different pointer types: %r, %r' % (
                robj1, robj2))
            
        v_list = hop.inputargs(robj1, robj2)
        return hop.genop('ptr_eq', v_list, resulttype=Bool)

# ____________________________________________________________


def missing_rtype_operation(self, hop):
    raise MissingRTypeOperation("unimplemented operation: '%s' on %r" % (
        hop.spaceop.opname, self))

def setattr_default(obj, attr, value):
    if not hasattr(obj, attr):
        setattr(obj, attr, value)

for opname in annmodel.UNARY_OPERATIONS:
    setattr_default(Repr, 'rtype_' + opname, missing_rtype_operation)

# hardwired_*call*
setattr_default(Repr, 'rtype_hardwired_simple_call', missing_rtype_operation)
setattr_default(Repr, 'rtype_hardwired_call_args'  , missing_rtype_operation)

for opname in annmodel.BINARY_OPERATIONS:
    setattr_default(pairtype(Repr, Repr),
                    'rtype_' + opname, missing_rtype_operation)

# not in BINARY_OPERATIONS
setattr_default(pairtype(Repr, Repr),
                'rtype_contains', missing_rtype_operation)

class __extend__(pairtype(Repr, Repr)):
    def convert_from_to((r_from, r_to), v, llops):
        return NotImplemented

# ____________________________________________________________
# Primitive Repr classes, in the same hierarchical order as
# the corresponding SomeObjects

class FloatRepr(Repr):
    lowleveltype = Float

class IntegerRepr(FloatRepr):
    lowleveltype = Signed

class BoolRepr(IntegerRepr):
    lowleveltype = Bool

class StringRepr(Repr):
    pass

class CharRepr(StringRepr):
    lowleveltype = Char

class UniCharRepr(Repr):
    lowleveltype = UniChar

class VoidRepr(Repr):
    lowleveltype = Void
impossible_repr = VoidRepr()

# ____________________________________________________________

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
    if lltype != Void:
        try:
            realtype = typeOf(value)
        except (AssertionError, AttributeError):
            realtype = '???'
        if realtype != lltype:
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

# __________ utilities __________

PyObjPtr = Ptr(PyObject)

def getconcretetype(v):
    return getattr(v, 'concretetype', PyObjPtr)

def getfunctionptr(translator, graphfunc, getconcretetype=getconcretetype):
    """Make a functionptr from the given Python function."""
    graph = translator.getflowgraph(graphfunc)
    llinputs = [getconcretetype(v) for v in graph.getargs()]
    lloutput = getconcretetype(graph.getreturnvar())
    FT = FuncType(llinputs, lloutput)
    _callable = getattr(graphfunc, '_specializedversionof_', graphfunc)
    return functionptr(FT, graphfunc.func_name, graph = graph, _callable = _callable)

def warning(msg):
    ansi_print("*** WARNING: %s" % (msg,), esc="31") # RED
