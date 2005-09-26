"""
A color print.
"""

import sys

def ansi_print(text, esc, file=None, newline=True, flush=False):
    if file is None: file = sys.stderr
    text = text.rstrip()
    if esc and sys.platform != "win32" and file.isatty():
        text = ('\x1b[%sm' % esc  +  
                text +
                '\x1b[0m')     # ANSI color code "reset"
    if newline:
        text += '\n'
    file.write(text)
    if flush:
        file.flush()


class AnsiLog:

    def __init__(self, kw_to_color={}, file=None):
        self.kw_to_color = kw_to_color
        self.file = file

    def __call__(self, msg):
        tty = getattr(sys.stderr, 'isatty', lambda: False)()
        flush = False
        newline = True
        keywords = []
        for kw in msg.keywords:
            color = self.kw_to_color.get(kw)
            if color and color not in keywords:
                keywords.append(color)
            keywords.append(kw)
        if 'start' in keywords:
            if tty:
                newline = False
                flush = True
                keywords.remove('start')
        elif 'done' in keywords:
            if tty:
                print >> sys.stderr
                return
        if 'bold' in keywords: 
            keywords.remove('bold')
            esc = "1"
        elif 'red' in keywords: 
            keywords.remove('red')
            esc = "31"
        else: 
            esc = None
        ansi_print("[%s] %s" %(":".join(keywords), msg.content()), esc, 
                   file=self.file, newline=newline, flush=flush)
 
ansi_log = AnsiLog()
