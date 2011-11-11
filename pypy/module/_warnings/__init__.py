from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """provides basic warning filtering support.
    It is a helper module to speed up interpreter start-up."""
    cannot_override_in_import_statements = True

    interpleveldefs = {
        'warn'         : 'interp_warnings.warn',
        'warn_explicit': 'interp_warnings.warn_explicit',
    }

    appleveldefs = {
    }

    def setup_after_space_initialization(self):
        from pypy.module._warnings.interp_warnings import State
        state = self.space.fromcache(State)
        self.setdictvalue(self.space, "filters", state.w_filters)
        self.setdictvalue(self.space, "once_registry", state.w_once_registry)
        self.setdictvalue(self.space, "default_action", state.w_default_action)

