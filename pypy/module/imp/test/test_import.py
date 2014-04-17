# coding: utf-8
import py
from pypy.interpreter.module import Module
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.interpreter.pycode import PyCode
from pypy.module.imp.test.support import BaseImportTest
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

def setup_directory_structure(cls):
    space = cls.space
    root = setuppkg("",
                    a = "imamodule = 1\ninpackage = 0",
                    ambig = "imamodule = 1",
                    test_reload = "def test():\n    raise ValueError\n",
                    infinite_reload = "import infinite_reload, imp; imp.reload(infinite_reload)",
                    del_sys_module = "import sys\ndel sys.modules['del_sys_module']\n",
                    itertools = "hello_world = 42\n",
                    gc = "should_never_be_seen = 42\n",
                    )
    root.ensure("notapackage", dir=1)    # empty, no __init__.py
    setuppkg("pkg",
             a          = "imamodule = 1\ninpackage = 1",
             b          = "imamodule = 1\ninpackage = 1",
             relative_a = "import a",
             abs_b      = "import b",
             abs_x_y    = "import x.y",
             abs_sys    = "import sys",
             struct     = "inpackage = 1",
             errno      = "",
             absolute   = "from __future__ import absolute_import\nimport struct",
             relative_b = "from __future__ import absolute_import\nfrom . import struct",
             relative_c = "from __future__ import absolute_import\nfrom .struct import inpackage",
             relative_f = "from .imp import get_magic",
             relative_g = "import imp; from .imp import get_magic",
             inpackage  = "inpackage = 1",
             function_a = "g = {'__name__': 'pkg.a'}; __import__('inpackage', g); print(g)",
             function_b = "g = {'__name__': 'not.a'}; __import__('inpackage', g); print(g)",
             )
    setuppkg("pkg.pkg1",
             __init__   = 'from . import a',
             a          = '',
             relative_d = "from __future__ import absolute_import\nfrom ..struct import inpackage",
             relative_e = "from __future__ import absolute_import\nfrom .. import struct",
             relative_g = "from .. import pkg1\nfrom ..pkg1 import b",
             b          = "insubpackage = 1",
             )
    setuppkg("pkg.pkg2", a='', b='')
    setuppkg("pkg_r", inpkg = "import x.y")
    setuppkg("pkg_r.x", y='')
    setuppkg("x")
    setuppkg("ambig", __init__ = "imapackage = 1")
    setuppkg("pkg_relative_a",
             __init__ = "import a",
             a        = "imamodule = 1\ninpackage = 1",
             )
    setuppkg("pkg_substituting",
             __init__ = "import sys, pkg_substituted\n"
                        "print('TOTO', __name__)\n"
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
    p = setuppkg("encoded",
             # actually a line 2, setuppkg() sets up a line1
             line2 = "# encoding: iso-8859-1\n",
             bad = "# encoding: uft-8\n")

    fsenc = sys.getfilesystemencoding()
    # covers utf-8 and Windows ANSI code pages one non-space symbol from
    # every page (http://en.wikipedia.org/wiki/Code_page)
    known_locales = {
        'utf-8' : b'\xc3\xa4',
        'cp1250' : b'\x8C',
        'cp1251' : b'\xc0',
        'cp1252' : b'\xc0',
        'cp1253' : b'\xc1',
        'cp1254' : b'\xc0',
        'cp1255' : b'\xe0',
        'cp1256' : b'\xe0',
        'cp1257' : b'\xc0',
        'cp1258' : b'\xc0',
        }

    if sys.platform == 'darwin':
        # Mac OS X uses the Normal Form D decomposition
        # http://developer.apple.com/mac/library/qa/qa2001/qa1173.html
        special_char = b'a\xcc\x88'
    else:
        special_char = known_locales.get(fsenc)

    if special_char:
        p.join(special_char + '.py').write('pass')
        cls.w_special_char = space.wrap(special_char.decode(fsenc))
    else:
        cls.w_special_char = space.w_None

    # create compiled/x.py and a corresponding pyc file
    p = setuppkg("compiled", x = "x = 84")
    if conftest.option.runappdirect:
        import marshal, stat, struct, os, imp
        code = py.code.Source(p.join("x.py").read()).compile()
        s3 = marshal.dumps(code)
        s2 = struct.pack("i", os.stat(str(p.join("x.py")))[stat.ST_MTIME])
        p.join("x.pyc").write(imp.get_magic() + s2 + s3, mode='wb')
    else:
        w = space.wrap
        w_modname = w("compiled.x")
        filename = str(p.join("x.py"))
        pycname = importing.make_compiled_pathname("x.py")
        stream = streamio.open_file_as_stream(filename, "r")
        try:
            importing.load_source_module(
                space, w_modname, w(importing.Module(space, w_modname)),
                filename, stream.readall(),
                stream.try_to_find_file_descriptor())
        finally:
            stream.close()
        if space.config.objspace.usepycfiles:
            # also create a lone .pyc file
            p.join('lone.pyc').write(p.join(pycname).read(mode='rb'),
                                     mode='wb')

    # create a .pyw file
    p = setuppkg("windows", x = "x = 78")
    try:
        p.join('x.pyw').remove()
    except py.error.ENOENT:
        pass
    p.join('x.py').rename(p.join('x.pyw'))

    return str(root)


def _setup(cls):
    space = cls.space
    dn = setup_directory_structure(cls)
    return _setup_path(space, dn)

def _setup_path(space, path):
    return space.appexec([space.wrap(path)], """
        (dn): 
            import sys
            path = list(sys.path)
            sys.path.insert(0, dn)
            return path, sys.modules.copy()
    """)

def _teardown(space, w_saved_modules):
    space.appexec([w_saved_modules], """
        (path_and_modules):
            saved_path, saved_modules = path_and_modules
            import sys
            sys.path[:] = saved_path
            sys.modules.clear()
            sys.modules.update(saved_modules)
    """)


class AppTestImport(BaseImportTest):
    spaceconfig = {
        "usemodules": ['rctime'],
    }

    def setup_class(cls):
        BaseImportTest.setup_class.im_func(cls)
        cls.w_runappdirect = cls.space.wrap(conftest.option.runappdirect)
        cls.w_saved_modules = _setup(cls)
        #XXX Compile class

    def teardown_class(cls):
        _teardown(cls.space, cls.w_saved_modules)

    def w_exec_(self, cmd, ns):
        exec(cmd, ns)

    def test_file_and_cached(self):
        import compiled.x
        assert "__pycache__" not in compiled.x.__file__
        assert compiled.x.__file__.endswith(".py")
        assert "__pycache__" in compiled.x.__cached__
        assert compiled.x.__cached__.endswith(".pyc")

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

        import _warnings
        def simplefilter(action, category):
            _warnings.filters.insert(0, (action, None, category, None, 0))
        simplefilter('error', ImportWarning)
        try:
            raises(ImportWarning, imp)
        finally:
            simplefilter('default', ImportWarning)

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
        assert exc.value.args[0] == "Import by filename is not supported."

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

    def test_import_absolute(self):
        from pkg import relative_a
        assert relative_a.a.inpackage == 0

    def test_import_absolute_dont_default_to_relative(self):
        def imp():
            from pkg import abs_b
        raises(ImportError, imp)

    def test_import_pkg_absolute(self):
        import pkg_relative_a
        assert pkg_relative_a.a.inpackage == 0

    def test_import_absolute_partial_success(self):
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
            os.chmod(p, 0o555)
        except:
            skip("cannot chmod() the test directory to read-only")
        try:
            import readonly.x    # cannot write x.pyc, but should not crash
        finally:
            os.chmod(p, 0o775)
        assert "__pycache__" in readonly.x.__cached__

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
        exec("__name__ = None; import sys", glob)
        import sys
        assert glob['sys'] is sys

    def test_future_absolute_import(self):
        def imp():
            from pkg import absolute
            assert hasattr(absolute.struct, 'pack')
        imp()

    def test_future_relative_import_without_from_name(self):
        from pkg import relative_b
        assert relative_b.struct.inpackage == 1

    def test_no_relative_import(self):
        def imp():
            from pkg import relative_f
        exc = raises(ImportError, imp)
        assert exc.value.args[0] == "No module named pkg.imp"

    def test_no_relative_import_bug(self):
        def imp():
            from pkg import relative_g
        exc = raises(ImportError, imp)
        assert exc.value.args[0] == "No module named pkg.imp"

    def test_import_msg(self):
        def imp():
            import pkg.i_am_not_here.neither_am_i
        exc = raises(ImportError, imp)
        assert exc.value.args[0] == "No module named pkg.i_am_not_here"

    def test_future_relative_import_level_1(self):
        from pkg import relative_c
        assert relative_c.inpackage == 1

    def test_future_relative_import_level_2(self):
        from pkg.pkg1 import relative_d
        assert relative_d.inpackage == 1

    def test_future_relative_import_level_2_without_from_name(self):
        from pkg.pkg1 import relative_e
        assert relative_e.struct.inpackage == 1

    def test_future_relative_import_level_3(self):
        from pkg.pkg1 import relative_g
        assert relative_g.b.insubpackage == 1
        import pkg.pkg1
        assert pkg.pkg1.__package__ == 'pkg.pkg1'

    def test_future_relative_import_error_when_in_non_package(self):
        ns = {'__name__': __name__}
        exec("""def imp():
                    print('__name__ =', __name__)
                    from .struct import inpackage
        """, ns)
        raises(ValueError, ns['imp'])

    def test_future_relative_import_error_when_in_non_package2(self):
        ns = {'__name__': __name__}
        exec("""def imp():
                    from .. import inpackage
        """, ns)
        raises(ValueError, ns['imp'])

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
            self.exec_("from os import path", ns)
        def check_relative():
            self.exec_("from . import a", ns)

        import pkg

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

        # Check relative fails when __package__ set to a non-string
        ns = dict(__package__=object())
        check_absolute()
        raises(ValueError, check_relative)

    def test_import_function(self):
        # More tests for __import__
        import sys
        if sys.version < '3.3':
            from pkg import function_a
            assert function_a.g['__package__'] == 'pkg'
            raises(ImportError, "from pkg import function_b")
        else:
            raises(ImportError, "from pkg import function_a")

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
        import test_reload, imp
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
        imp.reload(test_reload)
        try:
            test_reload.test()
        except NotImplementedError:
            pass

        # Ensure that the file is closed
        # (on windows at least)
        import os
        os.unlink(test_reload.__file__)

        # restore it for later tests
        with open(test_reload.__file__, "w") as f:
            f.write("def test():\n    raise ValueError\n")

    def test_reload_failing(self):
        import test_reload
        import time, imp
        time.sleep(1)
        f = open(test_reload.__file__, "w")
        f.write("a = 10 // 0\n")
        f.close()

        # A failing reload should leave the previous module in sys.modules
        raises(ZeroDivisionError, imp.reload, test_reload)
        import os, sys
        assert 'test_reload' in sys.modules
        assert test_reload.test
        os.unlink(test_reload.__file__)

    def test_reload_submodule(self):
        import pkg.a, imp
        imp.reload(pkg.a)

    def test_reload_builtin(self):
        import sys, imp
        oldpath = sys.path
        try:
            del sys.settrace
        except AttributeError:
            pass

        imp.reload(sys)

        assert sys.path is oldpath
        assert 'settrace' in dir(sys)

    def test_reload_builtin_doesnt_clear(self):
        import imp
        import sys
        sys.foobar = "baz"
        imp.reload(sys)
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
        import imp, sys, time
        oldpath = sys.path
        time.tzname = "<test_reimport_builtin removed this>"

        del sys.modules['time']
        import time as time1
        assert sys.modules['time'] is time1

        assert time.tzname == "<test_reimport_builtin removed this>"

        imp.reload(time1)   # don't leave a broken time.tzname behind
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

    def test_cache_from_source(self):
        import imp
        pycfile = imp.cache_from_source('a/b/c.py')
        assert pycfile.startswith('a/b/__pycache__/c.pypy-')
        assert pycfile.endswith('.pyc')
        assert imp.source_from_cache('a/b/__pycache__/c.pypy-17.pyc'
                                     ) == 'a/b/c.py'
        raises(ValueError, imp.source_from_cache, 'a/b/c.py')

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
        import sys
        sys.modules.pop('itertools', None)
        import itertools
        assert hasattr(itertools, 'hello_world')
        assert not hasattr(itertools, 'count')
        assert '(built-in)' not in repr(itertools)
        del sys.modules['itertools']

    def test_shadow_extension_2(self):
        if self.runappdirect: skip("hard to test: module is already imported")
        # 'import _md5' is supposed to find the built-in module even
        # if there is also one in sys.path as long as it is *after* the
        # special entry '.../lib_pypy/__extensions__'.  (Note that for now
        # there is one in lib_pypy/_md5.py, which should not be seen
        # either; hence the (built-in) test below.)
        import sys
        sys.modules.pop('itertools', None)
        sys.path.append(sys.path.pop(0))
        try:
            import itertools
            assert not hasattr(itertools, 'hello_world')
            assert hasattr(itertools, 'islice')
            assert '(built-in)' in repr(itertools)
        finally:
            sys.path.insert(0, sys.path.pop())
        del sys.modules['itertools']

    def test_invalid_pathname(self):
        import imp
        import pkg
        import os
        pathname = os.path.join(os.path.dirname(pkg.__file__), 'a.py')
        module = imp.load_module('a', open(pathname),
                                 'invalid_path_name', ('.py', 'r', imp.PY_SOURCE))
        assert module.__name__ == 'a'
        assert module.__file__ == 'invalid_path_name'

    def test_crash_load_module(self):
        import imp
        raises(ValueError, imp.load_module, "", "", "", [1, 2, 3, 4])

    def test_source_encoding(self):
        import imp
        import encoded
        fd = imp.find_module('line2', encoded.__path__)[0]
        assert fd.encoding == 'iso-8859-1'
        assert fd.tell() == 0

    def test_bad_source_encoding(self):
        import imp
        import encoded
        raises(SyntaxError, imp.find_module, 'bad', encoded.__path__)

    def test_find_module_fsdecode(self):
        import sys
        name = self.special_char
        if not name:
            skip("can't run this test with %s as filesystem encoding"
                 % sys.getfilesystemencoding())
        import imp
        import encoded
        f, filename, _ = imp.find_module(name, encoded.__path__)
        assert f is not None
        assert filename[:-3].endswith(name)

    def test_unencodable(self):
        if not self.testfn_unencodable:
            skip("need an unencodable filename")
        import imp
        import os
        name = self.testfn_unencodable
        os.mkdir(name)
        try:
            raises(ImportError, imp.NullImporter, name)
        finally:
            os.rmdir(name)


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

def _testfile(space, magic, mtime, co=None):
    cpathname = str(udir.join('test.pyc'))
    f = file(cpathname, "wb")
    f.write(_getlong(magic))
    f.write(_getlong(mtime))
    if co:
        # marshal the code object with the PyPy marshal impl
        pyco = PyCode._from_code(space, co)
        w_marshal = space.getbuiltinmodule('marshal')
        w_marshaled_code = space.call_method(w_marshal, 'dumps', pyco)
        marshaled_code = space.bytes_w(w_marshaled_code)
        f.write(marshaled_code)
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
        cpathname = _testfile(space, importing.get_pyc_magic(space), mtime)
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
        cpathname = _testfile(space, importing.get_pyc_magic(space)+1, mtime)
        ret = importing.check_compiled_module(space,
                                              cpathname,
                                              mtime)
        assert ret is None

        # check for empty .pyc file
        f = open(cpathname, 'wb')
        f.close()
        ret = importing.check_compiled_module(space,
                                              cpathname,
                                              mtime)
        assert ret is None
        os.remove(cpathname)

    def test_read_compiled_module(self):
        space = self.space
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(space, importing.get_pyc_magic(space), mtime, co)
        stream = streamio.open_file_as_stream(cpathname, "rb")
        try:
            stream.seek(8, 0)
            w_code = importing.read_compiled_module(
                    space, cpathname, stream.readall())
            pycode = w_code
        finally:
            stream.close()
        assert type(pycode) is PyCode
        w_dic = space.newdict()
        pycode.exec_code(space, w_dic, w_dic)
        w_ret = space.getitem(w_dic, space.wrap('x'))
        ret = space.int_w(w_ret)
        assert ret == 42

    def test_load_compiled_module(self):
        space = self.space
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(space, importing.get_pyc_magic(space), mtime, co)
        w_modulename = space.wrap('somemodule')
        stream = streamio.open_file_as_stream(cpathname, "rb")
        try:
            w_mod = space.wrap(Module(space, w_modulename))
            magic = importing._r_long(stream)
            timestamp = importing._r_long(stream)
            w_ret = importing.load_compiled_module(space,
                                                   w_modulename,
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

    def test_load_compiled_module_nopathname(self):
        space = self.space
        mtime = 12345
        co = compile('x = 42', '?', 'exec')
        cpathname = _testfile(space, importing.get_pyc_magic(space), mtime, co)
        w_modulename = space.wrap('somemodule')
        stream = streamio.open_file_as_stream(cpathname, "rb")
        try:
            w_mod = space.wrap(Module(space, w_modulename))
            magic = importing._r_long(stream)
            timestamp = importing._r_long(stream)
            w_ret = importing.load_compiled_module(space,
                                                   w_modulename,
                                                   w_mod,
                                                   None,
                                                   magic,
                                                   timestamp,
                                                   stream.readall())
        finally:
            stream.close()
        filename = space.getattr(w_ret, space.wrap('__file__'))
        assert space.str_w(filename) == u'?'

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
        assert type(pycode) is PyCode
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
            w_ret = importing.load_source_module(
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
            w_ret = importing.load_source_module(
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
            w_ret = importing.load_source_module(
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
            w_ret = importing.load_source_module(
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
            w_ret = importing.load_source_module(
                space, w_modulename, w_mod,
                pathname, stream.readall(),
                stream.try_to_find_file_descriptor())
        except OperationError:
            # OperationError("NameError", "global name 'unknown_name' is not defined")
            pass
        stream.close()

        # And the .pyc has been generated
        cpathname = udir.join(importing.make_compiled_pathname('test.py'))
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
        assert type(pycode) is PyCode

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
                cpathname = _testfile(space1, importing.get_pyc_magic(space1),
                                      mtime, co)
                w_modulename = space2.wrap('somemodule')
                stream = streamio.open_file_as_stream(cpathname, "rb")
                try:
                    w_mod = space2.wrap(Module(space2, w_modulename))
                    magic = importing._r_long(stream)
                    timestamp = importing._r_long(stream)
                    space2.raises_w(space2.w_ImportError,
                                    importing.load_compiled_module,
                                    space2,
                                    w_modulename,
                                    w_mod,
                                    cpathname,
                                    magic,
                                    timestamp,
                                    stream.readall())
                finally:
                    stream.close()

    def test_annotation(self):
        from rpython.annotator.annrpython import RPythonAnnotator
        from rpython.annotator import model as annmodel
        def f():
            return importing.make_compiled_pathname('abc/foo.py')
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeString)
        assert s.no_nul


def test_PYTHONPATH_takes_precedence(space): 
    if sys.platform == "win32":
        py.test.skip("unresolved issues with win32 shell quoting rules")
    from pypy.interpreter.test.test_zpy import pypypath 
    extrapath = udir.ensure("pythonpath", dir=1) 
    extrapath.join("urllib.py").write("print(42)\n")
    old = os.environ.get('PYTHONPATH', None)
    oldlang = os.environ.pop('LANG', None)
    try:
        os.environ['PYTHONPATH'] = str(extrapath)
        output = py.process.cmdexec('''"%s" "%s" -c "import urllib"''' %
                                 (sys.executable, pypypath))
        assert output.strip() == '42'
    finally:
        if old:
            os.environ['PYTHONPATH'] = old
        if oldlang:
            os.environ['LANG'] = oldlang


class AppTestImportHooks(object):
    spaceconfig = {
        "usemodules": ['struct', 'itertools', 'rctime'],
    }

    def setup_class(cls):
        mydir = os.path.dirname(__file__)
        cls.w_hooktest = cls.space.wrap(os.path.join(mydir, 'hooktest'))
        cls.w_saved_modules = _setup_path(cls.space, mydir)
        cls.space.appexec([], """
            ():
                # Obscure: manually bootstrap the utf-8/latin1 codecs
                # for TextIOs opened by imp.find_module. It's not
                # otherwise loaded by the test infrastructure but would
                # have been by app_main
                import encodings.utf_8
                import encodings.latin_1
        """)

    def teardown_class(cls):
        _teardown(cls.space, cls.w_saved_modules)

    def test_meta_path(self):
        tried_imports = []
        class Importer(object):
            def find_module(self, fullname, path=None):
                tried_imports.append((fullname, path))

        import sys, math
        del sys.modules["math"]

        sys.meta_path.append(Importer())
        try:
            import math
            assert len(tried_imports) == 1
            package_name = '.'.join(__name__.split('.')[:-1])
            if package_name:
                assert tried_imports[0][0] == package_name + ".math"
            else:
                assert tried_imports[0][0] == "math"
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
                except ImportError:
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
            mnames = ("colorsys", "html.parser")
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

class AppTestPyPyExtension(object):
    spaceconfig = dict(usemodules=['imp', 'zipimport', '__pypy__'])

    def setup_class(cls):
        cls.w_udir = cls.space.wrap(str(udir))

    def test_run_compiled_module(self):
        # XXX minimal test only
        import imp, types
        module = types.ModuleType('foobar')
        raises(IOError, imp._run_compiled_module,
               'foobar', 'this_file_does_not_exist', None, module)

    def test_getimporter(self):
        import imp, os
        # an existing directory
        importer = imp._getimporter(self.udir)
        assert importer is None
        # an existing file
        path = os.path.join(self.udir, 'test_getimporter')
        open(path, 'w').close()
        importer = imp._getimporter(path)
        assert isinstance(importer, imp.NullImporter)
        # a non-existing path
        path = os.path.join(self.udir, 'does_not_exist_at_all')
        importer = imp._getimporter(path)
        assert isinstance(importer, imp.NullImporter)
        # a mostly-empty zip file
        path = os.path.join(self.udir, 'test_getimporter.zip')
        f = open(path, 'wb')
        f.write(b'PK\x03\x04\n\x00\x00\x00\x00\x00P\x9eN>\x00\x00\x00\x00\x00'
                b'\x00\x00\x00\x00\x00\x00\x00\x05\x00\x15\x00emptyUT\t\x00'
                b'\x03wyYMwyYMUx\x04\x00\xf4\x01d\x00PK\x01\x02\x17\x03\n\x00'
                b'\x00\x00\x00\x00P\x9eN>\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                b'\x00\x00\x00\x05\x00\r\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                b'\xa4\x81\x00\x00\x00\x00emptyUT\x05\x00\x03wyYMUx\x00\x00PK'
                b'\x05\x06\x00\x00\x00\x00\x01\x00\x01\x00@\x00\x00\x008\x00'
                b'\x00\x00\x00\x00')
        f.close()
        importer = imp._getimporter(path)
        import zipimport
        assert isinstance(importer, zipimport.zipimporter)


class AppTestNoPycFile(object):
    spaceconfig = {
        "objspace.usepycfiles": False,
    }
    def setup_class(cls):
        usepycfiles = cls.spaceconfig['objspace.usepycfiles']
        cls.w_usepycfiles = cls.space.wrap(usepycfiles)
        cls.saved_modules = _setup(cls)

    def teardown_class(cls):
        _teardown(cls.space, cls.saved_modules)

    def test_import_possibly_from_pyc(self):
        from compiled import x
        assert x.__file__.endswith('.py')
        try:
            from compiled import lone
        except ImportError:
            assert not self.usepycfiles
        else:
            assert lone.__cached__.endswith('.pyc')

class AppTestNoLonePycFile(AppTestNoPycFile):
    spaceconfig = {
        "objspace.usepycfiles": True,
    }


class AppTestMultithreadedImp(object):
    spaceconfig = dict(usemodules=['thread', 'rctime'])

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
        import sys, _thread, time
        oldpath = sys.path[:]
        try:
            sys.path.insert(0, self.tmppath)
            got = []

            def check():
                import test_multithreaded_imp
                got.append(getattr(test_multithreaded_imp, 'x', '?'))

            for i in range(5):
                _thread.start_new_thread(check, ())

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
