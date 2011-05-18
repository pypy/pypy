import py
import sys
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.ll2ctypes import ALLOCATED
from pypy.rlib.test.test_clibffi import BaseFfiTest, get_libm_name
from pypy.rlib.libffi import CDLL, Func, get_libc_name, ArgChain, types

class TestLibffiMisc(BaseFfiTest):

    CDLL = CDLL

    def test_argchain(self):
        chain = ArgChain()
        assert chain.numargs == 0
        chain2 = chain.arg(42)
        assert chain2 is chain
        assert chain.numargs == 1
        intarg = chain.first
        assert chain.last is intarg
        assert intarg.intval == 42
        chain.arg(123.45)
        assert chain.numargs == 2
        assert chain.first is intarg
        assert intarg.next is chain.last
        floatarg = intarg.next
        assert floatarg.floatval == 123.45

    def test_wrong_args(self):
        # so far the test passes but for the wrong reason :-), i.e. because
        # .arg() only supports integers and floats
        chain = ArgChain()
        x = lltype.malloc(lltype.GcStruct('xxx'))
        y = lltype.malloc(lltype.GcArray(rffi.LONG), 3)
        z = lltype.malloc(lltype.Array(rffi.LONG), 4, flavor='raw')
        py.test.raises(TypeError, "chain.arg(x)")
        py.test.raises(TypeError, "chain.arg(y)")
        py.test.raises(TypeError, "chain.arg(z)")
        lltype.free(z, flavor='raw')

    def test_library_open(self):
        lib = self.get_libc()
        del lib
        assert not ALLOCATED

    def test_library_get_func(self):
        lib = self.get_libc()
        ptr = lib.getpointer('fopen', [], types.void)
        py.test.raises(KeyError, lib.getpointer, 'xxxxxxxxxxxxxxx', [], types.void)
        del ptr
        del lib
        assert not ALLOCATED


class TestLibffiCall(BaseFfiTest):
    """
    Test various kind of calls through libffi.

    The peculiarity of these tests is that they are run both directly (going
    really through libffi) and by jit/metainterp/test/test_fficall.py, which
    tests the call when JITted.

    If you need to test a behaviour than it's not affected by JITing (e.g.,
    typechecking), you should put your test in TestLibffiMisc.
    """

    CDLL = CDLL

    @classmethod
    def setup_class(cls):
        from pypy.tool.udir import udir
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        from pypy.translator.platform import platform

        BaseFfiTest.setup_class()
        # prepare C code as an example, so we can load it and call
        # it via rlib.libffi
        c_file = udir.ensure("test_libffi", dir=1).join("foolib.c")
        # automatically collect the C source from the docstrings of the tests
        snippets = []
        exports = []
        for name in dir(cls):
            if name.startswith('test_'):
                meth = getattr(cls, name)
                # the heuristic to determine it it's really C code could be
                # improved: so far we just check that there is a '{' :-)
                if meth.__doc__ is not None and '{' in meth.__doc__:
                    snippets.append(meth.__doc__)
                    import re
                    for match in re.finditer(" ([a-z_]+)\(", meth.__doc__):
                        exports.append(match.group(1))
        #
        c_file.write(py.code.Source('\n'.join(snippets)))
        eci = ExternalCompilationInfo(export_symbols=exports)
        cls.libfoo_name = str(platform.compile([c_file], eci, 'x',
                                               standalone=False))

    def get_libfoo(self):
        return self.CDLL(self.libfoo_name)

    def call(self, funcspec, args, RESULT, init_result=0):
        """
        Call the specified function after constructing and ArgChain with the
        arguments in ``args``.

        The function is specified with ``funcspec``, which is a tuple of the
        form (lib, name, argtypes, restype).

        This method is overridden by metainterp/test/test_fficall.py in
        order to do the call in a loop and JIT it. The optional arguments are
        used only by that overridden method.
        
        """
        lib, name, argtypes, restype = funcspec
        func = lib.getpointer(name, argtypes, restype)
        chain = ArgChain()
        for arg in args:
            chain.arg(arg)
        return func.call(chain, RESULT)

    def check_loops(self, *args, **kwds):
        """
        Ignored here, but does something in the JIT tests
        """
        pass

    # ------------------------------------------------------------------------

    def test_simple(self):
        """
            int sum_xy(int x, double y)
            {
                return (x + (int)y);
            }
        """
        libfoo = self.get_libfoo() 
        func = (libfoo, 'sum_xy', [types.sint, types.double], types.sint)
        res = self.call(func, [38, 4.2], rffi.LONG)
        assert res == 42
        self.check_loops({
                'call_may_force': 1,
                'guard_no_exception': 1,
                'guard_not_forced': 1,
                'int_add': 1,
                'int_lt': 1,
                'guard_true': 1,
                'jump': 1})

    def test_float_result(self):
        libm = self.get_libm()
        func = (libm, 'pow', [types.double, types.double], types.double)
        res = self.call(func, [2.0, 3.0], rffi.DOUBLE, init_result=0.0)
        assert res == 8.0
        self.check_loops(call_may_force=1, guard_no_exception=1, guard_not_forced=1)

    def test_cast_result(self):
        """
            unsigned char cast_to_uchar_and_ovf(int x)
            {
                return 200+(unsigned char)x;
            }
        """
        libfoo = self.get_libfoo()
        func = (libfoo, 'cast_to_uchar_and_ovf', [types.sint], types.uchar)
        res = self.call(func, [0], rffi.UCHAR)
        assert res == 200
        self.check_loops(call_may_force=1, guard_no_exception=1, guard_not_forced=1)

    def test_cast_argument(self):
        """
            int many_args(char a, int b)
            {
                return a+b;
            }
        """
        libfoo = self.get_libfoo()
        func = (libfoo, 'many_args', [types.uchar, types.sint], types.sint)
        res = self.call(func, [chr(20), 22], rffi.LONG)
        assert res == 42

    def test_unsigned_short_args(self):
        """
            unsigned short sum_xy_us(unsigned short x, unsigned short y)
            {
                return x+y;
            }
        """
        libfoo = self.get_libfoo()
        func = (libfoo, 'sum_xy_us', [types.ushort, types.ushort], types.ushort)
        res = self.call(func, [32000, 8000], rffi.USHORT)
        assert res == 40000


    def test_pointer_as_argument(self):
        """#include <stdlib.h>
            long inc(long* x)
            {
                long oldval;
                if (x == NULL)
                    return -1;
                oldval = *x;
                *x = oldval+1;
                return oldval;
            }
        """
        libfoo = self.get_libfoo()
        func = (libfoo, 'inc', [types.pointer], types.slong)
        LONGP = lltype.Ptr(rffi.CArray(rffi.LONG))
        null = lltype.nullptr(LONGP.TO)
        res = self.call(func, [null], rffi.LONG)
        assert res == -1
        #
        ptr_result = lltype.malloc(LONGP.TO, 1, flavor='raw')
        ptr_result[0] = 41
        res = self.call(func, [ptr_result], rffi.LONG)
        if self.__class__ is TestLibffiCall:
            # the function was called only once
            assert res == 41
            assert ptr_result[0] == 42
            lltype.free(ptr_result, flavor='raw')
            # the test does not make sense when run with the JIT through
            # meta_interp, because the __del__ are not properly called (hence
            # we "leak" memory)
            del libfoo
            assert not ALLOCATED
        else:
            # the function as been called 9 times
            assert res == 50
            assert ptr_result[0] == 51
            lltype.free(ptr_result, flavor='raw')

    def test_return_pointer(self):
        """
            struct pair {
                long a;
                long b;
            };

            struct pair my_static_pair = {10, 20};
            
            long* get_pointer_to_b()
            {
                return &my_static_pair.b;
            }
        """
        libfoo = self.get_libfoo()
        func = (libfoo, 'get_pointer_to_b', [], types.pointer)
        LONGP = lltype.Ptr(rffi.CArray(rffi.LONG))
        null = lltype.nullptr(LONGP.TO)
        res = self.call(func, [], LONGP, init_result=null)
        assert res[0] == 20

    def test_void_result(self):
        """
            int dummy;
            void set_dummy(int val) { dummy = val; }
            int get_dummy() { return dummy; }
        """
        libfoo = self.get_libfoo()
        set_dummy = (libfoo, 'set_dummy', [types.sint], types.void)
        get_dummy = (libfoo, 'get_dummy', [], types.sint)
        #
        initval = self.call(get_dummy, [], rffi.LONG)
        #
        res = self.call(set_dummy, [initval+1], lltype.Void, init_result=None)
        assert res is None
        #
        res = self.call(get_dummy, [], rffi.LONG)
        assert res == initval+1

    def test_wrong_number_of_arguments(self):
        from pypy.rpython.llinterp import LLException
        libfoo = self.get_libfoo() 
        func = (libfoo, 'sum_xy', [types.sint, types.double], types.sint)

        glob = globals()
        loc = locals()
        def my_raises(s):
            try:
                exec s in glob, loc
            except TypeError:
                pass
            except LLException, e:
                if str(e) != "<LLException 'TypeError'>":
                    raise
            else:
                assert False, 'Did not raise'

        my_raises("self.call(func, [38], rffi.LONG)") # one less
        my_raises("self.call(func, [38, 12.3, 42], rffi.LONG)") # one more
