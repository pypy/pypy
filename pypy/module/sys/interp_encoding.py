import sys
from rpython.rlib import rlocale
from rpython.rlib.objectmodel import we_are_translated

def getdefaultencoding(space):
    """Return the current default string encoding used by the Unicode
implementation."""
    return space.newtext(space.sys.defaultencoding)

base_encoding = "utf-8"
if sys.platform == "win32":
    base_error = "strict"
elif sys.platform == "darwin":
    base_error = "surrogateescape"
elif sys.platform == "linux2":
    base_error = "surrogateescape"
else:
    # Unknown platform
    base_error = "surrogateescape"

def _getfilesystemencoding(space):
    """If LC_CTYPE is currently C or POSIX, set it to "en_US", and return "utf-8"
       In CPython this checks other cases, that we ignore 
    """
    encoding = base_encoding
    if rlocale.HAVE_LANGINFO:
        try:
            oldlocale = rlocale.setlocale(rlocale.LC_CTYPE, None)
            if oldlocale in ("C", "POSIX"):
                rlocale.setlocale(rlocale.LC_CTYPE, "en_US.UTF-8")
        except rlocale.LocaleError:
            pass
    return encoding

def getfilesystemencoding(space):
    """Return the encoding used to convert Unicode filenames in
    operating system filenames.
    """
    if space.sys.filesystemencoding is None:
        return space.newtext(base_encoding)
    return space.newtext(space.sys.filesystemencoding)


def getfilesystemencodeerrors(space):
    return space.newtext(base_error)
