import py
from pypy.interpreter.module import Module
from pypy.interpreter import gateway
import pypy.interpreter.pycode
from pypy.tool.udir import udir 
import sys, os
import tempfile, marshal
from pypy.lib._osfilewrapper import OsFileWrapper

from pypy.module.__builtin__.importing import BIN_READMASK

def _setup(space): 
    dn=os.path.abspath(os.path.join(os.path.dirname(__file__), 'impsubdir'))
    return space.appexec([space.wrap(dn)], """
        (dn): 
            import sys
            sys.path.append(dn)
            return sys.modules.copy()
    """)

def _teardown(space, w_saved_modules):
    space.appexec([w_saved_modules], """
        (saved_modules): 
            import sys
            sys.path.pop()
            sys.modules.clear()
            sys.modules.update(saved_modules)
    """)

class AppTestImport:

    def setup_class(cls): # interpreter-level
        cls.saved_modules = _setup(cls.space)

    def teardown_class(cls): # interpreter-level
        _teardown(cls.space, cls.saved_modules)

    def test_import_bare_dir_fails(self):
        def imp():
            import notapackage
        raises(ImportError, imp)

    def test_import_sys(self):
        import sys

    def test_import_a(self):
        import sys
        import a
        assert a == sys.modules.get('a')

    def test_import_a_cache(self):
        import sys
        import a
        a0 = a
        import a
        assert a == a0

    def test_import_pkg(self):
        import sys
        import pkg
        assert pkg == sys.modules.get('pkg')

    def test_import_dotted(self):
        import sys
        import pkg.a
        assert pkg == sys.modules.get('pkg')
        assert pkg.a == sys.modules.get('pkg.a')

    def test_import_dotted_cache(self):
        import sys
        import pkg.a
        assert pkg == sys.modules.get('pkg')
        assert pkg.a == sys.modules.get('pkg.a')
        pkg0 = pkg
        pkg_a0 = pkg.a
        import pkg.a
        assert pkg == pkg0
        assert pkg.a == pkg_a0

    def test_import_dotted2(self):
        import sys
        import pkg.pkg1.a
        assert pkg == sys.modules.get('pkg')
        assert pkg.pkg1 == sys.modules.get('pkg.pkg1')
        assert pkg.pkg1.a == sys.modules.get('pkg.pkg1.a')

    def test_import_ambig(self):
        import sys
        import ambig
        assert ambig == sys.modules.get('ambig')
        assert hasattr(ambig,'imapackage')

    def test_from_a(self):
        import sys
        from a import imamodule
        assert 'a' in sys.modules
        assert imamodule == 1

    def test_from_dotted(self):
        import sys
        from pkg.a import imamodule
        assert 'pkg' in sys.modules
        assert 'pkg.a' in sys.modules
        assert imamodule == 1

    def test_from_pkg_import_module(self):
        import sys
        from pkg import a
        assert 'pkg' in sys.modules
        assert 'pkg.a' in sys.modules
        pkg = sys.modules.get('pkg')
        assert a == pkg.a
        aa = sys.modules.get('pkg.a')
        assert a == aa

    def test_import_relative(self):
        from pkg import relative_a
        assert relative_a.a.inpackage ==1

    def test_import_relative_back_to_absolute(self):
        from pkg import abs_b
        assert abs_b.b.inpackage ==0
        import sys
        assert sys.modules.get('pkg.b') ==None

    def test_import_pkg_relative(self):
        import pkg_relative_a
        assert pkg_relative_a.a.inpackage ==1

    def test_import_relative_partial_success(self):
        def imp():
            import pkg_r.inpkg
        raises(ImportError,imp)

    def test_import_Globals_Are_None(self):
        import sys
        m = __import__('sys')
        assert sys == m
        n = __import__('sys', None, None, [''])
        assert sys == n

    def test_import_relative_back_to_absolute2(self):
        from pkg import abs_x_y
        import sys
        assert abs_x_y.x.__name__ =='x'
        assert abs_x_y.x.y.__name__ =='x.y'
        # grrr XXX not needed probably...
        #self.assertEquals(sys.modules.get('pkg.x'),None)
        #self.assert_('pkg.x.y' not in sys.modules)

    def test_substituting_import(self):
        from pkg_substituting import mod
        assert mod.__name__ =='pkg_substituting.mod'

    def test_proper_failure_on_killed__path__(self):
        import pkg.pkg2.a
        del pkg.pkg2.__path__
        def imp_b():
            import pkg.pkg2.b
        raises(ImportError,imp_b)

from pypy.module.__builtin__ import importing

def _getlong(data):
    x = marshal.dumps(data)
    return x[-4:]

def _testfile(magic, mtime, co=None):
    fd, cpathname = tempfile.mkstemp()
    os.close(fd)
    f = file(cpathname, "wb")
    f.write(_getlong(magic))
    f.write(_getlong(mtime))
    if co:
        marshal.dump(co, f)
    f.close()
    return cpathname

class TestPycStuff:
    # ___________________ .pyc related stuff _________________

    def test_check_compiled_module(self):
        pathname = "whatever"
        mtime = 12345
        cpathname = _testfile(importing.pyc_magic, mtime)
        ret = importing.check_compiled_module(pathname, mtime, cpathname)
        assert ret == 1

        # check for wrong mtime
        ret = importing.check_compiled_module(pathname, mtime+1, cpathname)
        assert ret == 0
        os.remove(cpathname)

        # check for wrong version
        cpathname = _testfile(importing.pyc_magic+1, mtime)
        ret = importing.check_compiled_module(pathname, mtime, cpathname)
        assert ret == -1
        os.remove(cpathname)

    def test_read_compiled_module(self):
        space = self.space
        pathname = "whatever"
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(importing.pyc_magic, mtime, co)
        fd = os.open(cpathname, BIN_READMASK, 0777)
        os.lseek(fd, 8, 0)
        code_w = importing.read_compiled_module(space, cpathname, OsFileWrapper(fd))
        os.close(fd)
        assert type(code_w) is pypy.interpreter.pycode.PyCode
        w_dic = space.newdict([])
        code_w.exec_code(space, w_dic, w_dic)
        w_ret = space.getitem(w_dic, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

    def test_load_compiled_module(self):
        space = self.space
        pathname = "whatever"
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(importing.pyc_magic, mtime, co)
        w_modulename = space.wrap('somemodule')
        fd = os.open(cpathname, BIN_READMASK, 0777)
        w_mod = space.wrap(Module(space, w_modulename))
        w_ret = importing.load_compiled_module(space, w_modulename, w_mod, cpathname, OsFileWrapper(fd))
        os.close(fd)
        assert w_mod is w_ret
        w_ret = space.getattr(w_mod, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

def test_PYTHONPATH_takes_precedence(space): 
    if sys.platform == "win32":
        py.test.skip("unresolved issues with win32 shell quoting rules")
    from pypy.interpreter.test.test_py import pypypath 
    extrapath = udir.ensure("pythonpath", dir=1) 
    extrapath.join("urllib.py").write("print 42\n")
    old = os.environ.get('PYTHONPATH', None)
    try: 
        os.environ['PYTHONPATH'] = str(extrapath)
        output = py.process.cmdexec('''"%s" "%s" -c "import urllib"''' % 
                                 (sys.executable, pypypath) )
        assert output.strip() == '42' 
    finally: 
        if old: 
            os.environ['PYTHONPATH'] = old 
