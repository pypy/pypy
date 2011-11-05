import sys
from pypy.rlib.objectmodel import Symbolic, ComputedIntSymbolic
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.rlib.rarithmetic import r_longlong, is_emulated_long
from pypy.rlib.rfloat import isinf, isnan
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.lltypesystem import rffi, llgroup
from pypy.rpython.lltypesystem.llmemory import Address, \
     AddressOffset, ItemOffset, ArrayItemsOffset, FieldOffset, \
     CompositeOffset, ArrayLengthOffset, \
     GCHeaderOffset, GCREF, AddressAsInt
from pypy.rpython.lltypesystem.llarena import RoundedUpForAllocation
from pypy.translator.c.support import cdecl, barebonearray

# ____________________________________________________________
#
# Primitives

def name_signed(value, db):
    if isinstance(value, Symbolic):
        if isinstance(value, FieldOffset):
            structnode = db.gettypedefnode(value.TYPE)
            return 'offsetof(%s, %s)'%(
                cdecl(db.gettype(value.TYPE), ''),
                structnode.c_struct_field_name(value.fldname))
        elif isinstance(value, ItemOffset):
            if value.TYPE != Void and value.repeat != 0:
                size = 'sizeof(%s)' % (cdecl(db.gettype(value.TYPE), ''),)
                if value.repeat != 1:
                    size = '(%s * %s)' % (size, value.repeat)
                return size
            else:
                return '0'
        elif isinstance(value, ArrayItemsOffset):
            if (isinstance(value.TYPE, FixedSizeArray) or
                barebonearray(value.TYPE)):
                return '0'
            elif value.TYPE.OF != Void:
                return 'offsetof(%s, items)'%(
                    cdecl(db.gettype(value.TYPE), ''))
            else:
                return 'sizeof(%s)'%(cdecl(db.gettype(value.TYPE), ''),)
        elif isinstance(value, ArrayLengthOffset):
            return 'offsetof(%s, length)'%(
                cdecl(db.gettype(value.TYPE), ''))
        elif isinstance(value, CompositeOffset):
            names = [name_signed(item, db) for item in value.offsets]
            return '(%s)' % (' + '.join(names),)
        elif type(value) == AddressOffset:
            return '0'
        elif type(value) == GCHeaderOffset:
            return '0'
        elif type(value) == RoundedUpForAllocation:
            return 'ROUND_UP_FOR_ALLOCATION(%s, %s)' % (
                name_signed(value.basesize, db),
                name_signed(value.minsize, db))
        elif isinstance(value, CDefinedIntSymbolic):
            return str(value.expr)
        elif isinstance(value, ComputedIntSymbolic):
            value = value.compute_fn()
        elif isinstance(value, llgroup.CombinedSymbolic):
            name = name_small_integer(value.lowpart, db)
            assert (value.rest & value.MASK) == 0
            return '(%s+%dL)' % (name, value.rest)
        elif isinstance(value, AddressAsInt):
            return '((long)%s)' % name_address(value.adr, db)
        else:
            raise Exception("unimplemented symbolic %r"%value)
    if value is None:
        assert not db.completed
        return None
    if value == -sys.maxint-1:   # blame C
        return '(-%dL-1L)' % sys.maxint
    else:
        return '%dL' % value

def name_unsigned(value, db):
    assert value >= 0
    return '%dUL' % value

def name_unsignedlonglong(value, db):
    assert value >= 0
    return '%dULL' % value

def name_signedlonglong(value, db):
    maxlonglong = r_longlong.MASK>>1
    if value == -maxlonglong-1:    # blame C
        return '(-%dLL-1LL)' % maxlonglong
    else:
        return '%dLL' % value

def name_float(value, db):
    if isinf(value):
        if value > 0:
            return '(Py_HUGE_VAL)'
        else:
            return '(-Py_HUGE_VAL)'
    elif isnan(value):
        return '(Py_HUGE_VAL/Py_HUGE_VAL)'
    else:
        x = repr(value)
        assert not x.startswith('n')
        return x
name_longfloat = name_float

def name_singlefloat(value, db):
    value = float(value)
    if isinf(value):
        if value > 0:
            return '((float)Py_HUGE_VAL)'
        else:
            return '((float)-Py_HUGE_VAL)'
    elif isnan(value):
        # XXX are these expressions ok?
        return '((float)(Py_HUGE_VAL/Py_HUGE_VAL))'
    else:
        return repr(value) + 'f'

def name_char(value, db):
    assert type(value) is str and len(value) == 1
    if ' ' <= value < '\x7f':
        return "'%s'" % (value.replace("\\", r"\\").replace("'", r"\'"),)
    else:
        return '((char)%d)' % ord(value)

def name_bool(value, db):
    return '%d' % value

def name_void(value, db):
    return '/* nothing */'

def name_unichar(value, db):
    assert type(value) is unicode and len(value) == 1
    return '((wchar_t)%d)' % ord(value)

def name_address(value, db):
    if value:
        return db.get(value.ref())
    else:
        return 'NULL'

def name_gcref(value, db):
    if value:
        obj = value._obj
        if isinstance(obj, int):
            # a tagged pointer
            return _name_tagged(obj, db)
        realobj = obj.container
        if isinstance(realobj, int):
            return _name_tagged(realobj, db)
        realvalue = cast_opaque_ptr(Ptr(typeOf(realobj)), value)
        return db.get(realvalue)
    else:
        return 'NULL'

def _name_tagged(obj, db):
    assert obj & 1 == 1
    return '((%s) %d)' % (cdecl("void*", ''), obj)

def name_small_integer(value, db):
    """Works for integers of size at most INT or UINT."""
    if isinstance(value, Symbolic):
        if isinstance(value, llgroup.GroupMemberOffset):
            groupnode = db.getcontainernode(value.grpptr._as_obj())
            return 'GROUP_MEMBER_OFFSET(%s, member%s)' % (
                cdecl(groupnode.implementationtypename, ''),
                value.index,
                )
        else:
            raise Exception("unimplemented symbolic %r" % value)
    return str(value)

# On 64 bit machines, SignedLongLong and Signed are the same, so the
# order matters, because we want the Signed implementation.
PrimitiveName = {
    SignedLongLong:   name_signedlonglong,
    Signed:   name_signed,
    UnsignedLongLong: name_unsignedlonglong,
    Unsigned: name_unsigned,
    Float:    name_float,
    SingleFloat: name_singlefloat,
    LongFloat: name_longfloat,
    Char:     name_char,
    UniChar:  name_unichar,
    Bool:     name_bool,
    Void:     name_void,
    Address:  name_address,
    GCREF:    name_gcref,
    }

PrimitiveType = {
    SignedLongLong:   'long long @',
    Signed:   'long @',
    UnsignedLongLong: 'unsigned long long @',
    Unsigned: 'unsigned long @',
    Float:    'double @',
    SingleFloat: 'float @',
    LongFloat: 'long double @',
    Char:     'char @',
    UniChar:  'wchar_t @',
    Bool:     'bool_t @',
    Void:     'void @',
    Address:  'void* @',
    GCREF:    'void* @',
    }

# support for win64, where sizeof(long) == 4
if is_emulated_long:
    PrimitiveType.update( {
        Signed:   '__int64 @',
        Unsigned: 'unsigned __int64 @',
    } )

def define_c_primitive(ll_type, c_name, suffix=''):
    if ll_type in PrimitiveName:
        return
    if suffix == '':
        PrimitiveName[ll_type] = name_small_integer
    else:
        name_str = '((%s) %%d%s)' % (c_name, suffix)
        PrimitiveName[ll_type] = lambda value, db: name_str % value
    PrimitiveType[ll_type] = '%s @'% c_name

define_c_primitive(rffi.SIGNEDCHAR, 'signed char')
define_c_primitive(rffi.UCHAR, 'unsigned char')
define_c_primitive(rffi.SHORT, 'short')
define_c_primitive(rffi.USHORT, 'unsigned short')
define_c_primitive(rffi.INT, 'int')
define_c_primitive(rffi.INT_real, 'int')
define_c_primitive(rffi.UINT, 'unsigned int')
if is_emulated_long: # special case for win64
    define_c_primitive(rffi.LONG, '__int64', 'LL')
    define_c_primitive(rffi.ULONG, 'unsigned __int64', 'ULL')
else:
    define_c_primitive(rffi.LONG, 'long', 'L')
    define_c_primitive(rffi.ULONG, 'unsigned long', 'UL')
define_c_primitive(rffi.LONGLONG, 'long long', 'LL')
define_c_primitive(rffi.ULONGLONG, 'unsigned long long', 'ULL')
