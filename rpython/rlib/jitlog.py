
# generic parameters
MP_STR = (0x0, "s")
MP_INT = (0x0, "i")

# concrete parameters
MP_FILENAME = (0x1, "s")
MP_LINENO = (0x2, "i")
MP_INDEX = (0x4, "i")
MP_ENCLOSING = (0x8, "s")
MP_OPCODE = (0x10, "s")

def get_type(flag):
    pass

def returns(*args):
    """ Decorate your get_location function to specify the types.
        Use MP_* constant as parameters. An example impl for get_location
        would return the following:

        @returns(MP_FILENAME, MP_LINENO)
        def get_location(...):
            return ("a.py", 0)
    """
    def decor(method):
        method._loc_types = args
        return method
    return decor
