"""
Tests for the entry point of pypy-c, whether nanos.py is supplying
the needed names for app_main.py.
"""
import os

from pypy.translator.goal import app_main
this_dir = os.path.dirname(app_main.__file__)

from pypy.objspace.std import Space
from pypy.translator.goal.targetpypystandalone import create_entry_point
from pypy.tool.udir import udir


class TestNanos:
    def getnanos(self):
        from pypy.translator.goal.nanos import os_module_for_testing
        return os_module_for_testing

    def test_exists(self):
        os1 = self.getnanos()
        assert os1.name == os.name
        assert os1.sep == os.sep
        assert os1.pathsep == os.pathsep

    def test_dirname(self):
        p1 = os.path
        p2 = self.getnanos().path
        path = str(udir.join('baz'))
        assert p1.dirname(path) == p2.dirname(path)
        assert p1.dirname(path + os.sep) == p2.dirname(path + os.sep)
        assert p1.dirname(path + 2*os.sep) == p2.dirname(path + 2*os.sep)
        assert p1.dirname(p1.dirname(path)) == p2.dirname(p2.dirname(path))

    def test_join(self):
        p1 = os.path
        p2 = self.getnanos().path
        base = str(udir)
        assert p1.join(base, '') == p2.join(base, '')
        assert p1.join(base, 'baz') == p2.join(base, 'baz')
        assert p1.join(base + os.sep, 'baz') == p2.join(base + os.sep, 'baz')
        assert p1.join(base, 'baz' + os.sep) == p2.join(base, 'baz' + os.sep)
        assert p1.join(base, base) == p2.join(base, base)

    def test_abspath(self):
        p2 = self.getnanos().path
        base = str(udir)
        assert p2.abspath(base) == base
        assert p2.abspath('x') == os.path.join(os.getcwd(), 'x')

    def test_abspath_uses_normpath(self):
        p1 = os.path
        p2 = self.getnanos().path
        base = str(udir)
        assert p2.abspath(p1.join(base, '.')) == base
        assert p2.abspath(p1.join(base, '.', '.', '.')) == base
        assert p2.abspath(p1.join(base, 'foo', '..')) == base

    def test_isfile(self):
        p2 = self.getnanos().path
        udir.join('test_isfile').write('\n')
        base = str(udir)
        assert p2.isfile(p2.join(base, 'test_isfile'))
        assert not p2.isfile(p2.join(base, 'test_isfile.DOES.NOT.EXIST'))
        assert not p2.isfile(base)


def test_nanos():
    space = Space()
    # manually imports app_main.py
    filename = os.path.join(this_dir, 'app_main.py')
    w_dict = space.newdict()
    space.exec_(open(filename).read(), w_dict, w_dict)
    entry_point = create_entry_point(space, w_dict)

    # check that 'os' is not in sys.modules
    assert not space.is_true(
        space.call_method(space.sys.get('modules'),
                          '__contains__', space.wrap('os')))
    # But that 'sys' is still present
    assert space.is_true(
        space.call_method(space.sys.get('modules'),
                          '__contains__', space.wrap('sys')))

    entry_point(['', '-c', 'print 42'])
