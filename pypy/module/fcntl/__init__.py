from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
    }

    appleveldefs = {
        '_conv_descriptor': 'app_fcntl._conv_descriptor',
    }
