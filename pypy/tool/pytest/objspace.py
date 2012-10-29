import py
from pypy.config.config import ConflictConfigError
from pypy.tool.option import make_config, make_objspace
from pypy.tool.pytest import appsupport
from pypy.conftest import option

_SPACECACHE={}
def gettestobjspace(name=None, **kwds):
    """ helper for instantiating and caching space's for testing.
    """
    try:
        config = make_config(option, objspace=name, **kwds)
    except ConflictConfigError, e:
        # this exception is typically only raised if a module is not available.
        # in this case the test should be skipped
        py.test.skip(str(e))
    key = config.getkey()
    try:
        return _SPACECACHE[key]
    except KeyError:
        if getattr(option, 'runappdirect', None):
            if name not in (None, 'std'):
                myname = getattr(sys, 'pypy_objspaceclass', '')
                if not myname.lower().startswith(name):
                    py.test.skip("cannot runappdirect test: "
                                 "%s objspace required" % (name,))
            return TinyObjSpace(**kwds)
        space = maketestobjspace(config)
        _SPACECACHE[key] = space
        return space

def maketestobjspace(config=None):
    if config is None:
        config = make_config(option)
    space = make_objspace(config)
    space.startup() # Initialize all builtin modules
    space.setitem(space.builtin.w_dict, space.wrap('AssertionError'),
                  appsupport.build_pytest_assertion(space))
    space.setitem(space.builtin.w_dict, space.wrap('raises'),
                  space.wrap(appsupport.app_raises))
    space.setitem(space.builtin.w_dict, space.wrap('skip'),
                  space.wrap(appsupport.app_skip))
    space.raises_w = appsupport.raises_w.__get__(space)
    space.eq_w = appsupport.eq_w.__get__(space)
    return space

