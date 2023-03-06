import _io
import sys

def text_encoding(encoding, stacklevel=2):
    """
    A helper function to choose the text encoding.

    When encoding is not None, just return it.
    Otherwise, return the default text encoding (i.e. "locale").

    This function emits an EncodingWarning if *encoding* is None and
    sys.flags.warn_default_encoding is non-zero.

    This can be used in APIs with an encoding=None parameter
    that pass it to TextIOWrapper or open.
    However, please consider using encoding="utf-8" for new APIs.
    """
    if encoding is None:
        encoding = "locale"
        if sys.flags.warn_default_encoding != 0:
            import warnings
            warnings.warn("'encoding' argument not specified.",
                          EncodingWarning, stacklevel + 1)
    return encoding
