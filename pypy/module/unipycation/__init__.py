from pypy.interpreter.mixedmodule import MixedModule                            

class Module(MixedModule):
    appleveldefs = {}
    interpleveldefs = {
        'Engine'        : 'engine.W_Engine',        
    }
