from pypy.annotation.pairtype import pair, pairtype, extendabletype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import Void, Bool, Float, Signed, Char, UniChar
from pypy.rpython.lltype import typeOf, LowLevelType, Ptr, PyObject
from pypy.rpython.lltype import FuncType, functionptr


class Repr:
    """ An instance of Repr is associated with each instance of SomeXxx.
    It defines the chosen representation for the SomeXxx.  The Repr subclasses
    generally follows the SomeXxx subclass hierarchy, but there are numerous
    exceptions.  For example, the annotator uses SomeIter for any iterator, but
    we need different representations according to the type of container we are
    iterating over.
    """
    __metaclass__ = extendabletype

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.lowleveltype)

    def setup(self):
        "For recursive data structure, which must be initialized in two steps."

    def setup_final_touch(self):
        """Same as setup(), called a bit later, for effects that are only
        needed after the typer finished (as opposed to needed for other parts
        of the typer itself)."""

    def __getattr__(self, name):
        # Assume that when an attribute is missing, it's because setup() needs
        # to be called
        self.setup()
        try:
            return self.__dict__[name]
        except KeyError:
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
        return self.s_container.rtyper_makekey()

class __extend__(annmodel.SomeImpossibleValue):
    def rtyper_makerepr(self, rtyper):
        return impossible_repr
    def rtyper_makekey(self):
        return None

# ____ generic binary operations _____________________________


class __extend__(pairtype(Repr, Repr)):
    
    def rtype_is_((robj1, robj2), hop):
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

class TyperError(Exception):
    def __str__(self):
        result = Exception.__str__(self)
        if hasattr(self, 'where'):
            result += '\n.. %r\n.. %r' % self.where
        return result

class MissingRTypeOperation(TyperError):
    pass

def missing_rtype_operation(self, hop):
    raise MissingRTypeOperation("unimplemented operation: '%s' on %r" % (
        hop.spaceop.opname, self))

def setattr_default(obj, attr, value):
    if not hasattr(obj, attr):
        setattr(obj, attr, value)

for opname in annmodel.UNARY_OPERATIONS:
    setattr_default(Repr, 'rtype_' + opname, missing_rtype_operation)
for opname in annmodel.BINARY_OPERATIONS:
    setattr_default(pairtype(Repr, Repr),
                    'rtype_' + opname, missing_rtype_operation)


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

