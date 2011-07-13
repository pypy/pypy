from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """    """

    interpleveldefs = {
        '_load_lib'              : 'interp_cppyy.load_lib',
        '_type_byname'           : 'interp_cppyy.type_byname',
        '_template_byname'       : 'interp_cppyy.template_byname',
        'CPPInstance'            : 'interp_cppyy.W_CPPInstance',
    }

    appleveldefs = {
        'gbl'                    : 'pythonify.gbl',
        'load_lib'               : 'pythonify.load_lib',
    }
