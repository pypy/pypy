'''Operator interface.

This module exports a set of operators as functions. E.g. operator.add(x,y) is
equivalent to x+y.
'''
import __builtin__

def abs(obj,):
    'abs(a) -- Same as abs(a).'
    return __builtin__.abs(obj)
__abs__ = abs
def add(obj1, obj2):
    'add(a, b) -- Same as a + b.'
    return obj1 + obj2
__add__ = add
def and_(obj1,obj2):
    'and_(a, b) -- Same as a & b.'
    return obj1 & obj2
__and__ = and_
def attrgetter(attr):
    def f(obj):
        return getattr(obj, attr)
    return f
def concat(obj1, obj2):
    'concat(a, b) -- Same as a + b, for a and b sequences.'
    return obj1 + obj2  # XXX cPython only works on types with sequence api
                        # we support any with __add__
__concat__ = concat

def contains(obj1,obj2):
    'contains(a, b) -- Same as b in a (note reversed operands).'
    return obj2 in obj1 
__contains__ = contains
def countOf(a,b): 
    'countOf(a, b) -- Return the number of times b occurs in a.'
    count = 0
    for x in a:
        if x == b:
            count += 1
    return count
def delitem(obj, key):
    'delitem(a, b) -- Same as del a[b].'
    del obj[key]
__delitem__ = delitem
def delslice(obj, start, end):
    'delslice(a, b, c) -- Same as del a[b:c].'
    if not isinstance(start, int) or not isinstance(end, int):
        raise TypeError("an integer is expected")
    del obj[start:end]
__delslice__ = delslice
def div(a,b):
    'div(a, b) -- Same as a / b when __future__.division is not in effect.'
    return a / b
__div__ = div
def eq(a, b):
    'eq(a, b) -- Same as a==b.'
    return a == b 
__eq__ = eq
def floordiv(a, b):
    'floordiv(a, b) -- Same as a // b.'
    return a // b 
__floordiv__ = floordiv
def ge(a, b):
    'ge(a, b) -- Same as a>=b.'
    return a >= b
__ge__ = ge
def getitem(a, b):
    'getitem(a, b) -- Same as a[b].'
    return a[b] 
__getitem__ = getitem
def getslice(a, start, end):
    'getslice(a, b, c) -- Same as a[b:c].'
    if not isinstance(start, int) or not isinstance(end, int):
        raise TypeError("an integer is expected")
    return a[start:end] 
__getslice__ = getslice
def gt(a,b):
    'gt(a, b) -- Same as a>b.'
    return a > b
__gt__ = gt
def indexOf(a, b):
    'indexOf(a, b) -- Return the first index of b in a.'
    index = 0
    for x in a:
        if x == b:
            return index
        index += 1
    raise ValueError, 'sequence.index(x): x not in sequence'
def inv(obj,):
    'inv(a) -- Same as ~a.'
    return ~obj 
__inv__ = inv
def invert(obj,):
    'invert(a) -- Same as ~a.'
    return ~obj 
__invert__ = invert
def isCallable(obj,):
    'isCallable(a) -- Same as callable(a).'
    return callable(obj) 

# XXX the following is approximative
def isMappingType(obj,):
    'isMappingType(a) -- Return True if a has a mapping type, False otherwise.'
    return hasattr(obj, '__getitem__') and hasattr(obj, 'keys')
def isNumberType(obj,):
    'isNumberType(a) -- Return True if a has a numeric type, False otherwise.'
    return hasattr(obj, '__int__') or hasattr(obj, '__float__') 
def isSequenceType(obj,):
    'isSequenceType(a) -- Return True if a has a sequence type, False otherwise.'
    return hasattr(obj, '__getitem__')

def is_(a, b):
    'is_(a, b) -- Same as a is b.'
    return a is b 
def is_not(a, b):
    'is_not(a, b) -- Same as a is not b.'
    return a is not b 
def itemgetter(idx):
    def f(obj):
        return obj[idx]
    return f
def le(a, b):
    'le(a, b) -- Same as a<=b.'
    return a <= b 
__le__ = le
def lshift(a, b):
    'lshift(a, b) -- Same as a << b.'
    return a << b 
__lshift__ = lshift
def lt(a, b):
    'lt(a, b) -- Same as a<b.'
    return a < b 
__lt__ = lt
def mod(a, b):
    'mod(a, b) -- Same as a % b.'
    return a % b 
__mod__ = mod
def mul(a, b):
    'mul(a, b) -- Same as a * b.'
    return a * b 
__mul__ = mul
def ne(a, b):
    'ne(a, b) -- Same as a!=b.'
    return a != b 
__ne__ = ne
def neg(obj,):
    'neg(a) -- Same as -a.'
    return -obj
__neg__ = neg
def not_(obj,):
    'not_(a) -- Same as not a.'
    return not obj
__not__ = not_

def or_(a, b):
    'or_(a, b) -- Same as a | b.'
    return a | b 
__or__ = or_
def pos(obj,):
    'pos(a) -- Same as +a.'
    return +obj 
__pos__ = pos
def pow(a, b):
    'pow(a, b) -- Same as a**b.'
    return a ** b
__pow__ = pow
def repeat(obj, num):
    'repeat(a, b) -- Return a * b, where a is a sequence, and b is an integer.'
    if not isinstance(num, (int, long)):
        raise TypeError, 'an integer is required'
    return obj * num   # XXX cPython only supports objects with the sequence
                       # protocol. We support any with a __mul__
__repeat__ = repeat

def rshift(a, b):
    'rshift(a, b) -- Same as a >> b.'
    return a >> b 
__rshift__ = rshift
def sequenceIncludes(a, b):
    'sequenceIncludes(a, b) -- Same as b in a (note reversed operands; deprecated).'
    for x in a:
        if x == b:
            return True
    return False
def setitem(obj, key, value):
    'setitem(a, b, c) -- Same as a[b] = c.'
    obj[key] = value 
__setitem__ = setitem
def setslice(a, b, c, d):
    'setslice(a, b, c, d) -- Same as a[b:c] = d.'
    a[b:c] = d 
__setslice__ = setslice
def sub(a, b):
    'sub(a, b) -- Same as a - b.'
    return a - b 
__sub__ = sub

exec """from __future__ import division
def truediv(a, b):
    'truediv(a, b) -- Same as a / b when __future__.division is in effect.'
    return a / b 
"""
__truediv__ = truediv
def truth(a,):
    'truth(a) -- Return True if a is true, False otherwise.'
    return not not a 
def xor(a, b):
    'xor(a, b) -- Same as a ^ b.'
    return a ^ b 
__xor__ = xor
