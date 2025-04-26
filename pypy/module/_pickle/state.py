class State:
    def __init__(self, space):
        w_None = space.w_None
        # copyreg.dispatch_table, {type_object: pickling_function}
        self.w_dispatch_table = w_None

        # copyreg._extension_registry, {(module_name, function_name): code}
        self.w_extension_registry = w_None
        # copyreg._extension_cache, {code: object}
        self.w_extension_cache = w_None
        # copyreg._inverted_registry, {code: (module_name, function_name)}
        self.w_inverted_registry = w_None
        self.w_partial = w_None


    def startup(self, space):
        w_import = space.getattr(space.builtin, space.newtext("__import__"))
        w__compat_pickle = space.call_function(w_import, space.newtext('_compat_pickle'))
        self.w_NAME_MAPPING = space.getattr(w__compat_pickle, space.newtext("NAME_MAPPING"))
        self.w_IMPORT_MAPPING = space.getattr(w__compat_pickle, space.newtext("IMPORT_MAPPING"))
        # For the extension opcodes EXT1, EXT2 and EXT4.
        # from copyreg import (_extension_registry, _inverted_registry,
        # _extension_cache)
        w_copyreg = space.call_function(w_import, space.newtext('copyreg'))
        self.w_dispatch_table = space.getattr(w_copyreg, space.newtext('dispatch_table'))
        self.w_extension_registry = space.getattr(w_copyreg, space.newtext('_extension_registry'))
        self.w_extension_cache = space.getattr(w_copyreg, space.newtext('_extension_cache'))
        self.w_inverted_registry = space.getattr(w_copyreg, space.newtext('_inverted_registry'))
        w_functools = space.call_function(w_import, space.newtext('functools'))
        self.w_partial = space.getattr(w_functools, space.newtext("partial"))
        return
