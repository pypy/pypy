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

def _py_file():
    fn = __file__
    if fn.lower().endswith('c') or fn.lower().endswith('o'):
        fn = fn[:-1]
    assert fn.lower().endswith('.py')
    return fn

def _pyc_file():
    import marshal
    co = compile("marker=42", "x.py", "exec")
    f = open('@TEST.pyc', 'wb')
    f.write(imp.get_magic())
    f.write('\x00\x00\x00\x00')
    marshal.dump(co, f)
    f.close()
    return '@TEST.pyc'

def test_load_module_py():
    fn = _py_file()
    descr = ('.py', 'U', imp.PY_SOURCE)
    f = open(fn, 'U')
    mod = imp.load_module('test_imp_extra_AUTO1', f, fn, descr)
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
    fn = _py_file()
    mod = imp.load_source('test_imp_extra_AUTO3', fn)
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
    fn = _py_file()
    try:
        imp.load_compiled('test_imp_extra_AUTO5', fn)
    except ImportError:
        pass
    else:
        raise Exception("expected an ImportError")
