"""Appspace types module. 

Define names for all type symbols known in the standard interpreter.

Types that are part of optional modules (e.g. array) are not listed.
"""
from __future__ import generators

import sys

# Iterators in Python aren't a matter of type but of protocol.  A large
# and changing number of builtin types implement *some* flavor of
# iterator.  Don't check the type!  Use hasattr to check for both
# "__iter__" and "next" attributes instead.

NoneType = type(None)
TypeType = type
ObjectType = object

IntType = int
try:
    LongType = long
except NameError:
    pass
FloatType = float
try:
    ComplexType = complex
except NameError:
    pass

StringType = str
try:
    UnicodeType = unicode
    StringTypes = (StringType, UnicodeType)
except NameError:
    StringTypes = (StringType,)

try:
    BufferType = type(buffer(''))
except NameError:
    pass

TupleType = tuple
ListType = list
DictType = DictionaryType = dict

def _f(): pass
FunctionType = type(_f)
LambdaType = type(lambda: None)         # Same as FunctionType
try:
    CodeType = type(_f.func_code)
except RuntimeError:
    # Execution in restricted environment
    pass

def g():
    yield 1
try:
    GeneratorType = type(g())
except:
    # Refusing generators
    pass
del g

class _C:
    def _m(self): pass
ClassType = type(_C)
try:
    UnboundMethodType = type(_C._m)         # Same as MethodType
except AttributeError:
    pass
_x = _C()
InstanceType = type(_x)
MethodType = type(_x._m)

BuiltinFunctionType = type(len)
BuiltinMethodType = type([].append)     # Same as BuiltinFunctionType

ModuleType = type(sys)
try:
    FileType = file
    XRangeType = type(xrange(0))
except NameError:
   pass

try:
    raise TypeError
except TypeError:
    try:
        tb = sys.exc_info()[2]
        TracebackType = type(tb)
        FrameType = type(tb.tb_frame)
    except AttributeError:
        # In the restricted environment, exc_info returns (None, None,
        # None) Then, tb.tb_frame gives an attribute error
        pass
    tb = None; del tb

SliceType = type(slice(0))
EllipsisType = type(Ellipsis)

#DictProxyType = type(TypeType.__dict__)

del sys, _f, _C, _x#, generators                  # Not for export
