import sys
from pypy.rpython.lltype import *

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

def name_float(value):
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
    

PrimitiveName = {
    Signed:   name_signed,
    Unsigned: name_unsigned,
    Float:    name_float,
    Char:     name_char,
    UniChar:  name_unichar,
    Bool:     name_bool,
    Void:     name_void,
    }

PrimitiveType = {
    Signed:   'long @',
    Unsigned: 'unsigned long @',
    Float:    'double @',
    Char:     'char @',
    UniChar:  'Py_UCS4 @',
    Bool:     'char @',
    Void:     'void @',
    }

PrimitiveErrorValue = {
    Signed:   '-1',
    Unsigned: '((unsigned) -1)',
    Float:    '-1.0',
    Char:     '((char) -1)',
    UniChar:  '((Py_UCS4) -1)',
    Bool:     '((char) -1)',
    Void:     '/* error */',
    }
