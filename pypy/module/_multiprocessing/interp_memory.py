from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi
from pypy.module.mmap.interp_mmap import W_MMap

def address_of_buffer(space, w_obj):
    if space.config.objspace.usemodules.mmap:
        mmap = space.interp_w(W_MMap, w_obj)
        address = rffi.cast(rffi.SIZE_T, mmap.mmap.data)
        return space.newtuple([space.wrap(address),
                               space.wrap(mmap.mmap.size)])
    else:
        raise OperationError(space.w_TypeError, space.wrap(
            "cannot get address of buffer"))
