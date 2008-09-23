"""Imported by app_main.py when PyPy needs to fire up the interactive console.
"""
import sys


def interactive_console(mainmodule=None):
    try:
        from _pypy_irc_topic import some_topic
        text = "And now for something completely different: ``%s''" % (
            some_topic(),)
        if len(text) >= 80:
            i = text[:80].rfind(' ')
            print text[:i]
            text = text[i+1:]
        print text
    except ImportError:
        pass
    try:
        from pyrepl.simple_interact import run_multiline_interactive_console
    except ImportError:
        run_simple_interactive_console(mainmodule)
    else:
        run_multiline_interactive_console(mainmodule)

def run_simple_interactive_console(mainmodule):
    import code
    if mainmodule is None:
        import __main__ as mainmodule
    console = code.InteractiveConsole(mainmodule.__dict__)
    # some parts of code.py are copied here because it seems to be impossible
    # to start an interactive console without printing at least one line
    # of banner
    more = 0
    while 1:
        try:
            if more:
                prompt = getattr(sys, 'ps2', '... ')
            else:
                prompt = getattr(sys, 'ps1', '>>> ')
            try:
                line = raw_input(prompt)
            except EOFError:
                console.write("\n")
                break
            else:
                more = console.push(line)
        except KeyboardInterrupt:
            console.write("\nKeyboardInterrupt\n")
            console.resetbuffer()
            more = 0

# ____________________________________________________________

if __name__ == '__main__':    # for testing
    import os
    if os.getenv('PYTHONSTARTUP'):
        execfile(os.getenv('PYTHONSTARTUP'))
    interactive_console()
