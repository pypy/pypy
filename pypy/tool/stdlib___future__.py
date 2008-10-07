# load __future__.py constants

def load_module():
    import py
    module_path = py.path.local(__file__).dirpath().dirpath().dirpath('lib-python/2.5.2/__future__.py')
    execfile(str(module_path), globals())

load_module()
del load_module

# this could be generalized, it's also in opcode.py
