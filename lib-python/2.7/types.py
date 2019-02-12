"""Define names for all type symbols known in the standard interpreter.

Types that are part of optional modules (e.g. array) are not listed.
"""
import sys

# Iterators in Python aren't a matter of type but of protocol.  A large
# and changing number of builtin types implement *some* flavor of
# iterator.  Don't check the type!  Use hasattr to check for both
# "__iter__" and "next" attributes instead.

NoneType = type(None)
TypeType = type
ObjectType = object

IntType = int
LongType = long
FloatType = float
BooleanType = bool
try:
    ComplexType = complex
except NameError:
    pass

StringType = str

# StringTypes is already outdated.  Instead of writing "type(x) in
# types.StringTypes", you should use "isinstance(x, basestring)".  But
# we keep around for compatibility with Python 2.2.
try:
    UnicodeType = unicode
    StringTypes = (StringType, UnicodeType)
except NameError:
    StringTypes = (StringType,)

BufferType = buffer

TupleType = tuple
ListType = list
DictType = DictionaryType = dict

def _f(): pass
FunctionType = type(_f)
LambdaType = type(lambda: None)         # Same as FunctionType
CodeType = type(_f.func_code)

def _g():
    yield 1
GeneratorType = type(_g())

class _C:
    def _m(self): pass
ClassType = type(_C)
UnboundMethodType = type(_C._m)         # Same as MethodType
_x = _C()
InstanceType = type(_x)
MethodType = type(_x._m)

BuiltinFunctionType = type(len)
BuiltinMethodType = type([].append)     # Same as BuiltinFunctionType

ModuleType = type(sys)
FileType = file
XRangeType = xrange

try:
    raise TypeError
except TypeError:
    tb = sys.exc_info()[2]
    TracebackType = type(tb)
    FrameType = type(tb.tb_frame)
    del tb

# PyPy extension
try:
    FakeFrameType = type(next(sys._current_frames().itervalues()))
except (AttributeError, StopIteration):
    FakeFrameType = FrameType

SliceType = slice
EllipsisType = type(Ellipsis)

DictProxyType = type(TypeType.__dict__)
NotImplementedType = type(NotImplemented)

#
# On CPython, FunctionType.__code__ is a 'getset_descriptor', but
# FunctionType.__globals__ is a 'member_descriptor', just like app-level
# slots.  On PyPy, all descriptors of built-in types are
# 'getset_descriptor', but the app-level slots are 'member_descriptor'
# as well.  (On Jython the situation might still be different.)
#
# Note that MemberDescriptorType was equal to GetSetDescriptorType in
# PyPy <= 6.0.
#
GetSetDescriptorType = type(FunctionType.func_code)
class _C(object): __slots__ = 's'
MemberDescriptorType = type(_C.s)

del sys, _f, _g, _C, _x                           # Not for export

__all__ = list(n for n in globals() if n[:1] != '_')
