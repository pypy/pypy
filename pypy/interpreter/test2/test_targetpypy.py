from pypy.goal.targetpypystandalone import get_entry_point
from pypy.config.pypyoption import get_pypy_config

class TestTargetPyPy(object):
    def test_run(self):
        config = get_pypy_config(translating=False)
        entry_point = get_entry_point(config)[0]
        entry_point(['pypy-c' , '-S', '-c', 'print 3'])
