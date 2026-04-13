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

def _getfilesystemencoding(space):
    """Return the filesystem encoding. Always utf-8 on PyPy."""
    return base_encoding

def getfilesystemencoding(space):
    """Return the encoding used to convert Unicode filenames in
    operating system filenames.
    """
    if space.sys.filesystemencoding is None:
        return space.newtext(base_encoding)
    return space.newtext(space.sys.filesystemencoding)


def getfilesystemencodeerrors(space):
    return space.newtext(base_error)
