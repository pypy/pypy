#!/bin/env python
# -*- coding: LATIN-1 -*-
##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__getitem__'
## firstlineno 5
##SECTION##
def __getitem__(space, *args_w):
    kwlist = ["self", "idx"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__getitem__"
    w_self_1, w_idx_3 = PyArg_ParseMini(space, funcname, 2, 2, _args_w, defaults_w)
    return fastf_Exception___getitem__(space, w_self_1, w_idx_3)
f_Exception___getitem__ = globals().pop("__getitem__")

def __getitem__(space, w_self_1, w_idx_3):

    w_0=w_0=w_2=w_4=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self_1, gs_args)
            w_2 = space.getitem(w_0, w_idx_3)
            w_4 = w_2
            goto = 2

        if goto == 2:
            return w_4
fastf_Exception___getitem__ = globals().pop("__getitem__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__init__'
## firstlineno 9
##SECTION##
def __init__(space, *args_w):
    kwlist = ["self"]
    w_args_2 = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self_1, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_Exception___init__(space, w_self_1, w_args_2)
f_Exception___init__ = globals().pop("__init__")

def __init__(space, w_self_1, w_args_2):

    w_0=w_0=w_3=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.setattr(w_self_1, gs_args, w_args_2)
            w_3 = space.w_None
            goto = 2

        if goto == 2:
            return w_3
fastf_Exception___init__ = globals().pop("__init__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__str__'
## firstlineno 13
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
    w_self_1, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_Exception___str__(space, w_self_1)
f_Exception___str__ = globals().pop("__str__")

def __str__(space, w_self_1):

    w_0=w_0=w_argc_2=w_3=v4=w_self_6=w_argc_7=w_8=w_9=v10=w_self_16=None
    w_argc_17=w_argc_17=w_18=w_22=w_23=w_5=w_self_11=w_argc_12=w_13=None
    w_14=w_14=w_15=w_19=w_20=w_21=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self_1, gs_args)
            w_argc_2 = space.len(w_0)
            w_3 = space.eq(w_argc_2, gi_0)
            v4 = space.is_true(w_3)
            if v4 == True:
                w_5 = gs__emptystr_
                goto = 5
            else:
                assert v4 == False
                w_self_6, w_argc_7, w_8 = w_self_1, w_argc_2, w_3
                goto = 2

        if goto == 2:
            w_9 = space.eq(w_argc_7, gi_1)
            v10 = space.is_true(w_9)
            if v10 == True:
                (w_self_11, w_argc_12, w_13, w_14, w_15) = (w_self_6, w_argc_7,
                 w_8, w_9, v10)
                goto = 3
            else:
                assert v10 == False
                w_self_16, w_argc_17, w_18 = w_self_6, w_argc_7, w_9
                goto = 4

        if goto == 3:
            w_19 = space.getattr(w_self_11, gs_args)
            w_20 = space.getitem(w_19, gi_0)
            _tup = space.newtuple([w_20])
            w_21 = space.call(space.w_str, _tup)
            w_5 = w_21
            goto = 5

        if goto == 4:
            w_22 = space.getattr(w_self_16, gs_args)
            _tup = space.newtuple([w_22])
            w_23 = space.call(space.w_str, _tup)
            w_5 = w_23
            goto = 5

        if goto == 5:
            return w_5
fastf_Exception___str__ = globals().pop("__str__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__init__'
## firstlineno 41
##SECTION##
# global declarations
# global object gi_4
# global object gi_2
# global object gi_3

def __init__(space, *args_w):
    kwlist = ["self"]
    w_args_1 = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self_3, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeTranslateError___init__(space, w_self_3, w_args_1)
f_UnicodeTranslateError___init__ = globals().pop("__init__")

def __init__(space, w_self_3, w_args_1):

    w_argc_0=w_argc_0=w_2=w_4=v5=w_12=w_self_6=w_args_7=w_argc_8=None
    w_9=w_9=w_10=w_11=w_13=w_14=w_15=w_16=w_17=w_18=w_19=w_20=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc_0 = space.len(w_args_1)
            w_2 = space.setattr(w_self_3, gs_args, w_args_1)
            w_4 = space.eq(w_argc_0, gi_4)
            v5 = space.is_true(w_4)
            if v5 == True:
                (w_self_6, w_args_7, w_argc_8, w_9, w_10, w_11) = (w_self_3,
                 w_args_1, w_argc_0, w_2, w_4, v5)
                goto = 2
            else:
                assert v5 == False
                w_12 = space.w_None
                goto = 3

        if goto == 2:
            w_13 = space.getitem(w_args_7, gi_0)
            w_14 = space.setattr(w_self_6, gs_object, w_13)
            w_15 = space.getitem(w_args_7, gi_1)
            w_16 = space.setattr(w_self_6, gs_start, w_15)
            w_17 = space.getitem(w_args_7, gi_2)
            w_18 = space.setattr(w_self_6, gs_end, w_17)
            w_19 = space.getitem(w_args_7, gi_3)
            w_20 = space.setattr(w_self_6, gs_reason, w_19)
            w_12 = space.w_None
            goto = 3

        if goto == 3:
            return w_12
fastf_UnicodeTranslateError___init__ = globals().pop("__init__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__str__'
## firstlineno 51
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
    w_self_1, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeTranslateError___str__(space, w_self_1)
f_UnicodeTranslateError___str__ = globals().pop("__str__")

def __str__(space, w_self_1):

    w_0=w_0=w_2=w_3=w_4=w_5=w_6=w_7=w_8=w_9=w_10=w_11=w_12=w_13=w_14=None
    w_15=w_15=w_16=w_res_17=w_18=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self_1, gs_start)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_start_, w_2)
            w_4 = space.getattr(w_self_1, gs_reason)
            _tup = space.newtuple([w_4])
            w_5 = space.call(space.w_str, _tup)
            w_6 = space.add(gs_reason_, w_5)
            w_7 = space.getattr(w_self_1, gs_args)
            _tup = space.newtuple([w_7])
            w_8 = space.call(space.w_str, _tup)
            w_9 = space.add(gs_args_, w_8)
            w_10 = space.getattr(w_self_1, gs_end)
            _tup = space.newtuple([w_10])
            w_11 = space.call(space.w_str, _tup)
            w_12 = space.add(gs_end_, w_11)
            w_13 = space.getattr(w_self_1, gs_object)
            _tup = space.newtuple([w_13])
            w_14 = space.call(space.w_str, _tup)
            w_15 = space.add(gs_object_, w_14)
            w_16 = space.newlist([w_3, w_6, w_9, w_12, w_15])
            _tup = space.newtuple([w_16])
            w_res_17 = space.call(gbltinmethod_join, _tup)
            w_18 = w_res_17
            goto = 2

        if goto == 2:
            return w_18
fastf_UnicodeTranslateError___str__ = globals().pop("__str__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__str__'
## firstlineno 69
##SECTION##
def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self_1, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_KeyError___str__(space, w_self_1)
f_KeyError___str__ = globals().pop("__str__")

def __str__(space, w_self_1):

    w_0=w_0=w_argc_2=w_3=v4=w_self_6=w_argc_7=w_8=w_9=v10=w_self_16=None
    w_argc_17=w_argc_17=w_18=w_22=w_23=w_5=w_self_11=w_argc_12=w_13=None
    w_14=w_14=w_15=w_19=w_20=w_21=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self_1, gs_args)
            w_argc_2 = space.len(w_0)
            w_3 = space.eq(w_argc_2, gi_0)
            v4 = space.is_true(w_3)
            if v4 == True:
                w_5 = gs__emptystr_
                goto = 5
            else:
                assert v4 == False
                w_self_6, w_argc_7, w_8 = w_self_1, w_argc_2, w_3
                goto = 2

        if goto == 2:
            w_9 = space.eq(w_argc_7, gi_1)
            v10 = space.is_true(w_9)
            if v10 == True:
                (w_self_11, w_argc_12, w_13, w_14, w_15) = (w_self_6, w_argc_7,
                 w_8, w_9, v10)
                goto = 3
            else:
                assert v10 == False
                w_self_16, w_argc_17, w_18 = w_self_6, w_argc_7, w_9
                goto = 4

        if goto == 3:
            w_19 = space.getattr(w_self_11, gs_args)
            w_20 = space.getitem(w_19, gi_0)
            w_21 = space.repr(w_20)
            w_5 = w_21
            goto = 5

        if goto == 4:
            w_22 = space.getattr(w_self_16, gs_args)
            _tup = space.newtuple([w_22])
            w_23 = space.call(space.w_str, _tup)
            w_5 = w_23
            goto = 5

        if goto == 5:
            return w_5
fastf_KeyError___str__ = globals().pop("__str__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__init__'
## firstlineno 91
##SECTION##
def __init__(space, *args_w):
    kwlist = ["self"]
    w_args_1 = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self_3, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_EnvironmentError___init__(space, w_self_3, w_args_1)
f_EnvironmentError___init__ = globals().pop("__init__")

def __init__(space, w_self_3, w_args_1):

    w_argc_0=w_argc_0=w_2=w_4=w_5=w_6=w_7=v8=w_self_18=w_args_19=None
    w_argc_20=w_argc_20=w_21=v23=w_self_29=w_args_30=w_argc_31=w_36=None
    v37=v37=w_43=w_self_38=w_args_39=w_argc_40=w_41=w_42=w_44=w_45=None
    w_46=w_46=w_47=w_48=w_49=w_self_24=w_args_25=w_argc_26=w_27=w_28=None
    w_32=w_32=w_33=w_34=w_35=w_self_9=w_args_10=w_argc_11=w_12=w_13=None
    w_14=w_14=w_15=w_16=w_17=w_22=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc_0 = space.len(w_args_1)
            w_2 = space.setattr(w_self_3, gs_args, w_args_1)
            w_4 = space.setattr(w_self_3, gs_errno, space.w_None)
            w_5 = space.setattr(w_self_3, gs_strerror, space.w_None)
            w_6 = space.setattr(w_self_3, gs_filename, space.w_None)
            w_7 = space.le(gi_2, w_argc_0)
            v8 = space.is_true(w_7)
            if v8 == True:
                (w_self_9, w_args_10, w_argc_11, w_12, w_13, w_14, w_15, w_16,
                 w_17) = (w_self_3, w_args_1, w_argc_0, w_2, w_4, w_5, w_6, w_7,
                 v8)
                goto = 2
            else:
                assert v8 == False
                (w_self_18, w_args_19, w_argc_20, w_21) = (w_self_3, w_args_1,
                 w_argc_0, w_7)
                goto = 3

        if goto == 2:
            w_22 = space.le(w_argc_11, gi_3)
            (w_self_18, w_args_19, w_argc_20, w_21) = (w_self_9, w_args_10,
             w_argc_11, w_22)
            goto = 3

        if goto == 3:
            v23 = space.is_true(w_21)
            if v23 == True:
                (w_self_24, w_args_25, w_argc_26, w_27, w_28) = (w_self_18,
                 w_args_19, w_argc_20, w_21, v23)
                goto = 4
            else:
                assert v23 == False
                w_self_29, w_args_30, w_argc_31 = w_self_18, w_args_19, w_argc_20
                goto = 5

        if goto == 4:
            w_32 = space.getitem(w_args_25, gi_0)
            w_33 = space.setattr(w_self_24, gs_errno, w_32)
            w_34 = space.getitem(w_args_25, gi_1)
            w_35 = space.setattr(w_self_24, gs_strerror, w_34)
            w_self_29, w_args_30, w_argc_31 = w_self_24, w_args_25, w_argc_26
            goto = 5

        if goto == 5:
            w_36 = space.eq(w_argc_31, gi_3)
            v37 = space.is_true(w_36)
            if v37 == True:
                (w_self_38, w_args_39, w_argc_40, w_41, w_42) = (w_self_29,
                 w_args_30, w_argc_31, w_36, v37)
                goto = 6
            else:
                assert v37 == False
                w_43 = space.w_None
                goto = 7

        if goto == 6:
            w_44 = space.getitem(w_args_39, gi_2)
            w_45 = space.setattr(w_self_38, gs_filename, w_44)
            w_46 = space.getitem(w_args_39, gi_0)
            w_47 = space.getitem(w_args_39, gi_1)
            w_48 = space.newtuple([w_46, w_47])
            w_49 = space.setattr(w_self_38, gs_args, w_48)
            w_43 = space.w_None
            goto = 7

        if goto == 7:
            return w_43
fastf_EnvironmentError___init__ = globals().pop("__init__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__str__'
## firstlineno 105
##SECTION##
# global declarations
# global object gs_errno
# global object gs_errno_
# global object gs_strerror
# global object gs_strerror_
# global object gs_filename_
# global object gbltinmethod_join_1

def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self_1, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_EnvironmentError___str__(space, w_self_1)
f_EnvironmentError___str__ = globals().pop("__str__")

def __str__(space, w_self_1):

    w_0=w_0=w_2=w_3=w_4=w_5=w_6=w_7=w_8=w_9=w_10=w_11=w_12=w_13=w_res_14=None
    w_15=w_15=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self_1, gs_errno)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_errno_, w_2)
            w_4 = space.getattr(w_self_1, gs_args)
            _tup = space.newtuple([w_4])
            w_5 = space.call(space.w_str, _tup)
            w_6 = space.add(gs_args_, w_5)
            w_7 = space.getattr(w_self_1, gs_strerror)
            _tup = space.newtuple([w_7])
            w_8 = space.call(space.w_str, _tup)
            w_9 = space.add(gs_strerror_, w_8)
            w_10 = space.getattr(w_self_1, gs_filename)
            _tup = space.newtuple([w_10])
            w_11 = space.call(space.w_str, _tup)
            w_12 = space.add(gs_filename_, w_11)
            w_13 = space.newlist([w_3, w_6, w_9, w_12])
            _tup = space.newtuple([w_13])
            w_res_14 = space.call(gbltinmethod_join_1, _tup)
            w_15 = w_res_14
            goto = 2

        if goto == 2:
            return w_15
fastf_EnvironmentError___str__ = globals().pop("__str__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__init__'
## firstlineno 149
##SECTION##
def __init__(space, *args_w):
    kwlist = ["self"]
    w_args_1 = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self_3, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_SyntaxError___init__(space, w_self_3, w_args_1)
f_SyntaxError___init__ = globals().pop("__init__")

def __init__(space, w_self_3, w_args_1):

    w_argc_0=w_argc_0=w_2=w_4=v5=w_self_12=w_args_13=w_argc_14=w_17=None
    v18=v18=w_24=w_self_19=w_args_20=w_argc_21=w_22=w_23=w_25=w_26=None
    w_27=w_27=w_28=w_29=w_30=w_31=w_32=w_33=w_34=w_35=w_36=w_self_6=None
    w_args_7=w_args_7=w_argc_8=w_9=w_10=w_11=w_15=w_16=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc_0 = space.len(w_args_1)
            w_2 = space.setattr(w_self_3, gs_args, w_args_1)
            w_4 = space.ge(w_argc_0, gi_1)
            v5 = space.is_true(w_4)
            if v5 == True:
                (w_self_6, w_args_7, w_argc_8, w_9, w_10, w_11) = (w_self_3,
                 w_args_1, w_argc_0, w_2, w_4, v5)
                goto = 2
            else:
                assert v5 == False
                w_self_12, w_args_13, w_argc_14 = w_self_3, w_args_1, w_argc_0
                goto = 3

        if goto == 2:
            w_15 = space.getitem(w_args_7, gi_0)
            w_16 = space.setattr(w_self_6, gs_msg, w_15)
            w_self_12, w_args_13, w_argc_14 = w_self_6, w_args_7, w_argc_8
            goto = 3

        if goto == 3:
            w_17 = space.eq(w_argc_14, gi_2)
            v18 = space.is_true(w_17)
            if v18 == True:
                (w_self_19, w_args_20, w_argc_21, w_22, w_23) = (w_self_12,
                 w_args_13, w_argc_14, w_17, v18)
                goto = 4
            else:
                assert v18 == False
                w_24 = space.w_None
                goto = 5

        if goto == 4:
            w_25 = space.getitem(w_args_20, gi_1)
            w_26 = space.getitem(w_25, gi_0)
            w_27 = space.setattr(w_self_19, gs_filename, w_26)
            w_28 = space.getitem(w_args_20, gi_1)
            w_29 = space.getitem(w_28, gi_1)
            w_30 = space.setattr(w_self_19, gs_lineno, w_29)
            w_31 = space.getitem(w_args_20, gi_1)
            w_32 = space.getitem(w_31, gi_2)
            w_33 = space.setattr(w_self_19, gs_offset, w_32)
            w_34 = space.getitem(w_args_20, gi_1)
            w_35 = space.getitem(w_34, gi_3)
            w_36 = space.setattr(w_self_19, gs_text, w_35)
            w_24 = space.w_None
            goto = 5

        if goto == 5:
            return w_24
fastf_SyntaxError___init__ = globals().pop("__init__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__str__'
## firstlineno 161
##SECTION##
# global declaration
# global object gbltinmethod_join_2

def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self_1, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_SyntaxError___str__(space, w_self_1)
f_SyntaxError___str__ = globals().pop("__str__")

def __str__(space, w_self_1):

    w_0=w_0=w_2=w_3=w_4=w_res_5=w_6=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self_1, gs_args)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_args_, w_2)
            w_4 = space.newlist([w_3])
            _tup = space.newtuple([w_4])
            w_res_5 = space.call(gbltinmethod_join_2, _tup)
            w_6 = w_res_5
            goto = 2

        if goto == 2:
            return w_6
fastf_SyntaxError___str__ = globals().pop("__str__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__init__'
## firstlineno 175
##SECTION##
# global declaration
# global object gs_code

def __init__(space, *args_w):
    kwlist = ["self"]
    w_args_1 = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self_4, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_SystemExit___init__(space, w_self_4, w_args_1)
f_SystemExit___init__ = globals().pop("__init__")

def __init__(space, w_self_4, w_args_1):

    w_argc_0=w_argc_0=w_2=v3=w_self_10=w_args_11=w_argc_12=w_14=w_15=None
    v16=v16=w_self_23=w_args_24=w_argc_25=w_28=v29=w_35=w_self_30=None
    w_args_31=w_args_31=w_argc_32=w_33=w_34=w_36=w_self_17=w_args_18=None
    w_argc_19=w_argc_19=w_20=w_21=w_22=w_26=w_27=w_self_5=w_args_6=None
    w_argc_7=w_argc_7=w_8=w_9=w_13=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc_0 = space.len(w_args_1)
            w_2 = space.eq(w_argc_0, gi_0)
            v3 = space.is_true(w_2)
            if v3 == True:
                (w_self_5, w_args_6, w_argc_7, w_8, w_9) = (w_self_4, w_args_1,
                 w_argc_0, w_2, v3)
                goto = 2
            else:
                assert v3 == False
                w_self_10, w_args_11, w_argc_12 = w_self_4, w_args_1, w_argc_0
                goto = 3

        if goto == 2:
            w_13 = space.setattr(w_self_5, gs_code, space.w_None)
            w_self_10, w_args_11, w_argc_12 = w_self_5, w_args_6, w_argc_7
            goto = 3

        if goto == 3:
            w_14 = space.setattr(w_self_10, gs_args, w_args_11)
            w_15 = space.eq(w_argc_12, gi_1)
            v16 = space.is_true(w_15)
            if v16 == True:
                (w_self_17, w_args_18, w_argc_19, w_20, w_21, w_22) = (w_self_10,
                 w_args_11, w_argc_12, w_14, w_15, v16)
                goto = 4
            else:
                assert v16 == False
                w_self_23, w_args_24, w_argc_25 = w_self_10, w_args_11, w_argc_12
                goto = 5

        if goto == 4:
            w_26 = space.getitem(w_args_18, gi_0)
            w_27 = space.setattr(w_self_17, gs_code, w_26)
            w_self_23, w_args_24, w_argc_25 = w_self_17, w_args_18, w_argc_19
            goto = 5

        if goto == 5:
            w_28 = space.ge(w_argc_25, gi_2)
            v29 = space.is_true(w_28)
            if v29 == True:
                (w_self_30, w_args_31, w_argc_32, w_33, w_34) = (w_self_23,
                 w_args_24, w_argc_25, w_28, v29)
                goto = 6
            else:
                assert v29 == False
                w_35 = space.w_None
                goto = 7

        if goto == 6:
            w_36 = space.setattr(w_self_30, gs_code, w_args_31)
            w_35 = space.w_None
            goto = 7

        if goto == 7:
            return w_35
fastf_SystemExit___init__ = globals().pop("__init__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__init__'
## firstlineno 210
##SECTION##
def __init__(space, *args_w):
    kwlist = ["self"]
    w_args_1 = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self_3, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeDecodeError___init__(space, w_self_3, w_args_1)
f_UnicodeDecodeError___init__ = globals().pop("__init__")

def __init__(space, w_self_3, w_args_1):

    w_argc_0=w_argc_0=w_2=w_4=v5=w_12=w_self_6=w_args_7=w_argc_8=None
    w_9=w_9=w_10=w_11=w_13=w_14=w_15=w_16=w_17=w_18=w_19=w_20=w_21=None
    w_22=w_22=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc_0 = space.len(w_args_1)
            w_2 = space.setattr(w_self_3, gs_args, w_args_1)
            w_4 = space.eq(w_argc_0, gi_5)
            v5 = space.is_true(w_4)
            if v5 == True:
                (w_self_6, w_args_7, w_argc_8, w_9, w_10, w_11) = (w_self_3,
                 w_args_1, w_argc_0, w_2, w_4, v5)
                goto = 2
            else:
                assert v5 == False
                w_12 = space.w_None
                goto = 3

        if goto == 2:
            w_13 = space.getitem(w_args_7, gi_0)
            w_14 = space.setattr(w_self_6, gs_encoding, w_13)
            w_15 = space.getitem(w_args_7, gi_1)
            w_16 = space.setattr(w_self_6, gs_object, w_15)
            w_17 = space.getitem(w_args_7, gi_2)
            w_18 = space.setattr(w_self_6, gs_start, w_17)
            w_19 = space.getitem(w_args_7, gi_3)
            w_20 = space.setattr(w_self_6, gs_end, w_19)
            w_21 = space.getitem(w_args_7, gi_4)
            w_22 = space.setattr(w_self_6, gs_reason, w_21)
            w_12 = space.w_None
            goto = 3

        if goto == 3:
            return w_12
fastf_UnicodeDecodeError___init__ = globals().pop("__init__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__str__'
## firstlineno 221
##SECTION##
# global declaration
# global object gbltinmethod_join_4

def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self_1, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeDecodeError___str__(space, w_self_1)
f_UnicodeDecodeError___str__ = globals().pop("__str__")

def __str__(space, w_self_1):

    w_0=w_0=w_2=w_3=w_4=w_5=w_6=w_7=w_8=w_9=w_10=w_11=w_12=w_13=w_14=None
    w_15=w_15=w_16=w_17=w_18=w_19=w_res_20=w_21=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self_1, gs_object)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_object_, w_2)
            w_4 = space.getattr(w_self_1, gs_end)
            _tup = space.newtuple([w_4])
            w_5 = space.call(space.w_str, _tup)
            w_6 = space.add(gs_end_, w_5)
            w_7 = space.getattr(w_self_1, gs_encoding)
            _tup = space.newtuple([w_7])
            w_8 = space.call(space.w_str, _tup)
            w_9 = space.add(gs_encoding_, w_8)
            w_10 = space.getattr(w_self_1, gs_args)
            _tup = space.newtuple([w_10])
            w_11 = space.call(space.w_str, _tup)
            w_12 = space.add(gs_args_, w_11)
            w_13 = space.getattr(w_self_1, gs_start)
            _tup = space.newtuple([w_13])
            w_14 = space.call(space.w_str, _tup)
            w_15 = space.add(gs_start_, w_14)
            w_16 = space.getattr(w_self_1, gs_reason)
            _tup = space.newtuple([w_16])
            w_17 = space.call(space.w_str, _tup)
            w_18 = space.add(gs_reason_, w_17)
            w_19 = space.newlist([w_3, w_6, w_9, w_12, w_15, w_18])
            _tup = space.newtuple([w_19])
            w_res_20 = space.call(gbltinmethod_join_4, _tup)
            w_21 = w_res_20
            goto = 2

        if goto == 2:
            return w_21
fastf_UnicodeDecodeError___str__ = globals().pop("__str__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__init__'
## firstlineno 270
##SECTION##
# global declaration
# global object gi_5

def __init__(space, *args_w):
    kwlist = ["self"]
    w_args_1 = space.newtuple(list(args_w[1:]))
    _args_w = args_w[:1]
    defaults_w = ()
    funcname = "__init__"
    w_self_3, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeEncodeError___init__(space, w_self_3, w_args_1)
f_UnicodeEncodeError___init__ = globals().pop("__init__")

def __init__(space, w_self_3, w_args_1):

    w_argc_0=w_argc_0=w_2=w_4=v5=w_12=w_self_6=w_args_7=w_argc_8=None
    w_9=w_9=w_10=w_11=w_13=w_14=w_15=w_16=w_17=w_18=w_19=w_20=w_21=None
    w_22=w_22=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_argc_0 = space.len(w_args_1)
            w_2 = space.setattr(w_self_3, gs_args, w_args_1)
            w_4 = space.eq(w_argc_0, gi_5)
            v5 = space.is_true(w_4)
            if v5 == True:
                (w_self_6, w_args_7, w_argc_8, w_9, w_10, w_11) = (w_self_3,
                 w_args_1, w_argc_0, w_2, w_4, v5)
                goto = 2
            else:
                assert v5 == False
                w_12 = space.w_None
                goto = 3

        if goto == 2:
            w_13 = space.getitem(w_args_7, gi_0)
            w_14 = space.setattr(w_self_6, gs_encoding, w_13)
            w_15 = space.getitem(w_args_7, gi_1)
            w_16 = space.setattr(w_self_6, gs_object, w_15)
            w_17 = space.getitem(w_args_7, gi_2)
            w_18 = space.setattr(w_self_6, gs_start, w_17)
            w_19 = space.getitem(w_args_7, gi_3)
            w_20 = space.setattr(w_self_6, gs_end, w_19)
            w_21 = space.getitem(w_args_7, gi_4)
            w_22 = space.setattr(w_self_6, gs_reason, w_21)
            w_12 = space.w_None
            goto = 3

        if goto == 3:
            return w_12
fastf_UnicodeEncodeError___init__ = globals().pop("__init__")

##SECTION##
## filename    '/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.py'
## function    '__str__'
## firstlineno 281
##SECTION##
# global declarations
# global object gs_encoding
# global object gs_encoding_
# global object gbltinmethod_join_3

def __str__(space, *args_w):
    kwlist = ["self"]
    _args_w = args_w
    defaults_w = ()
    funcname = "__str__"
    w_self_1, = PyArg_ParseMini(space, funcname, 1, 1, _args_w, defaults_w)
    return fastf_UnicodeEncodeError___str__(space, w_self_1)
f_UnicodeEncodeError___str__ = globals().pop("__str__")

def __str__(space, w_self_1):

    w_0=w_0=w_2=w_3=w_4=w_5=w_6=w_7=w_8=w_9=w_10=w_11=w_12=w_13=w_14=None
    w_15=w_15=w_16=w_17=w_18=w_19=w_res_20=w_21=None

    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self_1, gs_object)
            _tup = space.newtuple([w_0])
            w_2 = space.call(space.w_str, _tup)
            w_3 = space.add(gs_object_, w_2)
            w_4 = space.getattr(w_self_1, gs_end)
            _tup = space.newtuple([w_4])
            w_5 = space.call(space.w_str, _tup)
            w_6 = space.add(gs_end_, w_5)
            w_7 = space.getattr(w_self_1, gs_encoding)
            _tup = space.newtuple([w_7])
            w_8 = space.call(space.w_str, _tup)
            w_9 = space.add(gs_encoding_, w_8)
            w_10 = space.getattr(w_self_1, gs_args)
            _tup = space.newtuple([w_10])
            w_11 = space.call(space.w_str, _tup)
            w_12 = space.add(gs_args_, w_11)
            w_13 = space.getattr(w_self_1, gs_start)
            _tup = space.newtuple([w_13])
            w_14 = space.call(space.w_str, _tup)
            w_15 = space.add(gs_start_, w_14)
            w_16 = space.getattr(w_self_1, gs_reason)
            _tup = space.newtuple([w_16])
            w_17 = space.call(space.w_str, _tup)
            w_18 = space.add(gs_reason_, w_17)
            w_19 = space.newlist([w_3, w_6, w_9, w_12, w_15, w_18])
            _tup = space.newtuple([w_19])
            w_res_20 = space.call(gbltinmethod_join_3, _tup)
            w_21 = w_res_20
            goto = 2

        if goto == 2:
            return w_21
fastf_UnicodeEncodeError___str__ = globals().pop("__str__")

##SECTION##
## filename    'geninterplevel.py'
## function    'test_exceptions'
## firstlineno 1253
##SECTION##
# global declarations
# global object gfunc_test_exceptions
# global object gbltinmethod_keys
# global object g46dict
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

    w_0=w_0=w_1=None

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
# global object gs_pypy_appspace__exceptions
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
# global object gs_StopIteration
# global object gcls_StopIteration
# global object gs_SyntaxWarning
# global object gcls_SyntaxWarning
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
# global object gs_ReferenceError
# global object gcls_ReferenceError
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
# global object gs_SystemExit
# global object gcls_SystemExit
# global object gs_EOFError
# global object gcls_EOFError
# global object gs___file__
# global object gs__home_arigo_svn_pypy_dist_pypy_a
# global object gs_TabError
# global object gcls_TabError
# global object gcls_IndentationError
# global object gcls_SyntaxError
# global object gs_SyntaxError
# global object gs_IndentationError
# global object gs_UnicodeEncodeError
# global object gcls_UnicodeEncodeError
# global object gs_SystemError
# global object gcls_SystemError
# global object gs___name__
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
# global object gs_PendingDeprecationWarning
# global object gcls_PendingDeprecationWarning
# global object gs_UnboundLocalError
# global object gcls_UnboundLocalError
# global object gs_NotImplementedError
# global object gcls_NotImplementedError
# global object gs_AttributeError
# global object gcls_AttributeError
# global object gs_OverflowError
# global object gcls_OverflowError
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
# global object gfunc_SystemExit___init__
# global object gfunc_EnvironmentError___init__
# global object gfunc_EnvironmentError___str__
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
    m.g46dict = space.newdict([])
    m.gs_keys = space.wrap('keys')
    m.gbltinmethod_keys = space.getattr(g46dict, gs_keys)
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
    m.gs_pypy_appspace__exceptions = space.wrap('pypy.appspace._exceptions')
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    m.gs___doc__ = space.wrap('__doc__')
    _doc = space.wrap("""Common base class for all exceptions.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_Exception = space.wrap('Exception')
    _bases = space.newtuple([])
    _args = space.newtuple([gs_Exception, _bases, _dic])
    m.gcls_Exception = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for all standard Python exceptions.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_StandardError = space.wrap('StandardError')
    _bases = space.newtuple([gcls_Exception])
    _args = space.newtuple([gs_StandardError, _bases, _dic])
    m.gcls_StandardError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Out of memory.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_MemoryError, _bases, _dic])
    m.gcls_MemoryError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_MemoryError, gcls_MemoryError)
    m.gs_ImportError = space.wrap('ImportError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Import can't find module, or can't find name in module.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_ImportError, _bases, _dic])
    m.gcls_ImportError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_ImportError, gcls_ImportError)
    m.gs_RuntimeError = space.wrap('RuntimeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Unspecified run-time error.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_RuntimeError, _bases, _dic])
    m.gcls_RuntimeError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_RuntimeError, gcls_RuntimeError)
    m.gs_UnicodeTranslateError = space.wrap('UnicodeTranslateError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Inappropriate argument value (of correct type).""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_ValueError = space.wrap('ValueError')
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_ValueError, _bases, _dic])
    m.gcls_ValueError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Unicode related error.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_UnicodeError = space.wrap('UnicodeError')
    _bases = space.newtuple([gcls_ValueError])
    _args = space.newtuple([gs_UnicodeError, _bases, _dic])
    m.gcls_UnicodeError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Unicode translation error.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_UnicodeError])
    _args = space.newtuple([gs_UnicodeTranslateError, _bases, _dic])
    m.gcls_UnicodeTranslateError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_UnicodeTranslateError, gcls_UnicodeTranslateError)
    m.gs_KeyError = space.wrap('KeyError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for lookup errors.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_LookupError = space.wrap('LookupError')
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_LookupError, _bases, _dic])
    m.gcls_LookupError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Mapping key not found.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_LookupError])
    _args = space.newtuple([gs_KeyError, _bases, _dic])
    m.gcls_KeyError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_KeyError, gcls_KeyError)
    m.gs_StopIteration = space.wrap('StopIteration')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Signal the end from iterator.next().""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Exception])
    _args = space.newtuple([gs_StopIteration, _bases, _dic])
    m.gcls_StopIteration = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_StopIteration, gcls_StopIteration)
    m.gs_SyntaxWarning = space.wrap('SyntaxWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for warning categories.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_Warning = space.wrap('Warning')
    _bases = space.newtuple([gcls_Exception])
    _args = space.newtuple([gs_Warning, _bases, _dic])
    m.gcls_Warning = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for warnings about dubious syntax.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_SyntaxWarning, _bases, _dic])
    m.gcls_SyntaxWarning = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_SyntaxWarning, gcls_SyntaxWarning)
    m.gs_EnvironmentError = space.wrap('EnvironmentError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for I/O related errors.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_EnvironmentError, _bases, _dic])
    m.gcls_EnvironmentError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_EnvironmentError, gcls_EnvironmentError)
    space.setitem(g46dict, gs_LookupError, gcls_LookupError)
    m.gs_OSError = space.wrap('OSError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""OS system call failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_EnvironmentError])
    _args = space.newtuple([gs_OSError, _bases, _dic])
    m.gcls_OSError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_OSError, gcls_OSError)
    m.gs_DeprecationWarning = space.wrap('DeprecationWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for warnings about deprecated features.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_DeprecationWarning, _bases, _dic])
    m.gcls_DeprecationWarning = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_DeprecationWarning, gcls_DeprecationWarning)
    space.setitem(g46dict, gs_UnicodeError, gcls_UnicodeError)
    m.gs_FloatingPointError = space.wrap('FloatingPointError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for arithmetic errors.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_ArithmeticError = space.wrap('ArithmeticError')
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_ArithmeticError, _bases, _dic])
    m.gcls_ArithmeticError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Floating point operation failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_ArithmeticError])
    _args = space.newtuple([gs_FloatingPointError, _bases, _dic])
    m.gcls_FloatingPointError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_FloatingPointError, gcls_FloatingPointError)
    m.gs_ReferenceError = space.wrap('ReferenceError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Weak ref proxy used after referent went away.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_ReferenceError, _bases, _dic])
    m.gcls_ReferenceError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_ReferenceError, gcls_ReferenceError)
    m.gs_NameError = space.wrap('NameError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Name not found globally.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_NameError, _bases, _dic])
    m.gcls_NameError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_NameError, gcls_NameError)
    m.gs_OverflowWarning = space.wrap('OverflowWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for warnings about numeric overflow.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_OverflowWarning, _bases, _dic])
    m.gcls_OverflowWarning = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_OverflowWarning, gcls_OverflowWarning)
    m.gs_IOError = space.wrap('IOError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""I/O operation failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_EnvironmentError])
    _args = space.newtuple([gs_IOError, _bases, _dic])
    m.gcls_IOError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_IOError, gcls_IOError)
    space.setitem(g46dict, gs_ValueError, gcls_ValueError)
    m.gs_FutureWarning = space.wrap('FutureWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for warnings about constructs that will change semantically in the future.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_FutureWarning, _bases, _dic])
    m.gcls_FutureWarning = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_FutureWarning, gcls_FutureWarning)
    m.gs_ZeroDivisionError = space.wrap('ZeroDivisionError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Second argument to a division or modulo operation was zero.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_ArithmeticError])
    _args = space.newtuple([gs_ZeroDivisionError, _bases, _dic])
    m.gcls_ZeroDivisionError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_ZeroDivisionError, gcls_ZeroDivisionError)
    m.gs_SystemExit = space.wrap('SystemExit')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Request to exit from the interpreter.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Exception])
    _args = space.newtuple([gs_SystemExit, _bases, _dic])
    m.gcls_SystemExit = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_SystemExit, gcls_SystemExit)
    space.setitem(g46dict, gs_Exception, gcls_Exception)
    m.gs_EOFError = space.wrap('EOFError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Read beyond end of file.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_EOFError, _bases, _dic])
    m.gcls_EOFError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_EOFError, gcls_EOFError)
    space.setitem(g46dict, gs_StandardError, gcls_StandardError)
    m.gs___file__ = space.wrap('__file__')
    m.gs__home_arigo_svn_pypy_dist_pypy_a = space.wrap('/home/arigo/svn/pypy/dist/pypy/appspace/_exceptions.pyc')
    space.setitem(g46dict, gs___file__, gs__home_arigo_svn_pypy_dist_pypy_a)
    m.gs_TabError = space.wrap('TabError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Invalid syntax.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_SyntaxError = space.wrap('SyntaxError')
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_SyntaxError, _bases, _dic])
    m.gcls_SyntaxError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Improper indentation.""")
    space.setitem(_dic, gs___doc__, _doc)
    m.gs_IndentationError = space.wrap('IndentationError')
    _bases = space.newtuple([gcls_SyntaxError])
    _args = space.newtuple([gs_IndentationError, _bases, _dic])
    m.gcls_IndentationError = space.call(space.w_type, _args)
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Improper mixture of spaces and tabs.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_IndentationError])
    _args = space.newtuple([gs_TabError, _bases, _dic])
    m.gcls_TabError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_TabError, gcls_TabError)
    space.setitem(g46dict, gs_SyntaxError, gcls_SyntaxError)
    m.gs_UnicodeEncodeError = space.wrap('UnicodeEncodeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Unicode encoding error.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_UnicodeError])
    _args = space.newtuple([gs_UnicodeEncodeError, _bases, _dic])
    m.gcls_UnicodeEncodeError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_UnicodeEncodeError, gcls_UnicodeEncodeError)
    m.gs_SystemError = space.wrap('SystemError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Internal error in the Python interpreter.
    
    Please report this to the Python maintainer, along with the traceback,
    the Python version, and the hardware/OS platform and version.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_SystemError, _bases, _dic])
    m.gcls_SystemError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_SystemError, gcls_SystemError)
    m.gs___name__ = space.wrap('__name__')
    space.setitem(g46dict, gs___name__, gs_pypy_appspace__exceptions)
    space.setitem(g46dict, gs_IndentationError, gcls_IndentationError)
    m.gs_AssertionError = space.wrap('AssertionError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Assertion failed.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_AssertionError, _bases, _dic])
    m.gcls_AssertionError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_AssertionError, gcls_AssertionError)
    m.gs_UnicodeDecodeError = space.wrap('UnicodeDecodeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Unicode decoding error.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_UnicodeError])
    _args = space.newtuple([gs_UnicodeDecodeError, _bases, _dic])
    m.gcls_UnicodeDecodeError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_UnicodeDecodeError, gcls_UnicodeDecodeError)
    m.gs_TypeError = space.wrap('TypeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Inappropriate argument type.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_TypeError, _bases, _dic])
    m.gcls_TypeError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_TypeError, gcls_TypeError)
    m.gs_IndexError = space.wrap('IndexError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Sequence index out of range.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_LookupError])
    _args = space.newtuple([gs_IndexError, _bases, _dic])
    m.gcls_IndexError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_IndexError, gcls_IndexError)
    m.gs_RuntimeWarning = space.wrap('RuntimeWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for warnings about dubious runtime behavior.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_RuntimeWarning, _bases, _dic])
    m.gcls_RuntimeWarning = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_RuntimeWarning, gcls_RuntimeWarning)
    m.gs_KeyboardInterrupt = space.wrap('KeyboardInterrupt')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Program interrupted by user.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_KeyboardInterrupt, _bases, _dic])
    m.gcls_KeyboardInterrupt = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_KeyboardInterrupt, gcls_KeyboardInterrupt)
    space.setitem(g46dict, gs___doc__, space.w_None)
    m.gs_UserWarning = space.wrap('UserWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for warnings generated by user code.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_UserWarning, _bases, _dic])
    m.gcls_UserWarning = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_UserWarning, gcls_UserWarning)
    m.gs_PendingDeprecationWarning = space.wrap('PendingDeprecationWarning')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Base class for warnings about features which will be deprecated in the future.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_Warning])
    _args = space.newtuple([gs_PendingDeprecationWarning, _bases, _dic])
    m.gcls_PendingDeprecationWarning = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_PendingDeprecationWarning, gcls_PendingDeprecationWarning)
    m.gs_UnboundLocalError = space.wrap('UnboundLocalError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Local name referenced but not bound to a value.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_NameError])
    _args = space.newtuple([gs_UnboundLocalError, _bases, _dic])
    m.gcls_UnboundLocalError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_UnboundLocalError, gcls_UnboundLocalError)
    space.setitem(g46dict, gs_ArithmeticError, gcls_ArithmeticError)
    space.setitem(g46dict, gs_Warning, gcls_Warning)
    m.gs_NotImplementedError = space.wrap('NotImplementedError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Method or function hasn't been implemented yet.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_RuntimeError])
    _args = space.newtuple([gs_NotImplementedError, _bases, _dic])
    m.gcls_NotImplementedError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_NotImplementedError, gcls_NotImplementedError)
    m.gs_AttributeError = space.wrap('AttributeError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Attribute not found.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_StandardError])
    _args = space.newtuple([gs_AttributeError, _bases, _dic])
    m.gcls_AttributeError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_AttributeError, gcls_AttributeError)
    m.gs_OverflowError = space.wrap('OverflowError')
    _dic = space.newdict([])
    space.setitem(_dic, gs___module__, gs_pypy_appspace__exceptions)
    _doc = space.wrap("""Result too large to be represented.""")
    space.setitem(_dic, gs___doc__, _doc)
    _bases = space.newtuple([gcls_ArithmeticError])
    _args = space.newtuple([gs_OverflowError, _bases, _dic])
    m.gcls_OverflowError = space.call(space.w_type, _args)
    space.setitem(g46dict, gs_OverflowError, gcls_OverflowError)
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
    m.gfunc_SystemExit___init__ = space.wrap(interp2app(f_SystemExit___init__))
    space.setattr(gcls_SystemExit, gs___init__, gfunc_SystemExit___init__)
    m.gfunc_EnvironmentError___init__ = space.wrap(interp2app(f_EnvironmentError___init__))
    space.setattr(gcls_EnvironmentError, gs___init__, gfunc_EnvironmentError___init__)
    m.gfunc_EnvironmentError___str__ = space.wrap(interp2app(f_EnvironmentError___str__))
    space.setattr(gcls_EnvironmentError, gs___str__, gfunc_EnvironmentError___str__)
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
    m.gs_errno = space.wrap('errno')
    m.gs_errno_ = space.wrap('errno=')
    m.gs_strerror = space.wrap('strerror')
    m.gs_strerror_ = space.wrap('strerror=')
    m.gs_filename_ = space.wrap('filename=')
    m.gbltinmethod_join_1 = space.getattr(gs__, gs_join)
    m.gs_code = space.wrap('code')
    m.gbltinmethod_join_2 = space.getattr(gs__, gs_join)
    m.gs_encoding = space.wrap('encoding')
    m.gs_encoding_ = space.wrap('encoding=')
    m.gbltinmethod_join_3 = space.getattr(gs__, gs_join)
    m.gi_5 = space.newint(5)
    m.gbltinmethod_join_4 = space.getattr(gs__, gs_join)

# entry point: test_exceptions, gfunc_test_exceptions)
if __name__ == "__main__":
    from pypy.objspace.std import StdObjSpace
    space = StdObjSpace()
    inittest_exceptions_1(space)
    print space.unwrap(space.call(
            gfunc_test_exceptions, space.newtuple([])))

