from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.function import descr_function_get
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.module._hpy_universal import llapi, handles
from pypy.module._hpy_universal.state import State
from .interp_extfunc import W_ExtensionFunction, W_ExtensionMethod

HPySlot_Slot = llapi.cts.gettype('HPySlot_Slot')

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

    def call(self, space, __args__):
        raise oefmt(space.w_RuntimeError, "bad slot wrapper")

W_SlotWrapper.typedef = TypeDef(
    'slot_wrapper',
    __get__ = interp2app(descr_function_get),
    __call__ = interp2app(W_SlotWrapper.descr_call),
    )
W_SlotWrapper.typedef.acceptable_as_base_class = False

class W_SlotWrapper_initproc(W_SlotWrapper):
    def call(self, space, __args__):
        with handles.using(space, __args__.arguments_w[0]) as h_self:
            n = len(__args__.arguments_w) - 1
            with lltype.scoped_alloc(rffi.CArray(llapi.HPy), n) as args_h:
                i = 0
                while i < n:
                    args_h[i] = handles.new(space, __args__.arguments_w[i + 1])
                    i += 1
                h_kw = 0
                if __args__.keywords:
                    w_kw = space.newdict()
                    for i in range(len(__args__.keywords)):
                        key = __args__.keywords[i]
                        w_value = __args__.keywords_w[i]
                        space.setitem_str(w_kw, key, w_value)
                    h_kw = handles.new(space, w_kw)
                fptr = llapi.cts.cast('HPyFunc_initproc', self.cfuncptr)
                state = space.fromcache(State)
                try:
                    result = fptr(state.ctx, h_self, args_h, n, h_kw)
                finally:
                    if h_kw:
                        handles.close(space, h_kw)
                    for i in range(n):
                        handles.close(space, args_h[i])
        if rffi.cast(lltype.Signed, result) < 0:
            # If we're here, it means no exception was set
            raise oefmt(space.w_SystemError,
                "Function returned an error result without setting an exception")
        return space.w_None


class W_tp_new_wrapper(W_ExtensionFunction):
    """
    Special case for HPy_tp_new. Note that is not NOT a SlotWrapper.

    This is the equivalent of CPython's tp_new_wrapper: the difference is that
    CPython's tp_new_wrapper is a regular PyMethodDef which is wrapped inside
    a PyCFunction, while here we have our own type
    """

    def __init__(self, space, cfuncptr, w_type):
        W_ExtensionFunction.__init__(self, space, '__new__', llapi.HPyFunc_KEYWORDS,
                                     cfuncptr, w_self=w_type)

    def call(self, space, h_type, __args__):
        # NOTE: h_type here is ignored. In CPython's tp_new_wrapper it is only
        # used to fish the ->tp_new to call, but here we already have the
        # cfuncptr
        #
        # XXX: tp_new_wrapper does additional checks, we should write tests
        # and implement the same checks
        w_self = __args__.arguments_w[0]
        with handles.using(space, w_self) as h_self:
            return self.call_varargs_kw(space, h_self, __args__,
                                        skip_args=1, has_keywords=True)




# NOTE: we need to import this module here, to avoid circular imports
from pypy.module._hpy_universal import autogen_interp_slots as AGS # "Auto Gen Slots"

SLOTS = unrolling_iterable([
    # CPython slots
#   ('mp_ass_subscript',           '__xxx__',       AGS.W_SlotWrapper_...),
#   ('mp_length',                  '__xxx__',       AGS.W_SlotWrapper_...),
#   ('mp_subscript',               '__getitem__',   AGS.W_SlotWrapper_binaryfunc),
    ('nb_absolute',                '__abs__',       AGS.W_SlotWrapper_unaryfunc),
    ('nb_add',                     '__add__',       AGS.W_SlotWrapper_binaryfunc),
    ('nb_and',                     '__and__',       AGS.W_SlotWrapper_binaryfunc),
#   ('nb_bool',                    '__xxx__',       AGS.W_SlotWrapper_...),
    ('nb_divmod',                  '__divmod__',    AGS.W_SlotWrapper_binaryfunc),
    ('nb_float',                   '__float__',     AGS.W_SlotWrapper_unaryfunc),
    ('nb_floor_divide',            '__floordiv__',  AGS.W_SlotWrapper_binaryfunc),
    ('nb_index',                   '__index__',     AGS.W_SlotWrapper_unaryfunc),
    ('nb_inplace_add',             '__iadd__',      AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_and',             '__iand__',      AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_floor_divide',    '__ifloordiv__', AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_lshift',          '__ilshift__',   AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_multiply',        '__imul__',      AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_or',              '__ior__',       AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_power',           '__ipow__',      AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_remainder',       '__imod__',      AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_rshift',          '__irshift__',   AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_subtract',        '__isub__',      AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_true_divide',     '__itruediv__',  AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_xor',             '__ixor__',      AGS.W_SlotWrapper_binaryfunc),
    ('nb_int',                     '__int__',       AGS.W_SlotWrapper_unaryfunc),
    ('nb_invert',                  '__invert__',    AGS.W_SlotWrapper_unaryfunc),
    ('nb_lshift',                  '__lshift__',    AGS.W_SlotWrapper_binaryfunc),
    ('nb_multiply',                '__mul__',       AGS.W_SlotWrapper_binaryfunc),
    ('nb_negative',                '__neg__',       AGS.W_SlotWrapper_unaryfunc),
    ('nb_or',                      '__or__',        AGS.W_SlotWrapper_binaryfunc),
    ('nb_positive',                '__pos__',       AGS.W_SlotWrapper_unaryfunc),
#   ('nb_power',                   '__xxx__',       AGS.W_SlotWrapper_...),
    ('nb_remainder',               '__mod__',       AGS.W_SlotWrapper_binaryfunc),
    ('nb_rshift',                  '__rshift__',    AGS.W_SlotWrapper_binaryfunc),
    ('nb_subtract',                '__sub__',       AGS.W_SlotWrapper_binaryfunc),
    ('nb_true_divide',             '__truediv__',   AGS.W_SlotWrapper_binaryfunc),
    ('nb_xor',                     '__xor__',       AGS.W_SlotWrapper_binaryfunc),
#   ('sq_ass_item',                '__xxx__',       AGS.W_SlotWrapper_...),
#   ('sq_concat',                  '__add__',       AGS.W_SlotWrapper_binaryfunc),
#   ('sq_contains',                '__xxx__',       AGS.W_SlotWrapper_...),
#   ('sq_inplace_concat',          '__iadd__',      AGS.W_SlotWrapper_binaryfunc),
#   ('sq_inplace_repeat',          '__xxx__',       AGS.W_SlotWrapper_...),
    ('sq_item',                    '__getitem__',   AGS.W_SlotWrapper_ssizeargfunc),
#   ('sq_length',                  '__xxx__',       AGS.W_SlotWrapper_...),
#   ('sq_repeat',                  '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_base',                    '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_bases',                   '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_call',                    '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_clear',                   '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_del',                     '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_descr_get',               '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_descr_set',               '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_doc',                     '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_getattr',                 '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_getattro',                '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_hash',                    '__xxx__',       AGS.W_SlotWrapper_...),
    ('tp_init',                    '__init__',      W_SlotWrapper_initproc),
#   ('tp_is_gc',                   '__xxx__',       AGS.W_SlotWrapper_...),
#    ('tp_iter',                    '__iter__',      AGS.W_SlotWrapper_unaryfunc),
#   ('tp_iternext',                '__xxx__',       AGS.W_SlotWrapper_...),
#   tp_new     SPECIAL-CASED
    ('tp_repr',                    '__repr__',      AGS.W_SlotWrapper_unaryfunc),
#   ('tp_richcompare',             '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_setattr',                 '__xxx__',       AGS.W_SlotWrapper_...),
#   ('tp_setattro',                '__xxx__',       AGS.W_SlotWrapper_...),
#    ('tp_str',                     '__str__',       AGS.W_SlotWrapper_unaryfunc),
#   ('tp_traverse',                '__xxx__',       AGS.W_SlotWrapper_...),
    ('nb_matrix_multiply',         '__matmul__',    AGS.W_SlotWrapper_binaryfunc),
    ('nb_inplace_matrix_multiply', '__imatmul__',   AGS.W_SlotWrapper_binaryfunc),
#    ('am_await',                   '__await__',     AGS.W_SlotWrapper_unaryfunc),
#    ('am_aiter',                   '__aiter__',     AGS.W_SlotWrapper_unaryfunc),
#    ('am_anext',                   '__anext__',     AGS.W_SlotWrapper_unaryfunc),
#   ('tp_finalize',                '__xxx__',       AGS.W_SlotWrapper_...),

    # extra HPy-specific slots
#   ('tp_destroy',                 '__xxx__',       AGS.W_SlotWrapper_...),
    ])


def fill_slot(space, w_type, hpyslot):
    slot_num = rffi.cast(lltype.Signed, hpyslot.c_slot)
    # special cases
    if slot_num == HPySlot_Slot.HPy_tp_new:
        w_func = W_tp_new_wrapper(space, hpyslot.c_impl, w_type)
        w_type.setdictvalue(space, '__new__', w_func)
        return
    elif slot_num == HPySlot_Slot.HPy_tp_destroy:
        w_type.tp_destroy = llapi.cts.cast('HPyFunc_destroyfunc', hpyslot.c_impl)
        return

    # generic cases
    for slotname, methname, cls in SLOTS:
        assert methname != '__xxx__' # sanity check
        n = getattr(HPySlot_Slot, 'HPy_' + slotname)
        if slot_num == n:
            w_slot = cls(slot_num, methname, hpyslot.c_impl, w_type)
            w_type.setdictvalue(space, methname, w_slot)
            return

    raise oefmt(space.w_NotImplementedError, "Unimplemented slot: %s", str(slot_num))
