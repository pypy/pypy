"""
A color print.
"""

import sys

def ansi_print(text, esc, file=None, newline=True):
    if file is None: file = sys.stderr
    text = text.rstrip()
    if esc and sys.platform != "win32" and file.isatty():
        text = ('\x1b[%sm' % esc  +  
                text +
                '\x1b[0m')     # ANSI color code "reset"
    if newline:
        text += '\n'
    file.write(text)

def ansi_log(msg): 
    keywords = list(msg.keywords)
    if 'bold' in keywords: 
        keywords.remove('bold')
        esc = "1"
    elif 'red' in keywords: 
        keywords.remove('red')
        esc = "31"
    else: 
        esc = None
    ansi_print("[%s] %s" %(":".join(keywords), msg.content()), esc)
 
