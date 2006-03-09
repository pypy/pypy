import sys
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.lltypesystem.llmemory import Address, fakeaddress, \
     AddressOffset, ItemOffset, ArrayItemsOffset, FieldOffset, \
     CompositeOffset, ArrayLengthOffset
from pypy.rpython.memory.gc import GCHeaderOffset
from pypy.rpython.memory.lladdress import NULL

# ____________________________________________________________
#
# Primitives

def name_signed(value, db):
    if isinstance(value, Symbolic):
        from pypy.translator.c.gc import REFCOUNT_IMMORTAL
        if isinstance(value, FieldOffset):
            structnode = db.gettypedefnode(value.TYPE)
            return 'offsetof(%s, %s)'%(
                db.gettype(value.TYPE).replace('@', ''),
                structnode.c_struct_field_name(value.fldname))
        elif isinstance(value, ItemOffset):
            return '(sizeof(%s) * %s)'%(
                db.gettype(value.TYPE).replace('@', ''), value.repeat)
        elif isinstance(value, ArrayItemsOffset):
            return 'offsetof(%s, items)'%(
                db.gettype(value.TYPE).replace('@', ''))
        elif isinstance(value, ArrayLengthOffset):
            return 'offsetof(%s, length)'%(
                db.gettype(value.TYPE).replace('@', ''))
        elif isinstance(value, CompositeOffset):
            return '%s + %s' % (name_signed(value.first, db), name_signed(value.second, db))
        elif type(value) == AddressOffset:
            return '0'
        elif type(value) == GCHeaderOffset:
            return '0'
        elif type(value) == REFCOUNT_IMMORTAL:
            return 'REFCOUNT_IMMORTAL'
        else:
            raise Exception("unimplemented symbolic %r"%value)
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
    return '%dLL' % value

def isinf(x):
    return x != 0.0 and x / 2 == x

def name_float(value, db):
    if isinf(value):
        if value > 0:
            return '(Py_HUGE_VAL)'
        else:
            return '(-Py_HUGE_VAL)'
    else:
        return repr(value)

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
    if value is NULL:
        return 'NULL'
    assert isinstance(value, fakeaddress)
    if value.offset is None:
        if value.ob is None:
            return 'NULL'
        else:
            if isinstance(typeOf(value.ob), ContainerType):
                return db.getcontainernode(value.ob).ptrname
            else:
                return db.get(value.ob)
    else:
        assert value.offset is not None
        if isinstance(typeOf(value.ob), ContainerType):
            base = db.getcontainernode(value.ob).ptrname
        else:
            base = db.get(value.ob)
        
        return '(void*)(((char*)(%s)) + (%s))'%(base, db.get(value.offset))

PrimitiveName = {
    Signed:   name_signed,
    SignedLongLong:   name_signedlonglong,
    Unsigned: name_unsigned,
    UnsignedLongLong: name_unsignedlonglong,
    Float:    name_float,
    Char:     name_char,
    UniChar:  name_unichar,
    Bool:     name_bool,
    Void:     name_void,
    Address:  name_address,
    }

PrimitiveType = {
    Signed:   'long @',
    SignedLongLong:   'long long @',
    Unsigned: 'unsigned long @',
    UnsignedLongLong: 'unsigned long long @',
    Float:    'double @',
    Char:     'char @',
    UniChar:  'unsigned int @',
    Bool:     'char @',
    Void:     'void @',
    Address:  'void* @',
    }

PrimitiveErrorValue = {
    Signed:   '-1',
    SignedLongLong:   '-1LL',
    Unsigned: '((unsigned) -1)',
    UnsignedLongLong: '((unsigned long long) -1)',
    Float:    '-1.0',
    Char:     '((char) -1)',
    UniChar:  '((unsigned) -1)',
    Bool:     '((char) -1)',
    Void:     '/* error */',
    Address:  'NULL',
    }
