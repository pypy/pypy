from pypy.rpython.lltypes import *

# ____________________________________________________________
#
# Primitives

def name_signed(value):
    return '%d' % value

def name_unsigned(value):
    assert value >= 0
    return '%d' % value

def name_char(value):
    value = value
    assert type(value) is str and len(value) == 1
    if ' ' <= value < '\x7f':
        return "'%s'" % (value.replace("'", r"\'"),)
    else:
        return '%d' % ord(value)

def name_bool(value):
    return '%d' % value

def name_void(value):
    return '/* nothing */'

PrimitiveName = {
    Signed:   name_signed,
    Unsigned: name_unsigned,
    Char:     name_char,
    Bool:     name_bool,
    Void:     name_void,
    }

PrimitiveType = {
    Signed:   'long @',
    Unsigned: 'unsigned long @',
    Char:     'char @',
    Bool:     'char @',
    Void:     'void @',
    }

PrimitiveErrorValue = {
    Signed:   '-1',
    Unsigned: '((unsigned) -1)',
    Char:     '((char) -1)',
    Bool:     '((char) -1)',
    Void:     '/* error */',
    }
