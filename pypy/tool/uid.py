import struct

HUGEVAL = 256 ** struct.calcsize('P')


def fixid(result):
    if result < 0:
        result += HUGEVAL
    return result

def uid(obj):
    """
    Return the id of an object as an unsigned number so that its hex
    representation makes sense
    """
    return fixid(id(obj))
