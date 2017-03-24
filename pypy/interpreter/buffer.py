from rpython.rlib.buffer import Buffer

class PyBuffer(Buffer):
    _immutable_ = True
