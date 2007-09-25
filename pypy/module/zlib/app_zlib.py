
"""
Application-level definitions for the zlib module.

NOT_RPYTHON
"""

class error(Exception):
    """
    Raised by zlib operations.
    """


# XXX the following should be moved to interp-level to avoid various overheads

def compress(string, *args):
    """
    compress(string[, level]) -- Returned compressed string.

    Optional arg level is the compression level, in 1-9.
    """
    import zlib
    compressor = zlib.compressobj(*args)
    return compressor.compress(string) + compressor.flush()


def decompress(string, *args):
    """
    decompress(string[, wbits[, bufsize]]) -- Return decompressed string.

    Optional arg wbits is the window buffer size.  Optional arg bufsize is
    the initial output buffer size.
    """
    # XXX bufsize is not accepted by this version but it's basically useless.
    import zlib
    decompressor = zlib.decompressobj(*args)
    return decompressor.decompress(string) + decompressor.flush()
