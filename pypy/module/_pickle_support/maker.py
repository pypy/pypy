from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.function import Function, Method
from pypy.interpreter.module import Module
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.generator import GeneratorIterator
from pypy.rlib.objectmodel import instantiate
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.objspace.std.dicttype import dictiter_typedef
from pypy.objspace.std.iterobject import W_SeqIterObject, W_ReverseSeqIterObject


#note: for now we don't use the actual value when creating the Cell.
#      (i.e. we assume it will be handled by __setstate__)
#      Stackless does use this so it might be needed here as well.

def cell_new(space):
    return space.wrap(instantiate(Cell))

def code_new(space, __args__):
    w_type = space.gettypeobject(PyCode.typedef)
    return space.call_args(w_type, __args__)
code_new.unwrap_spec = [ObjSpace, Arguments]

def func_new(space):
    fu = instantiate(Function)
    fu.w_func_dict = space.newdict()
    return space.wrap(fu)
func_new.unwrap_spec = [ObjSpace]

def module_new(space, w_name, w_dict):
    new_mod = Module(space, w_name, w_dict)
    return space.wrap(new_mod)

def method_new(space, __args__):
    w_type = space.gettypeobject(Method.typedef)
    return space.call_args(w_type, __args__)
method_new.unwrap_spec = [ObjSpace, Arguments]

def builtin_method_new(space, w_instance, w_name):
    return space.getattr(w_instance, w_name)

def dictiter_surrogate_new(space, w_lis):
    # we got a listobject.
    # simply create an iterator and that's it.
    return space.iter(w_lis)
dictiter_surrogate_new.unwrap_spec = [ObjSpace, W_Root]

def seqiter_new(space, w_seq, w_index):
    return W_SeqIterObject(w_seq, space.int_w(w_index))

def reverseseqiter_new(space, w_seq, w_index):
    w_len = space.len(w_seq)
    index = space.int_w(w_index) - space.int_w(w_len)
    return W_ReverseSeqIterObject(space, w_seq, index)
    
def frame_new(space, __args__):
    args_w, kwds_w = __args__.unpack()
    w_pycode, = args_w
    pycode = space.interp_w(PyCode, w_pycode)
    w = space.wrap
    new_frame = instantiate(space.FrameClass)   # XXX fish
    return space.wrap(new_frame)
frame_new.unwrap_spec = [ObjSpace, Arguments]

def traceback_new(space):
    tb = instantiate(PyTraceback)
    return space.wrap(tb)
traceback_new.unwrap_spec = [ObjSpace]

def generator_new(space, __args__):
    args_w, kwds_w = __args__.unpack()  #stolen from std/fake.py
    w_frame, w_running = args_w
    frame = space.interp_w(PyFrame, w_frame)
    running = space.int_w(w_running)
    new_generator = GeneratorIterator(frame)
    new_generator.running = running
    return space.wrap(new_generator)
generator_new.unwrap_spec = [ObjSpace, Arguments]

def xrangeiter_new(space, current, remaining, step):
    from pypy.module.__builtin__.functional import W_XRangeIterator
    new_iter = W_XRangeIterator(space, current, remaining, step)
    return space.wrap(new_iter)
xrangeiter_new.unwrap_spec = [ObjSpace, int, int, int]

# ___________________________________________________________________
# Helper functions for internal use

# adopted from prickelpit.c  (but almost completely different)

def slp_into_tuple_with_nulls(space, seq_w):
    """
    create a tuple with the object and store
    a tuple with the positions of NULLs as first element.
    """
    nulls = []
    tup = [space.w_None]
    w = space.wrap

    for w_obj in seq_w:
        if w_obj is None:
            nulls.append(w(len(tup)-1))
            w_obj = space.w_None
        tup.append(w_obj)
    tup[0] = space.newtuple(nulls)
    return space.newtuple(tup)

def slp_from_tuple_with_nulls(space, w_tup):
    tup_w = space.unpackiterable(w_tup)
    nulls = space.unpackiterable(tup_w.pop(0))
    for w_p in nulls:
        p = space.int_w(w_p)
        tup_w[p] = None
    return tup_w
