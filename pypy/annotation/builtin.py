"""
Built-in functions.
"""

import types
import sys, math
from pypy.tool.ansi_print import ansi_print
from pypy.annotation.model import SomeInteger, SomeObject, SomeChar, SomeBool
from pypy.annotation.model import SomeList, SomeString, SomeTuple, SomeSlice
from pypy.annotation.model import SomeFloat
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation.factory import ListFactory
from pypy.objspace.flow.model import Constant
import pypy.objspace.std.restricted_int

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

def builtin_len(s_obj):
    return s_obj.len()

def builtin_range(*args):
    factory = getbookkeeper().getfactory(ListFactory)
    factory.generalize(SomeInteger())  # XXX nonneg=...
    return factory.create()

def builtin_pow(s_base, s_exponent, *args):
    if s_base.knowntype is s_exponent.knowntype is int:
        return SomeInteger()
    else:
        return SomeObject()

def builtin_int(s_obj):     # we can consider 'int' as a function
    return s_obj.int()

def restricted_uint(s_obj):    # for r_uint
    return SomeInteger(nonneg=True, unsigned=True)

def builtin_chr(s_int):
    return SomeChar()

def builtin_ord(s_chr):
    return s_chr.ord()

def builtin_id(o):
    return SomeInteger()

def builtin_abs(o):
    return o.abs()

def builtin_divmod(o1, o2):
    return SomeTuple([SomeObject(), SomeObject()])    # XXX

def builtin_unicode(s_obj): 
    return SomeString() 

def builtin_float(s_obj): 
    return s_obj.float()

def builtin_long(s_obj): 
    return s_obj.long()

def our_issubclass(cls1, cls2):
    """ we're going to try to be less silly in the face of old-style classes"""
    return cls2 is object or issubclass(cls1, cls2)

def builtin_isinstance(s_obj, s_type, variables=None):
    s = SomeBool() 
    if s_type.is_constant():
        typ = s_type.const
        # XXX bit of a hack:
        if issubclass(typ, (int, long)):
            typ = int
        if s_obj.is_constant():
            s.const = isinstance(s_obj.const, typ)
        elif our_issubclass(s_obj.knowntype, typ):
            s.const = True 
        elif not our_issubclass(typ, s_obj.knowntype): 
            s.const = False 
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        bk = getbookkeeper()
        if variables is None:
            fn, block, i = bk.position_key
            op = block.operations[i]
            assert op.opname == "simple_call" 
            assert len(op.args) == 3
            assert op.args[0] == Constant(isinstance)
            variables = [op.args[1]]
        for variable in variables:
            assert bk.annotator.binding(variable) == s_obj
        s.knowntypedata = (variables, bk.valueoftype(typ))
    return s 

def builtin_issubclass(s_cls1, s_cls2):
    if s_cls1.is_constant() and s_cls2.is_constant():
        return immutablevalue(issubclass(s_cls1.const, s_cls2.const))
    if hasattr(s_cls1, 'is_type_of'):
        vars = s_cls1.is_type_of
        annotator = getbookkeeper().annotator
        return builtin_isinstance(annotator.binding(vars[0]), s_cls2, vars)
    return SomeBool()

def builtin_getattr(s_obj, s_attr, s_default=None):
    if not s_attr.is_constant() or not isinstance(s_attr.const, str):
        ansi_print("UN-RPYTHONIC-WARNING " +
                   '[%s] getattr(%r, %r) is not RPythonic enough' % (getbookkeeper().whereami(),
                                                                     s_obj, s_attr),
                   esc="31") # RED
        return SomeObject()
    return s_obj.getattr(s_attr)

def builtin_hasattr(s_obj, s_attr):
    if not s_attr.is_constant() or not isinstance(s_attr.const, str):
        ansi_print("UN-RPYTHONIC-WARNING " +
                   '[%s] hasattr(%r, %r) is not RPythonic enough' % (getbookkeeper().whereami(),
                                                                     s_obj, s_attr),
                   esc="31") # RED
    return SomeBool()

def builtin_hash(s_obj):
    return SomeInteger()

def builtin_callable(s_obj):
    return SomeBool()

def builtin_tuple(s_iterable):
    if isinstance(s_iterable, SomeTuple):
        return s_iterable
    return SomeObject()

def builtin_iter(s_obj):
    return s_obj.iter()

def builtin_type(s_obj, *moreargs):
    if moreargs:
        raise Exception, 'type() called with more than one argument'
    if s_obj.is_constant():
        return immutablevalue(type(s_obj.const))
    r = SomeObject()
    # hack info
    bk = getbookkeeper()
    fn, block, i = bk.position_key
    annotator = bk.annotator
    op = block.operations[i]
    assert op.opname == "simple_call" 
    assert len(op.args) == 2
    assert op.args[0] == Constant(type)
    assert annotator.binding(op.args[1]) == s_obj   
    r.is_type_of = [op.args[1]]
    return r

def builtin_str(s_obj):
    return s_obj.str()

def builtin_repr(s_obj):
    return s_obj.repr()

def builtin_hex(s_obj):
    return s_obj.hex()

def builtin_oct(s_obj):
    return s_obj.oct()

def builtin_list(s_iterable):
    factory = getbookkeeper().getfactory(ListFactory)
    s_iter = s_iterable.iter()
    factory.generalize(s_iter.next())
    return factory.create()

def builtin_zip(s_iterable1, s_iterable2):
    factory = getbookkeeper().getfactory(ListFactory)
    s_iter1 = s_iterable1.iter()
    s_iter2 = s_iterable2.iter()
    s_tup = SomeTuple((s_iter1.next(),s_iter2.next()))
    factory.generalize(s_tup)
    return factory.create()

def builtin_apply(*stuff):
    print "XXX ignoring apply%r" % (stuff,)
    return SomeObject()

def builtin_compile(*stuff):
    s = SomeObject()
    s.knowntype = types.CodeType
    return s

def builtin_slice(*args):
    bk = getbookkeeper()
    if len(args) == 1:
        return SomeSlice(
            bk.immutablevalue(None), args[0], bk.immutablevalue(None))
    elif len(args) == 2:
        return SomeSlice(
            args[0], args[1], bk.immutablevalue(None))
    elif len(args) == 3:
        return SomeSlice(
            args[0], args[1], args[2])
    else:
        raise Exception, "bogus call to slice()"
        

def exception_init(s_self, *args):
    s_self.setattr(immutablevalue('args'), SomeTuple(args))

def builtin_bool(s_obj):
    return s_obj.is_true()

def count(s_obj):
    return SomeInteger()

def math_fmod(x, y):
    return SomeObject()

def math_floor(x):
    return SomeObject()

# collect all functions
import __builtin__
BUILTIN_ANALYZERS = {}
for name, value in globals().items():
    if name.startswith('builtin_'):
        original = getattr(__builtin__, name[8:])
        BUILTIN_ANALYZERS[original] = value

BUILTIN_ANALYZERS[pypy.objspace.std.restricted_int.r_int] = builtin_int
BUILTIN_ANALYZERS[pypy.objspace.std.restricted_int.r_uint] = restricted_uint
BUILTIN_ANALYZERS[Exception.__init__.im_func] = exception_init
# this one is needed otherwise when annotating assert in a test we may try to annotate 
# py.test AssertionError.__init__ .
BUILTIN_ANALYZERS[AssertionError.__init__.im_func] = exception_init
BUILTIN_ANALYZERS[sys.getrefcount] = count
BUILTIN_ANALYZERS[math.fmod] = math_fmod
BUILTIN_ANALYZERS[math.floor] = math_floor
