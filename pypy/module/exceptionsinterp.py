#!/bin/env python
# -*- coding: LATIN-1 -*-

#*************************************************************

def initexceptions(space):
  """NOT_RPYTHON"""

  __doc__ = \
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

# global declarations
# global object g46dict
# global object gs_MemoryError
# global object gcls_MemoryError
# global object gcls_StandardError
# global object gcls_Exception
# global object gs___module__
# global object gs__exceptions
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
# global object gs_SyntaxWarning
# global object gcls_SyntaxWarning
# global object gcls_Warning
# global object gs_Warning
# global object gs_StopIteration
# global object gcls_StopIteration
# global object gs_PendingDeprecationWarning
# global object gcls_PendingDeprecationWarning
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
# global object gs_SystemExit
# global object gcls_SystemExit
# global object gs_EOFError
# global object gcls_EOFError
# global object gs___file__
# global object gs__home_hpk_pypy_dist_pypy_lib__ex
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
# global object gs_ZeroDivisionError
# global object gcls_ZeroDivisionError
# global object gs_NotImplementedError
# global object gcls_NotImplementedError
# global object gs_SystemError
# global object gcls_SystemError
# global object gs_OverflowError
# global object gcls_OverflowError
# global object gs___init__
# global object gfunc_UnicodeDecodeError___init__
# global object gs___str__
# global object gfunc_UnicodeDecodeError___str__
# global object gfunc_UnicodeEncodeError___init__
# global object gfunc_UnicodeEncodeError___str__
# global object gfunc_SystemExit___init__
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
# global object gfunc_KeyError___str__
# global object gfunc_UnicodeTranslateError___init__
# global object gfunc_UnicodeTranslateError___str__
# global object gs___getitem__
# global object gfunc_Exception___getitem__
# global object gfunc_Exception___init__
# global object gfunc_Exception___str__

##SECTION##
## filename    '/usr/lib/python2.3/posixpath.py'
## function    'split'
## firstlineno 74
##SECTION##
# global declarations
# global object gs_rfind
# global object gs___1
# global object gcls_ValueError_1
# global object gs_rstrip

  def split(space, __args__):
    '''Split a pathname.  Returns tuple "(head, tail)" where "tail" is
    everything after the final slash.  Either part may be empty.'''

    funcname = "split"
    signature = ['p'], None, None
    defaults_w = []
    w_p, = __args__.parse(funcname, signature, defaults_w)
    return fastf_split(space, w_p)

  f_split = split

  def split(space, w_p):
    '''Split a pathname.  Returns tuple "(head, tail)" where "tail" is
    everything after the final slash.  Either part may be empty.'''
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_p, gs_rfind)
            w_1 = space.call_function(w_0, gs___1)
            w_2 = space.add(w_1, gi_1)
            w_3 = space.newslice(space.w_None, w_2, space.w_None)
            w_4 = space.getitem(w_p, w_3)
            w_5 = space.newslice(w_2, space.w_None, space.w_None)
            w_6 = space.getitem(w_p, w_5)
            w_7 = space.newtuple([w_4, w_6])
            w_8 = space.len(w_7)
            w_9 = space.eq(w_8, gi_2)
            v0 = space.is_true(w_9)
            if v0 == True:
                w_10 = w_7
                goto = 2
            else:
                assert v0 == False
                w_etype, w_evalue = space.w_ValueError, space.w_None
                goto = 7

        if goto == 2:
            w_11 = space.getitem(w_10, gi_0)
            w_12 = space.getitem(w_10, gi_1)
            v1 = space.is_true(w_11)
            if v1 == True:
                w_head, w_tail = w_11, w_12
                goto = 3
            else:
                assert v1 == False
                w_head_1, w_tail_1, w_13 = w_11, w_12, w_11
                goto = 4

        if goto == 3:
            w_14 = space.len(w_head)
            w_15 = space.mul(gs___1, w_14)
            w_16 = space.ne(w_head, w_15)
            w_head_1, w_tail_1, w_13 = w_head, w_tail, w_16
            goto = 4

        if goto == 4:
            v2 = space.is_true(w_13)
            if v2 == True:
                w_tail_2, w_17 = w_tail_1, w_head_1
                goto = 5
            else:
                assert v2 == False
                w_18, w_19 = w_head_1, w_tail_1
                goto = 6

        if goto == 5:
            w_20 = space.getattr(w_17, gs_rstrip)
            w_21 = space.call_function(w_20, gs___1)
            w_18, w_19 = w_21, w_tail_2
            goto = 6

        if goto == 6:
            w_22 = space.newtuple([w_18, w_19])
            w_23 = w_22
            goto = 8

        if goto == 7:
            raise gOperationError(w_etype, w_evalue)

        if goto == 8:
            return w_23

  fastf_split = split

##SECTION##
## filename    '/usr/lib/python2.3/posixpath.py'
## function    'basename'
## firstlineno 110
##SECTION##
# global declaration
# global object gfunc_split

  def basename(space, __args__):
    """Returns the final component of a pathname"""

    funcname = "basename"
    signature = ['p'], None, None
    defaults_w = []
    w_p, = __args__.parse(funcname, signature, defaults_w)
    return fastf_basename(space, w_p)

  f_basename = basename

  def basename(space, w_p):
    """Returns the final component of a pathname"""
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf_split(space, w_p)
            w_1 = space.getitem(w_0, gi_1)
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_basename = basename

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__getitem__'
## firstlineno 93
##SECTION##
  def __getitem__(space, __args__):
    funcname = "__getitem__"
    signature = ['self', 'idx'], None, None
    defaults_w = []
    w_self, w_idx = __args__.parse(funcname, signature, defaults_w)
    return fastf_Exception___getitem__(space, w_self, w_idx)

  f_Exception___getitem__ = __getitem__

  def __getitem__(space, w_self, w_idx):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_args)
            w_1 = space.getitem(w_0, w_idx)
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_Exception___getitem__ = __getitem__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__init__'
## firstlineno 97
##SECTION##
  def __init__(space, __args__):
    funcname = "__init__"
    signature = ['self'], 'args', None
    defaults_w = []
    w_self, w_args = __args__.parse(funcname, signature, defaults_w)
    return fastf_Exception___init__(space, w_self, w_args)

  f_Exception___init__ = __init__

  def __init__(space, w_self, w_args):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.setattr(w_self, gs_args, w_args)
            w_1 = space.w_None
            goto = 2

        if goto == 2:
            return w_1

  fastf_Exception___init__ = __init__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__str__'
## firstlineno 101
##SECTION##
# global declarations
# global object gs_args
# global object gi_0
# global object gi_1

  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_Exception___str__(space, w_self)

  f_Exception___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_args)
            w_1 = space.len(w_0)
            w_2 = space.eq(w_1, gi_0)
            v0 = space.is_true(w_2)
            if v0 == True:
                w_3 = gs__emptystr_
                goto = 5
            else:
                assert v0 == False
                w_args, w_4 = w_0, w_1
                goto = 2

        if goto == 2:
            w_5 = space.eq(w_4, gi_1)
            v1 = space.is_true(w_5)
            if v1 == True:
                w_6 = w_args
                goto = 3
            else:
                assert v1 == False
                w_7 = w_args
                goto = 4

        if goto == 3:
            w_8 = space.getitem(w_6, gi_0)
            w_9 = space.str(w_8)
            w_3 = w_9
            goto = 5

        if goto == 4:
            w_10 = space.str(w_7)
            w_3 = w_10
            goto = 5

        if goto == 5:
            return w_3

  fastf_Exception___str__ = __str__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__init__'
## firstlineno 130
##SECTION##
# global declarations
# global object gi_4
# global object gi_2
# global object gi_3

  def __init__(space, __args__):
    funcname = "__init__"
    signature = ['self'], 'args', None
    defaults_w = []
    w_self, w_args = __args__.parse(funcname, signature, defaults_w)
    return fastf_UnicodeTranslateError___init__(space, w_self, w_args)

  f_UnicodeTranslateError___init__ = __init__

  def __init__(space, w_self, w_args):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.len(w_args)
            w_1 = space.setattr(w_self, gs_args, w_args)
            w_2 = space.eq(w_0, gi_4)
            v0 = space.is_true(w_2)
            if v0 == True:
                w_self_1, w_args_1 = w_self, w_args
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_None
                goto = 3

        if goto == 2:
            w_4 = space.getitem(w_args_1, gi_0)
            w_5 = space.setattr(w_self_1, gs_object, w_4)
            w_6 = space.getitem(w_args_1, gi_1)
            w_7 = space.setattr(w_self_1, gs_start, w_6)
            w_8 = space.getitem(w_args_1, gi_2)
            w_9 = space.setattr(w_self_1, gs_end, w_8)
            w_10 = space.getitem(w_args_1, gi_3)
            w_11 = space.setattr(w_self_1, gs_reason, w_10)
            w_3 = space.w_None
            goto = 3

        if goto == 3:
            return w_3

  fastf_UnicodeTranslateError___init__ = __init__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__str__'
## firstlineno 140
##SECTION##
# global declarations
# global object gs_getattr
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

  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_UnicodeTranslateError___str__(space, w_self)

  f_UnicodeTranslateError___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_start, space.w_None)
            w_1 = space.str(w_0)
            w_2 = space.add(gs_start_, w_1)
            w_3 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_reason, space.w_None)
            w_4 = space.str(w_3)
            w_5 = space.add(gs_reason_, w_4)
            w_6 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_args, space.w_None)
            w_7 = space.str(w_6)
            w_8 = space.add(gs_args_, w_7)
            w_9 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_end, space.w_None)
            w_10 = space.str(w_9)
            w_11 = space.add(gs_end_, w_10)
            w_12 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_object, space.w_None)
            w_13 = space.str(w_12)
            w_14 = space.add(gs_object_, w_13)
            w_15 = space.newlist([w_2, w_5, w_8, w_11, w_14])
            w_16 = space.call_function(gbltinmethod_join, w_15)
            w_17 = w_16
            goto = 2

        if goto == 2:
            return w_17

  fastf_UnicodeTranslateError___str__ = __str__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__str__'
## firstlineno 158
##SECTION##
  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_KeyError___str__(space, w_self)

  f_KeyError___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_args)
            w_1 = space.len(w_0)
            w_2 = space.eq(w_1, gi_0)
            v0 = space.is_true(w_2)
            if v0 == True:
                w_3 = gs__emptystr_
                goto = 5
            else:
                assert v0 == False
                w_args, w_4 = w_0, w_1
                goto = 2

        if goto == 2:
            w_5 = space.eq(w_4, gi_1)
            v1 = space.is_true(w_5)
            if v1 == True:
                w_6 = w_args
                goto = 3
            else:
                assert v1 == False
                w_7 = w_args
                goto = 4

        if goto == 3:
            w_8 = space.getitem(w_6, gi_0)
            w_9 = space.repr(w_8)
            w_3 = w_9
            goto = 5

        if goto == 4:
            w_10 = space.str(w_7)
            w_3 = w_10
            goto = 5

        if goto == 5:
            return w_3

  fastf_KeyError___str__ = __str__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__init__'
## firstlineno 181
##SECTION##
  def __init__(space, __args__):
    funcname = "__init__"
    signature = ['self'], 'args', None
    defaults_w = []
    w_self, w_args = __args__.parse(funcname, signature, defaults_w)
    return fastf_EnvironmentError___init__(space, w_self, w_args)

  f_EnvironmentError___init__ = __init__

  def __init__(space, w_self, w_args):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.len(w_args)
            w_1 = space.setattr(w_self, gs_args, w_args)
            w_2 = space.setattr(w_self, gs_errno, space.w_None)
            w_3 = space.setattr(w_self, gs_strerror, space.w_None)
            w_4 = space.setattr(w_self, gs_filename, space.w_None)
            w_5 = space.le(gi_2, w_0)
            v0 = space.is_true(w_5)
            if v0 == True:
                w_self_1, w_args_1, w_argc = w_self, w_args, w_0
                goto = 2
            else:
                assert v0 == False
                w_self_2, w_args_2, w_argc_1, w_6 = w_self, w_args, w_0, w_5
                goto = 3

        if goto == 2:
            w_7 = space.le(w_argc, gi_3)
            (w_self_2, w_args_2, w_argc_1, w_6) = (w_self_1, w_args_1, w_argc,
             w_7)
            goto = 3

        if goto == 3:
            v1 = space.is_true(w_6)
            if v1 == True:
                w_self_3, w_args_3, w_argc_2 = w_self_2, w_args_2, w_argc_1
                goto = 4
            else:
                assert v1 == False
                w_self_4, w_args_4, w_8 = w_self_2, w_args_2, w_argc_1
                goto = 5

        if goto == 4:
            w_9 = space.getitem(w_args_3, gi_0)
            w_10 = space.setattr(w_self_3, gs_errno, w_9)
            w_11 = space.getitem(w_args_3, gi_1)
            w_12 = space.setattr(w_self_3, gs_strerror, w_11)
            w_self_4, w_args_4, w_8 = w_self_3, w_args_3, w_argc_2
            goto = 5

        if goto == 5:
            w_13 = space.eq(w_8, gi_3)
            v2 = space.is_true(w_13)
            if v2 == True:
                w_self_5, w_args_5 = w_self_4, w_args_4
                goto = 6
            else:
                assert v2 == False
                w_14 = space.w_None
                goto = 7

        if goto == 6:
            w_15 = space.getitem(w_args_5, gi_2)
            w_16 = space.setattr(w_self_5, gs_filename, w_15)
            w_17 = space.getitem(w_args_5, gi_0)
            w_18 = space.getitem(w_args_5, gi_1)
            w_19 = space.newtuple([w_17, w_18])
            w_20 = space.setattr(w_self_5, gs_args, w_19)
            w_14 = space.w_None
            goto = 7

        if goto == 7:
            return w_14

  fastf_EnvironmentError___init__ = __init__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__str__'
## firstlineno 194
##SECTION##
# global declarations
# global object gs_errno
# global object gs_strerror
# global object gs__Errno__s___s___s
# global object gs__Errno__s___s

  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_EnvironmentError___str__(space, w_self)

  f_EnvironmentError___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_filename)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_self_1 = w_self
                goto = 3
            else:
                assert v0 == False
                w_self_2 = w_self
                goto = 2

        if goto == 2:
            w_2 = space.getattr(w_self_2, gs_errno)
            w_3 = space.getattr(w_self_2, gs_strerror)
            w_4 = space.getattr(w_self_2, gs_filename)
            w_5 = space.newtuple([w_2, w_3, w_4])
            w_6 = space.mod(gs__Errno__s___s___s, w_5)
            w_7 = w_6
            goto = 8

        if goto == 3:
            w_8 = space.getattr(w_self_1, gs_errno)
            v1 = space.is_true(w_8)
            if v1 == True:
                w_self_3 = w_self_1
                goto = 4
            else:
                assert v1 == False
                w_self_4, w_9 = w_self_1, w_8
                goto = 5

        if goto == 4:
            w_10 = space.getattr(w_self_3, gs_strerror)
            w_self_4, w_9 = w_self_3, w_10
            goto = 5

        if goto == 5:
            v2 = space.is_true(w_9)
            if v2 == True:
                w_self_5 = w_self_4
                goto = 6
            else:
                assert v2 == False
                w_11 = w_self_4
                goto = 7

        if goto == 6:
            w_12 = space.getattr(w_self_5, gs_errno)
            w_13 = space.getattr(w_self_5, gs_strerror)
            w_14 = space.newtuple([w_12, w_13])
            w_15 = space.mod(gs__Errno__s___s, w_14)
            w_7 = w_15
            goto = 8

        if goto == 7:
            w_16 = fastf_Exception___str__(space, w_11)
            w_7 = w_16
            goto = 8

        if goto == 8:
            return w_7

  fastf_EnvironmentError___str__ = __str__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__init__'
## firstlineno 238
##SECTION##
  def __init__(space, __args__):
    funcname = "__init__"
    signature = ['self'], 'args', None
    defaults_w = []
    w_self, w_args = __args__.parse(funcname, signature, defaults_w)
    return fastf_SyntaxError___init__(space, w_self, w_args)

  f_SyntaxError___init__ = __init__

  def __init__(space, w_self, w_args):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.len(w_args)
            w_1 = space.setattr(w_self, gs_args, w_args)
            w_2 = space.ge(w_0, gi_1)
            v0 = space.is_true(w_2)
            if v0 == True:
                w_self_1, w_args_1, w_argc = w_self, w_args, w_0
                goto = 2
            else:
                assert v0 == False
                w_self_2, w_args_2, w_3 = w_self, w_args, w_0
                goto = 3

        if goto == 2:
            w_4 = space.getitem(w_args_1, gi_0)
            w_5 = space.setattr(w_self_1, gs_msg, w_4)
            w_self_2, w_args_2, w_3 = w_self_1, w_args_1, w_argc
            goto = 3

        if goto == 3:
            w_6 = space.eq(w_3, gi_2)
            v1 = space.is_true(w_6)
            if v1 == True:
                w_self_3, w_args_3 = w_self_2, w_args_2
                goto = 4
            else:
                assert v1 == False
                w_7 = space.w_None
                goto = 5

        if goto == 4:
            w_8 = space.getitem(w_args_3, gi_1)
            w_9 = space.getitem(w_8, gi_0)
            w_10 = space.setattr(w_self_3, gs_filename, w_9)
            w_11 = space.getitem(w_args_3, gi_1)
            w_12 = space.getitem(w_11, gi_1)
            w_13 = space.setattr(w_self_3, gs_lineno, w_12)
            w_14 = space.getitem(w_args_3, gi_1)
            w_15 = space.getitem(w_14, gi_2)
            w_16 = space.setattr(w_self_3, gs_offset, w_15)
            w_17 = space.getitem(w_args_3, gi_1)
            w_18 = space.getitem(w_17, gi_3)
            w_19 = space.setattr(w_self_3, gs_text, w_18)
            w_7 = space.w_None
            goto = 5

        if goto == 5:
            return w_7

  fastf_SyntaxError___init__ = __init__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__str__'
## firstlineno 249
##SECTION##
# global declarations
# global object gs____
# global object gfunc_basename
# global object gs__s___s__line__ld_
# global object gs__s___s_
# global object gs__s__line__ld_

  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_SyntaxError___str__(space, w_self)

  f_SyntaxError___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.getattr(w_self, gs_msg)
            w_1 = space.type(w_0)
            w_2 = space.is_(w_1, space.w_str)
            v0 = space.is_true(w_2)
            if v0 == True:
                w_self_1 = w_self
                goto = 3
            else:
                assert v0 == False
                w_3 = w_self
                goto = 2

        if goto == 2:
            w_4 = space.getattr(w_3, gs_msg)
            w_5 = w_4
            goto = 13

        if goto == 3:
            w_6 = space.getattr(w_self_1, gs_msg)
            w_7 = space.getattr(w_self_1, gs_filename)
            w_8 = space.type(w_7)
            w_9 = space.is_(w_8, space.w_str)
            w_10 = space.getattr(w_self_1, gs_lineno)
            w_11 = space.type(w_10)
            w_12 = space.is_(w_11, space.w_int)
            v1 = space.is_true(w_9)
            if v1 == True:
                (w_self_2, w_buffer, w_have_lineno, w_have_filename,
                 w_13) = (w_self_1, w_6, w_12, w_9, w_9)
                goto = 4
            else:
                assert v1 == False
                (w_self_2, w_buffer, w_have_lineno, w_have_filename,
                 w_13) = (w_self_1, w_6, w_12, w_9, w_12)
                goto = 4

        if goto == 4:
            v2 = space.is_true(w_13)
            if v2 == True:
                (w_self_3, w_buffer_1, w_have_lineno_1,
                 w_have_filename_1) = (w_self_2, w_buffer, w_have_lineno,
                 w_have_filename)
                goto = 5
            else:
                assert v2 == False
                w_5 = w_buffer
                goto = 13

        if goto == 5:
            w_14 = space.getattr(w_self_3, gs_filename)
            v3 = space.is_true(w_14)
            if v3 == True:
                (w_self_4, w_buffer_2, w_have_lineno_2, w_have_filename_2,
                 w_15) = (w_self_3, w_buffer_1, w_have_lineno_1,
                 w_have_filename_1, w_14)
                goto = 6
            else:
                assert v3 == False
                (w_self_4, w_buffer_2, w_have_lineno_2, w_have_filename_2,
                 w_15) = (w_self_3, w_buffer_1, w_have_lineno_1,
                 w_have_filename_1, gs____)
                goto = 6

        if goto == 6:
            w_16 = fastf_basename(space, w_15)
            v4 = space.is_true(w_have_filename_2)
            if v4 == True:
                (w_self_5, w_fname, w_buffer_3, w_have_lineno_3,
                 w_have_filename_3, w_17) = (w_self_4, w_16, w_buffer_2,
                 w_have_lineno_2, w_have_filename_2, w_have_lineno_2)
                goto = 7
            else:
                assert v4 == False
                (w_self_5, w_fname, w_buffer_3, w_have_lineno_3,
                 w_have_filename_3, w_17) = (w_self_4, w_16, w_buffer_2,
                 w_have_lineno_2, w_have_filename_2, w_have_filename_2)
                goto = 7

        if goto == 7:
            v5 = space.is_true(w_17)
            if v5 == True:
                w_self_6, w_fname_1 = w_self_5, w_fname
                goto = 8
            else:
                assert v5 == False
                (w_self_7, w_fname_2, w_buffer_4, w_have_lineno_4,
                 w_18) = (w_self_5, w_fname, w_buffer_3, w_have_lineno_3,
                 w_have_filename_3)
                goto = 9

        if goto == 8:
            w_19 = space.getattr(w_self_6, gs_msg)
            w_20 = space.getattr(w_self_6, gs_lineno)
            w_21 = space.newtuple([w_19, w_fname_1, w_20])
            w_22 = space.mod(gs__s___s__line__ld_, w_21)
            w_5 = w_22
            goto = 13

        if goto == 9:
            v6 = space.is_true(w_18)
            if v6 == True:
                w_fname_3, w_23 = w_fname_2, w_self_7
                goto = 10
            else:
                assert v6 == False
                (w_self_8, w_buffer_5, w_24) = (w_self_7, w_buffer_4,
                 w_have_lineno_4)
                goto = 11

        if goto == 10:
            w_25 = space.getattr(w_23, gs_msg)
            w_26 = space.newtuple([w_25, w_fname_3])
            w_27 = space.mod(gs__s___s_, w_26)
            w_5 = w_27
            goto = 13

        if goto == 11:
            v7 = space.is_true(w_24)
            if v7 == True:
                w_self_9 = w_self_8
                goto = 12
            else:
                assert v7 == False
                w_5 = w_buffer_5
                goto = 13

        if goto == 12:
            w_28 = space.getattr(w_self_9, gs_msg)
            w_29 = space.getattr(w_self_9, gs_lineno)
            w_30 = space.newtuple([w_28, w_29])
            w_31 = space.mod(gs__s__line__ld_, w_30)
            w_5 = w_31
            goto = 13

        if goto == 13:
            return w_5

  fastf_SyntaxError___str__ = __str__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__init__'
## firstlineno 275
##SECTION##
# global declaration
# global object gs_code

  def __init__(space, __args__):
    funcname = "__init__"
    signature = ['self'], 'args', None
    defaults_w = []
    w_self, w_args = __args__.parse(funcname, signature, defaults_w)
    return fastf_SystemExit___init__(space, w_self, w_args)

  f_SystemExit___init__ = __init__

  def __init__(space, w_self, w_args):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.len(w_args)
            w_1 = space.eq(w_0, gi_0)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_self_1, w_args_1, w_argc = w_self, w_args, w_0
                goto = 2
            else:
                assert v0 == False
                w_self_2, w_args_2, w_argc_1 = w_self, w_args, w_0
                goto = 3

        if goto == 2:
            w_2 = space.setattr(w_self_1, gs_code, space.w_None)
            w_self_2, w_args_2, w_argc_1 = w_self_1, w_args_1, w_argc
            goto = 3

        if goto == 3:
            w_3 = space.setattr(w_self_2, gs_args, w_args_2)
            w_4 = space.eq(w_argc_1, gi_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_self_3, w_args_3, w_argc_2 = w_self_2, w_args_2, w_argc_1
                goto = 4
            else:
                assert v1 == False
                w_self_4, w_args_4, w_5 = w_self_2, w_args_2, w_argc_1
                goto = 5

        if goto == 4:
            w_6 = space.getitem(w_args_3, gi_0)
            w_7 = space.setattr(w_self_3, gs_code, w_6)
            w_self_4, w_args_4, w_5 = w_self_3, w_args_3, w_argc_2
            goto = 5

        if goto == 5:
            w_8 = space.ge(w_5, gi_2)
            v2 = space.is_true(w_8)
            if v2 == True:
                w_9, w_10 = w_args_4, w_self_4
                goto = 6
            else:
                assert v2 == False
                w_11 = space.w_None
                goto = 7

        if goto == 6:
            w_12 = space.setattr(w_10, gs_code, w_9)
            w_11 = space.w_None
            goto = 7

        if goto == 7:
            return w_11

  fastf_SystemExit___init__ = __init__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__init__'
## firstlineno 310
##SECTION##
  def __init__(space, __args__):
    funcname = "__init__"
    signature = ['self'], 'args', None
    defaults_w = []
    w_self, w_args = __args__.parse(funcname, signature, defaults_w)
    return fastf_UnicodeDecodeError___init__(space, w_self, w_args)

  f_UnicodeDecodeError___init__ = __init__

  def __init__(space, w_self, w_args):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.len(w_args)
            w_1 = space.setattr(w_self, gs_args, w_args)
            w_2 = space.eq(w_0, gi_5)
            v0 = space.is_true(w_2)
            if v0 == True:
                w_self_1, w_args_1 = w_self, w_args
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_None
                goto = 3

        if goto == 2:
            w_4 = space.getitem(w_args_1, gi_0)
            w_5 = space.setattr(w_self_1, gs_encoding, w_4)
            w_6 = space.getitem(w_args_1, gi_1)
            w_7 = space.setattr(w_self_1, gs_object, w_6)
            w_8 = space.getitem(w_args_1, gi_2)
            w_9 = space.setattr(w_self_1, gs_start, w_8)
            w_10 = space.getitem(w_args_1, gi_3)
            w_11 = space.setattr(w_self_1, gs_end, w_10)
            w_12 = space.getitem(w_args_1, gi_4)
            w_13 = space.setattr(w_self_1, gs_reason, w_12)
            w_3 = space.w_None
            goto = 3

        if goto == 3:
            return w_3

  fastf_UnicodeDecodeError___init__ = __init__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__str__'
## firstlineno 321
##SECTION##
  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_UnicodeDecodeError___str__(space, w_self)

  f_UnicodeDecodeError___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_object, space.w_None)
            w_1 = space.str(w_0)
            w_2 = space.add(gs_object_, w_1)
            w_3 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_end, space.w_None)
            w_4 = space.str(w_3)
            w_5 = space.add(gs_end_, w_4)
            w_6 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_encoding, space.w_None)
            w_7 = space.str(w_6)
            w_8 = space.add(gs_encoding_, w_7)
            w_9 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_args, space.w_None)
            w_10 = space.str(w_9)
            w_11 = space.add(gs_args_, w_10)
            w_12 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_start, space.w_None)
            w_13 = space.str(w_12)
            w_14 = space.add(gs_start_, w_13)
            w_15 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_reason, space.w_None)
            w_16 = space.str(w_15)
            w_17 = space.add(gs_reason_, w_16)
            w_18 = space.newlist([w_2, w_5, w_8, w_11, w_14, w_17])
            w_19 = space.call_function(gbltinmethod_join, w_18)
            w_20 = w_19
            goto = 2

        if goto == 2:
            return w_20

  fastf_UnicodeDecodeError___str__ = __str__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__init__'
## firstlineno 370
##SECTION##
# global declaration
# global object gi_5

  def __init__(space, __args__):
    funcname = "__init__"
    signature = ['self'], 'args', None
    defaults_w = []
    w_self, w_args = __args__.parse(funcname, signature, defaults_w)
    return fastf_UnicodeEncodeError___init__(space, w_self, w_args)

  f_UnicodeEncodeError___init__ = __init__

  def __init__(space, w_self, w_args):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.len(w_args)
            w_1 = space.setattr(w_self, gs_args, w_args)
            w_2 = space.eq(w_0, gi_5)
            v0 = space.is_true(w_2)
            if v0 == True:
                w_self_1, w_args_1 = w_self, w_args
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_None
                goto = 3

        if goto == 2:
            w_4 = space.getitem(w_args_1, gi_0)
            w_5 = space.setattr(w_self_1, gs_encoding, w_4)
            w_6 = space.getitem(w_args_1, gi_1)
            w_7 = space.setattr(w_self_1, gs_object, w_6)
            w_8 = space.getitem(w_args_1, gi_2)
            w_9 = space.setattr(w_self_1, gs_start, w_8)
            w_10 = space.getitem(w_args_1, gi_3)
            w_11 = space.setattr(w_self_1, gs_end, w_10)
            w_12 = space.getitem(w_args_1, gi_4)
            w_13 = space.setattr(w_self_1, gs_reason, w_12)
            w_3 = space.w_None
            goto = 3

        if goto == 3:
            return w_3

  fastf_UnicodeEncodeError___init__ = __init__

##SECTION##
## filename    'lib/_exceptions.py'
## function    '__str__'
## firstlineno 381
##SECTION##
# global declarations
# global object gs_encoding
# global object gs_encoding_

  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_UnicodeEncodeError___str__(space, w_self)

  f_UnicodeEncodeError___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_object, space.w_None)
            w_1 = space.str(w_0)
            w_2 = space.add(gs_object_, w_1)
            w_3 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_end, space.w_None)
            w_4 = space.str(w_3)
            w_5 = space.add(gs_end_, w_4)
            w_6 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_encoding, space.w_None)
            w_7 = space.str(w_6)
            w_8 = space.add(gs_encoding_, w_7)
            w_9 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_args, space.w_None)
            w_10 = space.str(w_9)
            w_11 = space.add(gs_args_, w_10)
            w_12 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_start, space.w_None)
            w_13 = space.str(w_12)
            w_14 = space.add(gs_start_, w_13)
            w_15 = space.call_function((space.builtin.get(space.str_w(gs_getattr))), w_self, gs_reason, space.w_None)
            w_16 = space.str(w_15)
            w_17 = space.add(gs_reason_, w_16)
            w_18 = space.newlist([w_2, w_5, w_8, w_11, w_14, w_17])
            w_19 = space.call_function(gbltinmethod_join, w_18)
            w_20 = w_19
            goto = 2

        if goto == 2:
            return w_20

  fastf_UnicodeEncodeError___str__ = __str__

##SECTION##
  w__doc__ = space.wrap(__doc__)
  g46dict = space.newdict([])
  gs_MemoryError = space.wrap('MemoryError')
  _dic = space.newdict([])
  gs___module__ = space.wrap('__module__')
  gs__exceptions = space.wrap('_exceptions')
  space.setitem(_dic, gs___module__, gs__exceptions)
  gs___doc__ = space.wrap('__doc__')
  _doc = space.wrap("""Common base class for all exceptions.""")
  space.setitem(_dic, gs___doc__, _doc)
  gs_Exception = space.wrap('Exception')
  _bases = space.newtuple([])
  _args = space.newtuple([gs_Exception, _bases, _dic])
  gcls_Exception = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for all standard Python exceptions.""")
  space.setitem(_dic, gs___doc__, _doc)
  gs_StandardError = space.wrap('StandardError')
  _bases = space.newtuple([gcls_Exception])
  _args = space.newtuple([gs_StandardError, _bases, _dic])
  gcls_StandardError = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Out of memory.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_MemoryError, _bases, _dic])
  gcls_MemoryError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_MemoryError, gcls_MemoryError)
  gs_ImportError = space.wrap('ImportError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Import can't find module, or can't find name in module.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_ImportError, _bases, _dic])
  gcls_ImportError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_ImportError, gcls_ImportError)
  gs_RuntimeError = space.wrap('RuntimeError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Unspecified run-time error.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_RuntimeError, _bases, _dic])
  gcls_RuntimeError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_RuntimeError, gcls_RuntimeError)
  gs_UnicodeTranslateError = space.wrap('UnicodeTranslateError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Inappropriate argument value (of correct type).""")
  space.setitem(_dic, gs___doc__, _doc)
  gs_ValueError = space.wrap('ValueError')
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_ValueError, _bases, _dic])
  gcls_ValueError = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Unicode related error.""")
  space.setitem(_dic, gs___doc__, _doc)
  gs_UnicodeError = space.wrap('UnicodeError')
  _bases = space.newtuple([gcls_ValueError])
  _args = space.newtuple([gs_UnicodeError, _bases, _dic])
  gcls_UnicodeError = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Unicode translation error.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_UnicodeError])
  _args = space.newtuple([gs_UnicodeTranslateError, _bases, _dic])
  gcls_UnicodeTranslateError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_UnicodeTranslateError, gcls_UnicodeTranslateError)
  gs_KeyError = space.wrap('KeyError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for lookup errors.""")
  space.setitem(_dic, gs___doc__, _doc)
  gs_LookupError = space.wrap('LookupError')
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_LookupError, _bases, _dic])
  gcls_LookupError = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Mapping key not found.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_LookupError])
  _args = space.newtuple([gs_KeyError, _bases, _dic])
  gcls_KeyError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_KeyError, gcls_KeyError)
  gs_SyntaxWarning = space.wrap('SyntaxWarning')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for warning categories.""")
  space.setitem(_dic, gs___doc__, _doc)
  gs_Warning = space.wrap('Warning')
  _bases = space.newtuple([gcls_Exception])
  _args = space.newtuple([gs_Warning, _bases, _dic])
  gcls_Warning = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for warnings about dubious syntax.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Warning])
  _args = space.newtuple([gs_SyntaxWarning, _bases, _dic])
  gcls_SyntaxWarning = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_SyntaxWarning, gcls_SyntaxWarning)
  gs_StopIteration = space.wrap('StopIteration')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Signal the end from iterator.next().""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Exception])
  _args = space.newtuple([gs_StopIteration, _bases, _dic])
  gcls_StopIteration = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_StopIteration, gcls_StopIteration)
  gs_PendingDeprecationWarning = space.wrap('PendingDeprecationWarning')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for warnings about features which will be deprecated in the future.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Warning])
  _args = space.newtuple([gs_PendingDeprecationWarning, _bases, _dic])
  gcls_PendingDeprecationWarning = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_PendingDeprecationWarning, gcls_PendingDeprecationWarning)
  gs_EnvironmentError = space.wrap('EnvironmentError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for I/O related errors.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_EnvironmentError, _bases, _dic])
  gcls_EnvironmentError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_EnvironmentError, gcls_EnvironmentError)
  space.setitem(g46dict, gs_LookupError, gcls_LookupError)
  gs_OSError = space.wrap('OSError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""OS system call failed.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_EnvironmentError])
  _args = space.newtuple([gs_OSError, _bases, _dic])
  gcls_OSError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_OSError, gcls_OSError)
  gs_DeprecationWarning = space.wrap('DeprecationWarning')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for warnings about deprecated features.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Warning])
  _args = space.newtuple([gs_DeprecationWarning, _bases, _dic])
  gcls_DeprecationWarning = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_DeprecationWarning, gcls_DeprecationWarning)
  space.setitem(g46dict, gs_UnicodeError, gcls_UnicodeError)
  gs_FloatingPointError = space.wrap('FloatingPointError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for arithmetic errors.""")
  space.setitem(_dic, gs___doc__, _doc)
  gs_ArithmeticError = space.wrap('ArithmeticError')
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_ArithmeticError, _bases, _dic])
  gcls_ArithmeticError = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Floating point operation failed.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_ArithmeticError])
  _args = space.newtuple([gs_FloatingPointError, _bases, _dic])
  gcls_FloatingPointError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_FloatingPointError, gcls_FloatingPointError)
  gs_AttributeError = space.wrap('AttributeError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Attribute not found.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_AttributeError, _bases, _dic])
  gcls_AttributeError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_AttributeError, gcls_AttributeError)
  gs_IndentationError = space.wrap('IndentationError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Invalid syntax.""")
  space.setitem(_dic, gs___doc__, _doc)
  gs_SyntaxError = space.wrap('SyntaxError')
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_SyntaxError, _bases, _dic])
  gcls_SyntaxError = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Improper indentation.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_SyntaxError])
  _args = space.newtuple([gs_IndentationError, _bases, _dic])
  gcls_IndentationError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_IndentationError, gcls_IndentationError)
  gs_NameError = space.wrap('NameError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Name not found globally.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_NameError, _bases, _dic])
  gcls_NameError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_NameError, gcls_NameError)
  gs_OverflowWarning = space.wrap('OverflowWarning')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for warnings about numeric overflow.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Warning])
  _args = space.newtuple([gs_OverflowWarning, _bases, _dic])
  gcls_OverflowWarning = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_OverflowWarning, gcls_OverflowWarning)
  gs_IOError = space.wrap('IOError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""I/O operation failed.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_EnvironmentError])
  _args = space.newtuple([gs_IOError, _bases, _dic])
  gcls_IOError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_IOError, gcls_IOError)
  space.setitem(g46dict, gs_ValueError, gcls_ValueError)
  gs_FutureWarning = space.wrap('FutureWarning')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for warnings about constructs that will change semantically in the future.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Warning])
  _args = space.newtuple([gs_FutureWarning, _bases, _dic])
  gcls_FutureWarning = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_FutureWarning, gcls_FutureWarning)
  gs_SystemExit = space.wrap('SystemExit')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Request to exit from the interpreter.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Exception])
  _args = space.newtuple([gs_SystemExit, _bases, _dic])
  gcls_SystemExit = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_SystemExit, gcls_SystemExit)
  space.setitem(g46dict, gs_Exception, gcls_Exception)
  gs_EOFError = space.wrap('EOFError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Read beyond end of file.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_EOFError, _bases, _dic])
  gcls_EOFError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_EOFError, gcls_EOFError)
  space.setitem(g46dict, gs_StandardError, gcls_StandardError)
  gs___file__ = space.wrap('__file__')
  gs__home_hpk_pypy_dist_pypy_lib__ex = space.wrap(
"""/home/hpk/pypy-dist/pypy/lib/_exceptions.py""")
  space.setitem(g46dict, gs___file__, gs__home_hpk_pypy_dist_pypy_lib__ex)
  gs_TabError = space.wrap('TabError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Improper mixture of spaces and tabs.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_IndentationError])
  _args = space.newtuple([gs_TabError, _bases, _dic])
  gcls_TabError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_TabError, gcls_TabError)
  space.setitem(g46dict, gs_SyntaxError, gcls_SyntaxError)
  gs_UnicodeEncodeError = space.wrap('UnicodeEncodeError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Unicode encoding error.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_UnicodeError])
  _args = space.newtuple([gs_UnicodeEncodeError, _bases, _dic])
  gcls_UnicodeEncodeError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_UnicodeEncodeError, gcls_UnicodeEncodeError)
  gs_UnboundLocalError = space.wrap('UnboundLocalError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Local name referenced but not bound to a value.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_NameError])
  _args = space.newtuple([gs_UnboundLocalError, _bases, _dic])
  gcls_UnboundLocalError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_UnboundLocalError, gcls_UnboundLocalError)
  gs___name__ = space.wrap('__name__')
  space.setitem(g46dict, gs___name__, gs__exceptions)
  gs_ReferenceError = space.wrap('ReferenceError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Weak ref proxy used after referent went away.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_ReferenceError, _bases, _dic])
  gcls_ReferenceError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_ReferenceError, gcls_ReferenceError)
  gs_AssertionError = space.wrap('AssertionError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Assertion failed.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_AssertionError, _bases, _dic])
  gcls_AssertionError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_AssertionError, gcls_AssertionError)
  gs_UnicodeDecodeError = space.wrap('UnicodeDecodeError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Unicode decoding error.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_UnicodeError])
  _args = space.newtuple([gs_UnicodeDecodeError, _bases, _dic])
  gcls_UnicodeDecodeError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_UnicodeDecodeError, gcls_UnicodeDecodeError)
  gs_TypeError = space.wrap('TypeError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Inappropriate argument type.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_TypeError, _bases, _dic])
  gcls_TypeError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_TypeError, gcls_TypeError)
  gs_IndexError = space.wrap('IndexError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Sequence index out of range.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_LookupError])
  _args = space.newtuple([gs_IndexError, _bases, _dic])
  gcls_IndexError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_IndexError, gcls_IndexError)
  gs_RuntimeWarning = space.wrap('RuntimeWarning')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for warnings about dubious runtime behavior.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Warning])
  _args = space.newtuple([gs_RuntimeWarning, _bases, _dic])
  gcls_RuntimeWarning = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_RuntimeWarning, gcls_RuntimeWarning)
  gs_KeyboardInterrupt = space.wrap('KeyboardInterrupt')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Program interrupted by user.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_KeyboardInterrupt, _bases, _dic])
  gcls_KeyboardInterrupt = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_KeyboardInterrupt, gcls_KeyboardInterrupt)
  gs_UserWarning = space.wrap('UserWarning')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Base class for warnings generated by user code.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_Warning])
  _args = space.newtuple([gs_UserWarning, _bases, _dic])
  gcls_UserWarning = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_UserWarning, gcls_UserWarning)
  gs_ZeroDivisionError = space.wrap('ZeroDivisionError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Second argument to a division or modulo operation was zero.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_ArithmeticError])
  _args = space.newtuple([gs_ZeroDivisionError, _bases, _dic])
  gcls_ZeroDivisionError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_ZeroDivisionError, gcls_ZeroDivisionError)
  space.setitem(g46dict, gs___doc__, w__doc__)
  space.setitem(g46dict, gs_ArithmeticError, gcls_ArithmeticError)
  space.setitem(g46dict, gs_Warning, gcls_Warning)
  gs_NotImplementedError = space.wrap('NotImplementedError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Method or function hasn't been implemented yet.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_RuntimeError])
  _args = space.newtuple([gs_NotImplementedError, _bases, _dic])
  gcls_NotImplementedError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_NotImplementedError, gcls_NotImplementedError)
  gs_SystemError = space.wrap('SystemError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Internal error in the Python interpreter.

Please report this to the Python maintainer, along with the traceback,
the Python version, and the hardware/OS platform and version.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_StandardError])
  _args = space.newtuple([gs_SystemError, _bases, _dic])
  gcls_SystemError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_SystemError, gcls_SystemError)
  gs_OverflowError = space.wrap('OverflowError')
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__exceptions)
  _doc = space.wrap("""Result too large to be represented.""")
  space.setitem(_dic, gs___doc__, _doc)
  _bases = space.newtuple([gcls_ArithmeticError])
  _args = space.newtuple([gs_OverflowError, _bases, _dic])
  gcls_OverflowError = space.call(space.w_type, _args)
  space.setitem(g46dict, gs_OverflowError, gcls_OverflowError)
  gs___init__ = space.wrap('__init__')
  from pypy.interpreter import gateway
  gfunc_UnicodeDecodeError___init__ = space.wrap(gateway.interp2app(f_UnicodeDecodeError___init__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_UnicodeDecodeError, gs___init__, gfunc_UnicodeDecodeError___init__)
  gs___str__ = space.wrap('__str__')
  gfunc_UnicodeDecodeError___str__ = space.wrap(gateway.interp2app(f_UnicodeDecodeError___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_UnicodeDecodeError, gs___str__, gfunc_UnicodeDecodeError___str__)
  gfunc_UnicodeEncodeError___init__ = space.wrap(gateway.interp2app(f_UnicodeEncodeError___init__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_UnicodeEncodeError, gs___init__, gfunc_UnicodeEncodeError___init__)
  gfunc_UnicodeEncodeError___str__ = space.wrap(gateway.interp2app(f_UnicodeEncodeError___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_UnicodeEncodeError, gs___str__, gfunc_UnicodeEncodeError___str__)
  gfunc_SystemExit___init__ = space.wrap(gateway.interp2app(f_SystemExit___init__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_SystemExit, gs___init__, gfunc_SystemExit___init__)
  gfunc_SyntaxError___init__ = space.wrap(gateway.interp2app(f_SyntaxError___init__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_SyntaxError, gs___init__, gfunc_SyntaxError___init__)
  gfunc_SyntaxError___str__ = space.wrap(gateway.interp2app(f_SyntaxError___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_SyntaxError, gs___str__, gfunc_SyntaxError___str__)
  gs_filename = space.wrap('filename')
  space.setattr(gcls_SyntaxError, gs_filename, space.w_None)
  gs_lineno = space.wrap('lineno')
  space.setattr(gcls_SyntaxError, gs_lineno, space.w_None)
  gs_msg = space.wrap('msg')
  gs__emptystr_ = space.wrap('')
  space.setattr(gcls_SyntaxError, gs_msg, gs__emptystr_)
  gs_offset = space.wrap('offset')
  space.setattr(gcls_SyntaxError, gs_offset, space.w_None)
  gs_print_file_and_line = space.wrap('print_file_and_line')
  space.setattr(gcls_SyntaxError, gs_print_file_and_line, space.w_None)
  gs_text = space.wrap('text')
  space.setattr(gcls_SyntaxError, gs_text, space.w_None)
  gfunc_EnvironmentError___init__ = space.wrap(gateway.interp2app(f_EnvironmentError___init__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_EnvironmentError, gs___init__, gfunc_EnvironmentError___init__)
  gfunc_EnvironmentError___str__ = space.wrap(gateway.interp2app(f_EnvironmentError___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_EnvironmentError, gs___str__, gfunc_EnvironmentError___str__)
  gfunc_KeyError___str__ = space.wrap(gateway.interp2app(f_KeyError___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_KeyError, gs___str__, gfunc_KeyError___str__)
  gfunc_UnicodeTranslateError___init__ = space.wrap(gateway.interp2app(f_UnicodeTranslateError___init__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_UnicodeTranslateError, gs___init__, gfunc_UnicodeTranslateError___init__)
  gfunc_UnicodeTranslateError___str__ = space.wrap(gateway.interp2app(f_UnicodeTranslateError___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_UnicodeTranslateError, gs___str__, gfunc_UnicodeTranslateError___str__)
  gs___getitem__ = space.wrap('__getitem__')
  gfunc_Exception___getitem__ = space.wrap(gateway.interp2app(f_Exception___getitem__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_Exception, gs___getitem__, gfunc_Exception___getitem__)
  gfunc_Exception___init__ = space.wrap(gateway.interp2app(f_Exception___init__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_Exception, gs___init__, gfunc_Exception___init__)
  gfunc_Exception___str__ = space.wrap(gateway.interp2app(f_Exception___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_Exception, gs___str__, gfunc_Exception___str__)
  gs_args = space.wrap('args')
  gi_0 = space.wrap(0)
  gi_1 = space.wrap(1)
  gs_getattr = space.wrap('getattr')
  gs_start = space.wrap('start')
  gs_start_ = space.wrap('start=')
  gs_reason = space.wrap('reason')
  gs_reason_ = space.wrap('reason=')
  gs_args_ = space.wrap('args=')
  gs_end = space.wrap('end')
  gs_end_ = space.wrap('end=')
  gs_object = space.wrap('object')
  gs_object_ = space.wrap('object=')
  gs__ = space.wrap(' ')
  gs_join = space.wrap('join')
  gbltinmethod_join = space.getattr(gs__, gs_join)
  gi_4 = space.wrap(4)
  gi_2 = space.wrap(2)
  gi_3 = space.wrap(3)
  gs_errno = space.wrap('errno')
  gs_strerror = space.wrap('strerror')
  gs__Errno__s___s___s = space.wrap('[Errno %s] %s: %s')
  gs__Errno__s___s = space.wrap('[Errno %s] %s')
  gs____ = space.wrap('???')
  gfunc_basename = space.wrap(gateway.interp2app(f_basename, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs__s___s__line__ld_ = space.wrap('%s (%s, line %ld)')
  gs__s___s_ = space.wrap('%s (%s)')
  gs__s__line__ld_ = space.wrap('%s (line %ld)')
  gfunc_split = space.wrap(gateway.interp2app(f_split, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs_rfind = space.wrap('rfind')
  gs___1 = space.wrap('/')
  gs_rstrip = space.wrap('rstrip')
  from pypy.interpreter.error import OperationError as gOperationError
  gs_code = space.wrap('code')
  gs_encoding = space.wrap('encoding')
  gs_encoding_ = space.wrap('encoding=')
  gi_5 = space.wrap(5)
  return g46dict

