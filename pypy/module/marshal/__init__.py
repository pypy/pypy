# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    This module implements marshal at interpreter level.
    """

    appleveldefs = {
    }

    interpleveldefs = {
        'dump'    : 'interp_marshal.dump',
        'dumps'   : 'interp_marshal.dumps',
        'load'    : 'interp_marshal.load',
        'loads'   : 'interp_marshal.loads',
        'version' : 'space.newint(interp_marshal.Py_MARSHAL_VERSION)',
    }
