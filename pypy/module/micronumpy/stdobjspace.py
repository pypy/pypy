
from pypy.objspace.std import bytesobject
from pypy.module.micronumpy import interp_boxes

def delegate_stringbox2stringobj(space, w_box):
    return space.wrap(w_box.dtype.itemtype.to_str(w_box))

def register_delegates(typeorder):
    typeorder[interp_boxes.W_StringBox] = [
        (bytesobject.W_StringObject, delegate_stringbox2stringobj),
    ]
