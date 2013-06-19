from pypy.interpreter.mixedmodule import MixedModule                            

class Module(MixedModule):

    appleveldefs = {
            'ParseError' : 'app_error.ParseError'
    }

    interpleveldefs = {
        'Engine'        : 'engine.W_Engine',        
    }
