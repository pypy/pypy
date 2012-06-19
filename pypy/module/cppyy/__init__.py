from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """    """

    interpleveldefs = {
        '_load_dictionary'       : 'interp_cppyy.load_dictionary',
        '_resolve_name'          : 'interp_cppyy.resolve_name',
        '_scope_byname'          : 'interp_cppyy.scope_byname',
        '_template_byname'       : 'interp_cppyy.template_byname',
        '_set_class_generator'   : 'interp_cppyy.set_class_generator',
        '_register_class'        : 'interp_cppyy.register_class',
        'CPPInstance'            : 'interp_cppyy.W_CPPInstance',
        'addressof'              : 'interp_cppyy.addressof',
        'bind_object'            : 'interp_cppyy.bind_object',
    }

    appleveldefs = {
        'gbl'                    : 'pythonify.gbl',
        'load_reflection_info'   : 'pythonify.load_reflection_info',
        'add_pythonization'      : 'pythonify.add_pythonization',
    }
