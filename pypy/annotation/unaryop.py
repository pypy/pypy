"""
Unary operations on SomeValues.
"""

from types import FunctionType
from pypy.interpreter.argument import Arguments
from pypy.annotation.pairtype import pair
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeChar, SomeList, SomeDict
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeBuiltin, SomeFloat
from pypy.annotation.model import SomeIterator, SomePBC, new_or_old_class
from pypy.annotation.model import unionof, set, setunion, missing_operation
from pypy.annotation.factory import BlockedInference, generalize, ListFactory
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation.classdef import isclassdef
from pypy.annotation import builtin

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

UNARY_OPERATIONS = set(['len', 'is_true', 'getattr', 'setattr', 'hash',
                        'simple_call', 'call_args', 'str', 'repr',
                        'iter', 'next', 'invert', 'type', 'issubtype',
                        'pos', 'neg', 'nonzero', 'abs', 'hex', 'oct',
                        'ord', 'int', 'float', 'long']) 

for opname in UNARY_OPERATIONS:
    missing_operation(SomeObject, opname)


class __extend__(SomeObject):

    def type(obj, *moreargs):
        if moreargs:
            raise Exception, 'type() called with more than one argument'
        if obj.is_constant():
            r = immutablevalue(obj.knowntype)
        else:
            r = SomeObject()
        bk = getbookkeeper()
        fn, block, i = bk.position_key
        annotator = bk.annotator
        op = block.operations[i]
        assert op.opname == "type"
        assert len(op.args) == 1
        assert annotator.binding(op.args[0]) == obj
        r.is_type_of = [op.args[0]]
        return r

    def issubtype(obj, s_cls):
        if obj.is_constant() and s_cls.is_constant():
            return immutablevalue(issubclass(obj.const, s_cls.const))
        if hasattr(obj, 'is_type_of'):
            vars = obj.is_type_of
            annotator = getbookkeeper().annotator
            return builtin.builtin_isinstance(annotator.binding(vars[0]),
                                              s_cls, vars)
        return SomeBool()

    def len(obj):
        return SomeInteger(nonneg=True)

    def is_true(obj):
        if obj.is_constant():
            return immutablevalue(bool(obj.const))
        else:
            s_len = obj.len()
            if s_len.is_constant():
                return immutablevalue(s_len.const > 0)
            else:
                return SomeBool()

    def nonzero(obj):
        return obj.is_true()

    def hash(obj):
        return SomeInteger()

    def str(obj):
        return SomeString()

    repr = hex = oct = str

    def int(obj):
        return SomeInteger()

    def float(obj):
        return SomeFloat()

    def long(obj):
        return SomeObject()   # XXX

    def find_method(obj, name):
        "Look for a special-case implementation for the named method."
        analyser = getattr(obj.__class__, 'method_' + name)
        return SomeBuiltin(analyser, obj)

    def getattr(obj, s_attr):
        # get a SomeBuiltin if the SomeObject has
        # a corresponding method to handle it
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            try:
                return obj.find_method(attr)
            except AttributeError:
                pass
            # if the SomeObject is itself a constant, allow reading its attrs
            if obj.is_constant() and hasattr(obj.const, attr):
                return immutablevalue(getattr(obj.const, attr))
        else:
            getbookkeeper().warning('getattr(%r, %r) is not RPythonic enough' %
                                    (obj, s_attr))
        return SomeObject()

    def bindcallables(obj, classdef):
        return obj   # default unbound __get__ implementation

    def simple_call(obj, *args_s):
        space = RPythonCallsSpace()
        return obj.call(Arguments(space, args_s))

    def call_args(obj, s_shape, *args_s):
        space = RPythonCallsSpace()
        return obj.call(Arguments.fromshape(space, s_shape.const, args_s))

    def call(obj, args):
        #raise Exception, "cannot follow call_args%r" % ((obj, args),)
        getbookkeeper().warning("cannot follow call(%r, %r)" % (obj, args))
        return SomeObject()

class __extend__(SomeInteger):

    def invert(self):
        if self.unsigned:
            return SomeInteger(unsigned=True)
        return SomeInteger()

    def pos(self):
        return self

    int = pos

    def neg(self):
        if self.unsigned:
            return SomeInteger(unsigned=True)
        return SomeInteger()

    def abs(self):
        if self.unsigned:
            return self
        return SomeInteger(nonneg=True)


class __extend__(SomeBool):
    def is_true(self):
        return self


class __extend__(SomeFloat):

    def pos(flt):
        return flt

    def neg(flt):
        return SomeFloat()

    abs = neg


class __extend__(SomeTuple):

    def len(tup):
        return immutablevalue(len(tup.items))

    def iter(tup):
        return SomeIterator(unionof(*tup.items))


class __extend__(SomeList):

    def method_append(lst, s_value):
        pair(lst, SomeInteger()).setitem(s_value)

    def method_extend(lst, s_iterable):
        s_iter = s_iterable.iter()
        pair(lst, SomeInteger()).setitem(s_iter.next())

    def method_reverse(lst):
        pass

    def method_insert(lst, s_index, s_value):
        pair(lst, SomeInteger()).setitem(s_value)
        
    def method_pop(lst, s_index=None):
        return lst.s_item

    def iter(lst):
        return SomeIterator(lst.s_item)

class __extend__(SomeDict):
    def iter(dct):
        return SomeIterator(dct.s_key)

    def method_copy(dct):
        return SomeDict(dct.factories, dct.s_key, dct.s_value)

    def method_update(dct1, dct2):
        generalize(dct1.factories, dct2.s_key, dct2.s_value)

    def method_keys(dct):
        factory = getbookkeeper().getfactory(ListFactory)
        factory.generalize(dct.s_key)
        return factory.create()

    def method_values(dct):
        factory = getbookkeeper().getfactory(ListFactory)
        factory.generalize(dct.s_value)
        return factory.create()

    def method_items(dct):
        factory = getbookkeeper().getfactory(ListFactory)
        factory.generalize(SomeTuple((dct.s_key, dct.s_value)))
        return factory.create()
        

class __extend__(SomeString):

    def method_join(str, s_list):
        return SomeString()

    def iter(str):
        return SomeIterator(SomeChar())

    def ord(str):
        return SomeInteger(nonneg=True)

    def method_split(str, patt): # XXX
        factory = getbookkeeper().getfactory(ListFactory)
        factory.generalize(SomeString())
        return factory.create()    


class __extend__(SomeChar):

    def len(chr):
        return immutablevalue(1)


class __extend__(SomeIterator):

    def next(itr):
        return itr.s_item


class __extend__(SomeInstance):

    def getattr(ins, s_attr):
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            attrdef = ins.classdef.find_attribute(attr)
            position = getbookkeeper().position_key
            attrdef.read_locations[position] = True
            s_result = attrdef.getvalue()
            # hack: if s_result is a set of methods, discard the ones
            #       that can't possibly apply to an instance of ins.classdef.
            # XXX do it more nicely
            if isinstance(s_result, SomePBC):
                s_result = ins.classdef.matching(s_result, attr)
            return s_result
        return SomeObject()

    def setattr(ins, s_attr, s_value):
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            # find the (possibly parent) class where this attr is defined
            clsdef = ins.classdef.locate_attribute(attr)
            attrdef = clsdef.attrs[attr]
            attrdef.readonly = False

            # if the attrdef is new, this must fail
            if attrdef.getvalue().contains(s_value):
                return
            # create or update the attribute in clsdef
            clsdef.generalize_attr(attr, s_value)


class __extend__(SomeBuiltin):
    def simple_call(bltn, *args):
        if bltn.s_self is not None:
            return bltn.analyser(bltn.s_self, *args)
        else:
            return bltn.analyser(*args)

    def call(bltn, args):
        args, kw = args.unpack()
        assert not kw, "don't call builtins with keywords arguments"
        if bltn.s_self is not None:
            return bltn.analyser(bltn.s_self, *args)
        else:
            return bltn.analyser(*args)
        

class __extend__(SomePBC):

    def getattr(pbc, s_attr):
        bookkeeper = getbookkeeper()
        return bookkeeper.pbc_getattr(pbc, s_attr)
        
##         assert s_attr.is_constant()
##         attr = s_attr.const
##         actuals = []
##         for c in pbc.prebuiltinstances:
##             if hasattr(c, attr):
##                 # force the attribute to be considered on the class
##                 ##classdef = bookkeeper.getclassdef(new_or_old_class(c))
##                 ##classdef.find_attribute(attr).getvalue()
##                 # but only return the more precise result getattr(c, attr)
##                 actuals.append(immutablevalue(getattr(c, attr)))
##         return unionof(*actuals)

    def setattr(pbc, s_attr, s_value):
        getbookkeeper().warning("setattr not wanted on %r" % (pbc,))

    def call(pbc, args):
        bookkeeper = getbookkeeper()
        results = []
        for func, classdef in pbc.prebuiltinstances.items():
            if isclassdef(classdef): 
                s_self = SomeInstance(classdef)
                args1 = args.prepend(s_self)
            else:
                args1 = args
            results.append(bookkeeper.pycall(func, args1))
        return unionof(*results) 

    def bindcallables(pbc, classdef):   
        """ turn the callables in the given SomeCallable 'cal' 
            into bound versions.
        """
        d = {}
        for func, value in pbc.prebuiltinstances.items():
            if isinstance(func, FunctionType): 
                if isclassdef(value):
                    getbookkeeper().warning("rebinding an already bound "
                                            "method %r with %r" % (func, value))
                d[func] = classdef
            elif isinstance(func, staticmethod):
                d[func.__get__(43)] = value
            else:
                d[func] = value 
        return SomePBC(d)

    def is_true(pbc):
        outcome = None
        for c in pbc.prebuiltinstances:
            if outcome is None:
                outcome = bool(c)
            else:
                if outcome != bool(c):
                    return SomeBool()
        return immutablevalue(outcome)
            
            
class RPythonCallsSpace:
    """Pseudo Object Space providing almost no real operation.
    For the Arguments class: if it really needs other operations, it means
    that the call pattern is too complex for R-Python.
    """
    def newtuple(self, items_s):
        return SomeTuple(items_s)

    def newdict(self, stuff):
        raise CallPatternTooComplex, "'**' argument"

    def unpackiterable(self, s_obj, expected_length=None):
        if isinstance(s_obj, SomeTuple):
            if (expected_length is not None and
                expected_length != len(s_obj.items)):
                raise ValueError
            return s_obj.items
        raise CallPatternTooComplex, "'*' argument must be SomeTuple"

class CallPatternTooComplex(Exception):
    pass
