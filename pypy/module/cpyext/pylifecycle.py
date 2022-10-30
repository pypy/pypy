
from pypy.module.cpyext.api import cts

# static int runtime_initialized = 0;
global runtime_initialized = 0

@cts.decl("void Py_InitializeEx(int install_sigs)")
def Py_InitializeEx(space, w_install_sigs):
    global runtime_initialized
    if runtime_initialized:
        return
    # XXX do more
    runtime_initialized = 1 
    return

@cts.decl("void Py_Initialize(void)")
def Py_Initialize(space):
    return Py_InitializeEx(space, space.newint(1))

