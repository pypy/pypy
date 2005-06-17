"""
Unary operations on SomeValues.
"""

from types import FunctionType
from pypy.interpreter.argument import Arguments
from pypy.annotation.pairtype import pair
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeChar, SomeList, SomeDict
from pypy.annotation.model import SomeUnicodeCodePoint
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeBuiltin, SomeFloat
from pypy.annotation.model import SomeIterator, SomePBC, new_or_old_class
from pypy.annotation.model import unionof, set, setunion, missing_operation
from pypy.annotation.bookkeeper import getbookkeeper, RPythonCallsSpace
from pypy.annotation.classdef import isclassdef
from pypy.annotation import builtin

from pypy.annotation.binaryop import _clone ## XXX where to put this?

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

UNARY_OPERATIONS = set(['len', 'is_true', 'getattr', 'setattr', 'delattr', 'hash',
                        'simple_call', 'call_args', 'str', 'repr',
                        'iter', 'next', 'invert', 'type', 'issubtype',
                        'pos', 'neg', 'nonzero', 'abs', 'hex', 'oct',
                        'ord', 'int', 'float', 'long', 'id',
                        'neg_ovf', 'abs_ovf'])

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
            r.knowntype = type
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

    def id(obj): # xxx
        return SomeInteger()

    def int(obj):
        return SomeInteger()

    def float(obj):
        return SomeFloat()

    def long(obj):
        return SomeObject()   # XXX

    def delattr(obj, s_attr):
        if obj.__class__ != SomeObject or obj.knowntype != object:
            getbookkeeper().warning(
                ("delattr on potentally non-SomeObjects is not RPythonic: delattr(%r,%r)" %
                 (obj, s_attr)))

    def find_method(obj, name):
        "Look for a special-case implementation for the named method."
        analyser = getattr(obj.__class__, 'method_' + name)
        return SomeBuiltin(analyser, obj, name)

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
        return obj.call(getbookkeeper().build_args("simple_call", args_s))

    def call_args(obj, *args_s):
        return obj.call(getbookkeeper().build_args("call_args", args_s))

    def call(obj, args, implicit_init=False):
        #raise Exception, "cannot follow call_args%r" % ((obj, args),)
        getbookkeeper().warning("cannot follow call(%r, %r)" % (obj, args))
        return SomeObject()

class __extend__(SomeInteger):

    def invert(self):
        if self.unsigned:
            return SomeInteger(unsigned=True)
        return SomeInteger()

    invert.can_only_throw = []

    def pos(self):
        return self

    pos.can_only_throw = []
    int = pos

    # these are the only ones which can overflow:

    def neg(self):
        if self.unsigned:
            return SomeInteger(unsigned=True)
        return SomeInteger()

    neg.can_only_throw = []
    neg_ovf = _clone(neg, [OverflowError])

    def abs(self):
        if self.unsigned:
            return self
        return SomeInteger(nonneg=True)

    abs.can_only_throw = []
    abs_ovf = _clone(abs, [OverflowError])


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
        getbookkeeper().count("tuple_iter", tup)
        return SomeIterator(tup)

    def getanyitem(tup):
        return unionof(*tup.items)


class __extend__(SomeList):

    def method_append(lst, s_value):
        lst.listdef.resize()
        pair(lst, SomeInteger()).setitem(s_value)

    def method_extend(lst, s_iterable):
        lst.listdef.resize()
        if isinstance(s_iterable, SomeList):   # unify the two lists
            lst.listdef.union(s_iterable.listdef)
        else:
            s_iter = s_iterable.iter()
            pair(lst, SomeInteger()).setitem(s_iter.next())

    def method_reverse(lst):
        lst.listdef.mutate()

    def method_insert(lst, s_index, s_value):
        lst.listdef.resize()
        pair(lst, SomeInteger()).setitem(s_value)

    def method_pop(lst, s_index=None):
        lst.listdef.resize()
        return lst.listdef.read_item()

    def method_index(lst, el):
        getbookkeeper().count("list_index")
        return SomeInteger(nonneg=True)

    def len(lst):
        s_item = lst.listdef.read_item()
        if isinstance(s_item, SomeImpossibleValue):
            r = SomeInteger(nonneg=True)
            r.const = 0
            return r
        return SomeObject.len(lst)

    def iter(lst):
        return SomeIterator(lst)

    def getanyitem(lst):
        return lst.listdef.read_item()

class __extend__(SomeDict):

    def len(dct):
        s_key = dct.dictdef.read_key()
        s_value = dct.dictdef.read_value()
        if isinstance(s_key, SomeImpossibleValue) and isinstance(s_value, SomeImpossibleValue):
            r = SomeInteger(nonneg=True)
            r.const = 0
            return r
        return SomeObject.len(dct)

    def iter(dct):
        return SomeIterator(dct)

    def getanyitem(dct):
        return dct.dictdef.read_key()

    def method_get(dct, key, dfl):
        return unionof(dct.dictdef.read_value(), dfl)

    def method_copy(dct):
        return dct

    def method_update(dct1, dct2):
        dct1.dictdef.generalize_key(dct2.dictdef.read_key())
        dct1.dictdef.generalize_value(dct2.dictdef.read_value())

    def method_keys(dct):
        return getbookkeeper().newlist(dct.dictdef.read_key())

    def method_values(dct):
        return getbookkeeper().newlist(dct.dictdef.read_value())

    def method_items(dct):
        return getbookkeeper().newlist(SomeTuple((dct.dictdef.read_key(),
                                                  dct.dictdef.read_value())))


class __extend__(SomeString):

    def method_startswith(str, frag):
        return SomeBool()

    def method_endswith(str, frag):
        return SomeBool()

    def method_join(str, s_list):
        getbookkeeper().count("str_join", str)
        return SomeString()

    def iter(str):
        return SomeIterator(str)

    def getanyitem(str):
        return SomeChar()

    def ord(str):
        return SomeInteger(nonneg=True)

    def method_split(str, patt): # XXX
        return getbookkeeper().newlist(SomeString())


class __extend__(SomeChar):

    def len(chr):
        return immutablevalue(1)

class __extend__(SomeUnicodeCodePoint):

    def ord(uchr):
        return SomeInteger(nonneg=True)


class __extend__(SomeIterator):

    def iter(itr):
        return itr

    def next(itr):
        return itr.s_container.getanyitem()


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
            elif isinstance(s_result, SomeImpossibleValue):
                ins.classdef.check_missing_attribute_update(attr)
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

    def call(bltn, args, implicit_init=False):
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

    def setattr(pbc, s_attr, s_value):
        getbookkeeper().warning("setattr not wanted on %r" % (pbc,))

    def call(pbc, args, implicit_init=False):
        bookkeeper = getbookkeeper()
        return bookkeeper.pbc_call(pbc, args, implicit_init=implicit_init)

        #bookkeeper = getbookkeeper()
        #results = []
        #for func, classdef in pbc.prebuiltinstances.items():
        #    if isclassdef(classdef):
        #        s_self = SomeInstance(classdef)
        #        args1 = args.prepend(s_self)
        #    else:
        #        args1 = args
        #    results.append(bookkeeper.pycall(func, args1))
        #return unionof(*results)

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


# annotation of low-level types
from pypy.annotation.model import SomePtr, ll_to_annotation, annotation_to_lltype
class __extend__(SomePtr):

    def getattr(p, s_attr):
        assert s_attr.is_constant(), "getattr on ptr %r with non-constant field-name" % p.ll_ptrtype
        v = getattr(p.ll_ptrtype._example(), s_attr.const)
        return ll_to_annotation(v)

    def len(p):
        return ll_to_annotation(len(p.ll_ptrtype._example()))

    def setattr(p, s_attr, s_value): # just doing checking
        assert s_attr.is_constant(), "getattr on ptr %r with non-constant field-name" % p.ll_ptrtype
        v_lltype = annotation_to_lltype(s_value)
        setattr(p.ll_ptrtype._example(), s_attr.const,
                v_lltype._defl())

    def simple_call(p, *args_s):
        llargs = [annotation_to_lltype(arg_s)._defl() for arg_s in args_s]
        v = p.ll_ptrtype._example()(*llargs)
        return ll_to_annotation(v)

    def is_true(p):
        return SomeBool()
