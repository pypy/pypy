from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'array': 'interp_array.W_ArrayBase',
        'ArrayType': 'interp_array.W_ArrayBase',
        '_array_reconstructor': 'reconstructor.array_reconstructor',
    }

    appleveldefs = {
    }

    def startup(self, space):
        w_mod = space.call_function(space.w_default_importlib_import, space.newtext("_collections_abc"))
        w_cls = space.getattr(w_mod, space.newtext("MutableSequence"))
        w_arraytype = space.getattr(self, space.newtext("array"))
        space.call_method(w_cls, "register", w_arraytype)

