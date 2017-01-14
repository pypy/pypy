import py, pytest
import contextlib
from rpython.rtyper.lltypesystem import lltype
from pypy.interpreter.baseobjspace import W_Root
from pypy.module.cpyext.state import State
from pypy.module.cpyext.api import (
    slot_function, cpython_api, copy_header_files, INTERPLEVEL_API,
    Py_ssize_t, Py_ssize_tP, PyObject)
from pypy.module.cpyext.test.test_cpyext import freeze_refcnts, LeakCheckingTest
from pypy.interpreter.error import OperationError
from rpython.rlib import rawrefcount
import os

@contextlib.contextmanager
def raises_w(space, expected_exc):
    with pytest.raises(OperationError) as excinfo:
        yield
    operror = excinfo.value
    assert operror.w_type is getattr(space, 'w_' + expected_exc.__name__)

class BaseApiTest(LeakCheckingTest):
    def setup_class(cls):
        space = cls.space
        # warm up reference counts:
        # - the posix module allocates a HCRYPTPROV on Windows
        # - writing to stdout and stderr allocates a file lock
        space.getbuiltinmodule("cpyext")
        space.getbuiltinmodule(os.name)
        space.call_function(space.getattr(space.sys.get("stderr"),
                                          space.wrap("write")),
                            space.wrap(""))
        space.call_function(space.getattr(space.sys.get("stdout"),
                                          space.wrap("write")),
                            space.wrap(""))

        class CAPI:
            def __getattr__(self, name):
                return getattr(cls.space, name)
        cls.api = CAPI()
        CAPI.__dict__.update(INTERPLEVEL_API)

        print 'DONT_FREE_ANY_MORE'
        rawrefcount._dont_free_any_more()

    def raises(self, space, api, expected_exc, f, *args):
        if not callable(f):
            raise Exception("%s is not callable" % (f,))
        f(*args)
        state = space.fromcache(State)
        operror = state.operror
        if not operror:
            raise Exception("DID NOT RAISE")
        if getattr(space, 'w_' + expected_exc.__name__) is not operror.w_type:
            raise Exception("Wrong exception")
        return state.clear_exception()

    def setup_method(self, func):
        freeze_refcnts(self)

    def teardown_method(self, func):
        state = self.space.fromcache(State)
        try:
            state.check_and_raise_exception()
        except OperationError as e:
            print e.errorstr(self.space)
            raise

        try:
            self.space.getexecutioncontext().cleanup_cpyext_threadstate()
        except AttributeError:
            pass

        if self.check_and_print_leaks():
            assert False, "Test leaks or loses object(s)."

@slot_function([PyObject], lltype.Void)
def PyPy_GetWrapped(space, w_arg):
    assert isinstance(w_arg, W_Root)

@slot_function([PyObject], lltype.Void)
def PyPy_GetReference(space, arg):
    assert lltype.typeOf(arg) ==  PyObject

@cpython_api([Py_ssize_t], Py_ssize_t, error=-1)
def PyPy_TypedefTest1(space, arg):
    assert lltype.typeOf(arg) == Py_ssize_t
    return 0

@cpython_api([Py_ssize_tP], Py_ssize_tP)
def PyPy_TypedefTest2(space, arg):
    assert lltype.typeOf(arg) == Py_ssize_tP
    return None

class TestConversion(BaseApiTest):
    def test_conversions(self, space):
        PyPy_GetWrapped(space, space.w_None)
        PyPy_GetReference(space, space.w_None)

    def test_typedef(self, space):
        from rpython.translator.c.database import LowLevelDatabase
        db = LowLevelDatabase()
        assert PyPy_TypedefTest1.api_func.get_c_restype(db) == 'Py_ssize_t'
        assert PyPy_TypedefTest1.api_func.get_c_args(db) == 'Py_ssize_t arg0'
        assert PyPy_TypedefTest2.api_func.get_c_restype(db) == 'Py_ssize_t *'
        assert PyPy_TypedefTest2.api_func.get_c_args(db) == 'Py_ssize_t *arg0'

        PyPy_TypedefTest1(space, 0)
        ppos = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')
        ppos[0] = 0
        PyPy_TypedefTest2(space, ppos)
        lltype.free(ppos, flavor='raw')

@pytest.mark.skipif(os.environ.get('USER')=='root',
                    reason='root can write to all files')
def test_copy_header_files(tmpdir):
    copy_header_files(tmpdir, True)
    def check(name):
        f = tmpdir.join(name)
        assert f.check(file=True)
        py.test.raises(py.error.EACCES, "f.open('w')") # check that it's not writable
    check('Python.h')
    check('modsupport.h')
    check('pypy_decl.h')
