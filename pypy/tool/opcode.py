# load opcode.py as pythonopcode from our own lib
# This should handle missing local copy
def load_opcode():
    import py
    opcode_path = py.path.local(__file__).dirpath().dirpath().dirpath('lib-python/modified-2.4.1/opcode.py')
    execfile(str(opcode_path), globals())

load_opcode()
del load_opcode
