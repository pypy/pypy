# overrides for annotation specific to PyPy codebase
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation import model as annmodel

from pypy.interpreter import error
from pypy.interpreter import pyframe
from pypy.objspace.std import fake
from pypy.module.sys2 import state as sys_state
import pypy.interpreter.typedef as itypedef
from pypy.objspace.std.objspace import StdObjSpace

def hole(*args):
    return annmodel.SomeImpossibleValue(benign=True)

def ignore(*args):
    bk = getbookkeeper()
    return bk.immutablevalue(None)

def instantiate(cls):
    clsdef = getbookkeeper().getclassdef(itypedef.W_Root)
    return annmodel.SomeInstance(clsdef)

def wrap_exception_cls(space, x):
    import pypy.objspace.std.typeobject as typeobject
    clsdef = getbookkeeper().getclassdef(typeobject.W_TypeObject)
    return annmodel.SomeInstance(clsdef, can_be_None=True)

def fake_object(space, x):
    clsdef = getbookkeeper().getclassdef(itypedef.W_Root)
    return annmodel.SomeInstance(clsdef)    

pypy_overrides = {}

def install(tgt, override):
    if hasattr(tgt, 'im_func'):
        tgt = tgt.im_func
    pypy_overrides[tgt] = override

install(pyframe.cpython_tb, ignore)
install(error.OperationError.record_interpreter_traceback, ignore)
install(sys_state.pypy_getudir, ignore)
install(fake.wrap_exception, hole)
install(fake.fake_object, fake_object)
install(itypedef.instantiate, instantiate)
install(StdObjSpace.wrap_exception_cls, wrap_exception_cls)
