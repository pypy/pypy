
import autopath
from pypy.tool.udir import udir
import py
import sys

pypypath = str(py.path.local(autopath.pypydir).join('bin', 'py.py'))

def test_nonfake_stdfile():
    """  """
    uselibfile = udir.join('uselibfile.py')
    uselibfile.write("""if 1:
    import sys
    assert not _isfake(sys.stdin)
    assert not _isfake(sys.stdout)
    assert not _isfake(sys.stderr)
    assert not _isfake(sys.__stdin__)
    assert not _isfake(sys.__stdout__)
    assert not _isfake(sys.__stderr__)
    print "ok"
    """)
    output = py.process.cmdexec( '''"%s" "%s" --file "%s"''' %
                                (sys.executable, pypypath, uselibfile) )
    assert output.splitlines()[-1] == "ok"
