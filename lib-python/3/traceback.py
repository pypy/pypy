"""Extract, format and print information about Python stack traces."""

import collections
import itertools
import linecache
import sys

__all__ = ['extract_stack', 'extract_tb', 'format_exception',
           'format_exception_only', 'format_list', 'format_stack',
           'format_tb', 'print_exc', 'format_exc', 'print_exception',
           'print_last', 'print_stack', 'print_tb', 'clear_frames',
           'FrameSummary', 'StackSummary', 'TracebackException',
           'walk_stack', 'walk_tb']

#
# Formatting and printing lists of traceback lines.
#

def print_list(extracted_list, file=None):
    """Print the list of tuples as returned by extract_tb() or
    extract_stack() as a formatted stack trace to the given file."""
    if file is None:
        file = sys.stderr
    for item in StackSummary.from_list(extracted_list).format():
        print(item, file=file, end="")

def format_list(extracted_list):
    """Format a list of tuples or FrameSummary objects for printing.

    Given a list of tuples or FrameSummary objects as returned by
    extract_tb() or extract_stack(), return a list of strings ready
    for printing.

    Each string in the resulting list corresponds to the item with the
    same index in the argument list.  Each string ends in a newline;
    the strings may contain internal newlines as well, for those items
    whose source text line is not None.
    """
    return StackSummary.from_list(extracted_list).format()

#
# Printing and Extracting Tracebacks.
#

def print_tb(tb, limit=None, file=None):
    """Print up to 'limit' stack trace entries from the traceback 'tb'.

    If 'limit' is omitted or None, all entries are printed.  If 'file'
    is omitted or None, the output goes to sys.stderr; otherwise
    'file' should be an open file or file-like object with a write()
    method.
    """
    print_list(extract_tb(tb, limit=limit), file=file)

def format_tb(tb, limit=None):
    """A shorthand for 'format_list(extract_tb(tb, limit))'."""
    return extract_tb(tb, limit=limit).format()

def extract_tb(tb, limit=None):
    """
    Return a StackSummary object representing a list of
    pre-processed entries from traceback.

    This is useful for alternate formatting of stack traces.  If
    'limit' is omitted or None, all entries are extracted.  A
    pre-processed stack trace entry is a FrameSummary object
    containing attributes filename, lineno, name, and line
    representing the information that is usually printed for a stack
    trace.  The line is a string with leading and trailing
    whitespace stripped; if the source is not available it is None.
    """
    return StackSummary.extract(walk_tb(tb), limit=limit)

#
# Exception formatting and output.
#

_cause_message = (
    "\nThe above exception was the direct cause "
    "of the following exception:\n\n")

_context_message = (
    "\nDuring handling of the above exception, "
    "another exception occurred:\n\n")


class _Sentinel:
    def __repr__(self):
        return "<implicit>"

_sentinel = _Sentinel()

def _parse_value_tb(exc, value, tb):
    if (value is _sentinel) != (tb is _sentinel):
        raise ValueError("Both or neither of value and tb must be given")
    if value is tb is _sentinel:
        if exc is not None:
            return exc, exc.__traceback__
        else:
            return None, None
    return value, tb


def print_exception(exc, /, value=_sentinel, tb=_sentinel, limit=None, \
                    file=None, chain=True):
    """Print exception up to 'limit' stack trace entries from 'tb' to 'file'.

    This differs from print_tb() in the following ways: (1) if
    traceback is not None, it prints a header "Traceback (most recent
    call last):"; (2) it prints the exception type and value after the
    stack trace; (3) if type is SyntaxError and value has the
    appropriate format, it prints the line where the syntax error
    occurred with a caret on the next line indicating the approximate
    position of the error.
    """
    value, tb = _parse_value_tb(exc, value, tb)
    if file is None:
        file = sys.stderr
    te = TracebackException(type(value), value, tb, limit=limit, compact=True)
    for line in te.format(chain=chain):
        print(line, file=file, end="")


def format_exception(exc, /, value=_sentinel, tb=_sentinel, limit=None, \
                     chain=True):
    """Format a stack trace and the exception information.

    The arguments have the same meaning as the corresponding arguments
    to print_exception().  The return value is a list of strings, each
    ending in a newline and some containing internal newlines.  When
    these lines are concatenated and printed, exactly the same text is
    printed as does print_exception().
    """
    value, tb = _parse_value_tb(exc, value, tb)
    te = TracebackException(type(value), value, tb, limit=limit, compact=True)
    return list(te.format(chain=chain))


def format_exception_only(exc, /, value=_sentinel):
    """Format the exception part of a traceback.

    The return value is a list of strings, each ending in a newline.

    Normally, the list contains a single string; however, for
    SyntaxError exceptions, it contains several lines that (when
    printed) display detailed information about where the syntax
    error occurred.

    The message indicating which exception occurred is always the last
    string in the list.

    """
    if value is _sentinel:
        value = exc
    te = TracebackException(type(value), value, None, compact=True)
    return list(te.format_exception_only())


# -- not official API but folk probably use these two functions.

def _format_final_exc_line(etype, value):
    valuestr = _some_str(value)
    if value is None or not valuestr:
        line = "%s\n" % etype
    else:
        line = "%s: %s\n" % (etype, valuestr)
    return line

def _some_str(value):
    try:
        return str(value)
    except:
        return '<unprintable %s object>' % type(value).__name__

# --

def print_exc(limit=None, file=None, chain=True):
    """Shorthand for 'print_exception(*sys.exc_info(), limit, file)'."""
    print_exception(*sys.exc_info(), limit=limit, file=file, chain=chain)

def format_exc(limit=None, chain=True):
    """Like print_exc() but return a string."""
    return "".join(format_exception(*sys.exc_info(), limit=limit, chain=chain))

def print_last(limit=None, file=None, chain=True):
    """This is a shorthand for 'print_exception(sys.last_type,
    sys.last_value, sys.last_traceback, limit, file)'."""
    if not hasattr(sys, "last_type"):
        raise ValueError("no last exception")
    print_exception(sys.last_type, sys.last_value, sys.last_traceback,
                    limit, file, chain)

#
# Printing and Extracting Stacks.
#

def print_stack(f=None, limit=None, file=None):
    """Print a stack trace from its invocation point.

    The optional 'f' argument can be used to specify an alternate
    stack frame at which to start. The optional 'limit' and 'file'
    arguments have the same meaning as for print_exception().
    """
    if f is None:
        f = sys._getframe().f_back
    print_list(extract_stack(f, limit=limit), file=file)


def format_stack(f=None, limit=None):
    """Shorthand for 'format_list(extract_stack(f, limit))'."""
    if f is None:
        f = sys._getframe().f_back
    return format_list(extract_stack(f, limit=limit))


def extract_stack(f=None, limit=None):
    """Extract the raw traceback from the current stack frame.

    The return value has the same format as for extract_tb().  The
    optional 'f' and 'limit' arguments have the same meaning as for
    print_stack().  Each item in the list is a quadruple (filename,
    line number, function name, text), and the entries are in order
    from oldest to newest stack frame.
    """
    if f is None:
        f = sys._getframe().f_back
    stack = StackSummary.extract(walk_stack(f), limit=limit)
    stack.reverse()
    return stack


def clear_frames(tb):
    "Clear all references to local variables in the frames of a traceback."
    while tb is not None:
        try:
            tb.tb_frame.clear()
        except RuntimeError:
            # Ignore the exception raised if the frame is still executing.
            pass
        tb = tb.tb_next


class FrameSummary:
    """A single frame from a traceback.

    - :attr:`filename` The filename for the frame.
    - :attr:`lineno` The line within filename for the frame that was
      active when the frame was captured.
    - :attr:`name` The name of the function or method that was executing
      when the frame was captured.
    - :attr:`line` The text from the linecache module for the
      of code that was running when the frame was captured.
    - :attr:`locals` Either None if locals were not supplied, or a dict
      mapping the name to the repr() of the variable.
    """

    def __init__(self, filename, lineno, name, *, lookup_line=True,
            locals=None, line=None):
        """Construct a FrameSummary.

        :param lookup_line: If True, `linecache` is consulted for the source
            code line. Otherwise, the line will be looked up when first needed.
        :param locals: If supplied the frame locals, which will be captured as
            object representations.
        :param line: If provided, use this instead of looking up the line in
            the linecache.
        """
        self.filename = filename
        self.lineno = lineno
        self.name = name
        self._line = line
        if lookup_line:
            self.line
        self.locals = {k: repr(v) for k, v in locals.items()} if locals else None

    def __eq__(self, other):
        if isinstance(other, FrameSummary):
            return (self.filename == other.filename and
                    self.lineno == other.lineno and
                    self.name == other.name and
                    self.locals == other.locals)
        if isinstance(other, tuple):
            return (self.filename, self.lineno, self.name, self.line) == other
        return NotImplemented

    def __getitem__(self, pos):
        return (self.filename, self.lineno, self.name, self.line)[pos]

    def __iter__(self):
        return iter([self.filename, self.lineno, self.name, self.line])

    def __repr__(self):
        return "<FrameSummary file {filename}, line {lineno} in {name}>".format(
            filename=self.filename, lineno=self.lineno, name=self.name)

    def __len__(self):
        return 4

    @property
    def line(self):
        if self._line is None:
            if self.lineno is None:
                return None
            self._line = linecache.getline(self.filename, self.lineno)
        return self._line.strip()

# PyPy modification: adapt to the changes in extract to use a helper function
def walk_stack(f):
    """Walk a stack yielding the frame and line number for each frame.

    This will follow f.f_back from the given frame. If no frame is given, the
    current stack is used. Usually used with StackSummary.extract.
    """
    if f is None:
        f = sys._getframe().f_back
    return _walk_stack(f)

def _walk_stack(f):
    while f is not None:
        yield f, f.f_lineno
        f = f.f_back
# end PyPy modification


def walk_tb(tb):
    """Walk a traceback yielding the frame and line number for each frame.

    This will follow tb.tb_next (and thus is in the opposite order to
    walk_stack). Usually used with StackSummary.extract.
    """
    while tb is not None:
        yield tb.tb_frame, tb.tb_lineno
        tb = tb.tb_next

# PyPy 3 change: precise traceback ranges
def _walk_tb_with_lasti(tb):
    while tb is not None:
        yield tb.tb_frame, tb.tb_lineno, getattr(tb, 'tb_lasti', None)
        tb = tb.tb_next

def _byte_offset_to_character_offset(str, offset):
    as_utf8 = str.encode('utf-8')
    if offset > len(as_utf8):
        offset = len(as_utf8)

    return len(as_utf8[:offset + 1].decode("utf-8"))

def _default_frame_gen(frame_gen):
    for frame, lineno in frame_gen:
        yield frame, lineno, None

def _default_frame_constructor(f, last_i, *args, **kwargs):
    return FrameSummary(*args, **kwargs)
# End PyPy 3 change


_RECURSIVE_CUTOFF = 3 # Also hardcoded in traceback.c.

class StackSummary(list):
    """A stack of frames."""

    @classmethod
    def extract(klass, frame_gen, *, limit=None, lookup_lines=True,
            capture_locals=False):
        """Create a StackSummary from a traceback or stack object.

        :param frame_gen: A generator that yields (frame, lineno) tuples to
            include in the stack.
        :param limit: None to include all frames or the number of frames to
            include.
        :param lookup_lines: If True, lookup lines for each frame immediately,
            otherwise lookup is deferred until the frame is rendered.
        :param capture_locals: If True, the local variables from each frame will
            be captured as object representations into the FrameSummary.
        """

        # PyPy 3 change: precise traceback ranges
        return klass._extract_from_extended_frame_gen(
            _default_frame_gen(frame_gen), _default_frame_constructor, limit=limit, lookup_lines=lookup_lines,
            capture_locals=capture_locals)

    @classmethod
    def _extract_from_extended_frame_gen(klass, frame_gen, frame_constructor, *, limit=None,
            lookup_lines=True, capture_locals=False):
        # End PyPy 3 change
        if limit is None:
            limit = getattr(sys, 'tracebacklimit', None)
            if limit is not None and limit < 0:
                limit = 0
        if limit is not None:
            if limit >= 0:
                frame_gen = itertools.islice(frame_gen, limit)
            else:
                frame_gen = collections.deque(frame_gen, maxlen=-limit)

        result = klass()
        fnames = set()
        for f, lineno, last_i in frame_gen:
            co = f.f_code
            filename = co.co_filename
            name = co.co_name

            fnames.add(filename)
            linecache.lazycache(filename, f.f_globals)
            # Must defer line lookups until we have called checkcache.
            if capture_locals:
                f_locals = f.f_locals
            else:
                f_locals = None
            result.append(frame_constructor(f, last_i,
                filename, lineno, name, lookup_line=False, locals=f_locals))
        for filename in fnames:
            linecache.checkcache(filename)
        # If immediate lookup was desired, trigger lookups now.
        if lookup_lines:
            for f in result:
                f.line
        return result

    @classmethod
    def from_list(klass, a_list):
        """
        Create a StackSummary object from a supplied list of
        FrameSummary objects or old-style list of tuples.
        """
        # While doing a fast-path check for isinstance(a_list, StackSummary) is
        # appealing, idlelib.run.cleanup_traceback and other similar code may
        # break this by making arbitrary frames plain tuples, so we need to
        # check on a frame by frame basis.
        result = StackSummary()
        for frame in a_list:
            if isinstance(frame, FrameSummary):
                result.append(frame)
            else:
                filename, lineno, name, line = frame
                result.append(FrameSummary(filename, lineno, name, line=line))
        return result

    def format(self):
        """Format the stack ready for printing.

        Returns a list of strings ready for printing.  Each string in the
        resulting list corresponds to a single frame from the stack.
        Each string ends in a newline; the strings may contain internal
        newlines as well, for those items with source text lines.

        For long sequences of the same frame and line, the first few
        repetitions are shown, followed by a summary line stating the exact
        number of further repetitions.
        """
        result = []
        last_file = None
        last_line = None
        last_name = None
        count = 0
        for frame in self:
            if (last_file is None or last_file != frame.filename or
                last_line is None or last_line != frame.lineno or
                last_name is None or last_name != frame.name):
                if count > _RECURSIVE_CUTOFF:
                    count -= _RECURSIVE_CUTOFF
                    result.append(
                        f'  [Previous line repeated {count} more '
                        f'time{"s" if count > 1 else ""}]\n'
                    )
                last_file = frame.filename
                last_line = frame.lineno
                last_name = frame.name
                count = 0
            count += 1
            if count > _RECURSIVE_CUTOFF:
                continue
            row = []
            row.append('  File "{}", line {}, in {}\n'.format(
                frame.filename, frame.lineno, frame.name))
            if frame.line:
                row.append('    {}\n'.format(frame.line.strip()))
                # PyPy 3 change: precise traceback ranges
                if hasattr(frame, 'end_lineno'):
                    assert hasattr(frame, 'colno')
                    assert hasattr(frame, 'end_colno')
                    original_line = linecache.getline(frame.filename, frame.lineno)
                    stripped_characters = len(original_line) - len(frame.line.lstrip())
                    if frame.end_lineno == frame.lineno and frame.end_colno != 0:
                        colno = _byte_offset_to_character_offset(original_line, frame.colno)
                        end_colno = _byte_offset_to_character_offset(original_line, frame.end_colno)

                        if end_colno - colno != len(frame.line.strip()):
                            row.append('    ')
                            row.append(' ' * (colno - stripped_characters))
                            row.append('^' * (end_colno - colno))
                            row.append('\n')
                # End PyPy3 change
            if frame.locals:
                for name, value in sorted(frame.locals.items()):
                    row.append('    {name} = {value}\n'.format(name=name, value=value))
            result.append(''.join(row))
        if count > _RECURSIVE_CUTOFF:
            count -= _RECURSIVE_CUTOFF
            result.append(
                f'  [Previous line repeated {count} more '
                f'time{"s" if count > 1 else ""}]\n'
            )
        return result


class TracebackException:
    """An exception ready for rendering.

    The traceback module captures enough attributes from the original exception
    to this intermediary form to ensure that no references are held, while
    still being able to fully print or format it.

    Use `from_exception` to create TracebackException instances from exception
    objects, or the constructor to create TracebackException instances from
    individual components.

    - :attr:`__cause__` A TracebackException of the original *__cause__*.
    - :attr:`__context__` A TracebackException of the original *__context__*.
    - :attr:`__suppress_context__` The *__suppress_context__* value from the
      original exception.
    - :attr:`stack` A `StackSummary` representing the traceback.
    - :attr:`exc_type` The class of the original traceback.
    - :attr:`filename` For syntax errors - the filename where the error
      occurred.
    - :attr:`lineno` For syntax errors - the linenumber where the error
      occurred.
    - :attr:`end_lineno` For syntax errors - the end linenumber where the error
      occurred. Can be `None` if not present.
    - :attr:`text` For syntax errors - the text where the error
      occurred.
    - :attr:`offset` For syntax errors - the offset into the text where the
      error occurred.
    - :attr:`end_offset` For syntax errors - the end offset into the text where
      the error occurred. Can be `None` if not present.
    - :attr:`msg` For syntax errors - the compiler error message.
    """

    def __init__(self, exc_type, exc_value, exc_traceback, *, limit=None,
            lookup_lines=True, capture_locals=False, _seen=None,
            # PyPy 3 change: precise traceback ranges
            _frame_constructor=_default_frame_constructor
            # End PyPy 3 change
        ):
        # NB: we need to accept exc_traceback, exc_value, exc_traceback to
        # permit backwards compat with the existing API, otherwise we
        # need stub thunk objects just to glue it together.
        # Handle loops in __cause__ or __context__.
        is_recursive_call = _seen is not None
        if _seen is None:
            _seen = set()
        _seen.add(id(exc_value))
        # Gracefully handle (the way Python 2.4 and earlier did) the case of
        # being called with no type or value (None, None, None).
        self._truncated = False
        try:
            if (exc_value and exc_value.__cause__ is not None
                and id(exc_value.__cause__) not in _seen):
                cause = TracebackException(
                    type(exc_value.__cause__),
                    exc_value.__cause__,
                    exc_value.__cause__.__traceback__,
                    limit=limit,
                    lookup_lines=False,
                    capture_locals=capture_locals,
                    _seen=_seen,
                    _frame_constructor=_frame_constructor)
            else:
                cause = None
            if (exc_value and exc_value.__context__ is not None
                and id(exc_value.__context__) not in _seen):
                context = TracebackException(
                    type(exc_value.__context__),
                    exc_value.__context__,
                    exc_value.__context__.__traceback__,
                    limit=limit,
                    lookup_lines=False,
                    capture_locals=capture_locals,
                    _seen=_seen,
                    _frame_constructor=_frame_constructor)
            else:
                context = None
        except RecursionError:
            # The recursive call to the constructors above
            # may result in a stack overflow for long exception chains,
            # so we must truncate.
            self._truncated = True
            cause = None
            context = None
        self.__cause__ = cause
        self.__context__ = context
        self.__suppress_context__ = \
            exc_value.__suppress_context__ if exc_value else False
        # TODO: locals.
        # PyPy 3 change: precise traceback ranges
        self.stack = StackSummary._extract_from_extended_frame_gen(
            _walk_tb_with_lasti(exc_traceback), _frame_constructor, limit=limit, lookup_lines=lookup_lines,
            capture_locals=capture_locals)
        # End PyPy 3 change
        self.exc_type = exc_type
        # Capture now to permit freeing resources: only complication is in the
        # unofficial API _format_final_exc_line
        self._str = _some_str(exc_value)
        if exc_type and issubclass(exc_type, SyntaxError):
            # Handle SyntaxError's specially
            self.filename = exc_value.filename
            lno = exc_value.lineno
            self.lineno = str(lno) if lno is not None else None
            end_lno = exc_value.end_lineno
            self.end_lineno = str(end_lno) if end_lno is not None else None
            self.text = exc_value.text
            self.offset = exc_value.offset
            self.end_offset = exc_value.end_offset
            self.msg = exc_value.msg
        elif exc_type and issubclass(exc_type, (NameError, AttributeError)) and \
                getattr(exc_value, "name", None) is not None:
            wrong_name = getattr(exc_value, "name", None)
            suggestion = _compute_suggestion_error(exc_value, exc_traceback, wrong_name)
            if suggestion:
                self._str += f". Did you mean: '{suggestion}'?"
            if issubclass(exc_type, NameError):
                wrong_name = getattr(exc_value, "name", None)
                if wrong_name is not None and wrong_name in sys.stdlib_module_names:
                    if suggestion:
                        self._str += f" Or did you forget to import '{wrong_name}'"
                    else:
                        self._str += f". Did you forget to import '{wrong_name}'"
        if lookup_lines:
            self._load_lines()
        self.__suppress_context__ = \
            exc_value.__suppress_context__ if exc_value is not None else False

        # Convert __cause__ and __context__ to `TracebackExceptions`s, use a
        # queue to avoid recursion (only the top-level call gets _seen == None)
        if not is_recursive_call:
            queue = [(self, exc_value)]
            while queue:
                te, e = queue.pop()
                if (e and e.__cause__ is not None
                    and id(e.__cause__) not in _seen):
                    cause = TracebackException(
                        type(e.__cause__),
                        e.__cause__,
                        e.__cause__.__traceback__,
                        limit=limit,
                        lookup_lines=lookup_lines,
                        capture_locals=capture_locals,
                        _seen=_seen)
                else:
                    cause = None

                if compact:
                    need_context = (cause is None and
                                    e is not None and
                                    not e.__suppress_context__)
                else:
                    need_context = True
                if (e and e.__context__ is not None
                    and need_context and id(e.__context__) not in _seen):
                    context = TracebackException(
                        type(e.__context__),
                        e.__context__,
                        e.__context__.__traceback__,
                        limit=limit,
                        lookup_lines=lookup_lines,
                        capture_locals=capture_locals,
                        _seen=_seen)
                else:
                    context = None
                te.__cause__ = cause
                te.__context__ = context
                if cause:
                    queue.append((te.__cause__, e.__cause__))
                if context:
                    queue.append((te.__context__, e.__context__))

    @classmethod
    def from_exception(cls, exc, *args, **kwargs):
        """Create a TracebackException from an exception."""
        return cls(type(exc), exc, exc.__traceback__, *args, **kwargs)

    def _load_lines(self):
        """Private API. force all lines in the stack to be loaded."""
        for frame in self.stack:
            frame.line

    def __eq__(self, other):
        if isinstance(other, TracebackException):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __str__(self):
        return self._str

    def format_exception_only(self):
        """Format the exception part of the traceback.

        The return value is a generator of strings, each ending in a newline.

        Normally, the generator emits a single string; however, for
        SyntaxError exceptions, it emits several lines that (when
        printed) display detailed information about where the syntax
        error occurred.

        The message indicating which exception occurred is always the last
        string in the output.
        """
        if self.exc_type is None:
            yield _format_final_exc_line(None, self._str)
            return

        stype = self.exc_type.__qualname__
        smod = self.exc_type.__module__
        if smod not in ("__main__", "builtins"):
            if not isinstance(smod, str):
                smod = "<unknown>"
            stype = smod + '.' + stype

        if not issubclass(self.exc_type, SyntaxError):
            yield _format_final_exc_line(stype, self._str)
        else:
            yield from self._format_syntax_error(stype)

    def _format_syntax_error(self, stype):
        """Format SyntaxError exceptions (internal helper)."""
        # Show exactly where the problem was found.
        filename_suffix = ''
        if self.lineno is not None:
            yield '  File "{}", line {}\n'.format(
                self.filename or "<string>", self.lineno)
        elif self.filename is not None:
            filename_suffix = ' ({})'.format(self.filename)

        text = self.text
        if text is not None:
            # text  = "   foo\n"
            # rtext = "   foo"
            # ltext =    "foo"
            rtext = text.rstrip('\n')
            ltext = rtext.lstrip(' \n\f')
            spaces = len(rtext) - len(ltext)
            yield '    {}\n'.format(ltext)

            if self.offset is not None:
                offset = self.offset
                end_offset = self.end_offset if self.end_offset not in {None, 0} else offset
                if offset == end_offset or end_offset == -1:
                    end_offset = offset + 1

                # Convert 1-based column offset to 0-based index into stripped text
                colno = offset - 1 - spaces
                end_colno = end_offset - 1 - spaces
                if colno >= 0:
                    # non-space whitespace (likes tabs) must be kept for alignment
                    caretspace = ((c if c.isspace() else ' ') for c in ltext[:colno])
                    yield '    {}{}'.format("".join(caretspace), ('^' * (end_colno - colno) + "\n"))
        msg = self.msg or "<no detail available>"
        yield "{}: {}{}\n".format(stype, msg, filename_suffix)

    def format(self, *, chain=True):
        """Format the exception.

        If chain is not *True*, *__cause__* and *__context__* will not be formatted.

        The return value is a generator of strings, each ending in a newline and
        some containing internal newlines. `print_exception` is a wrapper around
        this method which just prints the lines to a file.

        The message indicating which exception occurred is always the last
        string in the output.
        """

        output = []
        exc = self
        while exc:
            if chain:
                if exc.__cause__ is not None:
                    chained_msg = _cause_message
                    chained_exc = exc.__cause__
                elif (exc.__context__  is not None and
                      not exc.__suppress_context__):
                    chained_msg = _context_message
                    chained_exc = exc.__context__
                else:
                    chained_msg = None
                    chained_exc = None

                output.append((chained_msg, exc))
                exc = chained_exc
            else:
                output.append((None, exc))
                exc = None

        for msg, exc in reversed(output):
            if msg is not None:
                yield msg
            if exc.stack:
                yield 'Traceback (most recent call last):\n'
                yield from exc.stack.format()
            yield from exc.format_exception_only()


# PyPy change: backport of the 3.12 pure python suggestion implementation

_MAX_CANDIDATE_ITEMS = 750
_MAX_STRING_SIZE = 80
_MOVE_COST = 2
_CASE_COST = 1


def _substitution_cost(ch_a, ch_b):
    if ch_a == ch_b:
        return 0
    if ch_a.lower() == ch_b.lower():
        return _CASE_COST
    return _MOVE_COST


def _compute_suggestion_error(exc_value, tb, wrong_name):
    if wrong_name is None or not isinstance(wrong_name, str):
        return None
    if isinstance(exc_value, AttributeError):
        obj = exc_value.obj
        try:
            d = dir(obj)
        except Exception:
            return None
    elif isinstance(exc_value, ImportError):
        try:
            mod = __import__(exc_value.name)
            d = dir(mod)
        except Exception:
            return None
    else:
        assert isinstance(exc_value, NameError)
        # find most recent frame
        if tb is None:
            return None
        while tb.tb_next is not None:
            tb = tb.tb_next
        frame = tb.tb_frame
        d = (
            list(frame.f_locals)
            + list(frame.f_globals)
            + list(frame.f_builtins)
        )

        # Check first if we are in a method and the instance
        # has the wrong name as attribute
        if 'self' in frame.f_locals:
            self = frame.f_locals['self']
            if hasattr(self, wrong_name):
                return f"self.{wrong_name}"

    # Compute closest match

    if len(d) > _MAX_CANDIDATE_ITEMS:
        return None
    wrong_name_len = len(wrong_name)
    if wrong_name_len > _MAX_STRING_SIZE:
        return None
    best_distance = wrong_name_len
    suggestion = None
    for possible_name in d:
        if possible_name == wrong_name:
            # A missing attribute is "found". Don't suggest it (see GH-88821).
            continue
        # No more than 1/3 of the involved characters should need changed.
        max_distance = (len(possible_name) + wrong_name_len + 3) * _MOVE_COST // 6
        # Don't take matches we've already beaten.
        max_distance = min(max_distance, best_distance - 1)
        current_distance = _levenshtein_distance(wrong_name, possible_name, max_distance)
        if current_distance > max_distance:
            continue
        if not suggestion or current_distance < best_distance:
            suggestion = possible_name
            best_distance = current_distance
    return suggestion


def _levenshtein_distance(a, b, max_cost):
    # A Python implementation of Python/suggestions.c:levenshtein_distance.

    # Both strings are the same
    if a == b:
        return 0

    # Trim away common affixes
    pre = 0
    while a[pre:] and b[pre:] and a[pre] == b[pre]:
        pre += 1
    a = a[pre:]
    b = b[pre:]
    post = 0
    while a[:post or None] and b[:post or None] and a[post-1] == b[post-1]:
        post -= 1
    a = a[:post or None]
    b = b[:post or None]
    if not a or not b:
        return _MOVE_COST * (len(a) + len(b))
    if len(a) > _MAX_STRING_SIZE or len(b) > _MAX_STRING_SIZE:
        return max_cost + 1

    # Prefer shorter buffer
    if len(b) < len(a):
        a, b = b, a

    # Quick fail when a match is impossible
    if (len(b) - len(a)) * _MOVE_COST > max_cost:
        return max_cost + 1

    # Instead of producing the whole traditional len(a)-by-len(b)
    # matrix, we can update just one row in place.
    # Initialize the buffer row
    row = list(range(_MOVE_COST, _MOVE_COST * (len(a) + 1), _MOVE_COST))

    result = 0
    for bindex in range(len(b)):
        bchar = b[bindex]
        distance = result = bindex * _MOVE_COST
        minimum = sys.maxsize
        for index in range(len(a)):
            # 1) Previous distance in this row is cost(b[:b_index], a[:index])
            substitute = distance + _substitution_cost(bchar, a[index])
            # 2) cost(b[:b_index], a[:index+1]) from previous row
            distance = row[index]
            # 3) existing result is cost(b[:b_index+1], a[index])

            insert_delete = min(result, distance) + _MOVE_COST
            result = min(insert_delete, substitute)

            # cost(b[:b_index+1], a[:index+1])
            row[index] = result
            if result < minimum:
                minimum = result
        if minimum > max_cost:
            # Everything in this row is too big, so bail early.
            return max_cost + 1
    return result
