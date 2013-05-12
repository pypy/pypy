from pypy.goal.targetpypystandalone import get_entry_point, create_entry_point
from pypy.config.pypyoption import get_pypy_config

class TestTargetPyPy(object):
    def test_run(self):
        config = get_pypy_config(translating=False)
        entry_point = get_entry_point(config)[0]
        entry_point(['pypy-c' , '-S', '-c', 'print 3'])

def test_exeucte_source(space):
    _, execute_source = create_entry_point(space, None)
    execute_source("import sys; sys.modules['xyz'] = 3")
    x = space.int_w(space.getitem(space.getattr(space.builtin_modules['sys'],
                                                space.wrap('modules')),
                                                space.wrap('xyz')))
    assert x == 3
    execute_source("sys")
    # did not crash - the same globals
