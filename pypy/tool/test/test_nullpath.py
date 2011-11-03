import sys
import py
from pypy.tool.nullpath import NullPyPathLocal

def setup_module():
    if 'posix' not in sys.builtin_module_names:
        py.test.skip('posix only')

def test_nullpath(tmpdir):
    path = NullPyPathLocal(tmpdir)
    assert repr(path).endswith('[fake]')
    foo_txt = path.join('foo.txt')
    assert isinstance(foo_txt, NullPyPathLocal)
    #
    f = foo_txt.open('w')
    assert f.name == '/dev/null'
