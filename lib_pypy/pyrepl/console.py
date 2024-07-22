#   Copyright 2000-2004 Michael Hudson-Doyle <micahel@gmail.com>
#
#                        All Rights Reserved
#
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose is hereby granted without fee,
# provided that the above copyright notice appear in all copies and
# that both that copyright notice and this permission notice appear in
# supporting documentation.
#
# THE AUTHOR MICHAEL HUDSON DISCLAIMS ALL WARRANTIES WITH REGARD TO
# THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL,
# INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import annotations

import _colorize  # type: ignore[import-not-found]

from abc import ABC, abstractmethod
import ast
import code
from dataclasses import dataclass, field
import os.path
import sys


TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import IO
    from typing import Callable


@dataclass
class Event:
    evt: str
    data: str
    raw: bytes = b""


@dataclass
class Console(ABC):
    screen: list[str] = field(default_factory=list)
    height: int = 25
    width: int = 80

    def __init__(
        self,
        f_in: IO[bytes] | int = 0,
        f_out: IO[bytes] | int = 1,
        term: str = "",
        encoding: str = "",
    ):
        self.encoding = encoding or sys.getdefaultencoding()

        if isinstance(f_in, int):
            self.input_fd = f_in
        else:
            self.input_fd = f_in.fileno()

        if isinstance(f_out, int):
            self.output_fd = f_out
        else:
            self.output_fd = f_out.fileno()

    @abstractmethod
    def refresh(self, screen: list[str], xy: tuple[int, int]) -> None: ...

    @abstractmethod
    def prepare(self) -> None: ...

    @abstractmethod
    def restore(self) -> None: ...

    @abstractmethod
    def move_cursor(self, x: int, y: int) -> None: ...

    @abstractmethod
    def set_cursor_vis(self, visible: bool) -> None: ...

    @abstractmethod
    def getheightwidth(self) -> tuple[int, int]:
        """Return (height, width) where height and width are the height
        and width of the terminal window in characters."""
        ...

    @abstractmethod
    def get_event(self, block: bool = True) -> Event | None:
        """Return an Event instance.  Returns None if |block| is false
        and there is no event pending, otherwise waits for the
        completion of an event."""
        ...

    @abstractmethod
    def push_char(self, char: int | bytes) -> None:
        """
        Push a character to the console event queue.
        """
        ...

    @abstractmethod
    def beep(self) -> None: ...

    @abstractmethod
    def clear(self) -> None:
        """Wipe the screen"""
        ...

    @abstractmethod
    def finish(self) -> None:
        """Move the cursor to the end of the display and otherwise get
        ready for end.  XXX could be merged with restore?  Hmm."""
        ...

    @abstractmethod
    def flushoutput(self) -> None:
        """Flush all output to the screen (assuming there's some
        buffering going on somewhere)."""
        ...

    @abstractmethod
    def forgetinput(self) -> None:
        """Forget all pending, but not yet processed input."""
        ...

    @abstractmethod
    def getpending(self) -> Event:
        """Return the characters that have been typed but not yet
        processed."""
        ...

    @abstractmethod
    def wait(self, timeout: float | None) -> bool:
        """Wait for an event. The return value is True if an event is
        available, False if the timeout has been reached. If timeout is
        None, wait forever. The timeout is in milliseconds."""
        ...

    @property
    def input_hook(self) -> Callable[[], int] | None:
        """Returns the current input hook."""
        ...

    @abstractmethod
    def repaint(self) -> None: ...


class InteractiveColoredConsole(code.InteractiveConsole):
    def __init__(
        self,
        locals: dict[str, object] | None = None,
        filename: str = "<console>",
        *,
        local_exit: bool = False,
    ) -> None:
        super().__init__(locals=locals, filename=filename)  # type: ignore[call-arg]
        self.can_colorize = _colorize.can_colorize()

    def showsyntaxerror(self, filename=None):
        """Display the syntax error that just occurred.

        This doesn't display a stack trace because there isn't one.

        If a filename is given, it is stuffed in the exception instead
        of what was there before (because Python's parser always uses
        "<string>" when reading from a string).

        The output is written by self.write(), below.

        """
        # pypy modification: rewrite this function to a) support positions and
        # b) pass self.can_colorize
        type, value, tb = sys.exc_info()
        sys.last_exc = value
        sys.last_type = type
        sys.last_value = value
        sys.last_traceback = tb
        if filename and type is SyntaxError:
            # Work hard to stuff the correct filename in the exception
            try:
                msg, (dummy_filename, lineno, offset, line) = value.args
            except ValueError:
                # Not the format we expect; leave it alone
                pass
            else:
                # Stuff in the right filename
                value = SyntaxError(msg, (filename, lineno, offset, line))
                sys.last_exc = sys.last_value = value
        if sys.excepthook is sys.__excepthook__:
            lines = traceback.format_exception_only(type, value, colorize=self.can_colorize)
            self.write(''.join(lines))
        else:
            # If someone has set sys.excepthook, we let that take precedence
            # over self.write
            sys.excepthook(type, value, tb)

    def showtraceback(self):
        """Display the exception that just occurred.

        We remove the first stack item because it is our own code.

        The output is written by self.write(), below.

        """
        # pypy modification: rewrite this function to a) support positions and
        # b) pass self.can_colorize
        import traceback
        sys.last_type, sys.last_value, last_tb = ei = sys.exc_info()
        sys.last_traceback = last_tb
        try:
            if sys.excepthook is sys.__excepthook__:
                tb_exc = traceback.TracebackException(
                    ei[0],
                    ei[1],
                    last_tb,
                    _frame_constructor=traceback._construct_positionful_frame
                )
                lines = tb_exc.format(colorize=self.can_colorize)
                self.write(''.join(lines))
            else:
                # If someone has set sys.excepthook, we let that take precedence
                # over self.write
                sys.excepthook(ei[0], ei[1], last_tb)
        finally:
            last_tb = ei = None


    def push(self, line, filename=None, _symbol="single"):
        """Push a line to the interpreter.

        The line should not have a trailing newline; it may have
        internal newlines.  The line is appended to a buffer and the
        interpreter's runsource() method is called with the
        concatenated contents of the buffer as source.  If this
        indicates that the command was executed or invalid, the buffer
        is reset; otherwise, the command is incomplete, and the buffer
        is left as it was after the line was appended.  The return
        value is 1 if more input is required, 0 if the line was dealt
        with in some way (this is the same as runsource()).

        """
        # pypy modification: copied over from CPy 3.13's code.py, to allow
        # passing filename
        self.buffer.append(line)
        source = "\n".join(self.buffer)
        if filename is None:
            filename = self.filename
        more = self.runsource(source, filename, symbol=_symbol)
        if not more:
            self.resetbuffer()
        return more

    def runsource(self, source, filename="<input>", symbol="single"):
        try:
            tree = ast.parse(source)
        except (SyntaxError, OverflowError, ValueError):
            self.showsyntaxerror(filename)
            return False
        if tree.body:
            *_, last_stmt = tree.body
        for stmt in tree.body:
            wrapper = ast.Interactive if stmt is last_stmt else ast.Module
            the_symbol = symbol if stmt is last_stmt else "exec"
            item = wrapper([stmt])
            try:
                code = self.compile.compiler(item, filename, the_symbol, dont_inherit=True)
            except SyntaxError as e:
                if e.args[0] == "'await' outside function":
                    python = os.path.basename(sys.executable)
                    e.add_note(
                        f"Try the asyncio REPL ({python} -m asyncio) to use"
                        f" top-level 'await' and run background asyncio tasks."
                    )
                self.showsyntaxerror(filename)
                return False
            except (OverflowError, ValueError):
                self.showsyntaxerror(filename)
                return False

            if code is None:
                return True

            self.runcode(code)
        return False
