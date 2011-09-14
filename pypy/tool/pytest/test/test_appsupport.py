import sys
import py
import pypy

pytest_plugins = "pytester"

def setpypyconftest(testdir):
    path = str(py.path.local(pypy.__file__).dirpath().dirpath())
    testdir.makeconftest("""
        import sys
        sys.path.insert(0, %r)
        from pypy.conftest import *
    """ % path)

def test_pypy_collection(testdir):
    testdir.makepyfile("""
        def test_func():
            pass
        class TestClassInt:
            def test_method(self, space):
                pass
        class AppTestClass:
            def test_method(self):
                pass
    """)
    setpypyconftest(testdir)
    result = testdir.runpytest("--collectonly")
    assert result.ret == 0
    result.stdout.fnmatch_lines([
        "*IntTestFunction*test_func*",
        "*IntClassCollector*TestClassInt*",
        "*IntTestFunction*test_method*",
        "*AppClassCollector*AppTestClass*",
        "*AppTestMethod*", 
    ])

class TestSpaceConfig:
    def test_applevel_skipped_on_cpython_and_spaceconfig(self, testdir):
        setpypyconftest(testdir)
        testdir.makepyfile("""
            class AppTestClass:
                spaceconfig = {"objspace.usemodules._random": True}
                def setup_class(cls):
                    assert 0
                def test_applevel(self):
                    pass
        """)
        result = testdir.runpytest("-A")
        assert result.ret == 0
        if hasattr(sys, 'pypy_translation_info') and \
           sys.pypy_translation_info.get('objspace.usemodules._random'):
            result.stdout.fnmatch_lines(["*1 error*"])
        else:
            # setup_class didn't get called, otherwise it would error
            result.stdout.fnmatch_lines(["*1 skipped*"])

    def test_interp_spaceconfig(self, testdir):
        setpypyconftest(testdir)
        p = testdir.makepyfile("""
            class TestClass:
                spaceconfig = {"objspace.usemodules._random": False}
                def setup_class(cls):
                    assert not cls.space.config.objspace.usemodules._random
                def test_interp(self, space):
                    assert self.space is space
                def test_interp2(self, space):
                    assert self.space is space
        """)
        result = testdir.runpytest(p)
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*2 passed*"])

def test_applevel_raises_simple_display(testdir):
    setpypyconftest(testdir)
    p = testdir.makepyfile("""
        def app_test_raises():
            raises(ValueError, x)
        class AppTestRaises:
            def test_func(self):
                raises (ValueError, x)
        #
    """)
    result = testdir.runpytest(p, "-s")
    assert result.ret == 1
    result.stdout.fnmatch_lines([
        "*E*application-level*NameError*x*not defined",
        "*test_func(self)*",
        ">*raises*ValueError*",
        "*E*application-level*NameError*x*not defined",
        "*test_applevel_raises_simple_display*",
    ])
    result = testdir.runpytest(p) # this time we may run the pyc file
    assert result.ret == 1
    result.stdout.fnmatch_lines([
        "*E*application-level*NameError*x*not defined",
    ])

def test_applevel_raises_display(testdir):
    setpypyconftest(testdir)
    p = testdir.makepyfile("""
        def app_test_raises():
            raises(ValueError, "x")
            pass
    """)
    result = testdir.runpytest(p, "-s")
    assert result.ret == 1
    result.stdout.fnmatch_lines([
        "*E*application-level*NameError*x*not defined",
    ])
    result = testdir.runpytest(p) # this time we may run the pyc file
    assert result.ret == 1
    result.stdout.fnmatch_lines([
        "*E*application-level*NameError*x*not defined",
    ])

def test_applevel_raise_keyerror(testdir):
    setpypyconftest(testdir)
    p = testdir.makepyfile("""
        def app_test_raises():
            raise KeyError(42)
            pass
    """)
    result = testdir.runpytest(p, "-s")
    assert result.ret == 1
    result.stdout.fnmatch_lines([
        "*E*application-level*KeyError*42*",
    ])

def app_test_raises():
    info = raises(TypeError, id)
    assert info.type is TypeError
    assert isinstance(info.value, TypeError)

    x = 43
    info = raises(ZeroDivisionError, "x/0")
    assert info.type is ZeroDivisionError    
    assert isinstance(info.value, ZeroDivisionError)    
