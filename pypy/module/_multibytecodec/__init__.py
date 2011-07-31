from pypy.interpreter.mixedmodule import MixedModule 


class Module(MixedModule):

    interpleveldefs = {
        # for compatibility this name is obscured, and should be called
        # via the _codecs_*.py modules written in lib_pypy.
        '__getcodec': 'interp_multibytecodec.getcodec',

        'MultibyteIncrementalDecoder':
            'interp_incremental.MultibyteIncrementalDecoder',
    }

    appleveldefs = {
        'MultibyteIncrementalEncoder':
            'app_multibytecodec.MultibyteIncrementalEncoder',
        'MultibyteStreamReader':
            'app_multibytecodec.MultibyteStreamReader',
        'MultibyteStreamWriter':
            'app_multibytecodec.MultibyteStreamWriter',
    }
