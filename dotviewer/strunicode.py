RAW_ENCODING = "utf-8"
ENCODING_ERROR_HANDLING = "replace"


def forceunicode(name):
    """ returns `name` as unicode, even if it wasn't before  """
    return name if isinstance(name, unicode) else name.decode(RAW_ENCODING, ENCODING_ERROR_HANDLING)


def forcestr(name):
    """ returns `name` as string, even if it wasn't before  """
    return name if isinstance(name, str) else name.encode(RAW_ENCODING, ENCODING_ERROR_HANDLING)


def tryencode(name):
    """ returns `name` as encoded string if it was unicode before """
    return name.encode(RAW_ENCODING, ENCODING_ERROR_HANDLING) if isinstance(name, unicode) else name
