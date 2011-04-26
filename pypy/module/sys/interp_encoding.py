import sys
from pypy.rlib import rlocale
from pypy.rlib.objectmodel import we_are_translated

def getdefaultencoding(space):
    """Return the current default string encoding used by the Unicode 
implementation."""
    return space.wrap(space.sys.defaultencoding)

def setdefaultencoding(space, w_encoding):
    """Set the current default string encoding used by the Unicode 
implementation."""
    encoding = space.str_w(w_encoding)
    mod = space.getbuiltinmodule("_codecs")
    w_lookup = space.getattr(mod, space.wrap("lookup"))
    # check whether the encoding is there
    space.call_function(w_lookup, w_encoding)
    space.sys.w_default_encoder = None
    space.sys.defaultencoding = encoding

def get_w_default_encoder(space):
    assert not (space.config.translating and not we_are_translated()), \
        "get_w_default_encoder() should not be called during translation"
    w_encoding = space.wrap(space.sys.defaultencoding)
    mod = space.getbuiltinmodule("_codecs")
    w_lookup = space.getattr(mod, space.wrap("lookup"))
    w_functuple = space.call_function(w_lookup, w_encoding)
    w_encoder = space.getitem(w_functuple, space.wrap(0))
    space.sys.w_default_encoder = w_encoder    # cache it
    return w_encoder

if sys.platform == "win32":
    base_encoding = "mbcs"
elif sys.platform == "darwin":
    base_encoding = "utf-8"
else:
    base_encoding = None

def _getfilesystemencoding(space):
    if (space.config.translation.type_system == 'ootype'):
        # XXX: fix this for ootype
        return base_encoding
    #
    encoding = base_encoding
    if rlocale.HAVE_LANGINFO and rlocale.CODESET:
        oldlocale = rlocale.setlocale(rlocale.LC_CTYPE, None)
        rlocale.setlocale(rlocale.LC_CTYPE, "")
        loc_codeset = rlocale.nl_langinfo(rlocale.CODESET)
        if loc_codeset:
            codecmod = space.getbuiltinmodule('_codecs')
            w_res = space.call_function(space.getattr(codecmod,
                                                      space.wrap('lookup')),
                                        space.wrap(loc_codeset))
            if space.is_true(w_res):
                encoding = loc_codeset
    return encoding

def getfilesystemencoding(space):
    """Return the encoding used to convert Unicode filenames in
    operating system filenames.
    """
    if space.sys.filesystemencoding is None:
        space.sys.filesystemencoding = _getfilesystemencoding(space)
    return space.wrap(space.sys.filesystemencoding)
