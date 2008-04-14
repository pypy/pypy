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
    w_encoding = space.wrap(space.sys.defaultencoding)
    mod = space.getbuiltinmodule("_codecs")
    w_lookup = space.getattr(mod, space.wrap("lookup"))
    w_functuple = space.call_function(w_lookup, w_encoding)
    w_encoder = space.getitem(w_functuple, space.wrap(0))
    space.sys.w_default_encoder = w_encoder    # cache it
    return w_encoder
