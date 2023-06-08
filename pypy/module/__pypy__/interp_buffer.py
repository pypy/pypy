"""
Allow use of the buffer interface from python
"""

from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.objspace.std.memoryobject import BufferViewND
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, generic_new_descr

class W_Bufferable(W_Root):
    def __init__(self, space):
        pass

    def descr_buffer(self, space, w_flags):
        if type(self) is W_Bufferable:
            raise oefmt(space.w_ValueError, "override __buffer__ in a subclass")
        return space.call_method(self, '__buffer__', w_flags)

    def readbuf_w(self, space):
        mv = space.call_method(self, '__buffer__', space.newint(0))
        return mv.buffer_w(space, 0).as_readbuf()

W_Bufferable.typedef = TypeDef("Bufferable", None, None, 'read-write',
    __doc__ = """a helper class for a app-level class (like _ctypes.Array)
that want to support tp_as_buffer.bf_getbuffer via a __buffer__ method""",
    __new__ = generic_new_descr(W_Bufferable),
    __buffer__ = interp2app(W_Bufferable.descr_buffer),
)

@unwrap_spec(itemsize=int, format='text')
def newmemoryview(space, w_obj, itemsize, format, w_shape=None, w_strides=None):
    '''
    newmemoryview(buf, itemsize, format, shape=None, strides=None)
    '''
    if not space.isinstance_w(w_obj, space.w_memoryview):
        raise oefmt(space.w_ValueError, "memoryview expected")
    # minimal error checking
    lgt = space.len_w(w_obj)
    old_size = w_obj.getitemsize()
    nbytes = lgt * old_size
    if w_shape:
        tot = 1
        shape = []
        for w_v in space.listview(w_shape):
            v = space.int_w(w_v)
            shape.append(v)
            tot *= v
        if tot * itemsize != nbytes:
            raise oefmt(space.w_ValueError,
                  "shape/itemsize %s/%d does not match obj len/itemsize %d/%d",
                  str(shape), itemsize, lgt, old_size)
    else:
        if itemsize == 0:
            raise oefmt(space.w_ValueError,
                "cannot guess shape when itemsize==0")
        if nbytes % itemsize != 0:
            raise oefmt(space.w_ValueError,
                  "itemsize %d does not match obj len/itemsize %d/%d",
                  itemsize, lgt, old_size)
        shape = [nbytes / itemsize,]
    ndim = len(shape)
    if w_strides:
        strides = []
        for w_v in space.listview(w_strides):
            v = space.int_w(w_v)
            strides.append(v)
        if not w_shape and len(strides) != 1:
            raise oefmt(space.w_ValueError,
                  "strides must have one value if shape not provided")
        if len(strides) != ndim:
            raise oefmt(space.w_ValueError,
                  "shape %s does not match strides %s",
                  str(shape), str(strides))
    else:
        # start from the right, c-order layout
        strides = [itemsize] * ndim
        for v in range(ndim - 2, -1, -1):
            strides[v] = strides[v + 1] * shape[v + 1]
    # check that the strides are not too big
    for i in range(ndim):
        if strides[i] * shape[i] > nbytes:
            raise oefmt(space.w_ValueError,
                  "shape %s and strides %s exceed object size %d",
                  shape, strides, nbytes)
    view = space.buffer_w(w_obj, 0)
    return space.newmemoryview(FormatBufferViewND(view, itemsize, format, ndim,
                                                  shape, strides))

class FormatBufferViewND(BufferViewND):
    _immutable_ = True
    _attrs_ = ['readonly', 'parent', 'ndim', 'shape', 'strides',
               'format', 'itemsize']
    def __init__(self, parent, itemsize, format, ndim, shape, strides):
        BufferViewND.__init__(self, parent, ndim, shape, strides)
        self.format = format
        self.itemsize = itemsize

    def getformat(self):
        return self.format

    def getitemsize(self):
        return self.itemsize
