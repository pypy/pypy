from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """    """

    interpleveldefs = {
        '_load_dictionary'       : 'interp_cppyy.load_dictionary',
        '_type_byname'           : 'interp_cppyy.type_byname',
        '_template_byname'       : 'interp_cppyy.template_byname',
        'CPPInstance'            : 'interp_cppyy.W_CPPInstance',
        'addressof'              : 'interp_cppyy.addressof',
    }

    appleveldefs = {
        'gbl'                    : 'pythonify.gbl',
        'load_reflection_info'   : 'pythonify.load_reflection_info',
    }
