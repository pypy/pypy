from pypy.interpreter import gateway
from pypy.interpreter.function import StaticMethod
from pypy.interpreter.error import wrap_windowserror
from pypy.rlib import rwin32
from pypy.rpython.lltypesystem import rffi

def handle_w(space, w_handle):
    return rffi.cast(rwin32.HANDLE, space.int_w(w_handle))

def CloseHandle(space, w_handle):
    handle = handle_w(space, w_handle)
    if not rwin32.CloseHandle(handle):
        raise wrap_windowserror(space, rwin32.lastWindowsError())

def win32_namespace(space):
    "NOT_RPYTHON"
    w_win32 = space.call_function(space.w_type,
                                  space.wrap("win32"),
                                  space.newtuple([]),
                                  space.newdict())
    try:
        for name in ['CloseHandle',
                     ]:
            function = globals()[name]
            w_function = space.wrap(gateway.interp2app(function))
            w_method = space.wrap(StaticMethod(w_function))
            space.setattr(w_win32, space.wrap(name), w_method)
    except Exception, e:
        import pdb; pdb.set_trace()
    return w_win32
