from pypy.interpreter.mixedmodule import MixedModule                            

class Module(MixedModule):

    appleveldefs = {
            'ParseError' : 'app_error.Parse_Error'
    }

    interpleveldefs = {
        'Engine'        : 'engine.W_Engine',        
    }
