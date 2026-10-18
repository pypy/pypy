import sys

def getdefaultencoding(space):
    """Return the current default string encoding used by the Unicode
implementation."""
    return space.newtext(space.sys.defaultencoding)

base_encoding = "utf-8"
if sys.platform == "win32":
    # PEP 529
    base_error = "surrogatepass"
else:
    base_error = "surrogateescape"

def getfilesystemencoding(space):
    """Return the encoding used to convert Unicode filenames in
    operating system filenames.
    """
    return space.newtext(base_encoding)


def getfilesystemencodeerrors(space):
    return space.newtext(base_error)
