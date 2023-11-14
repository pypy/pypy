from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rarithmetic import widen
from pypy.interpreter.error import oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import llapi
from pypy.objspace.std.capsuleobject import W_Capsule

Keys = llapi.cts.gettype("_HPyCapsule_key")

def _get_legal_capsule(space, handles, h_capsule, func):
    if not h_capsule:
        raise oefmt(space.w_ValueError,
            "%s called with NULL capsule", func)
    w_capsule = handles.deref(h_capsule)
    if not isinstance(w_capsule, W_Capsule):
        raise oefmt(space.w_ValueError,
            "%s called with invalid capsule object", func)
    if not w_capsule.pointer:
        raise oefmt(space.w_ValueError,
            "%s called with invalid capsule object", func)
    return w_capsule


def name_matches(w_capsule, name):
    # Assumes `\x00' terminated strings
    if not name:
        return not w_capsule.name
    if not w_capsule.name:
        return not name
    i = 0
    while True:
        if w_capsule.name[i] == '\x00':
            return name[i] == '\x00'
        if name[i] != w_capsule.name[i]:
            return False
        i+= 1
    return True

def check_destructor_impl(space, ptr):
    if not ptr:
        return 
    if not ptr.c_impl:
        raise oefmt(space.w_ValueError,
            "invalid HPyCapsule destructor")

@API.func("HPy HPyCapsule_New(HPyContext *ctx, void *pointer, const char *name, HPyCapsule_Destructor *destructor)")
def HPyCapsule_New(space, handles, ctx, pointer, name, destructor):
    if not pointer:
        raise oefmt(space.w_ValueError, "HPyCapsule_New called with null pointer")
    check_destructor_impl(space, destructor)
    w_capsule = W_Capsule(space, pointer, name)
    if destructor:
        w_capsule.set_destructor_hpy(space, destructor)
    return handles.new(w_capsule)

@API.func("void * HPyCapsule_Get(HPyContext *ctx, HPy capsule, int key, const char *name)")
def HPyCapsule_Get(space, handles, ctx, h_capsule, key, name):
    w_capsule = _get_legal_capsule(space, handles, h_capsule, "HPyCapsule_Get")
    key = widen(key)
    if key == Keys.HPyCapsule_key_Pointer:
        if not name_matches(w_capsule, name):
            raise oefmt(space.w_ValueError,
                "HPyCapsule_Get called with incorrect name")
        return w_capsule.pointer
    elif key == Keys.HPyCapsule_key_Name:
        return rffi.cast(rffi.VOIDP, w_capsule.name)
    elif key == Keys.HPyCapsule_key_Context:
        return w_capsule.context
    elif key == Keys.HPyCapsule_key_Destructor:
        raise oefmt(space.w_ValueError,
           "Invalid operation: get HPyCapsule_key_Destructor") 
    return rffi.cast(rffi.VOIDP, 0)
 
@API.func("int HPyCapsule_Set(HPyContext *, HPy, int, void *)", error_value=API.int(-1))
def HPyCapsule_Set(space, handles, ctx, h_capsule, key, ptr):
    w_capsule = _get_legal_capsule(space, handles, h_capsule, "HPyCapsule_Set")
    key = widen(key)
    if key == Keys.HPyCapsule_key_Pointer:
        w_capsule.pointer = ptr
    elif key == Keys.HPyCapsule_key_Name:
        w_capsule.name = rffi.cast(rffi.CONST_CCHARP, ptr)
    elif key == Keys.HPyCapsule_key_Context:
        w_capsule.context = ptr
    elif key == Keys.HPyCapsule_key_Destructor:
        destructor = llapi.cts.cast("HPyCapsule_Destructor *", ptr)
        check_destructor_impl(space, destructor)
        if destructor:
            w_capsule.set_destructor_hpy(space, destructor)
    else:
        raise oefmt(space.w_ValueError,
           "Invalid operation: unknown key")
    return API.int(0)

@API.func("int HPyCapsule_IsValid(HPyContext *ctx, HPy capsule, const char *utf8_name)", error_value=API.int(-1))
def HPyCapsule_IsValid(space, handles, ctx, h_capsule, name):
    if not h_capsule:
        return API.int(0)
    w_capsule = handles.deref(h_capsule)
    if not isinstance(w_capsule, W_Capsule):
        return API.int(0)
    if not w_capsule.pointer:
        return API.int(0)
    return API.int(name_matches(w_capsule, name))
