from pypy.interpreter import gateway, baseobjspace
from pypy.rlib.objectmodel import we_are_translated

# commonly imported there, used from types, variable, thread
from pypy.module._stackless.coroutine import AppCoroutine

import os

class State: pass

NO_DEBUG_INFO = State()
NO_DEBUG_INFO.state = True

def w(*msgs):
    """writeln"""
    if NO_DEBUG_INFO.state: return
    v(*msgs)
    os.write(1, ' \n')

def v(*msgs):
    """write"""
    if NO_DEBUG_INFO.state: return
    for msg in list(msgs):
        os.write(1, msg)
        os.write(1, ' ')

def get_current_cspace(space):
    curr = AppCoroutine.w_getcurrent(space)
    assert isinstance(curr, AppCoroutine)
    if curr._cspace is None:
        if not we_are_translated():
            import pdb
            pdb.set_trace()
    return curr._cspace

def interp_id(space, w_obj):
    "debugging purposes only"
    assert isinstance(w_obj, baseobjspace.W_Root) 
    return space.newint(id(w_obj))
app_interp_id = gateway.interp2app(interp_id)

def switch_debug_info(space):
    NO_DEBUG_INFO.state = not NO_DEBUG_INFO.state
switch_debug_info.unwrap_spec = [baseobjspace.ObjSpace]

