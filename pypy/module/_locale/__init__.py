from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._locale import interp_locale
import sys

class Module(MixedModule):
    """Support for POSIX locales."""

    interpleveldefs  = {
            'setlocale':                'interp_locale.setlocale',
            'localeconv':               'interp_locale.localeconv',
            'strcoll':                  'interp_locale.strcoll',
            'strxfrm':                  'interp_locale.strxfrm',
            }

    if sys.platform == 'win32':
        interpleveldefs.update({
            '_getdefaultlocale':        'interp_locale.getdefaultlocale',
            })

    if interp_locale.HAVE_LANGINFO:
        interpleveldefs.update({
            'nl_langinfo':              'interp_locale.nl_langinfo',
            })
    if interp_locale.HAVE_LIBINTL:
        interpleveldefs.update({
            'gettext':                  'interp_locale.gettext',
            'dgettext':                 'interp_locale.dgettext',
            'dcgettext':                'interp_locale.dcgettext',
            'textdomain':               'interp_locale.textdomain',
            'bindtextdomain':           'interp_locale.bindtextdomain',
            })
        if interp_locale.HAVE_BIND_TEXTDOMAIN_CODESET:
            interpleveldefs.update({
            'bind_textdomain_codeset':'interp_locale.bind_textdomain_codeset',
            })

    appleveldefs  = {
            'Error':                'app_locale.Error',
            '_fixup_ulcase':        'app_locale._fixup_ulcase',
            }

    def buildloaders(cls):
        for constant, value in interp_locale.constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
