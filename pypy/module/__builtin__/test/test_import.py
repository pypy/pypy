import py
from pypy.interpreter.module import Module
from pypy.interpreter import gateway
import pypy.interpreter.pycode
from pypy.tool.udir import udir
from pypy.rlib import streamio
from pypy.conftest import gettestobjspace
import sys, os
import tempfile, marshal

from pypy.module.__builtin__ import importing

from pypy import conftest

def setuppkg(pkgname, **entries):
    p = udir.join('impsubdir')
    if pkgname:
        p = p.join(*pkgname.split('.'))
    p.ensure(dir=1)
    f = p.join("__init__.py").open('w')
    print >> f, "# package"
    f.close()
    for filename, content in entries.items():
        filename += '.py'
        f = p.join(filename).open('w')
        print >> f, '#', filename
        print >> f, content
        f.close()
    return p

def setup_directory_structure(space):
    root = setuppkg("",
                    a = "imamodule = 1\ninpackage = 0",
                    b = "imamodule = 1\ninpackage = 0",
                    ambig = "imamodule = 1",
                    )
    root.ensure("notapackage", dir=1)    # empty, no __init__.py
    setuppkg("pkg",
             a          = "imamodule = 1\ninpackage = 1",
             relative_a = "import a",
             abs_b      = "import b",
             abs_x_y    = "import x.y",
             )
    setuppkg("pkg.pkg1", a='')
    setuppkg("pkg.pkg2", a='', b='')
    setuppkg("pkg_r", inpkg = "import x.y")
    setuppkg("pkg_r.x")
    setuppkg("x", y='')
    setuppkg("ambig", __init__ = "imapackage = 1")
    setuppkg("pkg_relative_a",
             __init__ = "import a",
             a        = "imamodule = 1\ninpackage = 1",
             )
    setuppkg("pkg_substituting",
             __init__ = "import sys, pkg_substituted\n"
                        "sys.modules[__name__] = pkg_substituted")
    setuppkg("pkg_substituted", mod='')
    p = setuppkg("readonly", x='')

    # create compiled/x.py and a corresponding pyc file
    p = setuppkg("compiled", x = "x = 84")
    if conftest.option.runappdirect:
        pass
    else:
        w = space.wrap
        w_modname = w("compiled.x")
        filename = str(p.join("x.py"))
        stream = streamio.open_file_as_stream(filename, "r")
        try:
            importing.load_source_module(space,
                                         w_modname,
                                         w(importing.Module(space, w_modname)),
                                         filename,
                                         stream)
        finally:
            stream.close()

    return str(root)


def _setup(space):
    dn = setup_directory_structure(space)
    return space.appexec([space.wrap(dn)], """
        (dn): 
            import sys
            path = list(sys.path)
            sys.path.insert(0, dn)
            return path, sys.modules.copy()
    """)

def _teardown(space, w_saved_modules):
    space.appexec([w_saved_modules], """
        ((saved_path, saved_modules)): 
            import sys
            sys.path[:] = saved_path
            sys.modules.clear()
            sys.modules.update(saved_modules)
    """)

class AppTestImport:

    def setup_class(cls): # interpreter-level
        cls.saved_modules = _setup(cls.space)
        #XXX Compile class

        
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

    def test_pyc(self):
        import sys
        import compiled.x
        assert compiled.x == sys.modules.get('compiled.x')

    def test_cannot_write_pyc(self):
        import sys, os
        p = os.path.join(sys.path[-1], 'readonly')
        try:
            os.chmod(p, 0555)
        except:
            skip("cannot chmod() the test directory to read-only")
        try:
            import readonly.x    # cannot write x.pyc, but should not crash
        finally:
            os.chmod(p, 0775)

    def test__import__empty_string(self):
        raises(ValueError, __import__, "")

    def test_invalid__name__(self):
        glob = {}
        exec "__name__ = None; import sys" in glob
        import sys
        assert glob['sys'] is sys

def _getlong(data):
    x = marshal.dumps(data)
    return x[-4:]

def _testfile(magic, mtime, co=None):
    cpathname = str(udir.join('test.pyc'))
    f = file(cpathname, "wb")
    f.write(_getlong(magic))
    f.write(_getlong(mtime))
    if co:
        marshal.dump(co, f)
    f.close()
    return cpathname

def _testfilesource():
    pathname = str(udir.join('test.py'))
    f = file(pathname, "wb")
    f.write("x=42")
    f.close()
    return pathname

class TestPycStuff:
    # ___________________ .pyc related stuff _________________

    def test_check_compiled_module(self):
        space = self.space
        pathname = "whatever"
        mtime = 12345
        cpathname = _testfile(importing.get_pyc_magic(space), mtime)
        ret = importing.check_compiled_module(space,
                                              pathname,
                                              mtime,
                                              cpathname)
        assert ret == 1

        # check for wrong mtime
        ret = importing.check_compiled_module(space,
                                              pathname,
                                              mtime+1,
                                              cpathname)
        assert ret == 0
        os.remove(cpathname)

        # check for wrong version
        cpathname = _testfile(importing.get_pyc_magic(space)+1, mtime)
        ret = importing.check_compiled_module(space,
                                              pathname,
                                              mtime,
                                              cpathname)
        assert ret == -1

        # check for empty .pyc file
        f = open(cpathname, 'wb')
        f.close()
        ret = importing.check_compiled_module(space,
                                              pathname,
                                              mtime,
                                              cpathname)
        assert ret == -1
        os.remove(cpathname)

    def test_read_compiled_module(self):
        space = self.space
        pathname = "whatever"
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(importing.get_pyc_magic(space), mtime, co)
        stream = streamio.open_file_as_stream(cpathname, "r")
        try:
            stream.seek(8, 0)
            w_code = importing.read_compiled_module(
                    space, cpathname, stream)
            pycode = space.interpclass_w(w_code)
        finally:
            stream.close()
        assert type(pycode) is pypy.interpreter.pycode.PyCode
        w_dic = space.newdict()
        pycode.exec_code(space, w_dic, w_dic)
        w_ret = space.getitem(w_dic, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

    def test_load_compiled_module(self):
        space = self.space
        pathname = "whatever"
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(importing.get_pyc_magic(space), mtime, co)
        w_modulename = space.wrap('somemodule')
        stream = streamio.open_file_as_stream(cpathname, "r")
        try:
            w_mod = space.wrap(Module(space, w_modulename))
            w_ret = importing.load_compiled_module(space,
                                                   w_modulename,
                                                   w_mod,
                                                   cpathname,
                                                   stream)
        finally:
            stream.close()
        assert w_mod is w_ret
        w_ret = space.getattr(w_mod, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

    def test_parse_source_module(self):
        space = self.space
        pathname = _testfilesource()
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            w_ret = importing.parse_source_module(space,
                                                  pathname,
                                                  stream)
        finally:
            stream.close()
        pycode = space.interpclass_w(w_ret)
        assert type(pycode) is pypy.interpreter.pycode.PyCode
        w_dic = space.newdict()
        pycode.exec_code(space, w_dic, w_dic)
        w_ret = space.getitem(w_dic, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

    def test_long_writes(self):
        pathname = str(udir.join('test.dat'))
        stream = streamio.open_file_as_stream(pathname, "wb")
        try:
            importing._w_long(stream, 42)
            importing._w_long(stream, 12312)
            importing._w_long(stream, 128397198)
        finally:
            stream.close()
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            res = importing._r_long(stream)
            assert res == 42
            res = importing._r_long(stream)
            assert res == 12312
            res = importing._r_long(stream)
            assert res == 128397198
        finally:
            stream.close()

    def test_load_source_module(self):
        space = self.space
        w_modulename = space.wrap('somemodule')
        w_mod = space.wrap(Module(space, w_modulename))
        pathname = _testfilesource()
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            w_ret = importing.load_source_module(space,
                                                 w_modulename,
                                                 w_mod,
                                                 pathname,
                                                 stream)
        finally:
            stream.close()
        assert w_mod is w_ret
        w_ret = space.getattr(w_mod, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

        #XXX Note tested while no writing

    def test_write_compiled_module(self):
        space = self.space
        pathname = _testfilesource()
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            w_ret = importing.parse_source_module(space,
                                                  pathname,
                                                  stream)
        finally:
            stream.close()
        pycode = space.interpclass_w(w_ret)
        assert type(pycode) is pypy.interpreter.pycode.PyCode

        cpathname = str(udir.join('cpathname.pyc'))
        mtime = 12345
        importing.write_compiled_module(space,
                                        pycode,
                                        cpathname,
                                        mtime)

        # check
        pathname = str(udir.join('cpathname.py'))
        ret = importing.check_compiled_module(space,
                                              pathname,
                                              mtime,
                                              cpathname)
        assert ret == 1

        # read compile module
        stream = streamio.open_file_as_stream(cpathname, "r")
        try:
            stream.seek(8, 0)
            w_code = importing.read_compiled_module(space, cpathname, stream)
            pycode = space.interpclass_w(w_code)
        finally:
            stream.close()

        # check value of load
        w_dic = space.newdict()
        pycode.exec_code(space, w_dic, w_dic)
        w_ret = space.getitem(w_dic, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

    def test_pyc_magic_changes(self):
        # test that the pyc files produced by a space are not reimportable
        # from another, if they differ in what opcodes they support
        allspaces = [self.space]
        for opcodename in self.space.config.objspace.opcodes.getpaths():
            key = 'objspace.opcodes.' + opcodename
            space2 = gettestobjspace(**{key: True})
            allspaces.append(space2)
        for space1 in allspaces:
            for space2 in allspaces:
                if space1 is space2:
                    continue
                pathname = "whatever"
                mtime = 12345
                co = compile('x = 42', '?', 'exec')
                cpathname = _testfile(importing.get_pyc_magic(space1),
                                      mtime, co)
                w_modulename = space2.wrap('somemodule')
                stream = streamio.open_file_as_stream(cpathname, "r")
                try:
                    w_mod = space2.wrap(Module(space2, w_modulename))
                    space2.raises_w(space2.w_ImportError,
                                    importing.load_compiled_module,
                                    space2,
                                    w_modulename,
                                    w_mod,
                                    cpathname,
                                    stream)
                finally:
                    stream.close()


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
