from pypy.interpreter.gateway import ObjSpace
from pypy.rpython import objectmodel

def unwind():
    objectmodel.stack_unwind()
unwind.unwrap_spec = []

def frames_depth(space):
    return space.wrap(objectmodel.stack_frames_depth())
frames_depth.unwrap_spec = [ObjSpace]

def too_big(space):
    return space.newbool(objectmodel.stack_too_big())
too_big.unwrap_spec = [ObjSpace]

def check():
    objectmodel.stack_check()
check.unwrap_spec = []
