
import py
from pypy.tool.release.make_release import browse_nightly

XML = py.path.local(__file__).join('..', 'nightly.xml').read()

def test_browse_nightly():
    res = browse_nightly('branch', override_xml=XML)
    assert res[('jit', 'linux')] == (40170, 'pypy-c-jit-40170-c407c9dc5382-linux.tar.bz2')
    assert len(res) == 6
    assert res[('nojit', 'linux64')] == (40170, 'pypy-c-nojit-40170-c407c9dc5382-linux64.tar.bz2')
