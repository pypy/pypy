import py
import os
import stat
import errno
from pypy.rlib import streamio
from pypy.rlib.rarithmetic import r_longlong
from pypy.rlib.rstring import StringBuilder
from pypy.module._file.interp_stream import (W_AbstractStream, StreamErrors,
    wrap_streamerror, wrap_oserror_as_ioerror)
from pypy.module.posix.interp_posix import dispatch_filename
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
    interp_attrproperty, make_weakref_descr, interp_attrproperty_w)
from pypy.interpreter.gateway import interp2app, unwrap_spec


class W_File(W_AbstractStream):
    """An interp-level file object.  This implements the same interface than
    the app-level files, with the following differences:

      * method names are prefixed with 'file_'
      * the 'normal' app-level constructor is implemented by file___init__().
      * the methods with the 'direct_' prefix should be used if the caller
          locks and unlocks the file itself, and takes care of StreamErrors.
    """

    # Default values until the file is successfully opened
    stream   = None
    w_name   = None
    mode     = "<uninitialized file>"
    binary   = False
    softspace= 0     # Required according to file object docs
    encoding = None
    errors   = None
    fd       = -1

    newlines = 0     # Updated when the stream is closed

    def __init__(self, space):
        self.space = space

    def __del__(self):
        # assume that the file and stream objects are only visible in the
        # thread that runs __del__, so no race condition should be possible
        self.clear_all_weakrefs()
        if self.stream is not None:
            self.enqueue_for_destruction(self.space, W_File.destructor,
                                         'close() method of ')

    def destructor(self):
        assert isinstance(self, W_File)
        try:
            self.direct_close()
        except StreamErrors, e:
            operr = wrap_streamerror(self.space, e, self.w_name)
            raise operr

    def fdopenstream(self, stream, fd, mode, w_name=None):
        self.fd = fd
        self.mode = mode
        self.binary = "b" in mode
        if w_name is not None:
            self.w_name = w_name
        self.stream = stream
        if stream.flushable():
            getopenstreams(self.space)[stream] = None

    def check_not_dir(self, fd):
        try:
            st = os.fstat(fd)
        except OSError:
            pass
        else:
            if (stat.S_ISDIR(st[0])):
                ose = OSError(errno.EISDIR, '')
                raise wrap_oserror_as_ioerror(self.space, ose, self.w_name)

    def check_mode_ok(self, mode):
        if (not mode or mode[0] not in ['r', 'w', 'a', 'U'] or
            ('U' in mode and ('w' in mode or 'a' in mode))):
            space = self.space
            raise operationerrfmt(space.w_ValueError,
                                  "invalid mode: '%s'", mode)

    def check_closed(self):
        if self.stream is None:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("I/O operation on closed file")
            )

    def getstream(self):
        """Return self.stream or raise an app-level ValueError if missing
        (i.e. if the file is closed)."""
        self.check_closed()
        return self.stream

    def _when_reading_first_flush(self, otherfile):
        """Flush otherfile before reading from self."""
        self.stream = streamio.CallbackReadFilter(self.stream,
                                                  otherfile._try_to_flush)

    def _try_to_flush(self):
        stream = self.stream
        if stream is not None:
            stream.flush()

    # ____________________________________________________________
    #
    # The 'direct_' methods assume that the caller already acquired the
    # file lock.  They don't convert StreamErrors to OperationErrors, too.

    @unwrap_spec(mode=str, buffering=int)
    def direct___init__(self, w_name, mode='r', buffering=-1):
        self.direct_close()
        self.w_name = w_name
        self.check_mode_ok(mode)
        stream = dispatch_filename(streamio.open_file_as_stream)(
            self.space, w_name, mode, buffering)
        fd = stream.try_to_find_file_descriptor()
        self.check_not_dir(fd)
        self.fdopenstream(stream, fd, mode)

    def direct___enter__(self):
        self.check_closed()
        return self

    def file__exit__(self, __args__):
        """__exit__(*excinfo) -> None. Closes the file."""
        self.space.call_method(self, "close")
        # can't return close() value
        return None

    def direct_fdopen(self, fd, mode='r', buffering=-1):
        self.direct_close()
        self.w_name = self.space.wrap('<fdopen>')
        self.check_mode_ok(mode)
        stream = streamio.fdopen_as_stream(fd, mode, buffering)
        self.fdopenstream(stream, fd, mode)

    def direct_close(self):
        space = self.space
        stream = self.stream
        if stream is not None:
            self.newlines = self.stream.getnewlines()
            self.stream = None
            self.fd = -1
            openstreams = getopenstreams(self.space)
            try:
                del openstreams[stream]
            except KeyError:
                pass
            stream.close()

    def direct_fileno(self):
        self.getstream()    # check if the file is still open
        return self.fd

    def direct_flush(self):
        self.getstream().flush()

    def direct_next(self):
        line = self.getstream().readline()
        if line == '':
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        return line

    @unwrap_spec(n=int)
    def direct_read(self, n=-1):
        stream = self.getstream()
        if n < 0:
            return stream.readall()
        else:
            result = StringBuilder(n)
            while n > 0:
                data = stream.read(n)
                if not data:
                    break
                n -= len(data)
                result.append(data)
            return result.build()

    @unwrap_spec(size=int)
    def direct_readline(self, size=-1):
        stream = self.getstream()
        if size < 0:
            return stream.readline()
        else:
            # very inefficient unless there is a peek()
            result = []
            while size > 0:
                # "peeks" on the underlying stream to see how many chars
                # we can safely read without reading past an end-of-line
                peeked = stream.peek()
                pn = peeked.find("\n", 0, size)
                if pn < 0:
                    pn = min(size-1, len(peeked))
                c = stream.read(pn + 1)
                if not c:
                    break
                result.append(c)
                if c.endswith('\n'):
                    break
                size -= len(c)
            return ''.join(result)

    @unwrap_spec(size=int)
    def direct_readlines(self, size=0):
        stream = self.getstream()
        # NB. this implementation is very inefficient for unbuffered
        # streams, but ok if stream.readline() is efficient.
        if size <= 0:
            result = []
            while True:
                line = stream.readline()
                if not line:
                    break
                result.append(line)
                size -= len(line)
        else:
            result = []
            while size > 0:
                line = stream.readline()
                if not line:
                    break
                result.append(line)
                size -= len(line)
        return result

    @unwrap_spec(offset=r_longlong, whence=int)
    def direct_seek(self, offset, whence=0):
        self.getstream().seek(offset, whence)

    def direct_tell(self):
        return self.getstream().tell()

    def direct_truncate(self, w_size=None):  # note: a wrapped size!
        stream = self.getstream()
        space = self.space
        if w_size is None or space.is_w(w_size, space.w_None):
            size = stream.tell()
        else:
            size = space.r_longlong_w(w_size)
        stream.truncate(size)

    def direct_write(self, w_data):
        space = self.space
        if not self.binary and space.isinstance_w(w_data, space.w_unicode):
            w_data = space.call_method(w_data, "encode", space.wrap(self.encoding), space.wrap(self.errors))
        data = space.bufferstr_w(w_data)
        self.do_direct_write(data)

    def do_direct_write(self, data):
        self.softspace = 0
        self.getstream().write(data)

    def direct___iter__(self):
        self.getstream()
        return self
    direct_xreadlines = direct___iter__

    def direct_isatty(self):
        self.getstream()    # check if the file is still open
        return os.isatty(self.fd)

    # ____________________________________________________________
    #
    # The 'file_' methods are the one exposed to app-level.

    def file_fdopen(self, fd, mode="r", buffering=-1):
        try:
            self.direct_fdopen(fd, mode, buffering)
        except StreamErrors, e:
            raise wrap_streamerror(self.space, e, self.w_name)

    _exposed_method_names = []

    def _decl(class_scope, name, docstring,
              wrapresult="space.wrap(result)"):
        # hack hack to build a wrapper around the direct_xxx methods.
        # The wrapper adds lock/unlock calls and a space.wrap() on
        # the result, conversion of stream errors to OperationErrors,
        # and has the specified docstring and unwrap_spec.
        direct_fn = class_scope['direct_' + name]
        co = direct_fn.func_code
        argnames = co.co_varnames[:co.co_argcount]
        defaults = direct_fn.func_defaults or ()
        unwrap_spec = getattr(direct_fn, 'unwrap_spec', None)

        args = []
        for i, argname in enumerate(argnames):
            try:
                default = defaults[-len(argnames) + i]
            except IndexError:
                args.append(argname)
            else:
                args.append('%s=%r' % (argname, default))
        sig = ', '.join(args)
        assert argnames[0] == 'self'
        callsig = ', '.join(argnames[1:])

        src = py.code.Source("""
            def file_%(name)s(%(sig)s):
                %(docstring)r
                space = self.space
                self.lock()
                try:
                    try:
                        result = self.direct_%(name)s(%(callsig)s)
                    except StreamErrors, e:
                        raise wrap_streamerror(space, e, self.w_name)
                finally:
                    self.unlock()
                return %(wrapresult)s
        """ % locals())
        exec str(src) in globals(), class_scope
        if unwrap_spec is not None:
            class_scope['file_' + name].unwrap_spec = unwrap_spec
        class_scope['_exposed_method_names'].append(name)


    _decl(locals(), "__init__", """Opens a file.""")

    _decl(locals(), "__enter__", """__enter__() -> self.""")

    _decl(locals(), "close",
        """close() -> None or (perhaps) an integer.  Close the file.

Sets data attribute .closed to True.  A closed file cannot be used for
further I/O operations.  close() may be called more than once without
error.  Some kinds of file objects (for example, opened by popen())
may return an exit status upon closing.""")
        # NB. close() needs to use the stream lock to avoid double-closes or
        # close-while-another-thread-uses-it.


    _decl(locals(), "fileno",
        '''fileno() -> integer "file descriptor".

This is needed for lower-level file interfaces, such os.read().''')

    _decl(locals(), "flush",
        """flush() -> None.  Flush the internal I/O buffer.""")

    _decl(locals(), "isatty",
        """isatty() -> true or false.  True if the file is connected to a tty device.""")

    _decl(locals(), "next",
        """next() -> the next line in the file, or raise StopIteration""")

    _decl(locals(), "read",
        """read([size]) -> read at most size bytes, returned as a string.

If the size argument is negative or omitted, read until EOF is reached.
Notice that when in non-blocking mode, less data than what was requested
may be returned, even if no size parameter was given.""")

    _decl(locals(), "readline",
        """readline([size]) -> next line from the file, as a string.

Retain newline.  A non-negative size argument limits the maximum
number of bytes to return (an incomplete line may be returned then).
Return an empty string at EOF.""")

    _decl(locals(), "readlines",
        """readlines([size]) -> list of strings, each a line from the file.

Call readline() repeatedly and return a list of the lines so read.
The optional size argument, if given, is an approximate bound on the
total number of bytes in the lines returned.""",
        wrapresult = "wrap_list_of_str(space, result)")

    _decl(locals(), "seek",
        """seek(offset[, whence]) -> None.  Move to new file position.

Argument offset is a byte count.  Optional argument whence defaults to
0 (offset from start of file, offset should be >= 0); other values are 1
(move relative to current position, positive or negative), and 2 (move
relative to end of file, usually negative, although many platforms allow
seeking beyond the end of a file).  If the file is opened in text mode,
only offsets returned by tell() are legal.  Use of other offsets causes
undefined behavior.
Note that not all file objects are seekable.""")

    _decl(locals(), "tell",
        "tell() -> current file position, an integer (may be a long integer).")

    _decl(locals(), "truncate",
        """truncate([size]) -> None.  Truncate the file to at most size bytes.

Size defaults to the current file position, as returned by tell().""")

    _decl(locals(), "write",
        """write(str) -> None.  Write string str to file.

Note that due to buffering, flush() or close() may be needed before
the file on disk reflects the data written.""")

    _decl(locals(), "__iter__",
        """Iterating over files, as in 'for line in f:', returns each line of
the file one by one.""")

    _decl(locals(), "xreadlines",
        """xreadlines() -> returns self.

For backward compatibility. File objects now include the performance
optimizations previously implemented in the xreadlines module.""")

    def file__repr__(self):
        if self.stream is None:
            head = "closed"
        else:
            head = "open"
        info = "%s file %s, mode '%s'" % (
            head,
            self.getdisplayname(),
            self.mode)
        return self.getrepr(self.space, info)

    def getdisplayname(self):
        w_name = self.w_name
        if w_name is None:
            return '?'
        elif self.space.is_true(self.space.isinstance(w_name,
                                                      self.space.w_str)):
            return "'%s'" % self.space.str_w(w_name)
        else:
            return self.space.str_w(self.space.repr(w_name))

    def file_writelines(self, w_lines):
        """writelines(sequence_of_strings) -> None.  Write the strings to the file.

Note that newlines are not added.  The sequence can be any iterable object
producing strings. This is equivalent to calling write() for each string."""

        space = self.space
        self.check_closed()
        w_iterator = space.iter(w_lines)
        while True:
            try:
                w_line = space.next(w_iterator)
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break  # done
            self.file_write(w_line)

    def file_readinto(self, w_rwbuffer):
        """readinto() -> Undocumented.  Don't use this; it may go away."""
        # XXX not the most efficient solution as it doesn't avoid the copying
        space = self.space
        rwbuffer = space.rwbuffer_w(w_rwbuffer)
        w_data = self.file_read(rwbuffer.getlength())
        data = space.str_w(w_data)
        rwbuffer.setslice(0, data)
        return space.wrap(len(data))


# ____________________________________________________________


def descr_file__new__(space, w_subtype, __args__):
    file = space.allocate_instance(W_File, w_subtype)
    W_File.__init__(file, space)
    return space.wrap(file)

@unwrap_spec(fd=int, mode=str, buffering=int)
def descr_file_fdopen(space, w_subtype, fd, mode='r', buffering=-1):
    file = space.allocate_instance(W_File, w_subtype)
    W_File.__init__(file, space)
    file.file_fdopen(fd, mode, buffering)
    return space.wrap(file)

def descr_file_closed(space, file):
    return space.wrap(file.stream is None)

def descr_file_newlines(space, file):
    if file.stream:
        newlines = file.stream.getnewlines()
    else:
        newlines = file.newlines
    if newlines == 0:
        return space.w_None
    elif newlines == 1:
        return space.wrap("\r")
    elif newlines == 2:
        return space.wrap("\n")
    elif newlines == 4:
        return space.wrap("\r\n")
    result = []
    if newlines & 1:
        result.append(space.wrap('\r'))
    if newlines & 2:
        result.append(space.wrap('\n'))
    if newlines & 4:
        result.append(space.wrap('\r\n'))
    return space.newtuple(result[:])

def descr_file_softspace(space, file):
    return space.wrap(file.softspace)

def descr_file_setsoftspace(space, file, w_newvalue):
    file.softspace = space.int_w(w_newvalue)

# ____________________________________________________________

W_File.typedef = TypeDef(
    "file",
    __doc__ = """file(name[, mode[, buffering]]) -> file object

Open a file.  The mode can be 'r', 'w' or 'a' for reading (default),
writing or appending.  The file will be created if it doesn't exist
when opened for writing or appending; it will be truncated when
opened for writing.  Add a 'b' to the mode for binary files.
Add a '+' to the mode to allow simultaneous reading and writing.
If the buffering argument is given, 0 means unbuffered, 1 means line
buffered, and larger numbers specify the buffer size.
Add a 'U' to mode to open the file for input with universal newline
support.  Any line ending in the input file will be seen as a '\n'
in Python.  Also, a file so opened gains the attribute 'newlines';
the value for this attribute is one of None (no newline read yet),
'\r', '\n', '\r\n' or a tuple containing all the newline types seen.

Note:  open() is an alias for file().
""",
    __new__  = interp2app(descr_file__new__),
    fdopen   = interp2app(descr_file_fdopen, as_classmethod=True),
    name     = interp_attrproperty_w('w_name', cls=W_File, doc="file name"),
    mode     = interp_attrproperty('mode', cls=W_File,
                              doc = "file mode ('r', 'U', 'w', 'a', "
                                    "possibly with 'b' or '+' added)"),
    encoding = interp_attrproperty('encoding', cls=W_File),
    errors = interp_attrproperty('errors', cls=W_File),
    closed   = GetSetProperty(descr_file_closed, cls=W_File,
                              doc="True if the file is closed"),
    newlines = GetSetProperty(descr_file_newlines, cls=W_File,
                              doc="end-of-line convention used in this file"),
    softspace= GetSetProperty(descr_file_softspace,
                              descr_file_setsoftspace,
                              cls=W_File,
                              doc="Support for 'print'."),
    __repr__ = interp2app(W_File.file__repr__),
    readinto = interp2app(W_File.file_readinto),
    writelines = interp2app(W_File.file_writelines),
    __exit__ = interp2app(W_File.file__exit__),
    __weakref__ = make_weakref_descr(W_File),
    **dict([(name, interp2app(getattr(W_File, 'file_' + name)))
                for name in W_File._exposed_method_names])
    )

# ____________________________________________________________

def wrap_list_of_str(space, lst):
    return space.newlist([space.wrap(s) for s in lst])

class FileState:
    def __init__(self, space):
        self.openstreams = {}

def getopenstreams(space):
    return space.fromcache(FileState).openstreams


@unwrap_spec(file=W_File, encoding="str_or_None", errors="str_or_None")
def set_file_encoding(space, file, encoding=None, errors=None):
    file.encoding = encoding
    file.errors = errors
