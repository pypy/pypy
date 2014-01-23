
import struct


class error(Exception):
    pass


def _check_size(size):
    if size != 1 and size != 2 and size != 4:
         raise error("Size should be 1, 2 or 4")


def _check_params(length, size):
    _check_size(size)
    if length % size != 0:
        raise error("not a whole number of frames")


def getsample(cp, size, i):
    _check_params(len(cp), size)
    if not (0 <= i < len(cp) / size):
        raise error("Index out of range")
    if size == 1:
        return struct.unpack_from("B", buffer(cp)[i:])[0]
    elif size == 2:
        return struct.unpack_from("H", buffer(cp)[i * 2:])[0]
    elif size == 4:
        return struct.unpack_from("I", buffer(cp)[i * 4:])[0]
