from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.error import OperationError
from pypy.rlib import rgc

def collect(space):
    "Run a full collection."
    rgc.collect()
    return space.wrap(0)
    
collect.unwrap_spec = [ObjSpace]

def enable_finalizers(space):
    if space.user_del_action.finalizers_lock_count == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("finalizers are already enabled"))
    space.user_del_action.finalizers_lock_count -= 1
    space.user_del_action.fire()
enable_finalizers.unwrap_spec = [ObjSpace]

def disable_finalizers(space):
    space.user_del_action.finalizers_lock_count += 1
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
