from pypy.lib import imp 
import os

def test_find_module():
    file, pathname, description = imp.find_module('StringIO')
    assert file is not None
    file.close()
    assert os.path.exists(pathname)
    pathname = pathname.lower()
    assert (pathname.endswith('.py') or pathname.endswith('.pyc')
                                     or pathname.endswith('.pyo'))
    assert description in imp.get_suffixes()


def test_suffixes():
    for suffix, mode, type in imp.get_suffixes():
        if mode == imp.PY_SOURCE:
            assert suffix == '.py'
            assert type == 'r'
        elif mode == imp.PY_COMPILED:
            assert suffix in ('.pyc', '.pyo')
            assert type == 'rb'


def test_obscure_functions():
    mod = imp.new_module('hi')
    assert mod.__name__ == 'hi'
    mod = imp.init_builtin('hello.world.this.is.never.a.builtin.module.name')
    assert mod is None
    mod = imp.init_frozen('hello.world.this.is.never.a.frozen.module.name')
    assert mod is None
    assert imp.is_builtin('sys')
    assert not imp.is_builtin('hello.world.this.is.never.a.builtin.module.name')
    assert not imp.is_frozen('hello.world.this.is.never.a.frozen.module.name')


MARKER = 42

def _pyc_file():
    # XXX quick hack
    # (that's the bytecode for the module containing only 'marker=42')
    f = open('@TEST.pyc', 'wb')
    f.write('m\xf2\r\n\xd6\x85\x0cCc\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00'
            '\x00\x00@\x00\x00\x00s\n\x00\x00\x00d\x00\x00Z\x00\x00d\x01\x00'
            'S(\x02\x00\x00\x00i*\x00\x00\x00N(\x01\x00\x00\x00t\x06\x00\x00'
            '\x00marker(\x01\x00\x00\x00R\x00\x00\x00\x00(\x00\x00\x00\x00('
            '\x00\x00\x00\x00t\x04\x00\x00\x00x.pyt\x01\x00\x00\x00?\x01\x00'
            '\x00\x00s\x00\x00\x00\x00')
    f.close()
    return '@TEST.pyc'

def test_load_module_py():
    descr = ('.py', 'U', imp.PY_SOURCE)
    f = open(__file__, 'U')
    mod = imp.load_module('test_imp_extra_AUTO1', f, __file__, descr)
    f.close()
    assert mod.MARKER == 42
    import test_imp_extra_AUTO1
    assert mod is test_imp_extra_AUTO1

def test_load_module_pyc():
    fn = _pyc_file()
    try:
        descr = ('.pyc', 'rb', imp.PY_COMPILED)
        f = open(fn, 'rb')
        mod = imp.load_module('test_imp_extra_AUTO2', f, fn, descr)
        f.close()
        assert mod.marker == 42
        import test_imp_extra_AUTO2
        assert mod is test_imp_extra_AUTO2
    finally:
        os.unlink(fn)

def test_load_source():
    mod = imp.load_source('test_imp_extra_AUTO3', __file__)
    assert mod.MARKER == 42
    import test_imp_extra_AUTO3
    assert mod is test_imp_extra_AUTO3

def test_load_module_pyc():
    fn = _pyc_file()
    try:
        mod = imp.load_compiled('test_imp_extra_AUTO4', fn)
        assert mod.marker == 42
        import test_imp_extra_AUTO4
        assert mod is test_imp_extra_AUTO4
    finally:
        os.unlink(fn)

def test_load_broken_pyc():
    try:
        imp.load_compiled('test_imp_extra_AUTO5', __file__)
    except ImportError:
        pass
    else:
        raise Exception("expected an ImportError")
