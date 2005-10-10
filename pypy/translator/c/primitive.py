import sys
from pypy.rpython.lltype import *
from pypy.rpython.memory.lladdress import Address, NULL

# ____________________________________________________________
#
# Primitives

def name_signed(value):
    if value == -sys.maxint-1:   # blame C
        return '(-%dL-1L)' % sys.maxint
    else:
        return '%dL' % value

def name_unsigned(value):
    assert value >= 0
    return '%dUL' % value

def isinf(x):
    return x != 0.0 and x / 2 == x

def name_float(value):
    if isinf(value):
        if value > 0:
            return '(Py_HUGE_VAL)'
        else:
            return '(-Py_HUGE_VAL)'
    else:
        return repr(value)

def name_char(value):
    assert type(value) is str and len(value) == 1
    if ' ' <= value < '\x7f':
        return "'%s'" % (value.replace("\\", r"\\").replace("'", r"\'"),)
    else:
        return '%d' % ord(value)

def name_bool(value):
    return '%d' % value

def name_void(value):
    return '/* nothing */'

def name_unichar(value):
    assert type(value) is unicode and len(value) == 1
    return '%d' % ord(value)

def name_address(value):
    assert value == NULL
    return 'NULL' 


PrimitiveName = {
    Signed:   name_signed,
    Unsigned: name_unsigned,
    Float:    name_float,
    Char:     name_char,
    UniChar:  name_unichar,
    Bool:     name_bool,
    Void:     name_void,
    Address:  name_address,
    }

PrimitiveType = {
    Signed:   'long @',
    Unsigned: 'unsigned long @',
    Float:    'double @',
    Char:     'char @',
    UniChar:  'unsigned int @',
    Bool:     'char @',
    Void:     'void @',
    Address:  'void* @',
    }

PrimitiveErrorValue = {
    Signed:   '-1',
    Unsigned: '((unsigned) -1)',
    Float:    '-1.0',
    Char:     '((char) -1)',
    UniChar:  '((unsigned) -1)',
    Bool:     '((char) -1)',
    Void:     '/* error */',
    Address:  'NULL',
    }
