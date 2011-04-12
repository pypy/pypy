
#   Copyright 2000-2010 Michael Hudson-Doyle <micahel@gmail.com>
#                       Armin Rigo
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

# Some try-import logic for two purposes: avoiding to bring in the whole
# pure Python curses package if possible; and, in _curses is not actually
# present, falling back to _minimal_curses (which is either a ctypes-based
# pure Python module or a PyPy built-in module).
try:
    import _curses
except ImportError:
    try:
        import _minimal_curses as _curses
    except ImportError:
        # Who knows, maybe some environment has "curses" but not "_curses".
        # If not, at least the following import gives a clean ImportError.
        import _curses

setupterm = _curses.setupterm
tigetstr = _curses.tigetstr
tparm = _curses.tparm
error = _curses.error
