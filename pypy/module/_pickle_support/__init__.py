from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """Built-in functions, exceptions, and other objects."""

    appleveldefs = {
    }

    interpleveldefs = {
        'cell_new': 'maker.cell_new',
        'code_new': 'maker.code_new',
    }
