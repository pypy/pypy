import time
from pypy.interpreter.gateway import ObjSpace


def clock(space):
    return space.wrap(time.clock())

def time_(space):
    return space.wrap(time.time())

def sleep(space, seconds):
    # XXX Temporary hack: we need to make sure the GIL is released while
    #     sleeping.  XXX should be done differently !!!
    GIL = space.threadlocals.getGIL()
    if GIL is not None: GIL.release()
    time.sleep(seconds)
    if GIL is not None: GIL.acquire(True)
sleep.unwrap_spec = [ObjSpace, float]
