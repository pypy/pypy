from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.error import OperationError
from pypy.rlib import rgc

def collect(space):
    "Run a full collection."
    rgc.collect()
    
collect.unwrap_spec = [ObjSpace]

class State: 
    def __init__(self, space):
        self.finalizers_lock_count = 0
def getstate(space):
    return space.fromcache(State)

def enable_finalizers(space):
    state = getstate(space)
    if state.finalizers_lock_count == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("finalizers are already enabled"))
    state.finalizers_lock_count -= 1
    rgc.enable_finalizers()
enable_finalizers.unwrap_spec = [ObjSpace]

def disable_finalizers(space):
    state = getstate(space)
    rgc.disable_finalizers()
    state.finalizers_lock_count += 1
disable_finalizers.unwrap_spec = [ObjSpace]

# ____________________________________________________________

import sys
platform = sys.platform

def estimate_heap_size(space):
    # XXX should be done with the help of the GCs
    if platform == "linux2":
        import os
        pid = os.getpid()
        try:
            fd = os.open("/proc/" + str(pid) + "/status", os.O_RDONLY, 0777)
        except OSError:
            pass
        else:
            try:
                content = os.read(fd, 1000000)
            finally:
                os.close(fd)
            lines = content.split("\n")
            for line in lines:
                if line.startswith("VmSize:"):
                    stop = len(line) - 3
                    assert stop > 0
                    result = int(line[len("VmSize:"):stop].strip(" ")) * 1024
                    return space.wrap(result)
    raise OperationError(space.w_RuntimeError,
                         space.wrap("can't estimate the heap size"))
estimate_heap_size.unwrap_spec = [ObjSpace]
