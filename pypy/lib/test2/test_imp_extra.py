import support
imp = support.libmodule('imp')

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
