
import py, sys
from pypy.tool.pack import main
import tarfile

def test_pack():
    goal_dir = py.path.local(__file__).join('..', '..', '..', 'translator', 'goal')
    if not sys.platform == 'linux2':
        py.test.skip("untested on not linux")
    pypy_c = goal_dir.join('pypy-c')
    if not pypy_c.check():
        pypy_c.write('xxx')
        remove_pypy_c = True
    else:
        remove_pypy_c = False
    try:
        main()
    finally:
        if remove_pypy_c:
            pypy_c.remove()
    bzfile = goal_dir.join('pypy-c.tar.bz2')
    assert bzfile.check()
    assert tarfile.open(str(bzfile), 'r:bz2').getnames() == ['pypy-c']
    bzfile.remove()
