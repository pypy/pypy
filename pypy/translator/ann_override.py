# overrides for annotation specific to PyPy codebase
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation import model as annmodel

from pypy.interpreter import error
from pypy.interpreter import pyframe
from pypy.objspace.std import fake

def hole(*args):
    return annmodel.SomeImpossibleValue(benign=True)

def ignore(*args):
    bk = getbookkeeper()
    return bk.immutablevalue(None)

pypy_overrides = {}

def install(tgt, override):
    if hasattr(tgt, 'im_func'):
        tgt = tgt.im_func
    pypy_overrides[tgt] = override

install(pyframe.cpython_tb, ignore)
install(error.OperationError.record_interpreter_traceback, ignore)
install(fake.wrap_exception, hole)
