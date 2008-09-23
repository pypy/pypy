"""
Tests for the entry point of pypy-c, whether nanos.py is supplying
the needed names for app_main.py.
"""
import os

from pypy.translator.goal import app_main
this_dir = os.path.dirname(app_main.__file__)

from pypy.objspace.std import Space
from pypy.translator.goal.targetpypystandalone import create_entry_point

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
