import py
from pypy.interpreter.module import Module
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
import pypy.interpreter.pycode
from rpython.tool.udir import udir
from rpython.rlib import streamio
from pypy.tool.option import make_config
from pypy.tool.pytest.objspace import maketestobjspace
import pytest
import sys, os
import tempfile, marshal

from pypy.module.imp import importing

from pypy import conftest

def setuppkg(pkgname, **entries):
    p = udir.join('impsubdir')
    if pkgname:
        p = p.join(*pkgname.split('.'))
    p.ensure(dir=1)
    with p.join("__init__.py").open('w') as f:
        print >> f, "# package"
    for filename, content in entries.items():
        filename += '.py'
        with p.join(filename).open('w') as f:
            print >> f, '#', filename
            print >> f, content
    return p

def setup_directory_structure(space):
    root = setuppkg("",
                    a = "imamodule = 1\ninpackage = 0",
                    b = "imamodule = 1\ninpackage = 0",
                    ambig = "imamodule = 1",
                    test_reload = "def test():\n    raise ValueError\n",
                    infinite_reload = "import infinite_reload; reload(infinite_reload)",
                    del_sys_module = "import sys\ndel sys.modules['del_sys_module']\n",
                    _md5 = "hello_world = 42\n",
                    gc = "should_never_be_seen = 42\n",
                    )
    root.ensure("notapackage", dir=1)    # empty, no __init__.py
    setuppkg("pkg",
             a          = "imamodule = 1\ninpackage = 1",
             relative_a = "import a",
             abs_b      = "import b",
             abs_x_y    = "import x.y",
             abs_sys    = "import sys",
             string     = "inpackage = 1",
             errno      = "",
             absolute   = "from __future__ import absolute_import\nimport string",
             relative_b = "from __future__ import absolute_import\nfrom . import string",
             relative_c = "from __future__ import absolute_import\nfrom .string import inpackage",
             relative_f = "from .imp import get_magic",
             relative_g = "import imp; from .imp import get_magic",
             )
    setuppkg("pkg.pkg1",
             __init__   = 'from . import a',
             a          = '',
             relative_d = "from __future__ import absolute_import\nfrom ..string import inpackage",
             relative_e = "from __future__ import absolute_import\nfrom .. import string",
             relative_g = "from .. import pkg1\nfrom ..pkg1 import b",
             b          = "insubpackage = 1",
             )
    setuppkg("pkg.pkg2", a='', b='')
    setuppkg("pkg.withall",
             __init__  = "__all__ = ['foobar', 'barbaz']",
             foobar    = "found = 123",
             barbaz    = "other = 543")
    setuppkg("pkg.withoutall",
             __init__  = "",
             foobar    = "found = 123")
    setuppkg("pkg.bogusall",
             __init__  = "__all__ = 42")
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
                        "print 'TOTO', __name__\n"
                        "sys.modules[__name__] = pkg_substituted")
    setuppkg("pkg_substituted", mod='')
    setuppkg("evil_pkg",
             evil = "import sys\n"
                      "from evil_pkg import good\n"
                      "sys.modules['evil_pkg.evil'] = good",
             good = "a = 42")
    p = setuppkg("readonly", x='')
    p = setuppkg("pkg_univnewlines")
    p.join('__init__.py').write(
        'a=5\nb=6\rc="""hello\r\nworld"""\r', mode='wb')
    p.join('mod.py').write(
        'a=15\nb=16\rc="""foo\r\nbar"""\r', mode='wb')
    setuppkg("verbose1pkg", verbosemod='a = 1729')
    setuppkg("verbose2pkg", verbosemod='a = 1729')
    setuppkg("verbose0pkg", verbosemod='a = 1729')
    setuppkg("test_bytecode",
             a = '',
             b = '',
             c = '')

    # create compiled/x.py and a corresponding pyc file
    p = setuppkg("compiled", x = "x = 84")
    if conftest.option.runappdirect:
        import marshal, stat, struct, os, imp
        code = py.code.Source(p.join("x.py").read()).compile()
        s3 = marshal.dumps(code)
        s2 = struct.pack("<i", os.stat(str(p.join("x.py")))[stat.ST_MTIME])
        p.join("x.pyc").write(imp.get_magic() + s2 + s3, mode='wb')
    else:
        w = space.wrap
        w_modname = w("compiled.x")
        filename = str(p.join("x.py"))
        stream = streamio.open_file_as_stream(filename, "r")
        try:
            _load_source_module(
                space, w_modname, w(importing.Module(space, w_modname)),
                filename, stream.readall(),
                stream.try_to_find_file_descriptor())
        finally:
            stream.close()
        if not space.config.translation.sandbox:
            # also create a lone .pyc file
            p.join('lone.pyc').write(p.join('x.pyc').read(mode='rb'),
                                     mode='wb')

    # create a .pyw file
    p = setuppkg("windows", x = "x = 78")
    try:
        p.join('x.pyw').remove()
    except py.error.ENOENT:
        pass
    p.join('x.py').rename(p.join('x.pyw'))

    return str(root)

def _load_source_module(space, w_modname, w_mod, *args, **kwds):
    kwds.setdefault('check_afterwards', False)
    return importing.load_source_module(space, w_modname, w_mod, *args, **kwds)

def _load_compiled_module(space, w_modname, w_mod, *args, **kwds):
    kwds.setdefault('check_afterwards', False)
    return importing.load_compiled_module(space, w_modname, w_mod,
                                          *args, **kwds)


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
    p = udir.join('impsubdir')
    p.remove()
    space.appexec([w_saved_modules], """
        ((saved_path, saved_modules)):
            import sys
            sys.path[:] = saved_path
            sys.modules.clear()
            sys.modules.update(saved_modules)
    """)


class AppTestImport:
    spaceconfig = {
        "usemodules": ['_md5', 'time'],
    }

    def setup_class(cls):
        cls.w_runappdirect = cls.space.wrap(conftest.option.runappdirect)
        cls.saved_modules = _setup(cls.space)
        #XXX Compile class

    def teardown_class(cls):
        _teardown(cls.space, cls.saved_modules)

    def test_set_sys_modules_during_import(self):
        from evil_pkg import evil
        assert evil.a == 42

    def test_import_bare_dir_fails(self):
        def imp():
            import notapackage
        raises(ImportError, imp)

    def test_import_bare_dir_warns(self):
        def imp():
            import notapackage

        import warnings
        warnings.simplefilter('error', ImportWarning)
        try:
            raises(ImportWarning, imp)
        finally:
            warnings.simplefilter('default', ImportWarning)

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

    def test_trailing_slash(self):
        import sys
        try:
            sys.path[0] += '/'
            import a
        finally:
            sys.path[0] = sys.path[0].rstrip('/')

    def test_import_pkg(self):
        import sys
        import pkg
        assert pkg == sys.modules.get('pkg')

    def test_import_dotted(self):
        import sys
        import pkg.a
        assert pkg == sys.modules.get('pkg')
        assert pkg.a == sys.modules.get('pkg.a')

    def test_import_keywords(self):
        __import__(name='sys', level=0)

    def test_import_by_filename(self):
        import pkg.a
        filename = pkg.a.__file__
        assert filename.endswith('.py')
        exc = raises(ImportError, __import__, filename[:-3])
        assert exc.value.message == "Import by filename is not supported."

    def test_import_badcase(self):
        def missing(name):
            try:
                __import__(name)
            except ImportError:
                pass
            else:
                raise Exception("import should not have succeeded: %r" %
                                (name,))
        missing("Sys")
        missing("SYS")
        missing("fuNCTionAl")
        missing("pKg")
        missing("pKg.a")
        missing("pkg.A")

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
        raises(ImportError, imp)

    def test_import_builtin_inpackage(self):
        def imp():
            import pkg.sys
        raises(ImportError,imp)

        import sys, pkg.abs_sys
        assert pkg.abs_sys.sys is sys

        import errno, pkg.errno
        assert pkg.errno is not errno

    def test_import_Globals_Are_None(self):
        import sys
        m = __import__('sys')
        assert sys == m
        n = __import__('sys', None, None, [''])
        assert sys == n
        o = __import__('sys', [], [], ['']) # CPython accepts this
        assert sys == o

    def test_import_fromlist_must_not_contain_unicodes(self):
        raises(TypeError, __import__, 'encodings', None, None, [u'xxx'])

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

    @pytest.mark.skipif("sys.platform != 'win32'")
    def test_pyw(self):
        import windows.x
        assert windows.x.__file__.endswith('x.pyw')

    def test_cannot_write_pyc(self):
        import sys, os
        p = os.path.join(sys.path[0], 'readonly')
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

    def test_py_directory(self):
        import imp, os, sys
        source = os.path.join(sys.path[0], 'foo.py')
        os.mkdir(source)
        try:
            raises(ImportError, imp.find_module, 'foo')
        finally:
            os.rmdir(source)

    def test_invalid__name__(self):
        glob = {}
        exec "__name__ = None; import sys" in glob
        import sys
        assert glob['sys'] is sys

    def test_future_absolute_import(self):
        def imp():
            from pkg import absolute
            absolute.string.inpackage
        raises(AttributeError, imp)

    def test_future_relative_import_without_from_name(self):
        from pkg import relative_b
        assert relative_b.string.inpackage == 1

    def test_no_relative_import(self):
        def imp():
            from pkg import relative_f
        exc = raises(ImportError, imp)
        assert exc.value.message == "No module named pkg.imp"

    def test_no_relative_import_bug(self):
        def imp():
            from pkg import relative_g
        exc = raises(ImportError, imp)
        assert exc.value.message == "No module named pkg.imp"

    def test_future_relative_import_level_1(self):
        from pkg import relative_c
        assert relative_c.inpackage == 1

    def test_future_relative_import_level_2(self):
        from pkg.pkg1 import relative_d
        assert relative_d.inpackage == 1

    def test_future_relative_import_level_2_without_from_name(self):
        from pkg.pkg1 import relative_e
        assert relative_e.string.inpackage == 1

    def test_future_relative_import_level_3(self):
        from pkg.pkg1 import relative_g
        assert relative_g.b.insubpackage == 1
        import pkg.pkg1
        assert pkg.pkg1.__package__ == 'pkg.pkg1'

    def test_future_relative_import_error_when_in_non_package(self):
        exec """def imp():
                    from .string import inpackage
        """.rstrip()
        raises(ValueError, imp)

    def test_future_relative_import_error_when_in_non_package2(self):
        exec """def imp():
                    from .. import inpackage
        """.rstrip()
        raises(ValueError, imp)

    def test_relative_import_with___name__(self):
        import sys
        mydict = {'__name__': 'sys.foo'}
        res = __import__('', mydict, mydict, ('bar',), 1)
        assert res is sys

    def test_relative_import_with___name__and___path__(self):
        import sys
        import imp
        foo = imp.new_module('foo')
        sys.modules['sys.foo'] = foo
        mydict = {'__name__': 'sys.foo', '__path__': '/some/path'}
        res = __import__('', mydict, mydict, ('bar',), 1)
        assert res is foo

    def test_relative_import_pkg(self):
        import sys
        import imp
        pkg = imp.new_module('newpkg')
        sys.modules['newpkg'] = pkg
        mydict = {'__name__': 'newpkg.foo', '__path__': '/some/path'}
        res = __import__('', mydict, None, ['bar'], 2)
        assert res is pkg

    def test__package__(self):
        # Regression test for http://bugs.python.org/issue3221.
        def check_absolute():
            exec "from os import path" in ns
        def check_relative():
            exec "from . import a" in ns

        # Check both OK with __package__ and __name__ correct
        ns = dict(__package__='pkg', __name__='pkg.notarealmodule')
        check_absolute()
        check_relative()

        # Check both OK with only __name__ wrong
        ns = dict(__package__='pkg', __name__='notarealpkg.notarealmodule')
        check_absolute()
        check_relative()

        # Check relative fails with only __package__ wrong
        ns = dict(__package__='foo', __name__='pkg.notarealmodule')
        check_absolute() # XXX check warnings
        raises(SystemError, check_relative)

        # Check relative fails with __package__ and __name__ wrong
        ns = dict(__package__='foo', __name__='notarealpkg.notarealmodule')
        check_absolute() # XXX check warnings
        raises(SystemError, check_relative)

        # Check both fail with package set to a non-string
        ns = dict(__package__=object())
        raises(ValueError, check_absolute)
        raises(ValueError, check_relative)

    def test_universal_newlines(self):
        import pkg_univnewlines
        assert pkg_univnewlines.a == 5
        assert pkg_univnewlines.b == 6
        assert pkg_univnewlines.c == "hello\nworld"
        from pkg_univnewlines import mod
        assert mod.a == 15
        assert mod.b == 16
        assert mod.c == "foo\nbar"

    def test_reload(self):
        import test_reload
        try:
            test_reload.test()
        except ValueError:
            pass

        # If this test runs too quickly, test_reload.py's mtime
        # attribute will remain unchanged even if the file is rewritten.
        # Consequently, the file would not reload.  So, added a sleep()
        # delay to assure that a new, distinct timestamp is written.
        import time
        time.sleep(1)

        with open(test_reload.__file__, "w") as f:
            f.write("def test():\n    raise NotImplementedError\n")
        reload(test_reload)
        try:
            test_reload.test()
        except NotImplementedError:
            pass

        # Ensure that the file is closed
        # (on windows at least)
        import os
        os.unlink(test_reload.__file__)

    def test_reload_failing(self):
        import test_reload
        import time
        time.sleep(1)
        with open(test_reload.__file__, "w") as f:
            f.write("a = 10 // 0\n")

        # A failing reload should leave the previous module in sys.modules
        raises(ZeroDivisionError, reload, test_reload)
        import os, sys
        assert 'test_reload' in sys.modules
        assert test_reload.test
        os.unlink(test_reload.__file__)

    def test_reload_submodule(self):
        import pkg.a
        reload(pkg.a)

    def test_reload_builtin(self):
        import sys
        oldpath = sys.path
        try:
            del sys.setdefaultencoding
        except AttributeError:
            pass

        reload(sys)

        assert sys.path is oldpath
        assert 'setdefaultencoding' in dir(sys)

    def test_reload_builtin_doesnt_clear(self):
        import sys
        sys.foobar = "baz"
        reload(sys)
        assert sys.foobar == "baz"

    def test_reimport_builtin_simple_case_1(self):
        import sys, time
        del time.clock
        del sys.modules['time']
        import time
        assert hasattr(time, 'clock')

    def test_reimport_builtin_simple_case_2(self):
        import sys, time
        time.foo = "bar"
        del sys.modules['time']
        import time
        assert not hasattr(time, 'foo')

    def test_reimport_builtin(self):
        import sys, time
        oldpath = sys.path
        time.tzname = "<test_reimport_builtin removed this>"

        del sys.modules['time']
        import time as time1
        assert sys.modules['time'] is time1

        assert time.tzname == "<test_reimport_builtin removed this>"

        reload(time1)   # don't leave a broken time.tzname behind
        import time
        assert time.tzname != "<test_reimport_builtin removed this>"

    def test_reload_infinite(self):
        import infinite_reload

    def test_explicitly_missing(self):
        import sys
        sys.modules['foobarbazmod'] = None
        try:
            import foobarbazmod
            assert False, "should have failed, got instead %r" % (
                foobarbazmod,)
        except ImportError:
            pass

    def test_del_from_sys_modules(self):
        try:
            import del_sys_module
        except ImportError:
            pass    # ok
        else:
            assert False, 'should not work'

    def test_shadow_builtin(self):
        if self.runappdirect: skip("hard to test: module is already imported")
        # 'import gc' is supposed to always find the built-in module;
        # like CPython, it is a built-in module, so it shadows everything,
        # even though there is a gc.py.
        import sys
        assert 'gc' not in sys.modules
        import gc
        assert not hasattr(gc, 'should_never_be_seen')
        assert '(built-in)' in repr(gc)
        del sys.modules['gc']

    def test_shadow_extension_1(self):
        if self.runappdirect: skip("hard to test: module is already imported")
        # 'import _md5' is supposed to find _md5.py if there is
        # one in sys.path.
        import sys
        assert '_md5' not in sys.modules
        try:
            import _md5
            assert hasattr(_md5, 'hello_world')
            assert not hasattr(_md5, 'digest_size')
            assert '(built-in)' not in repr(_md5)
        finally:
            sys.modules.pop('_md5', None)

    def test_shadow_extension_2(self):
        if self.runappdirect: skip("hard to test: module is already imported")
        # 'import _md5' is supposed to find the built-in module even
        # if there is also one in sys.path as long as it is *after* the
        # special entry '.../lib_pypy/__extensions__'.  (Note that for now
        # there is one in lib_pypy/_md5.py, which should not be seen
        # either; hence the (built-in) test below.)
        import sys
        assert '_md5' not in sys.modules
        sys.path.append(sys.path.pop(0))
        try:
            import _md5
            assert not hasattr(_md5, 'hello_world')
            assert hasattr(_md5, 'digest_size')
            assert '(built-in)' in repr(_md5)
        finally:
            sys.path.insert(0, sys.path.pop())
            sys.modules.pop('_md5', None)

    def test_invalid_pathname(self):
        import imp
        import pkg
        import os
        pathname = os.path.join(os.path.dirname(pkg.__file__), 'a.py')
        with open(pathname) as fid:
            module = imp.load_module('a', fid,
                                 'invalid_path_name', ('.py', 'r', imp.PY_SOURCE))
        assert module.__name__ == 'a'
        assert module.__file__ == 'invalid_path_name'

    def test_crash_load_module(self):
        import imp
        raises(ValueError, imp.load_module, "", "", "", [1, 2, 3, 4])

    def test_import_star_finds_submodules_with___all__(self):
        for case in ["not-imported-yet", "already-imported"]:
            d = {}
            exec "from pkg.withall import *" in d
            assert d["foobar"].found == 123
            assert d["barbaz"].other == 543

    def test_import_star_does_not_find_submodules_without___all__(self):
        for case in ["not-imported-yet", "already-imported"]:
            d = {}
            exec "from pkg.withoutall import *" in d
            assert "foobar" not in d
        import pkg.withoutall.foobar     # <- import it here only
        for case in ["not-imported-yet", "already-imported"]:
            d = {}
            exec "from pkg.withoutall import *" in d
            assert d["foobar"].found == 123

    def test_import_star_with_bogus___all__(self):
        for case in ["not-imported-yet", "already-imported"]:
            try:
                exec "from pkg.bogusall import *" in {}
            except TypeError:
                pass    # 'int' object does not support indexing
            else:
                raise AssertionError("should have failed")

    def test_verbose_flag_1(self):
        output = []
        class StdErr(object):
            def write(self, line):
                output.append(line)

        import sys
        old_flags = sys.flags

        class Flags(object):
            verbose = 1
            def __getattr__(self, name):
                return getattr(old_flags, name)

        sys.flags = Flags()
        sys.stderr = StdErr()
        try:
            import verbose1pkg.verbosemod
        finally:
            reload(sys)
        assert 'import verbose1pkg # from ' in output[-2]
        assert 'import verbose1pkg.verbosemod # from ' in output[-1]

    def test_verbose_flag_2(self):
        output = []
        class StdErr(object):
            def write(self, line):
                output.append(line)

        import sys
        old_flags = sys.flags

        class Flags(object):
            verbose = 2
            def __getattr__(self, name):
                return getattr(old_flags, name)

        sys.flags = Flags()
        sys.stderr = StdErr()
        try:
            import verbose2pkg.verbosemod
        finally:
            reload(sys)
        assert any('import verbose2pkg # from ' in line
                   for line in output[:-2])
        assert output[-2].startswith('# trying')
        assert 'import verbose2pkg.verbosemod # from ' in output[-1]

    def test_verbose_flag_0(self):
        output = []
        class StdErr(object):
            def write(self, line):
                output.append(line)

        import sys
        sys.stderr = StdErr()
        try:
            import verbose0pkg.verbosemod
        finally:
            reload(sys)
        assert not output


class TestAbi:
    def test_abi_tag(self):
        space1 = maketestobjspace(make_config(None, soabi='TEST'))
        space2 = maketestobjspace(make_config(None, soabi=''))
        if sys.platform == 'win32':
            assert importing.get_so_extension(space1) == '.TESTi.pyd'
            assert importing.get_so_extension(space2) == '.pyd'
        else:
            assert importing.get_so_extension(space1) == '.TESTi.so'
            assert importing.get_so_extension(space2) == '.so'

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

def _testfilesource(source="x=42"):
    pathname = str(udir.join('test.py'))
    f = file(pathname, "wb")
    f.write(source)
    f.close()
    return pathname

class TestPycStuff:
    # ___________________ .pyc related stuff _________________

    def test_check_compiled_module(self):
        space = self.space
        mtime = 12345
        cpathname = _testfile(importing.get_pyc_magic(space), mtime)
        ret = importing.check_compiled_module(space,
                                              cpathname,
                                              mtime)
        assert ret is not None
        ret.close()

        # check for wrong mtime
        ret = importing.check_compiled_module(space,
                                              cpathname,
                                              mtime+1)
        assert ret is None

        # also check with expected mtime==0 (nothing special any more about 0)
        ret = importing.check_compiled_module(space,
                                              cpathname,
                                              0)
        assert ret is None
        os.remove(cpathname)

        # check for wrong version
        cpathname = _testfile(importing.get_pyc_magic(space)+1, mtime)
        ret = importing.check_compiled_module(space,
                                              cpathname,
                                              mtime)
        assert ret is None

        # check for empty .pyc file
        with open(cpathname, 'wb') as f:
            pass
        ret = importing.check_compiled_module(space,
                                              cpathname,
                                              mtime)
        assert ret is None
        os.remove(cpathname)

    def test_read_compiled_module(self):
        space = self.space
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(importing.get_pyc_magic(space), mtime, co)
        stream = streamio.open_file_as_stream(cpathname, "rb")
        try:
            stream.seek(8, 0)
            w_code = importing.read_compiled_module(
                    space, cpathname, stream.readall())
            pycode = w_code
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
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(importing.get_pyc_magic(space), mtime, co)
        w_modulename = space.wrap('somemodule')
        stream = streamio.open_file_as_stream(cpathname, "rb")
        try:
            w_mod = space.wrap(Module(space, w_modulename))
            magic = importing._r_long(stream)
            timestamp = importing._r_long(stream)
            w_ret = _load_compiled_module(space,   w_modulename,
                                                   w_mod,
                                                   cpathname,
                                                   magic,
                                                   timestamp,
                                                   stream.readall())
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
                                                  stream.readall())
        finally:
            stream.close()
        pycode = w_ret
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
        stream = streamio.open_file_as_stream(pathname, "rb")
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
            w_ret = _load_source_module(
                space, w_modulename, w_mod,
                pathname, stream.readall(),
                stream.try_to_find_file_descriptor())
        finally:
            stream.close()
        assert w_mod is w_ret
        w_ret = space.getattr(w_mod, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

        cpathname = udir.join('test.pyc')
        assert cpathname.check()
        cpathname.remove()

    def test_load_source_module_nowrite(self):
        space = self.space
        w_modulename = space.wrap('somemodule')
        w_mod = space.wrap(Module(space, w_modulename))
        pathname = _testfilesource()
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            w_ret = _load_source_module(
                space, w_modulename, w_mod,
                pathname, stream.readall(),
                stream.try_to_find_file_descriptor(),
                write_pyc=False)
        finally:
            stream.close()
        cpathname = udir.join('test.pyc')
        assert not cpathname.check()

    def test_load_source_module_dont_write_bytecode(self):
        space = self.space
        w_modulename = space.wrap('somemodule')
        w_mod = space.wrap(Module(space, w_modulename))
        pathname = _testfilesource()
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            space.setattr(space.sys, space.wrap('dont_write_bytecode'),
                          space.w_True)
            w_ret = _load_source_module(
                space, w_modulename, w_mod,
                pathname, stream.readall(),
                stream.try_to_find_file_descriptor())
        finally:
            space.setattr(space.sys, space.wrap('dont_write_bytecode'),
                          space.w_False)
            stream.close()
        cpathname = udir.join('test.pyc')
        assert not cpathname.check()

    def test_load_source_module_syntaxerror(self):
        # No .pyc file on SyntaxError
        space = self.space
        w_modulename = space.wrap('somemodule')
        w_mod = space.wrap(Module(space, w_modulename))
        pathname = _testfilesource(source="<Syntax Error>")
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            w_ret = _load_source_module(
                space, w_modulename, w_mod,
                pathname, stream.readall(),
                stream.try_to_find_file_descriptor())
        except OperationError:
            # OperationError("Syntax Error")
            pass
        stream.close()

        cpathname = udir.join('test.pyc')
        assert not cpathname.check()
        
    def test_load_source_module_importerror(self):
        # the .pyc file is created before executing the module
        space = self.space
        w_modulename = space.wrap('somemodule')
        w_mod = space.wrap(Module(space, w_modulename))
        pathname = _testfilesource(source="a = unknown_name")
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            w_ret = _load_source_module(
                space, w_modulename, w_mod,
                pathname, stream.readall(),
                stream.try_to_find_file_descriptor())
        except OperationError:
            # OperationError("NameError", "global name 'unknown_name' is not defined")
            pass
        stream.close()

        # And the .pyc has been generated
        cpathname = udir.join('test.pyc')
        assert cpathname.check()

    def test_write_compiled_module(self):
        space = self.space
        pathname = _testfilesource()
        os.chmod(pathname, 0777)
        stream = streamio.open_file_as_stream(pathname, "r")
        try:
            w_ret = importing.parse_source_module(space,
                                                  pathname,
                                                  stream.readall())
        finally:
            stream.close()
        pycode = w_ret
        assert type(pycode) is pypy.interpreter.pycode.PyCode

        cpathname = str(udir.join('cpathname.pyc'))
        mode = 0777
        mtime = 12345
        importing.write_compiled_module(space,
                                        pycode,
                                        cpathname,
                                        mode,
                                        mtime)

        # check
        ret = importing.check_compiled_module(space,
                                              cpathname,
                                              mtime)
        assert ret is not None
        ret.close()

        # Check that the executable bit was removed
        assert os.stat(cpathname).st_mode & 0111 == 0

        # read compiled module
        stream = streamio.open_file_as_stream(cpathname, "rb")
        try:
            stream.seek(8, 0)
            w_code = importing.read_compiled_module(space, cpathname,
                                                    stream.readall())
            pycode = w_code
        finally:
            stream.close()

        # check value of load
        w_dic = space.newdict()
        pycode.exec_code(space, w_dic, w_dic)
        w_ret = space.getitem(w_dic, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

    def test_pyc_magic_changes(self):
        py.test.skip("For now, PyPy generates only one kind of .pyc files")
        # test that the pyc files produced by a space are not reimportable
        # from another, if they differ in what opcodes they support
        allspaces = [self.space]
        for opcodename in self.space.config.objspace.opcodes.getpaths():
            key = 'objspace.opcodes.' + opcodename
            space2 = maketestobjspace(make_config(None, **{key: True}))
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
                stream = streamio.open_file_as_stream(cpathname, "rb")
                try:
                    w_mod = space2.wrap(Module(space2, w_modulename))
                    magic = importing._r_long(stream)
                    timestamp = importing._r_long(stream)
                    space2.raises_w(space2.w_ImportError,
                                    _load_compiled_module,
                                    space2,
                                    w_modulename,
                                    w_mod,
                                    cpathname,
                                    magic,
                                    timestamp,
                                    stream.readall())
                finally:
                    stream.close()


def test_PYTHONPATH_takes_precedence(space): 
    if sys.platform == "win32":
        py.test.skip("unresolved issues with win32 shell quoting rules")
    from pypy.interpreter.test.test_zpy import pypypath 
    extrapath = udir.ensure("pythonpath", dir=1) 
    extrapath.join("sched.py").write("print 42\n")
    old = os.environ.get('PYTHONPATH', None)
    oldlang = os.environ.pop('LANG', None)
    try:
        os.environ['PYTHONPATH'] = str(extrapath)
        output = py.process.cmdexec('''"%s" "%s" -c "import sched"''' %
                                 (sys.executable, pypypath))
        assert output.strip() == '42'
    finally:
        if old:
            os.environ['PYTHONPATH'] = old
        if oldlang:
            os.environ['LANG'] = oldlang


class AppTestImportHooks(object):
    spaceconfig = {
        "usemodules": ['struct', 'itertools', 'time'],
    }

    def setup_class(cls):
        mydir = os.path.dirname(__file__)
        cls.w_hooktest = cls.space.wrap(os.path.join(mydir, 'hooktest'))
        cls.space.appexec([cls.space.wrap(mydir)], """
            (mydir):
                import sys
                sys.path.append(mydir)
        """)

    def teardown_class(cls):
        cls.space.appexec([], """
            ():
                import sys
                sys.path.pop()
        """)

    def test_meta_path(self):
        tried_imports = []
        class Importer(object):
            def find_module(self, fullname, path=None):
                tried_imports.append((fullname, path))

        import sys, datetime
        del sys.modules["datetime"]

        sys.meta_path.append(Importer())
        try:
            import datetime
            assert len(tried_imports) == 1
            package_name = '.'.join(__name__.split('.')[:-1])
            if package_name:
                assert tried_imports[0][0] == package_name + ".datetime"
            else:
                assert tried_imports[0][0] == "datetime"
        finally:
            sys.meta_path.pop()

    def test_meta_path_block(self):
        class ImportBlocker(object):
            "Specified modules can't be imported, even if they are built-in"
            def __init__(self, *namestoblock):
                self.namestoblock = dict.fromkeys(namestoblock)
            def find_module(self, fullname, path=None):
                if fullname in self.namestoblock:
                    return self
            def load_module(self, fullname):
                raise ImportError("blocked")

        import sys, imp
        modname = "errno" # an arbitrary harmless builtin module
        mod = None
        if modname in sys.modules:
            mod = sys.modules
            del sys.modules[modname]
        sys.meta_path.append(ImportBlocker(modname))
        try:
            raises(ImportError, __import__, modname)
            # the imp module doesn't use meta_path, and is not blocked
            # (until imp.get_loader is implemented, see PEP302)
            file, filename, stuff = imp.find_module(modname)
            imp.load_module(modname, file, filename, stuff)
        finally:
            sys.meta_path.pop()
            if mod:
                sys.modules[modname] = mod

    def test_path_hooks_leaking(self):
        class Importer(object):
            def find_module(self, fullname, path=None):
                if fullname == "a":
                    return self

            def load_module(self, name):
                sys.modules[name] = sys
                return sys

        def importer_for_path(path):
            if path == "xxx":
                return Importer()
            raise ImportError()
        import sys, imp
        try:
            sys.path_hooks.append(importer_for_path)
            sys.path.insert(0, "yyy")
            sys.path.insert(0, "xxx")
            import a
            try:
                import b
            except ImportError:
                pass
            assert isinstance(sys.path_importer_cache['yyy'],
                              imp.NullImporter)
        finally:
            sys.path.pop(0)
            sys.path.pop(0)
            sys.path_hooks.pop()

    def test_imp_wrapper(self):
        import sys, os, imp
        class ImpWrapper:

            def __init__(self, path=None):
                if path is not None and not os.path.isdir(path):
                    raise ImportError
                self.path = path

            def find_module(self, fullname, path=None):
                subname = fullname.split(".")[-1]
                if subname != fullname and self.path is None:
                    return None
                if self.path is None:
                    path = None
                else:
                    path = [self.path]
                try:
                    file, filename, stuff = imp.find_module(subname, path)
                except ImportError as e:
                    return None
                return ImpLoader(file, filename, stuff)

        class ImpLoader:

            def __init__(self, file, filename, stuff):
                self.file = file
                self.filename = filename
                self.stuff = stuff

            def load_module(self, fullname):
                mod = imp.load_module(fullname, self.file, self.filename, self.stuff)
                if self.file:
                    self.file.close()
                mod.__loader__ = self  # for introspection
                return mod

        i = ImpWrapper()
        sys.meta_path.append(i)
        sys.path_hooks.append(ImpWrapper)
        sys.path_importer_cache.clear()
        try:
            mnames = ("colorsys", "urlparse", "email.mime", "compiler.misc")
            for mname in mnames:
                parent = mname.split(".")[0]
                for n in sys.modules.keys():
                    if n.startswith(parent):
                        del sys.modules[n]
            for mname in mnames:
                m = __import__(mname, globals(), locals(), ["__dummy__"])
                m.__loader__  # to make sure we actually handled the import
        finally:
            sys.meta_path.pop()
            sys.path_hooks.pop()

    def test_path_hooks_module(self):
        "Verify that non-sibling imports from module loaded by path hook works"

        import sys
        import hooktest

        hooktest.__path__.append(self.hooktest) # Avoid importing os at applevel

        sys.path_hooks.append(hooktest.Importer)

        try:
            import hooktest.foo
            def import_nonexisting():
                import hooktest.errno
            raises(ImportError, import_nonexisting)
        finally:
            sys.path_hooks.pop()

    def test_meta_path_import_error_1(self):
        # as far as I can tell, the problem is that in CPython, if you
        # use an import hook that doesn't update sys.modules, then the
        # import succeeds; but at the same time, you can have the same
        # result without an import hook (see test_del_from_sys_modules)
        # and then the import fails.  Mess mess mess.

        class ImportHook(object):
            def find_module(self, fullname, path=None):
                assert not fullname.endswith('*')
                if fullname == 'meta_path_pseudo_module':
                    return self
            def load_module(self, fullname):
                assert fullname == 'meta_path_pseudo_module'
                # we "forget" to update sys.modules
                return new.module('meta_path_pseudo_module')

        import sys, new
        sys.meta_path.append(ImportHook())
        try:
            import meta_path_pseudo_module
        finally:
            sys.meta_path.pop()

    def test_meta_path_import_star_2(self):
        class ImportHook(object):
            def find_module(self, fullname, path=None):
                if fullname.startswith('meta_path_2_pseudo_module'):
                    return self
            def load_module(self, fullname):
                assert fullname == 'meta_path_2_pseudo_module'
                m = new.module('meta_path_2_pseudo_module')
                m.__path__ = ['/some/random/dir']
                sys.modules['meta_path_2_pseudo_module'] = m
                return m

        import sys, new
        sys.meta_path.append(ImportHook())
        try:
            exec "from meta_path_2_pseudo_module import *" in {}
        finally:
            sys.meta_path.pop()


class AppTestPyPyExtension(object):
    spaceconfig = dict(usemodules=['imp', 'zipimport', '__pypy__'])

    def setup_class(cls):
        cls.w_udir = cls.space.wrap(str(udir))

    def test_run_compiled_module(self):
        # XXX minimal test only
        import imp, new
        module = new.module('foobar')
        raises(IOError, imp._run_compiled_module,
               'foobar', 'this_file_does_not_exist', None, module)

    def test_getimporter(self):
        import imp, os
        # an existing directory
        importer = imp._getimporter(self.udir)
        assert importer is None
        # an existing file
        path = os.path.join(self.udir, 'test_getimporter')
        with open(path, 'w') as f:
            pass
        importer = imp._getimporter(path)
        assert isinstance(importer, imp.NullImporter)
        # a non-existing path
        path = os.path.join(self.udir, 'does_not_exist_at_all')
        importer = imp._getimporter(path)
        assert isinstance(importer, imp.NullImporter)
        # a mostly-empty zip file
        path = os.path.join(self.udir, 'test_getimporter.zip')
        with open(path, 'wb') as f:
            f.write('PK\x03\x04\n\x00\x00\x00\x00\x00P\x9eN>\x00\x00\x00\x00\x00'
                '\x00\x00\x00\x00\x00\x00\x00\x05\x00\x15\x00emptyUT\t\x00'
                '\x03wyYMwyYMUx\x04\x00\xf4\x01d\x00PK\x01\x02\x17\x03\n\x00'
                '\x00\x00\x00\x00P\x9eN>\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                '\x00\x00\x00\x05\x00\r\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                '\xa4\x81\x00\x00\x00\x00emptyUT\x05\x00\x03wyYMUx\x00\x00PK'
                '\x05\x06\x00\x00\x00\x00\x01\x00\x01\x00@\x00\x00\x008\x00'
                '\x00\x00\x00\x00')
        importer = imp._getimporter(path)
        import zipimport
        assert isinstance(importer, zipimport.zipimporter)


class AppTestWriteBytecode(object):
    spaceconfig = {
        "translation.sandbox": False
    }

    def setup_class(cls):
        cls.saved_modules = _setup(cls.space)
        sandbox = cls.spaceconfig['translation.sandbox']
        cls.w_sandbox = cls.space.wrap(sandbox)

    def teardown_class(cls):
        _teardown(cls.space, cls.saved_modules)
        cls.space.appexec([], """
            ():
                import sys
                sys.dont_write_bytecode = False
        """)

    def test_default(self):
        import os.path
        from test_bytecode import a
        assert a.__file__.endswith('a.py')
        assert os.path.exists(a.__file__ + 'c') == (not self.sandbox)

    def test_write_bytecode(self):
        import os.path
        import sys
        sys.dont_write_bytecode = False
        from test_bytecode import b
        assert b.__file__.endswith('b.py')
        assert os.path.exists(b.__file__ + 'c')

    def test_dont_write_bytecode(self):
        import os.path
        import sys
        sys.dont_write_bytecode = True
        from test_bytecode import c
        assert c.__file__.endswith('c.py')
        assert not os.path.exists(c.__file__ + 'c')


class AppTestWriteBytecodeSandbox(AppTestWriteBytecode):
    spaceconfig = {
        "translation.sandbox": True
    }


class _AppTestLonePycFileBase(object):
    def setup_class(cls):
        lonepycfiles = cls.spaceconfig['objspace.lonepycfiles']
        cls.w_lonepycfiles = cls.space.wrap(lonepycfiles)
        cls.saved_modules = _setup(cls.space)

    def teardown_class(cls):
        _teardown(cls.space, cls.saved_modules)

    def test_import_possibly_from_pyc(self):
        from compiled import x
        assert x.__file__.endswith('x.pyc')
        try:
            from compiled import lone
        except ImportError:
            assert not self.lonepycfiles, "should have found 'lone.pyc'"
        else:
            assert self.lonepycfiles, "should not have found 'lone.pyc'"
            assert lone.__file__.endswith('lone.pyc')

class AppTestNoLonePycFile(_AppTestLonePycFileBase):
    spaceconfig = {
        "objspace.lonepycfiles": False
    }

class AppTestLonePycFile(_AppTestLonePycFileBase):
    spaceconfig = {
        "objspace.lonepycfiles": True
    }


class AppTestMultithreadedImp(object):
    spaceconfig = dict(usemodules=['thread', 'time'])

    def setup_class(cls):
        #if not conftest.option.runappdirect:
        #    py.test.skip("meant as an -A test")
        tmpfile = udir.join('test_multithreaded_imp.py')
        tmpfile.write('''if 1:
            x = 666
            import time
            for i in range(1000): time.sleep(0.001)
            x = 42
        ''')
        cls.w_tmppath = cls.space.wrap(str(udir))

    def test_multithreaded_import(self):
        import sys, thread, time
        oldpath = sys.path[:]
        try:
            sys.path.insert(0, self.tmppath)
            got = []

            def check():
                import test_multithreaded_imp
                got.append(getattr(test_multithreaded_imp, 'x', '?'))

            for i in range(5):
                thread.start_new_thread(check, ())

            for n in range(100):
                for i in range(105): time.sleep(0.001)
                if len(got) == 5:
                    break
            else:
                raise AssertionError("got %r so far but still waiting" %
                                     (got,))

            assert got == [42] * 5, got

        finally:
            sys.path[:] = oldpath
