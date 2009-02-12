from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """Support for POSIX locales."""

    interpleveldefs  = {
            #'Error':               'interp_locale.Error',
            #'LocalConfigure':      'interp_locale.LocaleConfigure',
            #'lconv':               'interp_locale.lconv',
            #'fixup_ulcase':        'interp_locale.fixup_ulcase',
            'setlocale':           'interp_locale.setlocale',
            'localeconv':          'interp_locale.localeconv',
            #'strcoll':             'interp_locale.strcoll',
            #'strxfrm':             'interp_locale.strxfrm',
            #'getdefaultlocale':    'interp_locale.getdefaultlocale',
            #'gettext':             'interp_locale.gettext',
            }

    appleveldefs  = {
            }

    def buildloaders(cls):
        from pypy.module._locale import interp_locale
        for constant, value in interp_locale.constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
