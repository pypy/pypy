from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.error import OperationError
from pypy.rlib import rgc # Force registration of gc.collect
import gc

def collect(space):
    "Run a full collection."
    gc.collect()
    
collect.unwrap_spec = [ObjSpace]

def estimate_heap_size(space):
    import sys
    # XXX should be done with the help of the GCs
    if sys.platform == "linux2":
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
