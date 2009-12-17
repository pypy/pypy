
import py
from pypy.tool.autopath import pypydir
from pypy.tool.package import main
import tarfile

def test_dir_structure():
    # make sure we have sort of pypy-c
    pypy_c = py.path.local(pypydir).join('translator', 'goal', 'pypy-c')
    if not pypy_c.check():
        pypy_c.write("xxx")
        fake_pypy_c = True
    else:
        fake_pypy_c = False
    try:
        builddir = main(py.path.local(pypydir).dirpath(), 'test')
        assert builddir.join('pypy', 'lib-python', '2.5.2', 'test').check()
        assert builddir.join('pypy', 'bin', 'pypy-c').check()
        assert builddir.join('pypy', 'pypy', 'lib', 'syslog.py').check()
        th = tarfile.open(str(builddir.join('test.tar.bz2')))
        assert th.getmember('pypy/pypy/lib/syslog.py')
    finally:
        if fake_pypy_c:
            pypy_c.remove()
