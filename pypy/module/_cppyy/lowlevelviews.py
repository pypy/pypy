# Naked C++ pointers carry no useful size or layout information, but often
# such information is externnally available. Low level views are arrays with
# a few more methods allowing such information to be set. Afterwards, it is
# simple to pass these views on to e.g. numpy (w/o the need to copy).

from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty_w
from pypy.module._rawffi.array import W_ArrayInstance


class W_LowLevelView(W_ArrayInstance):
    def __init__(self, space, shape, length, address):
        assert address   # if not address, base class will allocate memory
        W_ArrayInstance.__init__(self, space, shape, length, address)

    @unwrap_spec(args_w='args_w')
    def reshape(self, space, args_w):
        # llviews are only created from non-zero addresses, so we only need
        # to adjust length and shape

        nargs = len(args_w)
        if nargs == 0:
            raise oefmt(space.w_TypeError, "reshape expects a tuple argument")

        newshape_w = args_w
        if nargs != 1 or not space.isinstance_w(args_w[0], space.w_tuple) or \
               not space.len_w(args_w[0]) == 1:
            raise oefmt(space.w_TypeError,
                "tuple object of length 1 expected, received %T", args_w[0])

        w_shape = args_w[0]

        # shape in W_ArrayInstance-speak is somewhat different from what
        # e.g. numpy thinks of it: self.shape contains the info (itemcode,
        # size, etc.) of a single entry; length is user-facing shape
        self.length = space.int_w(space.getitem(w_shape, space.newint(0)))


W_LowLevelView.typedef = TypeDef(
    'LowLevelView',
    __repr__    = interp2app(W_LowLevelView.descr_repr),
    __setitem__ = interp2app(W_LowLevelView.descr_setitem),
    __getitem__ = interp2app(W_LowLevelView.descr_getitem),
    __len__     = interp2app(W_LowLevelView.getlength),
    buffer      = GetSetProperty(W_LowLevelView.getbuffer),
    shape       = interp_attrproperty_w('shape', W_LowLevelView),
    free        = interp2app(W_LowLevelView.free),
    byptr       = interp2app(W_LowLevelView.byptr),
    itemaddress = interp2app(W_LowLevelView.descr_itemaddress),
    reshape     = interp2app(W_LowLevelView.reshape),
)
W_ArrayInstance.typedef.acceptable_as_base_class = False

