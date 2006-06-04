from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.function import Function, Method
from pypy.interpreter.module import Module
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.generator import GeneratorIterator
from pypy.rpython.objectmodel import instantiate
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

def func_new(space, __args__):
    w_type = space.gettypeobject(Function.typedef)
    return space.call_args(w_type, __args__)
func_new.unwrap_spec = [ObjSpace, Arguments]

def module_new(space, w_name, w_dict):
    new_mod = Module(space, w_name, w_dict)
    return space.wrap(new_mod)

def method_new(space, __args__):
    w_type = space.gettypeobject(Method.typedef)
    return space.call_args(w_type, __args__)
method_new.unwrap_spec = [ObjSpace, Arguments]

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
    return None
##     args_w, kwds_w = __args__.unpack()  #stolen from std/fake.py
##     args = [space.unwrap(w_arg) for w_arg in args_w]
##     f_back, builtin, pycode, valuestack, blockstack, last_exception,\
##         globals, last_instr, next_instr, f_lineno, fastlocals, f_trace,\
##         instr_lb, instr_ub, instr_prev = args
##     w = space.wrap

##     new_frame = PyFrame(space, pycode, w(globals), None)
##     new_frame.f_back = f_back
##     new_frame.builtin = builtin
##     #new_frame.blockstack = blockstack
##     #new_frame.valuestack = valuestack
##     new_frame.last_exception = last_exception
##     new_frame.last_instr = last_instr
##     new_frame.next_instr = next_instr
##     new_frame.f_lineno = f_lineno
##     #new_frame.fastlocals_w = w(fastlocals)

##     if space.is_w(f_trace, space.w_None):
##         new_frame.w_f_trace = None
##     else:
##         new_frame.w_f_trace = w(f_trace)

##     new_frame.instr_lb = instr_lb   #the three for tracing
##     new_frame.instr_ub = instr_ub
##     new_frame.instr_prev = instr_prev

##     return space.wrap(new_frame)
frame_new.unwrap_spec = [ObjSpace, Arguments]

def traceback_new(space, __args__):
    return None
##     args_w, kwds_w = __args__.unpack()  #stolen from std/fake.py
##     args = [space.unwrap(w_arg) for w_arg in args_w]
##     frame, lasti, lineno, next = args
##     return PyTraceback(space, frame, lasti, lineno, next)
traceback_new.unwrap_spec = [ObjSpace, Arguments]

def generator_new(space, __args__):
    return None
##     args_w, kwds_w = __args__.unpack()  #stolen from std/fake.py
##     args = [space.unwrap(w_arg) for w_arg in args_w]
##     frame, running, exhausted = args
##     new_generator = GeneratorIterator(frame)
##     new_generator.running = running
##     new_generator.exhausted = exhausted
##     return new_generator
generator_new.unwrap_spec = [ObjSpace, Arguments]
