from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    "This module provides runtime bindings to C++ code for which reflection\n\
    info has been generated. Current supported back-ends are Reflex and CINT.\n\
    See http://doc.pypy.org/en/latest/cppyy.html for full details."

    interpleveldefs = {
        '_load_dictionary'       : 'interp_cppyy.load_dictionary',
        '_resolve_name'          : 'interp_cppyy.resolve_name',
        '_scope_byname'          : 'interp_cppyy.scope_byname',
        '_template_byname'       : 'interp_cppyy.template_byname',
        '_set_class_generator'   : 'interp_cppyy.set_class_generator',
        '_register_class'        : 'interp_cppyy.register_class',
        '_is_static'             : 'interp_cppyy.is_static',
        'CPPInstance'            : 'interp_cppyy.W_CPPInstance',
        'addressof'              : 'interp_cppyy.addressof',
        'bind_object'            : 'interp_cppyy.bind_object',
    }

    appleveldefs = {
        'gbl'                    : 'pythonify.gbl',
        'load_reflection_info'   : 'pythonify.load_reflection_info',
        'add_pythonization'      : 'pythonify.add_pythonization',
    }

    def __init__(self, space, *args):
        "NOT_RPYTHON"
        MixedModule.__init__(self, space, *args)

        # pythonization functions may be written in RPython, but the interp2app
        # code generation is not, so give it a chance to run now
        from pypy.module.cppyy import capi
        capi.register_pythonizations(space)
