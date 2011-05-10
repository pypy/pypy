from pypy.interpreter.mixedmodule import MixedModule 


class Module(MixedModule):

    interpleveldefs = {
        # for compatibility this name is obscured, and should be called
        # via the _codecs_*.py modules written in lib_pypy.
        '__getcodec': 'interp_multibytecodec.getcodec',
    }

    appleveldefs = {
        'MultibyteIncrementalEncoder':
            'app_multibytecodec.MultibyteIncrementalEncoder',
        'MultibyteIncrementalDecoder':
            'app_multibytecodec.MultibyteIncrementalDecoder',
        'MultibyteStreamReader':
            'app_multibytecodec.MultibyteStreamReader',
        'MultibyteStreamWriter':
            'app_multibytecodec.MultibyteStreamWriter',
    }
