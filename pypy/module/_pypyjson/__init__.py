from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """fast json implementation"""

    appleveldefs = {}

    interpleveldefs = {
        'loads' : 'interp_decoder.loads',
        }
