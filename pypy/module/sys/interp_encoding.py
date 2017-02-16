import sys
from rpython.rlib import rlocale
from rpython.rlib.objectmodel import we_are_translated

def getdefaultencoding(space):
    """Return the current default string encoding used by the Unicode
implementation."""
    return space.newtext(space.sys.defaultencoding)

if sys.platform == "win32":
    base_encoding = "mbcs"
elif sys.platform == "darwin":
    base_encoding = "utf-8"
elif sys.platform == "linux2":
    base_encoding = "ascii"
else:
    # In CPython, the default base encoding is NULL. This is paired with a
    # comment that says "If non-NULL, this is different than the default
    # encoding for strings". Therefore, the default filesystem encoding is the
    # default encoding for strings, which is ASCII.
    base_encoding = "ascii"

def _getfilesystemencoding(space):
    encoding = base_encoding
    if rlocale.HAVE_LANGINFO:
        try:
            oldlocale = rlocale.setlocale(rlocale.LC_CTYPE, None)
            rlocale.setlocale(rlocale.LC_CTYPE, "")
            try:
                loc_codeset = rlocale.nl_langinfo(rlocale.CODESET)
                if loc_codeset:
                    codecmod = space.getbuiltinmodule('_codecs')
                    w_res = space.call_method(codecmod, 'lookup',
                                              space.newtext(loc_codeset))
                    if space.is_true(w_res):
                        w_name = space.getattr(w_res, space.newtext('name'))
                        encoding = space.str_w(w_name)
            finally:
                rlocale.setlocale(rlocale.LC_CTYPE, oldlocale)
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
