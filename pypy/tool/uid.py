import struct

# This is temporary hack to run PyPy on PyPy
# until PyPy's struct module handle P format character.

#HUGEVAL = 256 ** struct.calcsize('P')
HUGEVAL = 0

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
