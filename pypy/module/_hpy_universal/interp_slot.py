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
VALID_SLOTS = tuple(sorted(value
    for key, value in SlotEnum.__dict__.items()
    if key.startswith('HPy_')))

# NOTE: most subclasses of W_SlotWrapper are inside autogen_interp_slots.py,
# and they are imported at the very bottom of this file
class W_SlotWrapper(W_Root):
    _immutable_fields_ = ["slot"]

    def __init__(self, slot, method_name, cfuncptr, w_objclass):
        #import pdb;pdb.set_trace()
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

def fill_slot_unimplemented(space, w_type, slot_num, hpyslot):
    raise oefmt(space.w_NotImplementedError, "Unimplemented slot: %s", str(slot_num))

for key, value in sorted(SlotEnum.__dict__.items(), key=lambda x: x[1]):
    if not key.startswith('HPy_'):
        continue
    globals()['fill_slot_' + key[4:]] = fill_slot_unimplemented

def fill_slot_tp_repr(space, w_type, slot_num, hpyslot):
    w_slotwrapper = W_SlotWrapper_reprfunc(slot_num, '__repr__', hpyslot.c_impl, w_type)
    w_type.setdictvalue(space, '__repr__', w_slotwrapper)


def make_unary_slot_filler(method_name):
    def fill_slot_unary(space, w_type, slot_num, hpyslot):
        w_slotwrapper = W_SlotWrapper_unaryfunc(slot_num, method_name, hpyslot.c_impl, w_type)
        w_type.setdictvalue(space, method_name, w_slotwrapper)
    return fill_slot_unary

UNARYFUNC_SLOTS = [
    ('nb_absolute', '__abs__'),
    ('nb_float', '__float__'),
    ('nb_index', '__index__'),
    ('nb_int', '__int__'),
    ('nb_invert', '__invert__'),
    ('nb_negative', '__neg__'),
    ('nb_positive', '__pos__'),
    ('tp_iter', '__iter__'),
    ('tp_repr', '__repr__'),
    ('tp_str', '__str__'),
    ('am_await', '__await__'),
    ('am_aiter', '__aiter__'),
    ('am_anext', '__anext__'),
]

for slot, meth in UNARYFUNC_SLOTS:
    globals()['fill_slot_%s' % slot] = make_unary_slot_filler(meth)


def make_binary_slot_filler(method_name):
    def fill_slot_binary(space, w_type, slot_num, hpyslot):
        w_slotwrapper = W_SlotWrapper_binaryfunc(slot_num, method_name, hpyslot.c_impl, w_type)
        w_type.setdictvalue(space, method_name, w_slotwrapper)
    return fill_slot_binary

BINARYFUNC_SLOTS = [
    ('mp_subscript', '__getitem__'),
    ('nb_inplace_add', '__iadd__'),
    ('nb_inplace_and', '__iand__'),
    ('nb_inplace_floor_divide', '__ifloordiv__'),
    ('nb_inplace_lshift', '__ilshift__'),
    ('nb_inplace_multiply', '__imul__'),
    ('nb_inplace_or', '__ior__'),
    ('nb_inplace_power', '__ipow__'),
    ('nb_inplace_remainder', '__imod__'),
    ('nb_inplace_rshift', '__irshift__'),
    ('nb_inplace_subtract', '__isub__'),
    ('nb_inplace_true_divide', '__itruediv__'),
    ('nb_inplace_xor', '__ixor__'),
    ('sq_concat', '__add__'),
    ('sq_inplace_concat', '__iadd__'),
    ('nb_inplace_matrix_multiply', '__imatmul__'),
]

for slot, meth in BINARYFUNC_SLOTS:
    globals()['fill_slot_%s' % slot] = make_binary_slot_filler(meth)

def fill_slot_tp_new(space, w_type, slot_num, hpyslot):
    w_func = W_ExtensionFunction(space, '__new__', llapi.HPy_METH_KEYWORDS, hpyslot.c_impl, w_type)
    w_type.setdictvalue(space, '__new__', w_func)


def fill_slot_sq_item(space, w_type, slot_num, hpyslot):
    #import pdb;pdb.set_trace()
    w_slotwrapper = W_SlotWrapper_ssizeargfunc(slot_num, '__getitem__', hpyslot.c_impl, w_type)
    w_type.setdictvalue(space, '__getitem__', w_slotwrapper)


SLOT_FILLERS = []
for key, value in sorted(SlotEnum.__dict__.items(), key=lambda x: x[1]):
    if not key.startswith('HPy_'):
        continue
    SLOT_FILLERS.append((value, globals()['fill_slot_' + key[4:]]))
SLOT_FILLERS = unrolling_iterable(SLOT_FILLERS)

def fill_slot(space, w_type, hpyslot):
    slot_num = rffi.cast(lltype.Signed, hpyslot.c_slot)
    for slot, func in SLOT_FILLERS:
        if slot_num == slot:
            func(space, w_type, slot_num, hpyslot)
            break
    else:
        raise oefmt(space.w_RuntimeError, "Unsupported HPy slot")

# XXX: this import at the bottom is very ugly, we need to find a better way
from pypy.module._hpy_universal.autogen_interp_slots import *
