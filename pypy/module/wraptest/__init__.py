from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    interpleveldefs = {
        'someclass' : 'interp_wraptest.new_someclass',
        'someclassbig' : 'interp_wraptest.someclassbig',
    }

    appleveldefs = {
    }
