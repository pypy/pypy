# -*- coding: iso-8859-1 -*-
import autopath
from pypy.conftest import option
from py.test import raises
from pypy.interpreter.gateway import app2interp_temp

def init_globals_via_builtins_hack(space):
    space.appexec([], """():
    import __builtin__ as b
    import cStringIO, sys
    b.cStringIO = cStringIO
    b.sys = sys
    """)

def test_stdin_exists(space):
    space.sys.get('stdin') 
    space.sys.get('__stdin__')

def test_stdout_exists(space):
    space.sys.get('stdout') 
    space.sys.get('__stdout__')

class AppTestAppSysTests:

    def setup_class(cls):
        cls.w_appdirect = cls.space.wrap(option.runappdirect)
    
    def test_sys_in_modules(self):
        import sys
        modules = sys.modules
        assert 'sys' in modules, ( "An entry for sys "
                                        "is not in sys.modules.")
        sys2 = sys.modules['sys']
        assert sys is sys2, "import sys is not sys.modules[sys]." 
    def test_builtin_in_modules(self):
        import sys
        modules = sys.modules
        assert '__builtin__' in modules, ( "An entry for __builtin__ "
                                                    "is not in sys.modules.")
        import __builtin__
        builtin2 = sys.modules['__builtin__']
        assert __builtin__ is builtin2, ( "import __builtin__ "
                                            "is not sys.modules[__builtin__].")
    def test_builtin_module_names(self):
        import sys
        names = sys.builtin_module_names
        assert 'sys' in names, (
                        "sys is not listed as a builtin module.")
        assert '__builtin__' in names, (
                        "__builtin__ is not listed as a builtin module.")

    def test_sys_exc_info(self):
        try:
            raise Exception
        except Exception,e:
            import sys
            exc_type,exc_val,tb = sys.exc_info()
        try:
            raise Exception   # 5 lines below the previous one
        except Exception,e2:
            exc_type2,exc_val2,tb2 = sys.exc_info()
        assert exc_type ==Exception
        assert exc_val ==e
        assert exc_type2 ==Exception
        assert exc_val2 ==e2
        assert tb2.tb_lineno - tb.tb_lineno == 5

    def test_dynamic_attributes(self):
        try:
            raise Exception
        except Exception,e:
            import sys
            exc_type = sys.exc_type
            exc_val = sys.exc_value
            tb = sys.exc_traceback
        try:
            raise Exception   # 7 lines below the previous one
        except Exception,e2:
            exc_type2 = sys.exc_type
            exc_val2 = sys.exc_value
            tb2 = sys.exc_traceback
        assert exc_type ==Exception
        assert exc_val ==e
        assert exc_type2 ==Exception
        assert exc_val2 ==e2
        assert tb2.tb_lineno - tb.tb_lineno == 7

    def test_exc_info_normalization(self):
        import sys
        try:
            1/0
        except ZeroDivisionError:
            etype, val, tb = sys.exc_info()
            assert isinstance(val, etype)
        else:
            raise AssertionError, "ZeroDivisionError not caught"

    def test_io(self): 
        import sys
        assert isinstance(sys.__stdout__, file)
        assert isinstance(sys.__stderr__, file)
        assert isinstance(sys.__stdin__, file)
    
        if self.appdirect and not isinstance(sys.stdin, file):
            return

        assert isinstance(sys.stdout, file)
        assert isinstance(sys.stderr, file)
        assert isinstance(sys.stdin, file)

class AppTestSysModulePortedFromCPython:

    def setup_class(cls):
        init_globals_via_builtins_hack(cls.space)
        cls.w_appdirect = cls.space.wrap(option.runappdirect)

    def test_original_displayhook(self):
        import __builtin__
        savestdout = sys.stdout
        out = cStringIO.StringIO()
        sys.stdout = out

        dh = sys.__displayhook__

        raises(TypeError, dh)
        if hasattr(__builtin__, "_"):
            del __builtin__._

        dh(None)
        assert out.getvalue() == ""
        assert not hasattr(__builtin__, "_")
        dh("hello")
        assert out.getvalue() == "'hello'\n"
        assert __builtin__._ == "hello"

        del sys.stdout
        raises(RuntimeError, dh, 42)

        sys.stdout = savestdout

    def test_lost_displayhook(self):
        olddisplayhook = sys.displayhook
        del sys.displayhook
        code = compile("42", "<string>", "single")
        raises(RuntimeError, eval, code)
        sys.displayhook = olddisplayhook

    def test_custom_displayhook(self):
        olddisplayhook = sys.displayhook
        def baddisplayhook(obj):
            raise ValueError
        sys.displayhook = baddisplayhook
        code = compile("42", "<string>", "single")
        raises(ValueError, eval, code)
        sys.displayhook = olddisplayhook

    def test_original_excepthook(self):
        import cStringIO
        savestderr = sys.stderr
        err = cStringIO.StringIO()
        sys.stderr = err

        eh = sys.__excepthook__

        raises(TypeError, eh)
        try:
            raise ValueError(42)
        except ValueError, exc:
            eh(*sys.exc_info())

        sys.stderr = savestderr
        assert err.getvalue().endswith("ValueError: 42\n")

    # FIXME: testing the code for a lost or replaced excepthook in
    # Python/pythonrun.c::PyErr_PrintEx() is tricky.

    def test_exc_clear(self):
        raises(TypeError, sys.exc_clear, 42)

        # Verify that exc_info is present and matches exc, then clear it, and
        # check that it worked.
        def clear_check(exc):
            typ, value, traceback = sys.exc_info()
            assert typ is not None
            assert value is exc
            assert traceback is not None

            sys.exc_clear()

            typ, value, traceback = sys.exc_info()
            assert typ is None
            assert value is None
            assert traceback is None

        def clear():
            try:
                raise ValueError, 42
            except ValueError, exc:
                clear_check(exc)

        # Raise an exception and check that it can be cleared
        clear()

        # Verify that a frame currently handling an exception is
        # unaffected by calling exc_clear in a nested frame.
        try:
            raise ValueError, 13
        except ValueError, exc:
            typ1, value1, traceback1 = sys.exc_info()
            clear()
            typ2, value2, traceback2 = sys.exc_info()

            assert typ1 is typ2
            assert value1 is exc
            assert value1 is value2
            assert traceback1 is traceback2

        # Check that an exception can be cleared outside of an except block
        clear_check(exc)

    def test_exit(self):
        raises(TypeError, sys.exit, 42, 42)

        # call without argument
        try:
            sys.exit(0)
        except SystemExit, exc:
            assert exc.code == 0
        except:
            raise AssertionError, "wrong exception"
        else:
            raise AssertionError, "no exception"

        # call with tuple argument with one entry
        # entry will be unpacked
        try:
            sys.exit(42)
        except SystemExit, exc:
            assert exc.code == 42
        except:
            raise AssertionError, "wrong exception"
        else:
            raise AssertionError, "no exception"

        # call with integer argument
        try:
            sys.exit((42,))
        except SystemExit, exc:
            assert exc.code == 42
        except:
            raise AssertionError, "wrong exception"
        else:
            raise AssertionError, "no exception"

        # call with string argument
        try:
            sys.exit("exit")
        except SystemExit, exc:
            assert exc.code == "exit"
        except:
            raise AssertionError, "wrong exception"
        else:
            raise AssertionError, "no exception"

        # call with tuple argument with two entries
        try:
            sys.exit((17, 23))
        except SystemExit, exc:
            assert exc.code == (17, 23)
        except:
            raise AssertionError, "wrong exception"
        else:
            raise AssertionError, "no exception"

    def test_getdefaultencoding(self):
        raises(TypeError, sys.getdefaultencoding, 42)
        # can't check more than the type, as the user might have changed it
        assert isinstance(sys.getdefaultencoding(), str)

    def test_setdefaultencoding(self):
        if self.appdirect:
            skip("not worth running appdirect")
            
        encoding = sys.getdefaultencoding()
        try:
            sys.setdefaultencoding("ascii")
            assert sys.getdefaultencoding() == 'ascii'
            raises(UnicodeDecodeError, unicode, '\x80')

            sys.setdefaultencoding("latin-1")
            assert sys.getdefaultencoding() == 'latin-1'
            assert unicode('\x80') == u'\u0080'
            
        finally:
            sys.setdefaultencoding(encoding)

            
    # testing sys.settrace() is done in test_trace.py
    # testing sys.setprofile() is done in test_profile.py

    def test_setcheckinterval(self):
        raises(TypeError, sys.setcheckinterval)
        orig = sys.getcheckinterval()
        for n in 0, 100, 120, orig: # orig last to restore starting state
            sys.setcheckinterval(n)
            assert sys.getcheckinterval() == n

    def test_recursionlimit(self):
        raises(TypeError, sys.getrecursionlimit, 42)
        oldlimit = sys.getrecursionlimit()
        raises(TypeError, sys.setrecursionlimit)
        raises(ValueError, sys.setrecursionlimit, -42)
        sys.setrecursionlimit(10000)
        assert sys.getrecursionlimit() == 10000
        sys.setrecursionlimit(oldlimit)

    def test_getwindowsversion(self):
        if hasattr(sys, "getwindowsversion"):
            v = sys.getwindowsversion()
            assert isinstance(v, tuple)
            assert len(v) == 5
            assert isinstance(v[0], int)
            assert isinstance(v[1], int)
            assert isinstance(v[2], int)
            assert isinstance(v[3], int)
            assert isinstance(v[4], str)

    def test_dlopenflags(self):
        if hasattr(sys, "setdlopenflags"):
            assert hasattr(sys, "getdlopenflags")
            raises(TypeError, sys.getdlopenflags, 42)
            oldflags = sys.getdlopenflags()
            raises(TypeError, sys.setdlopenflags)
            sys.setdlopenflags(oldflags+1)
            assert sys.getdlopenflags() == oldflags+1
            sys.setdlopenflags(oldflags)

    def test_refcount(self):
        if not hasattr(sys, "getrefcount"):
            skip('Reference counting is not implemented.')

        raises(TypeError, sys.getrefcount)
        c = sys.getrefcount(None)
        n = None
        assert sys.getrefcount(None) == c+1
        del n
        assert sys.getrefcount(None) == c
        if hasattr(sys, "gettotalrefcount"):
            assert isinstance(sys.gettotalrefcount(), int)

    def test_getframe(self):
        raises(TypeError, sys._getframe, 42, 42)
        raises(ValueError, sys._getframe, 2000000000)
        assert sys._getframe().f_code.co_name == 'test_getframe'
        #assert (
        #    TestSysModule.test_getframe.im_func.func_code \
        #    is sys._getframe().f_code
        #)

    def test_getframe_in_returned_func(self):
        def f():
            return g()
        def g():
            return sys._getframe(0)
        frame = f()
        assert frame.f_code.co_name == 'g'
        assert frame.f_back.f_code.co_name == 'f'
        assert frame.f_back.f_back.f_code.co_name == 'test_getframe_in_returned_func'

    def test_attributes(self):
        assert sys.__name__ == 'sys'
        assert isinstance(sys.modules, dict)
        assert isinstance(sys.path, list)
        assert isinstance(sys.api_version, int)
        assert isinstance(sys.argv, list)
        assert sys.byteorder in ("little", "big")
        assert isinstance(sys.builtin_module_names, tuple)
        assert isinstance(sys.copyright, basestring)
        #assert isinstance(sys.exec_prefix, basestring) -- not present!
        assert isinstance(sys.executable, basestring)
        assert isinstance(sys.hexversion, int)
        assert isinstance(sys.maxint, int)
        assert isinstance(sys.maxunicode, int)
        assert isinstance(sys.platform, basestring)
        #assert isinstance(sys.prefix, basestring) -- not present!
        assert isinstance(sys.version, basestring)
        assert isinstance(sys.warnoptions, list)
        vi = sys.version_info
        assert isinstance(vi, tuple)
        assert len(vi) == 5
        assert isinstance(vi[0], int)
        assert isinstance(vi[1], int)
        assert isinstance(vi[2], int)
        assert vi[3] in ("alpha", "beta", "candidate", "final")
        assert isinstance(vi[4], int)

    def test_settrace(self):
        counts = []
        def trace(x, y, z):
            counts.append(None)

        def x():
            pass
        sys.settrace(trace)
        try:
            x()
        finally:
            sys.settrace(None)
        assert len(counts) == 1

    def test_pypy_attributes(self):
        assert isinstance(sys.pypy_objspaceclass, str)
        assert isinstance(sys.pypy_svn_url, tuple)
        url = sys.pypy_svn_url
        assert isinstance(url[0], str)
        vi = sys.pypy_version_info
        assert isinstance(vi, tuple)
        assert len(vi) == 5
        assert isinstance(vi[0], int)
        assert isinstance(vi[1], int)
        assert isinstance(vi[2], int)
        assert vi[3] in ("alpha", "beta", "candidate", "final")
        assert isinstance(vi[4], int)
        assert url[1] == vi[4]

    def test_allattributes(self):
        sys.__dict__   # check that we don't crash initializing any attribute

    def test_subversion(self):
        project, svnbranch, revision = sys.subversion
        assert project == 'PyPy'
        assert svnbranch == svnbranch.strip('/')
        assert revision.isdigit()

    def test_trace_exec_execfile(self):
        found = []
        def do_tracing(f, *args):
            print f.f_code.co_filename, f.f_lineno, args
            if f.f_code.co_filename == 'foobar':
                found.append(args[0])
            return do_tracing
        co = compile("execfile('this-file-does-not-exist!')",
                     'foobar', 'exec')
        sys.settrace(do_tracing)
        try:
            exec co in {}
        except IOError:
            pass
        sys.settrace(None)
        assert found == ['call', 'line', 'exception', 'return']
