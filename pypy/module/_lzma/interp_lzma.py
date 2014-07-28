from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef

FORMAT_AUTO, FORMAT_XZ, FORMAT_ALONE, FORMAT_RAW = range(4)


class W_LZMACompressor(W_Root):
    pass

W_LZMACompressor.typedef = TypeDef("LZMACompressor",
)


class W_LZMADecompressor(W_Root):
    pass

W_LZMADecompressor.typedef = TypeDef("LZMADecompressor",
)


def encode_filter_properties(space, w_filter):
    """Return a bytes object encoding the options (properties) of the filter
       specified by *filter* (a dict).

    The result does not include the filter ID itself, only the options.
    """

def decode_filter_properties(space, w_filter_id, w_encoded_props):
    """Return a dict describing a filter with ID *filter_id*, and options
       (properties) decoded from the bytes object *encoded_props*.
    """
    
