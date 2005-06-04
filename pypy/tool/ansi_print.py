"""
A color print.
"""

import sys

f = None
n = 0

def ansi_print(text, esc, file=None):
    if file is None: file = sys.stderr
    text = text.rstrip()
    global f,n
    if not text.startswith('faking') and esc == "31":
        if not f:
            f = open("warnings.log",'w')
        n += 1
        f.write("<<< %03d\n"  % n)
        f.write(text+'\n')
        f.flush()
    if sys.platform != "win32" and file.isatty():
        text = ('\x1b[%sm' % esc  +  
                text +
                '\x1b[0m')     # ANSI color code "reset"
    file.write(text + '\n')
