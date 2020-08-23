from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.function import descr_function_get
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.module._hpy_universal import llapi, handles
from pypy.module._hpy_universal.state import State
from .interp_extfunc import W_ExtensionFunction

SlotEnum = llapi.cts.gettype('HPySlot_Slot')

# NOTE: most subclasses of W_SlotWrapper are inside autogen_interp_slots.py,
# which is imported later
class W_SlotWrapper(W_Root):
    _immutable_fields_ = ["slot"]

    def __init__(self, slot, method_name, cfuncptr, w_objclass):
        self.slot = slot
        self.name = method_name
        self.cfuncptr = cfuncptr
        self.w_objclass = w_objclass

    def check_args(self, space, __args__, arity):
        length = len(__args__.arguments_w)
        if length != arity:
            raise oefmt(space.w_TypeError, "expected %d arguments, got %d",
                        arity, length)
        if __args__.keywords:
            raise oefmt(space.w_TypeError,
                        "wrapper %s doesn't take any keyword arguments",
                        self.name)

    def descr_call(self, space, __args__):
        # XXX: basically a copy of cpyext's W_PyCMethodObject.descr_call()
        if len(__args__.arguments_w) == 0:
            w_objclass = self.w_objclass
            assert isinstance(w_objclass, W_TypeObject)
            raise oefmt(space.w_TypeError,
                "descriptor '%8' of '%s' object needs an argument",
                self.name, self.w_objclass.getname(space))
        w_instance = __args__.arguments_w[0]
        # XXX: needs a stricter test
        if not space.isinstance_w(w_instance, self.w_objclass):
            w_objclass = self.w_objclass
            assert isinstance(w_objclass, W_TypeObject)
            raise oefmt(space.w_TypeError,
                "descriptor '%8' requires a '%s' object but received a '%T'",
                self.name, w_objclass.name, w_instance)
        #
        return self.call(space, __args__)

    def call(self, space, h_self, __args__):
        raise oefmt(space.w_RuntimeError, "bad slot wrapper")

W_SlotWrapper.typedef = TypeDef(
    'slot_wrapper',
    __get__ = interp2app(descr_function_get),
    __call__ = interp2app(W_SlotWrapper.descr_call),
    )
W_SlotWrapper.typedef.acceptable_as_base_class = False

# NOTE: we need to import this module here, to avoid circular imports
from pypy.module._hpy_universal import autogen_interp_slots as AGS # "Auto Gen Slots"

SLOTS = unrolling_iterable([
    ('nb_absolute', '__abs__', AGS.W_SlotWrapper_unaryfunc),
    ('nb_float', '__float__', AGS.W_SlotWrapper_unaryfunc),
    ('nb_index', '__index__', AGS.W_SlotWrapper_unaryfunc),
    ('nb_int', '__int__', AGS.W_SlotWrapper_unaryfunc),
    ('nb_invert', '__invert__', AGS.W_SlotWrapper_unaryfunc),
    ('nb_negative', '__neg__', AGS.W_SlotWrapper_unaryfunc),
    ('nb_positive', '__pos__', AGS.W_SlotWrapper_unaryfunc),
    ('tp_iter', '__iter__', AGS.W_SlotWrapper_unaryfunc),
    ('tp_repr', '__repr__', AGS.W_SlotWrapper_unaryfunc),
    ('tp_str', '__str__', AGS.W_SlotWrapper_unaryfunc),
    ('am_await', '__await__', AGS.W_SlotWrapper_unaryfunc),
    ('am_aiter', '__aiter__', AGS.W_SlotWrapper_unaryfunc),
    ('am_anext', '__anext__', AGS.W_SlotWrapper_unaryfunc),

    ('mp_subscript', '__getitem__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_add', '__iadd__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_and', '__iand__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_floor_divide', '__ifloordiv__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_lshift', '__ilshift__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_multiply', '__imul__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_or', '__ior__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_power', '__ipow__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_remainder', '__imod__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_rshift', '__irshift__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_subtract', '__isub__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_true_divide', '__itruediv__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_xor', '__ixor__', AGS.W_SlotWrapper_binaryfunc),
    ('sq_concat', '__add__', AGS.W_SlotWrapper_binaryfunc),
    ('sq_inplace_concat', '__iadd__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_matrix_multiply', '__imatmul__', AGS.W_SlotWrapper_binaryfunc),

    ('sq_item', '__getitem__', AGS.W_SlotWrapper_ssizeargfunc),
    ('tp_repr', '__repr__', AGS.W_SlotWrapper_reprfunc),
    ])


def fill_slot(space, w_type, hpyslot):
    slot_num = rffi.cast(lltype.Signed, hpyslot.c_slot)
    # special cases
    if slot_num == SlotEnum.HPy_tp_new:
        w_func = W_ExtensionFunction(space, '__new__', llapi.HPy_METH_KEYWORDS,
                                     hpyslot.c_impl, w_type)
        w_type.setdictvalue(space, '__new__', w_func)
        return

    # generic cases
    for slotname, methname, cls in SLOTS:
        n = getattr(SlotEnum, 'HPy_' + slotname)
        if slot_num == n:
            w_slot = cls(slot_num, methname, hpyslot.c_impl, w_type)
            w_type.setdictvalue(space, methname, w_slot)
            return

    raise oefmt(space.w_NotImplementedError, "Unimplemented slot: %s", str(slot_num))
