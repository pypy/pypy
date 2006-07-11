from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'fcntl': 'interp_fcntl.fcntl',
        'flock': 'interp_fcntl.flock',
        'lockf': 'interp_fcntl.lockf'
    }

    appleveldefs = {
        '_conv_descriptor': 'app_fcntl._conv_descriptor',
    }
    
    def buildloaders(cls):
        from pypy.module.fcntl import interp_fcntl
        for constant, value in interp_fcntl.constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
