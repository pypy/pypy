class State:
    def __init__(self, space):
        pass

    def startup(self, space):
        w_import = space.getattr(space.builtin, space.newtext("__import__"))
        w__compat_pickle = space.call_function(w_import, space.newtext('_compat_pickle'))
        self.w_NAME_MAPPING = space.getattr(w__compat_pickle, space.newtext("NAME_MAPPING"))
        self.w_IMPORT_MAPPING = space.getattr(w__compat_pickle, space.newtext("IMPORT_MAPPING"))
        self.w_REVERSE_NAME_MAPPING = space.getattr(w__compat_pickle,
                             space.newtext("REVERSE_NAME_MAPPING"))
        self.w_REVERSE_IMPORT_MAPPING = space.getattr(w__compat_pickle,
                             space.newtext("REVERSE_IMPORT_MAPPING"))
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
