"""Test the exec statement functionality.

New for PyPy - Could be incorporated into CPython regression tests.
"""
from rpython.tool.udir import udir


def test_file(space):
    fn = udir.join('test_exec_file')
    fn.write('abc=1\ncba=2\n')
    space.appexec([space.wrap(str(fn))], '''
        (filename):
            fo = open(filename, 'r')
            g = {}
            exec fo in g
            assert 'abc' in g
            assert 'cba' in g
    ''')
