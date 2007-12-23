import sys
from pypy.rlib.objectmodel import Symbolic, ComputedIntSymbolic
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.rlib.rarithmetic import r_longlong, isinf, isnan
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem.llmemory import Address, \
     AddressOffset, ItemOffset, ArrayItemsOffset, FieldOffset, \
     CompositeOffset, ArrayLengthOffset, \
     GCHeaderOffset
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
            return 'ROUND_UP_FOR_ALLOCATION(%s)' % (
                name_signed(value.basesize, db))
        elif isinstance(value, CDefinedIntSymbolic):
            return str(value.expr)
        elif isinstance(value, ComputedIntSymbolic):
            value = value.compute_fn()
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
        return repr(value)

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
        return '%d' % ord(value)

def name_bool(value, db):
    return '%d' % value

def name_void(value, db):
    return '/* nothing */'

def name_unichar(value, db):
    assert type(value) is unicode and len(value) == 1
    return '%d' % ord(value)

def name_address(value, db):
    if value:
        return db.get(value.ref())
    else:
        return 'NULL'

# On 64 bit machines, SignedLongLong and Signed are the same, so the
# order matters, because we want the Signed implementation.
PrimitiveName = {
    SignedLongLong:   name_signedlonglong,
    Signed:   name_signed,
    UnsignedLongLong: name_unsignedlonglong,
    Unsigned: name_unsigned,
    Float:    name_float,
    SingleFloat: name_singlefloat,
    Char:     name_char,
    UniChar:  name_unichar,
    Bool:     name_bool,
    Void:     name_void,
    Address:  name_address,
    }

PrimitiveType = {
    SignedLongLong:   'long long @',
    Signed:   'long @',
    UnsignedLongLong: 'unsigned long long @',
    Unsigned: 'unsigned long @',
    Float:    'double @',
    SingleFloat: 'float @',
    Char:     'char @',
    UniChar:  'unsigned int @',
    Bool:     'bool_t @',
    Void:     'void @',
    Address:  'void* @',
    }

def define_c_primitive(ll_type, c_name):
    if ll_type in PrimitiveName:
        return
    if ll_type._cast(-1) > 0:
        name_str = '((%s) %%dULL)' % c_name
    else:
        name_str = '((%s) %%dLL)' % c_name
    PrimitiveName[ll_type] = lambda value, db: name_str % value
    PrimitiveType[ll_type] = '%s @'% c_name
    
for ll_type, c_name in [(rffi.SIGNEDCHAR, 'signed char'),
                        (rffi.UCHAR, 'unsigned char'),
                        (rffi.SHORT, 'short'),
                        (rffi.USHORT, 'unsigned short'),
                        (rffi.INT, 'int'),
                        (rffi.UINT, 'unsigned int'),
                        (rffi.LONG, 'long'),
                        (rffi.ULONG, 'unsigned long'),
                        (rffi.LONGLONG, 'long long'),
                        (rffi.ULONGLONG, 'unsigned long long')]:
    define_c_primitive(ll_type, c_name)
