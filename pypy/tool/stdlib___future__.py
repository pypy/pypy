# load __future__.py constants

def load_module():
    import py
    from pypy.module.sys.version import CPYTHON_VERSION_DIR
    to_future = "lib-python/%s/__future__.py" % (CPYTHON_VERSION_DIR,)
    module_path = py.path.local(__file__).dirpath().dirpath().dirpath(to_future)
    execfile(str(module_path), globals())

load_module()
del load_module

# this could be generalized, it's also in opcode.py
