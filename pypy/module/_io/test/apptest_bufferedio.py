"""
App-level buffer-protocol tests for _io buffered IO.
"""


def test_readinto_holds_bytearray_export_during_read():
    # Bug 2: W_BufferedIOBase._readinto calls writebuf_w(w_buffer) which
    # acquires and immediately releases the bytearray export before calling
    # self.read().  If self.read() is a Python method (user-defined subclass),
    # the bytearray is unprotected during the read and can be resized, leaving
    # the raw pointer that writebuf_w returned pointing into stale memory.
    #
    # Correct behaviour (CPython): the export must be held for the entire
    # duration of the readinto call, preventing resize until the write to
    # w_buffer is complete.
    import _io

    locked_during_read = []

    class ResizingBuf(_io._BufferedIOBase):
        def __init__(self, target):
            self.target = target
        def read(self, n=-1):
            # _readinto called writebuf_w(target) before calling this method.
            # If the export was released too early, append succeeds (bug).
            try:
                self.target.append(0)
                self.target.pop()
                locked_during_read.append(False)   # bad: was not locked
            except BufferError:
                locked_during_read.append(True)    # good: was locked
            return b'\x00' * (n if n >= 0 else 4)

    out = bytearray(4)
    rb = ResizingBuf(out)
    rb.readinto(out)
    assert locked_during_read[0], (
        "bytearray must be locked (export held) during BufferedIOBase.readinto"
    )


def test_rwpair_uninitialized_closed_and_isatty():
    # .closed and .isatty() on an uninitialized BufferedRWPair
    # dereferenced a None writer and segfaulted
    import _io
    from pytest import raises
    o = _io.BufferedRWPair.__new__(_io.BufferedRWPair)
    with raises(ValueError):
        o.closed
    with raises(ValueError):
        o.isatty()
    # everything that consults .closed inherited the fault. These go
    # through _check_closed, which swallows the ValueError, so they
    # merely must not crash.
    iter(o)
    o.__enter__()
