
""" Implementation of buffer protocol, interp level
"""

from pypy.rlib.rbuffer import RBuffer
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.typedef import TypeDef, GetSetProperty,\
     interp_attrproperty
from pypy.interpreter.gateway import interp2app
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.objspace.std.sliceobject import W_SliceObject

class W_Buffer(Wrappable):
    def __init__(self, space, w_arg):
        if space.is_true(space.isinstance(w_arg, space.w_unicode)):
            arg = space.unicode_w(w_arg)
            size = len(arg) * rffi.sizeof(lltype.UniChar)
            self._buffer = RBuffer(size)
            # XXX memory copy interface, redesign and share
            UNICODE_ARRAY_P = rffi.CArrayPtr(lltype.UniChar)
            ll_buffer = rffi.cast(UNICODE_ARRAY_P, self._buffer.ll_buffer)
            for i in range(len(arg)):
                ll_buffer[i] = arg[i]
        else:
            size = space.int_w(space.len(w_arg))
            self._buffer = RBuffer(size)
            for i in range(size):
                self._buffer.setitem(i, rffi.cast(lltype.Char, space.int_w(
                    space.getitem(w_arg, space.wrap(i)))))
        self.size = size                

    def getitem(self, space, w_item):
        if space.is_true(space.isinstance(w_item, space.w_slice)):
            start, stop, step = space.sliceindices(w_item,
                                                   space.wrap(self.size))
            # XXX a bit of code duplication from listobject

            if (step < 0 and stop >= start) or (step > 0 and start >= stop):
                slicelength = 0
            elif step < 0:
                slicelength = (stop - start + 1) / step + 1
            else:
                slicelength = (stop - start - 1) / step + 1
            res = ['\x00'] * slicelength
            for i in range(slicelength):
                res[i] = self._buffer.getitem(start)
                start += step
            return space.wrap("".join(res))
        return space.wrap(self._buffer.getitem(space.int_w(w_item)))
    getitem.unwrap_spec = ['self', ObjSpace, W_Root]

    def len(self, space):
        return space.wrap(self._buffer.size)
    len.unwrap_spec = ['self', ObjSpace]

    def delete(self):
        # XXX when exactly???
        self._buffer.free()

def descr_new_buffer(space, w_type, w_arg):
    return space.wrap(W_Buffer(space, w_arg))
descr_new_buffer.unwrap_spec = [ObjSpace, W_Root, W_Root]

W_Buffer.typedef = TypeDef(
    'buffer',
    __new__ = interp2app(descr_new_buffer),
    __del__ = interp2app(W_Buffer.delete),
    __len__ = interp2app(W_Buffer.len),
    __getitem__ = interp2app(W_Buffer.getitem),
)
