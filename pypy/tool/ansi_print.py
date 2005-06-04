"""
A color print.
"""

import sys

def ansi_print(text, esc, file=None):
    if file is None: file = sys.stderr
    text = text.rstrip()
    if sys.platform != "win32" and file.isatty():
        text = ('\x1b[%sm' % esc  +  
                text +
                '\x1b[0m')     # ANSI color code "reset"
    file.write(text + '\n')
