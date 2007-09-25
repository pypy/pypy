
"""
Application-level definitions for the zlib module.

NOT_RPYTHON
"""

class error(Exception):
    """
    Raised by zlib operations.
    """


def compressobj(level=None):
    """
    compressobj([level]) -- Return a compressor object.

    Optional arg level is the compression level, in 1-9.
    """
    import zlib
    return zlib.Compress(level)



def decompressobj(wbits=None):
    """
    decompressobj([wbits]) -- Return a decompressor object.

    Optional arg wbits is the window buffer size.
    """
    import zlib
    return zlib.Decompress(wbits)


def compress(string, level=None):
    """
    compress(string[, level]) -- Returned compressed string.

    Optional arg level is the compression level, in 1-9.
    """
    compressor = compressobj(level)
    return compressor.compress(string) + compressor.flush()


def decompress(string, wbits=None, bufsize=None):
    """
    decompress(string[, wbits[, bufsize]]) -- Return decompressed string.

    Optional arg wbits is the window buffer size.  Optional arg bufsize is
    the initial output buffer size.
    """
    # XXX bufsize is ignored because it's basically useless.
    decompressor = decompressobj(wbits)
    return decompressor.decompress(string) + decompressor.flush()
