"""
Built-in functions.
"""

import types
import sys, math, os
from pypy.tool.ansi_print import ansi_print
from pypy.annotation.model import SomeInteger, SomeObject, SomeChar, SomeBool
from pypy.annotation.model import SomeList, SomeString, SomeTuple, SomeSlice
from pypy.annotation.model import SomeFloat, unionof
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation.factory import ListFactory
from pypy.objspace.flow.model import Constant
import pypy.tool.rarithmetic

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

def builtin_range(*args):
    factory = getbookkeeper().getfactory(ListFactory)
    factory.generalize(SomeInteger())  # XXX nonneg=...
    return factory.create()

builtin_xrange = builtin_range # xxx for now allow it

def builtin_int(s_obj):
    return SomeInteger()

def restricted_uint(s_obj):    # for r_uint
    return SomeInteger(nonneg=True, unsigned=True)

def builtin_float(s_obj):
    return SomeFloat()

def builtin_long(s_obj):
    return SomeObject()

def builtin_chr(s_int):
    return SomeChar()

def builtin_unicode(s_obj): 
    return SomeString() 

def our_issubclass(cls1, cls2):
    """ we're going to try to be less silly in the face of old-style classes"""
    return cls2 is object or issubclass(cls1, cls2)

def builtin_isinstance(s_obj, s_type, variables=None):
    r = SomeBool() 
    if s_type.is_constant():
        typ = s_type.const
        if typ == pypy.tool.rarithmetic.r_uint:
            if s_obj.is_constant():
                r.const = isinstance(s_obj.const, typ)
            else:
                if s_obj.knowntype == int:
                    r.const = s_obj.unsigned
        else:
            if typ == long:
                getbookkeeper().warning("isinstance(., long) is not RPython")
                typ = int # XXX as we did before
            assert not issubclass(typ, (int,long)) or typ in (bool, int), (
                "for integers only isinstance(.,int|r_uint) are supported")
            if s_obj.is_constant():
                r.const = isinstance(s_obj.const, typ)
            elif our_issubclass(s_obj.knowntype, typ):
                r.const = True 
            elif not our_issubclass(typ, s_obj.knowntype): 
                r.const = False 
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
        r.knowntypedata = (variables, bk.valueoftype(typ))
    return r

def builtin_hasattr(s_obj, s_attr):
    if not s_attr.is_constant() or not isinstance(s_attr.const, str):
        getbookkeeper().warning('hasattr(%r, %r) is not RPythonic enough' %
                                (s_obj, s_attr))
    return SomeBool()

def builtin_callable(s_obj):
    return SomeBool()

def builtin_tuple(s_iterable):
    if isinstance(s_iterable, SomeTuple):
        return s_iterable
    return SomeObject()

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

def builtin_min(*s_values):
    if len(s_values) == 1: # xxx do we support this?
        s_iter = s_values[0].iter()
        return s_iter.next()
    else:
        return unionof(*s_values)

builtin_max = builtin_min

def builtin_apply(*stuff):
    getbookkeeper().warning("ignoring apply%r" % (stuff,))
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
    pass   # XXX check correctness of args, maybe

def count(s_obj):
    return SomeInteger()

def conf():
    return SomeString()

def math_fmod(x, y):
    return SomeObject()

def math_floor(x):
    return SomeObject()

def rarith_ovfcheck(s_obj):
    if isinstance(s_obj, SomeInteger) and s_obj.unsigned:
        getbookkeeper().warning("ovfcheck on unsigned")
    return s_obj

def rarith_ovfcheck_lshift(s_obj1, s_obj2):
    if isinstance(s_obj1, SomeInteger) and s_obj1.unsigned:
        getbookkeeper().warning("ovfcheck_lshift with unsigned")
    return SomeInteger()

def unicodedata_decimal(s_uchr):
    return SomeInteger()

def test(*args):
    return SomeBool()

def pathpart(*args):
    return SomeString()

# collect all functions
import __builtin__
BUILTIN_ANALYZERS = {}
for name, value in globals().items():
    if name.startswith('builtin_'):
        original = getattr(__builtin__, name[8:])
        BUILTIN_ANALYZERS[original] = value

BUILTIN_ANALYZERS[pypy.tool.rarithmetic.r_uint] = restricted_uint
BUILTIN_ANALYZERS[pypy.tool.rarithmetic.ovfcheck] = rarith_ovfcheck
BUILTIN_ANALYZERS[pypy.tool.rarithmetic.ovfcheck_lshift] = rarith_ovfcheck_lshift
BUILTIN_ANALYZERS[Exception.__init__.im_func] = exception_init
# this one is needed otherwise when annotating assert in a test we may try to annotate 
# py.test AssertionError.__init__ .
BUILTIN_ANALYZERS[AssertionError.__init__.im_func] = exception_init
BUILTIN_ANALYZERS[math.fmod] = math_fmod
BUILTIN_ANALYZERS[math.floor] = math_floor

BUILTIN_ANALYZERS[sys.getrefcount] = count
BUILTIN_ANALYZERS[sys.getdefaultencoding] = conf
import unicodedata
BUILTIN_ANALYZERS[unicodedata.decimal] = unicodedata_decimal # xxx

# os.path stuff
BUILTIN_ANALYZERS[os.path.dirname] = pathpart
BUILTIN_ANALYZERS[os.path.normpath] = pathpart
BUILTIN_ANALYZERS[os.path.join] = pathpart
BUILTIN_ANALYZERS[os.path.exists] = test
BUILTIN_ANALYZERS[os.path.isdir] = test
