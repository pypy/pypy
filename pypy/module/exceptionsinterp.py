#!/bin/env python
# -*- coding: LATIN-1 -*-

"""Python's standard exception class hierarchy.

Before Python 1.5, the standard exceptions were all simple string objects.
In Python 1.5, the standard exceptions were converted to classes organized
into a relatively flat hierarchy.  String-based standard exceptions were
optional, or used as a fallback if some problem occurred while importing
the exception module.  With Python 1.6, optional string-based standard
exceptions were removed (along with the -X command line flag).

The class exceptions were implemented in such a way as to be almost
completely backward compatible.  Some tricky uses of IOError could
potentially have broken, but by Python 1.6, all of these should have
been fixed.  As of Python 1.6, the class-based standard exceptions are
now implemented in C, and are guaranteed to exist in the Python
interpreter.

Here is a rundown of the class hierarchy.  The classes found here are
inserted into both the exceptions module and the `built-in' module.  It is
recommended that user defined class based exceptions be derived from the
`Exception' class, although this is currently not enforced.

Exception
 |
 +-- SystemExit
 +-- TaskletExit
 +-- StopIteration
 +-- StandardError
 |    |
 |    +-- KeyboardInterrupt
 |    +-- ImportError
 |    +-- EnvironmentError
 |    |    |
 |    |    +-- IOError
 |    |    +-- OSError
 |    |         |
 |    |         +-- WindowsError
 |    |         +-- VMSError
 |    |
 |    +-- EOFError
 |    +-- RuntimeError
 |    |    |
 |    |    +-- NotImplementedError
 |    |
 |    +-- NameError
 |    |    |
 |    |    +-- UnboundLocalError
 |    |
 |    +-- AttributeError
 |    +-- SyntaxError
 |    |    |
 |    |    +-- IndentationError
 |    |         |
 |    |         +-- TabError
 |    |
 |    +-- TypeError
 |    +-- AssertionError
 |    +-- LookupError
 |    |    |
 |    |    +-- IndexError
 |    |    +-- KeyError
 |    |
 |    +-- ArithmeticError
 |    |    |
 |    |    +-- OverflowError
 |    |    +-- ZeroDivisionError
 |    |    +-- FloatingPointError
 |    |
 |    +-- ValueError
 |    |    |
 |    |    +-- UnicodeError
 |    |        |
 |    |        +-- UnicodeEncodeError
 |    |        +-- UnicodeDecodeError
 |    |        +-- UnicodeTranslateError
 |    |
 |    +-- ReferenceError
 |    +-- SystemError
 |    +-- MemoryError
 |
 +---Warning
      |
      +-- UserWarning
      +-- DeprecationWarning
      +-- PendingDeprecationWarning
      +-- SyntaxWarning
      +-- OverflowWarning
      +-- RuntimeWarning
      +-- FutureWarning"""

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__getitem__'
## firstlineno 94
##SECTION##
def __getitem__(space, *args_w):
    kwlist = ["self", "idx"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__getitem__"
    w_self, w_idx = PyArg_ParseMini(space, funcname, 2, 2, _args_w, defaults_w)
    return fastf_Exception___getitem__(space, w_self, w_idx)
f_Exception___getitem__ = globals().pop("__getitem__")

def __getitem__(space, w_self, w_idx):

    w_0=w_2=w_4=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_args)
            w_2 = space.getitem(w_0, w_idx)
            w_4 = w_2
            goto = 2

        if goto == 2:
            return w_4
fastf_Exception___getitem__ = globals().pop("__getitem__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__init__'
## firstlineno 98
##SECTION##
def __init__(space, *args_w):
    kwlist = ["self"]
    w_args = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_Exception___init__(space, w_self, w_args)
f_Exception___init__ = globals().pop("__init__")

def __init__(space, w_self, w_args):

    w_0=w_3=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.setattr(w_self, gs_args, w_args)
            w_3 = space.w_None
            goto = 2

        if goto == 2:
            return w_3
fastf_Exception___init__ = globals().pop("__init__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__str__'
## firstlineno 102
##SECTION##
# global declarations
# global object gs_args
# global object gi_0
# global object gi_1

def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_Exception___str__(space, w_self)
f_Exception___str__ = globals().pop("__str__")

def __str__(space, w_self):

    w_args=w_argc=w_3=v4=w_args_1=w_argc_1=w_6=v7=w_args_3=w_10=w_5=None
    w_args_2=w_8=w_9=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_args = space.getattr(w_self, gs_args)
            w_argc = space.len(w_args)
            w_3 = space.eq(w_argc, gi_0)
            v4 = space.is_true(w_3)
            if v4 == True:
                w_5 = gs__emptystr_
                goto = 5
            else:
                assert v4 == False
                w_args_1, w_argc_1 = w_args, w_argc
                goto = 2

        if goto == 2:
            w_6 = space.eq(w_argc_1, gi_1)
            v7 = space.is_true(w_6)
            if v7 == True:
                w_args_2 = w_args_1
                goto = 3
            else:
                assert v7 == False
                w_args_3 = w_args_1
                goto = 4

        if goto == 3:
            w_8 = space.getitem(w_args_2, gi_0)
            _tup = space.newtuple([w_8])
            w_9 = space.call(space.w_str, _tup)
            w_5 = w_9
            goto = 5

        if goto == 4:
            _tup = space.newtuple([w_args_3])
            w_10 = space.call(space.w_str, _tup)
            w_5 = w_10
            goto = 5

        if goto == 5:
            return w_5
fastf_Exception___str__ = globals().pop("__str__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__init__'
## firstlineno 131
##SECTION##
# global declarations
# global object gi_4
# global object gi_2
# global object gi_3

def __init__(space, *args_w):
    kwlist = ["self"]
    w_args = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeTranslateError___init__(space, w_self, w_args)
f_UnicodeTranslateError___init__ = globals().pop("__init__")

def __init__(space, w_self, w_args):

    w_argc=w_2=w_4=v5=w_6=w_self_1=w_args_1=w_7=w_8=w_9=w_10=w_11=None
    w_12=w_13=w_14=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc = space.len(w_args)
            w_2 = space.setattr(w_self, gs_args, w_args)
            w_4 = space.eq(w_argc, gi_4)
            v5 = space.is_true(w_4)
            if v5 == True:
                w_self_1, w_args_1 = w_self, w_args
                goto = 2
            else:
                assert v5 == False
                w_6 = space.w_None
                goto = 3

        if goto == 2:
            w_7 = space.getitem(w_args_1, gi_0)
            w_8 = space.setattr(w_self_1, gs_object, w_7)
            w_9 = space.getitem(w_args_1, gi_1)
            w_10 = space.setattr(w_self_1, gs_start, w_9)
            w_11 = space.getitem(w_args_1, gi_2)
            w_12 = space.setattr(w_self_1, gs_end, w_11)
            w_13 = space.getitem(w_args_1, gi_3)
            w_14 = space.setattr(w_self_1, gs_reason, w_13)
            w_6 = space.w_None
            goto = 3

        if goto == 3:
            return w_6
fastf_UnicodeTranslateError___init__ = globals().pop("__init__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__str__'
## firstlineno 141
##SECTION##
# global declarations
# global object gs_start
# global object gs_start_
# global object gs_reason
# global object gs_reason_
# global object gs_args_
# global object gs_end
# global object gs_end_
# global object gs_object
# global object gs_object_
# global object gbltinmethod_join
# global object gs__
# global object gs_join

def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeTranslateError___str__(space, w_self)
f_UnicodeTranslateError___str__ = globals().pop("__str__")

def __str__(space, w_self):

    w_0=w_2=w_3=w_4=w_5=w_6=w_7=w_8=w_9=w_10=w_11=w_12=w_13=w_14=None
    w_15=w_16=w_res=w_18=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_start, space.w_None)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_start_, w_2)
            w_4 = space.getattr(w_self, gs_reason, space.w_None)
            _tup = space.newtuple([w_4])
            w_5 = space.call(space.w_str, _tup)
            w_6 = space.add(gs_reason_, w_5)
            w_7 = space.getattr(w_self, gs_args, space.w_None)
            _tup = space.newtuple([w_7])
            w_8 = space.call(space.w_str, _tup)
            w_9 = space.add(gs_args_, w_8)
            w_10 = space.getattr(w_self, gs_end, space.w_None)
            _tup = space.newtuple([w_10])
            w_11 = space.call(space.w_str, _tup)
            w_12 = space.add(gs_end_, w_11)
            w_13 = space.getattr(w_self, gs_object, space.w_None)
            _tup = space.newtuple([w_13])
            w_14 = space.call(space.w_str, _tup)
            w_15 = space.add(gs_object_, w_14)
            w_16 = space.newlist([w_3, w_6, w_9, w_12, w_15])
            _tup = space.newtuple([w_16])
            w_res = space.call(gbltinmethod_join, _tup)
            w_18 = w_res
            goto = 2

        if goto == 2:
            return w_18
fastf_UnicodeTranslateError___str__ = globals().pop("__str__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__str__'
## firstlineno 159
##SECTION##
def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_KeyError___str__(space, w_self)
f_KeyError___str__ = globals().pop("__str__")

def __str__(space, w_self):

    w_args=w_argc=w_3=v4=w_args_1=w_argc_1=w_6=v7=w_args_3=w_10=w_5=None
    w_args_2=w_8=w_9=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_args = space.getattr(w_self, gs_args)
            w_argc = space.len(w_args)
            w_3 = space.eq(w_argc, gi_0)
            v4 = space.is_true(w_3)
            if v4 == True:
                w_5 = gs__emptystr_
                goto = 5
            else:
                assert v4 == False
                w_args_1, w_argc_1 = w_args, w_argc
                goto = 2

        if goto == 2:
            w_6 = space.eq(w_argc_1, gi_1)
            v7 = space.is_true(w_6)
            if v7 == True:
                w_args_2 = w_args_1
                goto = 3
            else:
                assert v7 == False
                w_args_3 = w_args_1
                goto = 4

        if goto == 3:
            w_8 = space.getitem(w_args_2, gi_0)
            w_9 = space.repr(w_8)
            w_5 = w_9
            goto = 5

        if goto == 4:
            _tup = space.newtuple([w_args_3])
            w_10 = space.call(space.w_str, _tup)
            w_5 = w_10
            goto = 5

        if goto == 5:
            return w_5
fastf_KeyError___str__ = globals().pop("__str__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__init__'
## firstlineno 185
##SECTION##
def __init__(space, *args_w):
    kwlist = ["self"]
    w_args = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_EnvironmentError___init__(space, w_self, w_args)
f_EnvironmentError___init__ = globals().pop("__init__")

def __init__(space, w_self, w_args):

    w_argc=w_2=w_4=w_5=w_6=w_7=v8=w_self_2=w_args_2=w_argc_2=w_9=None
    v11=w_self_4=w_args_4=w_argc_4=w_16=v17=w_18=w_self_5=w_args_5=None
    w_19=w_20=w_21=w_22=w_23=w_24=w_self_3=w_args_3=w_argc_3=w_12=None
    w_13=w_14=w_15=w_self_1=w_args_1=w_argc_1=w_10=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc = space.len(w_args)
            w_2 = space.setattr(w_self, gs_args, w_args)
            w_4 = space.setattr(w_self, gs_errno, space.w_None)
            w_5 = space.setattr(w_self, gs_strerror, space.w_None)
            w_6 = space.setattr(w_self, gs_filename, space.w_None)
            w_7 = space.le(gi_2, w_argc)
            v8 = space.is_true(w_7)
            if v8 == True:
                w_self_1, w_args_1, w_argc_1 = w_self, w_args, w_argc
                goto = 2
            else:
                assert v8 == False
                w_self_2, w_args_2, w_argc_2, w_9 = w_self, w_args, w_argc, w_7
                goto = 3

        if goto == 2:
            w_10 = space.le(w_argc_1, gi_3)
            (w_self_2, w_args_2, w_argc_2, w_9) = (w_self_1, w_args_1,
             w_argc_1, w_10)
            goto = 3

        if goto == 3:
            v11 = space.is_true(w_9)
            if v11 == True:
                w_self_3, w_args_3, w_argc_3 = w_self_2, w_args_2, w_argc_2
                goto = 4
            else:
                assert v11 == False
                w_self_4, w_args_4, w_argc_4 = w_self_2, w_args_2, w_argc_2
                goto = 5

        if goto == 4:
            w_12 = space.getitem(w_args_3, gi_0)
            w_13 = space.setattr(w_self_3, gs_errno, w_12)
            w_14 = space.getitem(w_args_3, gi_1)
            w_15 = space.setattr(w_self_3, gs_strerror, w_14)
            w_self_4, w_args_4, w_argc_4 = w_self_3, w_args_3, w_argc_3
            goto = 5

        if goto == 5:
            w_16 = space.eq(w_argc_4, gi_3)
            v17 = space.is_true(w_16)
            if v17 == True:
                w_self_5, w_args_5 = w_self_4, w_args_4
                goto = 6
            else:
                assert v17 == False
                w_18 = space.w_None
                goto = 7

        if goto == 6:
            w_19 = space.getitem(w_args_5, gi_2)
            w_20 = space.setattr(w_self_5, gs_filename, w_19)
            w_21 = space.getitem(w_args_5, gi_0)
            w_22 = space.getitem(w_args_5, gi_1)
            w_23 = space.newtuple([w_21, w_22])
            w_24 = space.setattr(w_self_5, gs_args, w_23)
            w_18 = space.w_None
            goto = 7

        if goto == 7:
            return w_18
fastf_EnvironmentError___init__ = globals().pop("__init__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__str__'
## firstlineno 199
##SECTION##
# global declarations
# global object gs_errno
# global object gs_errno_
# global object gs_strerror
# global object gs_strerror_
# global object gs_filename_

def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_EnvironmentError___str__(space, w_self)
f_EnvironmentError___str__ = globals().pop("__str__")

def __str__(space, w_self):

    w_0=w_2=w_3=w_4=w_5=w_6=w_7=w_8=w_9=w_10=w_11=w_12=w_13=w_res=None
    w_15=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_errno, space.w_None)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_errno_, w_2)
            w_4 = space.getattr(w_self, gs_args, space.w_None)
            _tup = space.newtuple([w_4])
            w_5 = space.call(space.w_str, _tup)
            w_6 = space.add(gs_args_, w_5)
            w_7 = space.getattr(w_self, gs_strerror, space.w_None)
            _tup = space.newtuple([w_7])
            w_8 = space.call(space.w_str, _tup)
            w_9 = space.add(gs_strerror_, w_8)
            w_10 = space.getattr(w_self, gs_filename, space.w_None)
            _tup = space.newtuple([w_10])
            w_11 = space.call(space.w_str, _tup)
            w_12 = space.add(gs_filename_, w_11)
            w_13 = space.newlist([w_3, w_6, w_9, w_12])
            _tup = space.newtuple([w_13])
            w_res = space.call(gbltinmethod_join, _tup)
            w_15 = w_res
            goto = 2

        if goto == 2:
            return w_15
fastf_EnvironmentError___str__ = globals().pop("__str__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__init__'
## firstlineno 219
##SECTION##
# global declaration
# global object gi_5

def __init__(space, *args_w):
    kwlist = ["self"]
    w_args = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeEncodeError___init__(space, w_self, w_args)
f_UnicodeEncodeError___init__ = globals().pop("__init__")

def __init__(space, w_self, w_args):

    w_argc=w_2=w_4=v5=w_6=w_self_1=w_args_1=w_7=w_8=w_9=w_10=w_11=None
    w_12=w_13=w_14=w_15=w_16=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc = space.len(w_args)
            w_2 = space.setattr(w_self, gs_args, w_args)
            w_4 = space.eq(w_argc, gi_5)
            v5 = space.is_true(w_4)
            if v5 == True:
                w_self_1, w_args_1 = w_self, w_args
                goto = 2
            else:
                assert v5 == False
                w_6 = space.w_None
                goto = 3

        if goto == 2:
            w_7 = space.getitem(w_args_1, gi_0)
            w_8 = space.setattr(w_self_1, gs_encoding, w_7)
            w_9 = space.getitem(w_args_1, gi_1)
            w_10 = space.setattr(w_self_1, gs_object, w_9)
            w_11 = space.getitem(w_args_1, gi_2)
            w_12 = space.setattr(w_self_1, gs_start, w_11)
            w_13 = space.getitem(w_args_1, gi_3)
            w_14 = space.setattr(w_self_1, gs_end, w_13)
            w_15 = space.getitem(w_args_1, gi_4)
            w_16 = space.setattr(w_self_1, gs_reason, w_15)
            w_6 = space.w_None
            goto = 3

        if goto == 3:
            return w_6
fastf_UnicodeEncodeError___init__ = globals().pop("__init__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__str__'
## firstlineno 230
##SECTION##
# global declarations
# global object gs_encoding
# global object gs_encoding_

def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeEncodeError___str__(space, w_self)
f_UnicodeEncodeError___str__ = globals().pop("__str__")

def __str__(space, w_self):

    w_0=w_2=w_3=w_4=w_5=w_6=w_7=w_8=w_9=w_10=w_11=w_12=w_13=w_14=None
    w_15=w_16=w_17=w_18=w_19=w_res=w_21=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_object, space.w_None)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_object_, w_2)
            w_4 = space.getattr(w_self, gs_end, space.w_None)
            _tup = space.newtuple([w_4])
            w_5 = space.call(space.w_str, _tup)
            w_6 = space.add(gs_end_, w_5)
            w_7 = space.getattr(w_self, gs_encoding, space.w_None)
            _tup = space.newtuple([w_7])
            w_8 = space.call(space.w_str, _tup)
            w_9 = space.add(gs_encoding_, w_8)
            w_10 = space.getattr(w_self, gs_args, space.w_None)
            _tup = space.newtuple([w_10])
            w_11 = space.call(space.w_str, _tup)
            w_12 = space.add(gs_args_, w_11)
            w_13 = space.getattr(w_self, gs_start, space.w_None)
            _tup = space.newtuple([w_13])
            w_14 = space.call(space.w_str, _tup)
            w_15 = space.add(gs_start_, w_14)
            w_16 = space.getattr(w_self, gs_reason, space.w_None)
            _tup = space.newtuple([w_16])
            w_17 = space.call(space.w_str, _tup)
            w_18 = space.add(gs_reason_, w_17)
            w_19 = space.newlist([w_3, w_6, w_9, w_12, w_15, w_18])
            _tup = space.newtuple([w_19])
            w_res = space.call(gbltinmethod_join, _tup)
            w_21 = w_res
            goto = 2

        if goto == 2:
            return w_21
fastf_UnicodeEncodeError___str__ = globals().pop("__str__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__init__'
## firstlineno 270
##SECTION##
def __init__(space, *args_w):
    kwlist = ["self"]
    w_args = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_SyntaxError___init__(space, w_self, w_args)
f_SyntaxError___init__ = globals().pop("__init__")

def __init__(space, w_self, w_args):

    w_argc=w_2=w_4=v5=w_self_2=w_args_2=w_argc_2=w_8=v9=w_10=w_self_3=None
    w_args_3=w_11=w_12=w_13=w_14=w_15=w_16=w_17=w_18=w_19=w_20=w_21=None
    w_22=w_self_1=w_args_1=w_argc_1=w_6=w_7=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc = space.len(w_args)
            w_2 = space.setattr(w_self, gs_args, w_args)
            w_4 = space.ge(w_argc, gi_1)
            v5 = space.is_true(w_4)
            if v5 == True:
                w_self_1, w_args_1, w_argc_1 = w_self, w_args, w_argc
                goto = 2
            else:
                assert v5 == False
                w_self_2, w_args_2, w_argc_2 = w_self, w_args, w_argc
                goto = 3

        if goto == 2:
            w_6 = space.getitem(w_args_1, gi_0)
            w_7 = space.setattr(w_self_1, gs_msg, w_6)
            w_self_2, w_args_2, w_argc_2 = w_self_1, w_args_1, w_argc_1
            goto = 3

        if goto == 3:
            w_8 = space.eq(w_argc_2, gi_2)
            v9 = space.is_true(w_8)
            if v9 == True:
                w_self_3, w_args_3 = w_self_2, w_args_2
                goto = 4
            else:
                assert v9 == False
                w_10 = space.w_None
                goto = 5

        if goto == 4:
            w_11 = space.getitem(w_args_3, gi_1)
            w_12 = space.getitem(w_11, gi_0)
            w_13 = space.setattr(w_self_3, gs_filename, w_12)
            w_14 = space.getitem(w_args_3, gi_1)
            w_15 = space.getitem(w_14, gi_1)
            w_16 = space.setattr(w_self_3, gs_lineno, w_15)
            w_17 = space.getitem(w_args_3, gi_1)
            w_18 = space.getitem(w_17, gi_2)
            w_19 = space.setattr(w_self_3, gs_offset, w_18)
            w_20 = space.getitem(w_args_3, gi_1)
            w_21 = space.getitem(w_20, gi_3)
            w_22 = space.setattr(w_self_3, gs_text, w_21)
            w_10 = space.w_None
            goto = 5

        if goto == 5:
            return w_10
fastf_SyntaxError___init__ = globals().pop("__init__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__str__'
## firstlineno 282
##SECTION##
def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_SyntaxError___str__(space, w_self)
f_SyntaxError___str__ = globals().pop("__str__")

def __str__(space, w_self):

    w_0=w_2=w_3=w_4=w_res=w_6=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_args, space.w_None)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_args_, w_2)
            w_4 = space.newlist([w_3])
            _tup = space.newtuple([w_4])
            w_res = space.call(gbltinmethod_join, _tup)
            w_6 = w_res
            goto = 2

        if goto == 2:
            return w_6
fastf_SyntaxError___str__ = globals().pop("__str__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__init__'
## firstlineno 296
##SECTION##
# global declaration
# global object gs_code

def __init__(space, *args_w):
    kwlist = ["self"]
    w_args = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_SystemExit___init__(space, w_self, w_args)
f_SystemExit___init__ = globals().pop("__init__")

def __init__(space, w_self, w_args):

    w_argc=w_2=v3=w_self_2=w_args_2=w_argc_2=w_6=w_7=v8=w_self_4=None
    w_args_4=w_argc_4=w_11=v12=w_13=w_self_5=w_args_5=w_14=w_self_3=None
    w_args_3=w_argc_3=w_9=w_10=w_self_1=w_args_1=w_argc_1=w_5=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc = space.len(w_args)
            w_2 = space.eq(w_argc, gi_0)
            v3 = space.is_true(w_2)
            if v3 == True:
                w_self_1, w_args_1, w_argc_1 = w_self, w_args, w_argc
                goto = 2
            else:
                assert v3 == False
                w_self_2, w_args_2, w_argc_2 = w_self, w_args, w_argc
                goto = 3

        if goto == 2:
            w_5 = space.setattr(w_self_1, gs_code, space.w_None)
            w_self_2, w_args_2, w_argc_2 = w_self_1, w_args_1, w_argc_1
            goto = 3

        if goto == 3:
            w_6 = space.setattr(w_self_2, gs_args, w_args_2)
            w_7 = space.eq(w_argc_2, gi_1)
            v8 = space.is_true(w_7)
            if v8 == True:
                w_self_3, w_args_3, w_argc_3 = w_self_2, w_args_2, w_argc_2
                goto = 4
            else:
                assert v8 == False
                w_self_4, w_args_4, w_argc_4 = w_self_2, w_args_2, w_argc_2
                goto = 5

        if goto == 4:
            w_9 = space.getitem(w_args_3, gi_0)
            w_10 = space.setattr(w_self_3, gs_code, w_9)
            w_self_4, w_args_4, w_argc_4 = w_self_3, w_args_3, w_argc_3
            goto = 5

        if goto == 5:
            w_11 = space.ge(w_argc_4, gi_2)
            v12 = space.is_true(w_11)
            if v12 == True:
                w_self_5, w_args_5 = w_self_4, w_args_4
                goto = 6
            else:
                assert v12 == False
                w_13 = space.w_None
                goto = 7

        if goto == 6:
            w_14 = space.setattr(w_self_5, gs_code, w_args_5)
            w_13 = space.w_None
            goto = 7

        if goto == 7:
            return w_13
fastf_SystemExit___init__ = globals().pop("__init__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__init__'
## firstlineno 331
##SECTION##
def __init__(space, *args_w):
    kwlist = ["self"]
    w_args = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeDecodeError___init__(space, w_self, w_args)
f_UnicodeDecodeError___init__ = globals().pop("__init__")

def __init__(space, w_self, w_args):

    w_argc=w_2=w_4=v5=w_6=w_self_1=w_args_1=w_7=w_8=w_9=w_10=w_11=None
    w_12=w_13=w_14=w_15=w_16=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc = space.len(w_args)
            w_2 = space.setattr(w_self, gs_args, w_args)
            w_4 = space.eq(w_argc, gi_5)
            v5 = space.is_true(w_4)
            if v5 == True:
                w_self_1, w_args_1 = w_self, w_args
                goto = 2
            else:
                assert v5 == False
                w_6 = space.w_None
                goto = 3

        if goto == 2:
            w_7 = space.getitem(w_args_1, gi_0)
            w_8 = space.setattr(w_self_1, gs_encoding, w_7)
            w_9 = space.getitem(w_args_1, gi_1)
            w_10 = space.setattr(w_self_1, gs_object, w_9)
            w_11 = space.getitem(w_args_1, gi_2)
            w_12 = space.setattr(w_self_1, gs_start, w_11)
            w_13 = space.getitem(w_args_1, gi_3)
            w_14 = space.setattr(w_self_1, gs_end, w_13)
            w_15 = space.getitem(w_args_1, gi_4)
            w_16 = space.setattr(w_self_1, gs_reason, w_15)
            w_6 = space.w_None
            goto = 3

        if goto == 3:
            return w_6
fastf_UnicodeDecodeError___init__ = globals().pop("__init__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\lib\\_exceptions.py'
## function    '__str__'
## firstlineno 342
##SECTION##
def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeDecodeError___str__(space, w_self)
f_UnicodeDecodeError___str__ = globals().pop("__str__")

def __str__(space, w_self):

    w_0=w_2=w_3=w_4=w_5=w_6=w_7=w_8=w_9=w_10=w_11=w_12=w_13=w_14=None
    w_15=w_16=w_17=w_18=w_19=w_res=w_21=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_object, space.w_None)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_object_, w_2)
            w_4 = space.getattr(w_self, gs_end, space.w_None)
            _tup = space.newtuple([w_4])
            w_5 = space.call(space.w_str, _tup)
            w_6 = space.add(gs_end_, w_5)
            w_7 = space.getattr(w_self, gs_encoding, space.w_None)
            _tup = space.newtuple([w_7])
            w_8 = space.call(space.w_str, _tup)
            w_9 = space.add(gs_encoding_, w_8)
            w_10 = space.getattr(w_self, gs_args, space.w_None)
            _tup = space.newtuple([w_10])
            w_11 = space.call(space.w_str, _tup)
            w_12 = space.add(gs_args_, w_11)
            w_13 = space.getattr(w_self, gs_start, space.w_None)
            _tup = space.newtuple([w_13])
            w_14 = space.call(space.w_str, _tup)
            w_15 = space.add(gs_start_, w_14)
            w_16 = space.getattr(w_self, gs_reason, space.w_None)
            _tup = space.newtuple([w_16])
            w_17 = space.call(space.w_str, _tup)
            w_18 = space.add(gs_reason_, w_17)
            w_19 = space.newlist([w_3, w_6, w_9, w_12, w_15, w_18])
            _tup = space.newtuple([w_19])
            w_res = space.call(gbltinmethod_join, _tup)
            w_21 = w_res
            goto = 2

        if goto == 2:
            return w_21
fastf_UnicodeDecodeError___str__ = globals().pop("__str__")

##SECTION##
## filename    'D:\\pypy\\dist\\pypy\\translator\\geninterplevel.py'
## function    'test_exceptions'
## firstlineno 1261
##SECTION##
# global declarations
# global object gfunc_test_exceptions
# global object gbltinmethod_keys
# global object g47dict
# global object gs_keys

def test_exceptions(space, *args_w):
    """ enumerate all exceptions """
    kwlist = []
    _args_w = args_w
    defaults_w = ()
    funcname = "test_exceptions"
    PyArg_ParseMini(space, funcname, 0, 0, _args_w, defaults_w)
    return fastf_test_exceptions(space, )
f_test_exceptions = globals().pop("test_exceptions")

def test_exceptions(space, ):
    """ enumerate all exceptions """

    w_0=w_1=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            _tup = space.newtuple([])
            w_0 = space.call(gbltinmethod_keys, _tup)
            w_1 = w_0
            goto = 2

        if goto == 2:
            return w_1
fastf_test_exceptions = globals().pop("test_exceptions")

# global declarations
# global object gs_MemoryError
# global object gcls_MemoryError
# global object gcls_StandardError
# global object gcls_Exception
# global object gs___module__
# global object gs_exceptions
# global object gs___doc__
# global object gs_Exception
# global object gs_StandardError
# global object gs_ImportError
# global object gcls_ImportError
# global object gs_RuntimeError
# global object gcls_RuntimeError
# global object gs_UnicodeTranslateError
# global object gcls_UnicodeTranslateError
# global object gcls_UnicodeError
# global object gcls_ValueError
# global object gs_ValueError
# global object gs_UnicodeError
# global object gs_KeyError
# global object gcls_KeyError
# global object gcls_LookupError
# global object gs_LookupError
# global object gs_TaskletExit
# global object gcls_TaskletExit
# global object gcls_SystemExit
# global object gs_SystemExit
# global object gs_StopIteration
# global object gcls_StopIteration
# global object gs_PendingDeprecationWarning
# global object gcls_PendingDeprecationWarning
# global object gcls_Warning
# global object gs_Warning
# global object gs_EnvironmentError
# global object gcls_EnvironmentError
# global object gs_OSError
# global object gcls_OSError
# global object gs_DeprecationWarning
# global object gcls_DeprecationWarning
# global object gs_FloatingPointError
# global object gcls_FloatingPointError
# global object gcls_ArithmeticError
# global object gs_ArithmeticError
# global object gs_AttributeError
# global object gcls_AttributeError
# global object gs_IndentationError
# global object gcls_IndentationError
# global object gcls_SyntaxError
# global object gs_SyntaxError
# global object gs_NameError
# global object gcls_NameError
# global object gs_OverflowWarning
# global object gcls_OverflowWarning
# global object gs_IOError
# global object gcls_IOError
# global object gs_FutureWarning
# global object gcls_FutureWarning
# global object gs_ZeroDivisionError
# global object gcls_ZeroDivisionError
# global object gs_EOFError
# global object gcls_EOFError
# global object gs_TabError
# global object gcls_TabError
# global object gs_UnicodeEncodeError
# global object gcls_UnicodeEncodeError
# global object gs_UnboundLocalError
# global object gcls_UnboundLocalError
# global object gs___name__
# global object gs_ReferenceError
# global object gcls_ReferenceError
# global object gs_AssertionError
# global object gcls_AssertionError
# global object gs_UnicodeDecodeError
# global object gcls_UnicodeDecodeError
# global object gs_TypeError
# global object gcls_TypeError
# global object gs_IndexError
# global object gcls_IndexError
# global object gs_RuntimeWarning
# global object gcls_RuntimeWarning
# global object gs_KeyboardInterrupt
# global object gcls_KeyboardInterrupt
# global object gs_UserWarning
# global object gcls_UserWarning
# global object gs_SyntaxWarning
# global object gcls_SyntaxWarning
# global object gs_NotImplementedError
# global object gcls_NotImplementedError
# global object gs_SystemError
# global object gcls_SystemError
# global object gs_OverflowError
# global object gcls_OverflowError
# global object gs_WindowsError
# global object gcls_WindowsError
# global object gs___init__
# global object gfunc_UnicodeDecodeError___init__
# global object gs___str__
# global object gfunc_UnicodeDecodeError___str__
# global object gfunc_UnicodeEncodeError___init__
# global object gfunc_UnicodeEncodeError___str__
# global object gfunc_SyntaxError___init__
# global object gfunc_SyntaxError___str__
# global object gs_filename
# global object gs_lineno
# global object gs_msg
# global object gs__emptystr_
# global object gs_offset
# global object gs_print_file_and_line
# global object gs_text
# global object gfunc_EnvironmentError___init__
# global object gfunc_EnvironmentError___str__
# global object gfunc_SystemExit___init__
# global object gfunc_KeyError___str__
# global object gfunc_UnicodeTranslateError___init__
# global object gfunc_UnicodeTranslateError___str__
# global object gs___getitem__
# global object gfunc_Exception___getitem__
# global object gfunc_Exception___init__
# global object gfunc_Exception___str__

##SECTION##
#*************************************************************

def inittest_exceptions_1(space):
    """NOT_RPYTHON"""
    class m: pass # fake module
    m.__dict__ = globals()

    from pypy.interpreter.gateway import interp2app
    m.gfunc_test_exceptions = space.wrap(interp2app(f_test_exceptions))
    m.__doc__ = space.wrap(m.__doc__)
    m.g47dict = space.newdict([])
    m.gs_keys = space.wrap('keys')
    m.gbltinmethod_keys = space.getattr(g47dict, gs_keys)
    def PyArg_ParseMini(space, name, minargs, maxargs, args_w, defaults_w):
        err = None
        if len(args_w) < minargs:
            txt = "%s() takes at least %d argument%s (%d given)"
            plural = ['s', ''][minargs == 1]
            err = (name, minargs, plural, len(args_w))
        if len(args_w) > maxargs:
            plural = ['s', ''][maxargs == 1]
            if minargs == maxargs:
                if minargs == 0:
                    txt = '%s() takes no arguments (%d given)'
                    err = (name, len(args_w))
                elif minargs == 1:
                    txt = '%s() takes exactly %d argument%s (%d given)'
                    err = (name, maxargs, plural, len(args_w))
            else:
                txt = '%s() takes at most %d argument%s (%d given)'
                err = (name, maxargs, plural, len(args_w))
        if err:
            w_txt = space.wrap(txt)
            w_tup = space.wrap(err)
            w_txt = space.mod(w_txt, w_tup)
            raise OperationError(space.w_TypeError, w_txt)
    
        # finally, we create the result ;-)
        res_w = args_w + defaults_w[len(args_w) - minargs:]
        assert len(res_w) == maxargs
        return res_w
    
    m.PyArg_ParseMini = PyArg_ParseMini
    from pypy.interpreter.error import OperationError
    m.OperationError = OperationError
    m.gs_MemoryError = space.wrap('MemoryError')
    _dic = space.newdict([])
    m.gs___module__ = space.wrap('__module__')
    m.gs_exceptions = space.wrap('exceptions')
    space.setitem(_dic, gs___module__, gs_exceptions)
    m.gs___doc__ = space.wrap('__doc__')
    _doc = space.wrap("""Common base class for all exceptions.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_Exception = space.wrap('Exception')
    _bases = space.newtuple([])
    _args = space.newtuple([gs_Exception, _bases, _dic])
    m.gcls_Exception = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for all standard Python exceptions.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_StandardError = space.wrap('StandardError')
    _bases = space.newtuple([gcls_Exception])
    _args = space.newtuple([gs_StandardError, _bases, _dic])
    m.gcls_StandardError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Out of memory.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_MemoryError, _bases, _dic])
    m.gcls_MemoryError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_MemoryError, gcls_MemoryError)
    m.gs_ImportError = space.wrap('ImportError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Import can't find module, or can't find name in module.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_ImportError, _bases, _dic])
    m.gcls_ImportError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_ImportError, gcls_ImportError)
    m.gs_RuntimeError = space.wrap('RuntimeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Unspecified run-time error.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_RuntimeError, _bases, _dic])
    m.gcls_RuntimeError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_RuntimeError, gcls_RuntimeError)
    m.gs_UnicodeTranslateError = space.wrap('UnicodeTranslateError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Inappropriate argument value (of correct type).""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_ValueError = space.wrap('ValueError')
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_ValueError, _bases, _dic])
    m.gcls_ValueError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Unicode related error.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_UnicodeError = space.wrap('UnicodeError')
    _bases = space.newtuple([gcls_ValueError])
    _args = space.newtuple([gs_UnicodeError, _bases, _dic])
    m.gcls_UnicodeError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Unicode translation error.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_UnicodeError])
    _args = space.newtuple([gs_UnicodeTranslateError, _bases, _dic])
    m.gcls_UnicodeTranslateError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_UnicodeTranslateError, gcls_UnicodeTranslateError)
    m.gs_KeyError = space.wrap('KeyError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for lookup errors.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_LookupError = space.wrap('LookupError')
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_LookupError, _bases, _dic])
    m.gcls_LookupError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Mapping key not found.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_LookupError])
    _args = space.newtuple([gs_KeyError, _bases, _dic])
    m.gcls_KeyError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_KeyError, gcls_KeyError)
    m.gs_TaskletExit = space.wrap('TaskletExit')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Request to exit from the interpreter.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_SystemExit = space.wrap('SystemExit')
    _bases = space.newtuple([gcls_Exception])
    _args = space.newtuple([gs_SystemExit, _bases, _dic])
    m.gcls_SystemExit = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Request to exit from a tasklet.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_SystemExit])
    _args = space.newtuple([gs_TaskletExit, _bases, _dic])
    m.gcls_TaskletExit = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_TaskletExit, gcls_TaskletExit)
    m.gs_StopIteration = space.wrap('StopIteration')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Signal the end from iterator.next().""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Exception])
    _args = space.newtuple([gs_StopIteration, _bases, _dic])
    m.gcls_StopIteration = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_StopIteration, gcls_StopIteration)
    m.gs_PendingDeprecationWarning = space.wrap('PendingDeprecationWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for warning categories.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_Warning = space.wrap('Warning')
    _bases = space.newtuple([gcls_Exception])
    _args = space.newtuple([gs_Warning, _bases, _dic])
    m.gcls_Warning = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for warnings about features which will be deprecated in the future.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_PendingDeprecationWarning, _bases, _dic])
    m.gcls_PendingDeprecationWarning = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_PendingDeprecationWarning, gcls_PendingDeprecationWarning)
    m.gs_EnvironmentError = space.wrap('EnvironmentError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for I/O related errors.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_EnvironmentError, _bases, _dic])
    m.gcls_EnvironmentError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_EnvironmentError, gcls_EnvironmentError)
    space.setitem(g47dict, gs_LookupError, gcls_LookupError)
    m.gs_OSError = space.wrap('OSError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""OS system call failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_EnvironmentError])
    _args = space.newtuple([gs_OSError, _bases, _dic])
    m.gcls_OSError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_OSError, gcls_OSError)
    m.gs_DeprecationWarning = space.wrap('DeprecationWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for warnings about deprecated features.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_DeprecationWarning, _bases, _dic])
    m.gcls_DeprecationWarning = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_DeprecationWarning, gcls_DeprecationWarning)
    space.setitem(g47dict, gs_UnicodeError, gcls_UnicodeError)
    m.gs_FloatingPointError = space.wrap('FloatingPointError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for arithmetic errors.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_ArithmeticError = space.wrap('ArithmeticError')
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_ArithmeticError, _bases, _dic])
    m.gcls_ArithmeticError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Floating point operation failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_ArithmeticError])
    _args = space.newtuple([gs_FloatingPointError, _bases, _dic])
    m.gcls_FloatingPointError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_FloatingPointError, gcls_FloatingPointError)
    m.gs_AttributeError = space.wrap('AttributeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Attribute not found.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_AttributeError, _bases, _dic])
    m.gcls_AttributeError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_AttributeError, gcls_AttributeError)
    m.gs_IndentationError = space.wrap('IndentationError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Invalid syntax.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_SyntaxError = space.wrap('SyntaxError')
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_SyntaxError, _bases, _dic])
    m.gcls_SyntaxError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Improper indentation.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_SyntaxError])
    _args = space.newtuple([gs_IndentationError, _bases, _dic])
    m.gcls_IndentationError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_IndentationError, gcls_IndentationError)
    m.gs_NameError = space.wrap('NameError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Name not found globally.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_NameError, _bases, _dic])
    m.gcls_NameError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_NameError, gcls_NameError)
    m.gs_OverflowWarning = space.wrap('OverflowWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for warnings about numeric overflow.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_OverflowWarning, _bases, _dic])
    m.gcls_OverflowWarning = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_OverflowWarning, gcls_OverflowWarning)
    m.gs_IOError = space.wrap('IOError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""I/O operation failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_EnvironmentError])
    _args = space.newtuple([gs_IOError, _bases, _dic])
    m.gcls_IOError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_IOError, gcls_IOError)
    space.setitem(g47dict, gs_ValueError, gcls_ValueError)
    m.gs_FutureWarning = space.wrap('FutureWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for warnings about constructs that will change semantically in the future.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_FutureWarning, _bases, _dic])
    m.gcls_FutureWarning = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_FutureWarning, gcls_FutureWarning)
    m.gs_ZeroDivisionError = space.wrap('ZeroDivisionError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Second argument to a division or modulo operation was zero.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_ArithmeticError])
    _args = space.newtuple([gs_ZeroDivisionError, _bases, _dic])
    m.gcls_ZeroDivisionError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_ZeroDivisionError, gcls_ZeroDivisionError)
    space.setitem(g47dict, gs_SystemExit, gcls_SystemExit)
    space.setitem(g47dict, gs_Exception, gcls_Exception)
    m.gs_EOFError = space.wrap('EOFError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Read beyond end of file.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_EOFError, _bases, _dic])
    m.gcls_EOFError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_EOFError, gcls_EOFError)
    space.setitem(g47dict, gs_StandardError, gcls_StandardError)
    m.gs_TabError = space.wrap('TabError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Improper mixture of spaces and tabs.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_IndentationError])
    _args = space.newtuple([gs_TabError, _bases, _dic])
    m.gcls_TabError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_TabError, gcls_TabError)
    space.setitem(g47dict, gs_SyntaxError, gcls_SyntaxError)
    m.gs_UnicodeEncodeError = space.wrap('UnicodeEncodeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Unicode encoding error.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_UnicodeError])
    _args = space.newtuple([gs_UnicodeEncodeError, _bases, _dic])
    m.gcls_UnicodeEncodeError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_UnicodeEncodeError, gcls_UnicodeEncodeError)
    m.gs_UnboundLocalError = space.wrap('UnboundLocalError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Local name referenced but not bound to a value.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_NameError])
    _args = space.newtuple([gs_UnboundLocalError, _bases, _dic])
    m.gcls_UnboundLocalError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_UnboundLocalError, gcls_UnboundLocalError)
    m.gs___name__ = space.wrap('__name__')
    space.setitem(g47dict, gs___name__, gs_exceptions)
    m.gs_ReferenceError = space.wrap('ReferenceError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Weak ref proxy used after referent went away.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_ReferenceError, _bases, _dic])
    m.gcls_ReferenceError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_ReferenceError, gcls_ReferenceError)
    m.gs_AssertionError = space.wrap('AssertionError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Assertion failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_AssertionError, _bases, _dic])
    m.gcls_AssertionError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_AssertionError, gcls_AssertionError)
    m.gs_UnicodeDecodeError = space.wrap('UnicodeDecodeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Unicode decoding error.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_UnicodeError])
    _args = space.newtuple([gs_UnicodeDecodeError, _bases, _dic])
    m.gcls_UnicodeDecodeError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_UnicodeDecodeError, gcls_UnicodeDecodeError)
    m.gs_TypeError = space.wrap('TypeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Inappropriate argument type.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_TypeError, _bases, _dic])
    m.gcls_TypeError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_TypeError, gcls_TypeError)
    m.gs_IndexError = space.wrap('IndexError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Sequence index out of range.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_LookupError])
    _args = space.newtuple([gs_IndexError, _bases, _dic])
    m.gcls_IndexError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_IndexError, gcls_IndexError)
    m.gs_RuntimeWarning = space.wrap('RuntimeWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for warnings about dubious runtime behavior.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_RuntimeWarning, _bases, _dic])
    m.gcls_RuntimeWarning = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_RuntimeWarning, gcls_RuntimeWarning)
    m.gs_KeyboardInterrupt = space.wrap('KeyboardInterrupt')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Program interrupted by user.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_KeyboardInterrupt, _bases, _dic])
    m.gcls_KeyboardInterrupt = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_KeyboardInterrupt, gcls_KeyboardInterrupt)
    m.gs_UserWarning = space.wrap('UserWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for warnings generated by user code.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_UserWarning, _bases, _dic])
    m.gcls_UserWarning = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_UserWarning, gcls_UserWarning)
    m.gs_SyntaxWarning = space.wrap('SyntaxWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Base class for warnings about dubious syntax.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_SyntaxWarning, _bases, _dic])
    m.gcls_SyntaxWarning = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_SyntaxWarning, gcls_SyntaxWarning)
    space.setitem(g47dict, gs___doc__, __doc__)
    space.setitem(g47dict, gs_ArithmeticError, gcls_ArithmeticError)
    space.setitem(g47dict, gs_Warning, gcls_Warning)
    m.gs_NotImplementedError = space.wrap('NotImplementedError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Method or function hasn't been implemented yet.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_RuntimeError])
    _args = space.newtuple([gs_NotImplementedError, _bases, _dic])
    m.gcls_NotImplementedError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_NotImplementedError, gcls_NotImplementedError)
    m.gs_SystemError = space.wrap('SystemError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Internal error in the Python interpreter.

Please report this to the Python maintainer, along with the traceback,
the Python version, and the hardware/OS platform and version.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_SystemError, _bases, _dic])
    m.gcls_SystemError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_SystemError, gcls_SystemError)
    m.gs_OverflowError = space.wrap('OverflowError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""Result too large to be represented.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_ArithmeticError])
    _args = space.newtuple([gs_OverflowError, _bases, _dic])
    m.gcls_OverflowError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_OverflowError, gcls_OverflowError)
    m.gs_WindowsError = space.wrap('WindowsError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_exceptions)
    _doc = space.wrap("""MS-Windows OS system call failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_OSError])
    _args = space.newtuple([gs_WindowsError, _bases, _dic])
    m.gcls_WindowsError = space.call(space.w_type, _args)
    space.setitem(g47dict, gs_WindowsError, gcls_WindowsError)
    m.gs___init__ = space.wrap('__init__')
    m.gfunc_UnicodeDecodeError___init__ = space.wrap(interp2app(f_UnicodeDecodeError___init__))
    space.setattr(gcls_UnicodeDecodeError, gs___init__, gfunc_UnicodeDecodeError___init__)
    m.gs___str__ = space.wrap('__str__')
    m.gfunc_UnicodeDecodeError___str__ = space.wrap(interp2app(f_UnicodeDecodeError___str__))
    space.setattr(gcls_UnicodeDecodeError, gs___str__, gfunc_UnicodeDecodeError___str__)
    m.gfunc_UnicodeEncodeError___init__ = space.wrap(interp2app(f_UnicodeEncodeError___init__))
    space.setattr(gcls_UnicodeEncodeError, gs___init__, gfunc_UnicodeEncodeError___init__)
    m.gfunc_UnicodeEncodeError___str__ = space.wrap(interp2app(f_UnicodeEncodeError___str__))
    space.setattr(gcls_UnicodeEncodeError, gs___str__, gfunc_UnicodeEncodeError___str__)
    m.gfunc_SyntaxError___init__ = space.wrap(interp2app(f_SyntaxError___init__))
    space.setattr(gcls_SyntaxError, gs___init__, gfunc_SyntaxError___init__)
    m.gfunc_SyntaxError___str__ = space.wrap(interp2app(f_SyntaxError___str__))
    space.setattr(gcls_SyntaxError, gs___str__, gfunc_SyntaxError___str__)
    m.gs_filename = space.wrap('filename')
    space.setattr(gcls_SyntaxError, gs_filename, space.w_None)
    m.gs_lineno = space.wrap('lineno')
    space.setattr(gcls_SyntaxError, gs_lineno, space.w_None)
    m.gs_msg = space.wrap('msg')
    m.gs__emptystr_ = space.wrap('')
    space.setattr(gcls_SyntaxError, gs_msg, gs__emptystr_)
    m.gs_offset = space.wrap('offset')
    space.setattr(gcls_SyntaxError, gs_offset, space.w_None)
    m.gs_print_file_and_line = space.wrap('print_file_and_line')
    space.setattr(gcls_SyntaxError, gs_print_file_and_line, space.w_None)
    m.gs_text = space.wrap('text')
    space.setattr(gcls_SyntaxError, gs_text, space.w_None)
    m.gfunc_EnvironmentError___init__ = space.wrap(interp2app(f_EnvironmentError___init__))
    space.setattr(gcls_EnvironmentError, gs___init__, gfunc_EnvironmentError___init__)
    m.gfunc_EnvironmentError___str__ = space.wrap(interp2app(f_EnvironmentError___str__))
    space.setattr(gcls_EnvironmentError, gs___str__, gfunc_EnvironmentError___str__)
    m.gfunc_SystemExit___init__ = space.wrap(interp2app(f_SystemExit___init__))
    space.setattr(gcls_SystemExit, gs___init__, gfunc_SystemExit___init__)
    m.gfunc_KeyError___str__ = space.wrap(interp2app(f_KeyError___str__))
    space.setattr(gcls_KeyError, gs___str__, gfunc_KeyError___str__)
    m.gfunc_UnicodeTranslateError___init__ = space.wrap(interp2app(f_UnicodeTranslateError___init__))
    space.setattr(gcls_UnicodeTranslateError, gs___init__, gfunc_UnicodeTranslateError___init__)
    m.gfunc_UnicodeTranslateError___str__ = space.wrap(interp2app(f_UnicodeTranslateError___str__))
    space.setattr(gcls_UnicodeTranslateError, gs___str__, gfunc_UnicodeTranslateError___str__)
    m.gs___getitem__ = space.wrap('__getitem__')
    m.gfunc_Exception___getitem__ = space.wrap(interp2app(f_Exception___getitem__))
    space.setattr(gcls_Exception, gs___getitem__, gfunc_Exception___getitem__)
    m.gfunc_Exception___init__ = space.wrap(interp2app(f_Exception___init__))
    space.setattr(gcls_Exception, gs___init__, gfunc_Exception___init__)
    m.gfunc_Exception___str__ = space.wrap(interp2app(f_Exception___str__))
    space.setattr(gcls_Exception, gs___str__, gfunc_Exception___str__)
    m.gs_args = space.wrap('args')
    m.gi_0 = space.newint(0)
    m.gi_1 = space.newint(1)
    m.gs_start = space.wrap('start')
    m.gs_start_ = space.wrap('start=')
    m.gs_reason = space.wrap('reason')
    m.gs_reason_ = space.wrap('reason=')
    m.gs_args_ = space.wrap('args=')
    m.gs_end = space.wrap('end')
    m.gs_end_ = space.wrap('end=')
    m.gs_object = space.wrap('object')
    m.gs_object_ = space.wrap('object=')
    m.gs__ = space.wrap(' ')
    m.gs_join = space.wrap('join')
    m.gbltinmethod_join = space.getattr(gs__, gs_join)
    m.gi_4 = space.newint(4)
    m.gi_2 = space.newint(2)
    m.gi_3 = space.newint(3)
    m.gs_code = space.wrap('code')
    m.gs_errno = space.wrap('errno')
    m.gs_errno_ = space.wrap('errno=')
    m.gs_strerror = space.wrap('strerror')
    m.gs_strerror_ = space.wrap('strerror=')
    m.gs_filename_ = space.wrap('filename=')
    m.gs_encoding = space.wrap('encoding')
    m.gs_encoding_ = space.wrap('encoding=')
    m.gi_5 = space.newint(5)

# entry point: test_exceptions, gfunc_test_exceptions)
if __name__ == "__main__":
    from pypy.objspace.std import StdObjSpace
    space = StdObjSpace()
    inittest_exceptions_1(space)
    print space.unwrap(space.call(
            gfunc_test_exceptions, space.newtuple([])))

