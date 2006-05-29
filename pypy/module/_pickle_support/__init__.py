from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """Built-in functions, exceptions, and other objects."""

    appleveldefs = {
    }

    interpleveldefs = {
        'cell_new'     : 'maker.cell_new',
        'code_new'     : 'maker.code_new',
        'func_new'     : 'maker.func_new',
        'module_new'   : 'maker.module_new',
        'method_new'   : 'maker.method_new',
        'dictiter_surrogate_new' : 'maker.dictiter_surrogate_new',
        'seqiter_new'  : 'maker.seqiter_new',
        'reverseseqiter_new' : 'maker.reverseseqiter_new',
        'frame_new'    : 'maker.frame_new',
    }
