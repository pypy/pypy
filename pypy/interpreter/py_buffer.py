"""
CPython-style Py_buffer: a passive description struct.

The exporter object owns the release logic via its bf_getbuffer/
bf_releasebuffer methods on W_Root (named after CPython's
tp_as_buffer->bf_getbuffer/bf_releasebuffer).  Slicing, casting, and
readonly views are produced by adjusting fields in a fresh Py_buffer
rather than by stacking wrapper classes.

This is the prototype scaffolding for the port described in
PLAN_py_buffer_struct.md.  Initially we keep using rpython.rlib.buffer.Buffer
for the actual data backing, since it already abstracts over string / list /
raw memory.  The substantive change is moving releasebuffer onto the
exporter object and treating Py_buffer itself as data-only.
"""

from rpython.rlib.buffer import Buffer
from pypy.interpreter.baseobjspace import W_Root


class W_BufferExporter(W_Root):
    """Base class for W_Root subclasses that implement the buffer protocol.

    Inheriting from this (rather than directly from W_Root) keeps
    bf_getbuffer/bf_releasebuffer out of W_Root's vtable, so the ~10
    buffer-exporting types bear the cost instead of every Python object.
    """
    _attrs_ = []

    def bf_getbuffer(self, space, view, flags):
        from pypy.interpreter.buffer import BufferInterfaceNotFound
        raise BufferInterfaceNotFound

    def bf_releasebuffer(self, space, view):
        pass


class Py_buffer(object):
    """Passive description of an exported buffer.

    Mirrors CPython's Py_buffer struct.  Filled in by the exporter's
    bf_getbuffer method; released via space.release_py_buffer(view)
    which dispatches back to view.obj.bf_releasebuffer.

    Fields:
      obj      : the W_Root that owns this export.  Single owning reference.
      buf      : an rpython.rlib.buffer.Buffer providing the actual data
                 access.  May be None for purely descriptive views.
      length   : total size in bytes.
      readonly : True if the export is read-only.
      itemsize : bytes per element (matches CPython).
      ndim     : number of dimensions.
      format   : struct-style format string (e.g. 'B').
      shape    : list of per-dimension item counts, or None.
      strides  : list of per-dimension byte strides, or None.
    """
    _attrs_ = ['obj', 'buf', 'length', 'readonly', 'itemsize',
               'ndim', 'format', 'shape', 'strides']

    def __init__(self):
        self.obj = None
        self.buf = None
        self.length = -1
        self.readonly = True
        self.itemsize = 1
        self.ndim = 1
        self.format = 'B'
        self.shape = None
        self.strides = None


def fill_py_buffer_1d(view, obj, buf, readonly, itemsize=1, format='B'):
    """Populate a Py_buffer for a simple 1-D contiguous export.

    The vast majority of exporters are 1-D, contiguous, byte-oriented
    views; this helper fills all the boilerplate fields from the given
    owner, backing Buffer, readonly flag, and optional item metadata.
    """
    length = buf.getlength()
    view.obj = obj
    view.buf = buf
    view.length = length
    view.readonly = readonly
    view.itemsize = itemsize
    view.ndim = 1
    view.format = format
    view.shape = [length // itemsize if itemsize > 0 else length]
    view.strides = [itemsize]


def py_buffer_as_str(view):
    """Whole-buffer contents as an interp-level string."""
    return view.buf.as_str()


def py_buffer_getbytes(view, start, size):
    """Read `size` bytes starting at byte offset `start`."""
    return view.buf[start:start + size]


def py_buffer_setbytes(view, start, data):
    """Write `data` starting at byte offset `start`."""
    assert not view.readonly
    view.buf.setslice(start, data)


def py_buffer_as_readbuf(view):
    """Return an rpython.rlib.buffer.Buffer for read access."""
    buf = view.buf
    assert buf is not None
    return buf


def py_buffer_as_writebuf(view):
    """Return an rpython.rlib.buffer.Buffer for write access."""
    assert not view.readonly
    buf = view.buf
    assert buf is not None
    return buf
