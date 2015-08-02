from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import rffi
from rpython.translator.platform import platform


def get_compiler_info():
    """Returns a string like 'MSC v.# 32 bit' or 'GCC #.#.#'.
    Before translation, returns '(untranslated)'.

    Must be called at run-time, not before translation, otherwise
    you're freezing the string '(untranslated)' into the executable!
    """
    if we_are_translated():
        return rffi.charp2str(COMPILER_INFO)
    return "(untranslated)"

# ____________________________________________________________


if platform.name == 'msvc':
    # XXX hard-code the MSC version, I don't feel like computing it dynamically
    _C_COMPILER_INFO = '"MSC v.%d 32 bit"' % (platform.version * 10 + 600)
else:
    _C_COMPILER_INFO = '("GCC " __VERSION__)'

COMPILER_INFO = rffi.CConstant(_C_COMPILER_INFO, rffi.CCHARP)
