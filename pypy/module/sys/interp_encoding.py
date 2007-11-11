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
    space.sys.defaultencoding = encoding
