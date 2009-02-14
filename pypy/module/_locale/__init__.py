from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """Support for POSIX locales."""

    interpleveldefs  = {
            'setlocale':            'interp_locale.setlocale',
            'localeconv':           'interp_locale.localeconv',
            'strcoll':              'interp_locale.strcoll',
            #'strxfrm':             'interp_locale.strxfrm',
            #'getdefaultlocale':    'interp_locale.getdefaultlocale',
            'gettext':              'interp_locale.gettext',
            'dgettext':             'interp_locale.dgettext',
            'dcgettext':            'interp_locale.dcgettext',
            'textdomain':           'interp_locale.textdomain',
            }

    appleveldefs  = {
            'Error':               'app_locale.Error',
            '_fixup_ulcase':        'app_locale._fixup_ulcase',
            }

    def buildloaders(cls):
        from pypy.module._locale import interp_locale
        for constant, value in interp_locale.constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
