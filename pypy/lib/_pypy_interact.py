"""Imported by app_main.py when PyPy needs to fire up the interactive console.
"""
import sys


def interactive_console(mainmodule=None):
    import code
    if mainmodule is None:
        import __main__ as mainmodule
    console = code.InteractiveConsole(mainmodule.__dict__)
    try:
        from readline import multiline_input
    except ImportError:
        run_simple_interactive_console(console)
    else:
        run_multiline_interactive_console(console)

def run_simple_interactive_console(console):
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

def run_multiline_interactive_console(console):
    from readline import multiline_input

    def more_lines(unicodetext):
        # ooh, look at the hack:
        src = "#coding:utf-8\n"+unicodetext.encode('utf-8')
        try:
            code = console.compile(src, '<input>', 'single')
        except (OverflowError, SyntaxError, ValueError):
            return False
        else:
            return code is None

    while 1:
        try:
            ps1 = getattr(sys, 'ps1', '>>> ')
            ps2 = getattr(sys, 'ps2', '... ')
            try:
                statement = multiline_input(more_lines, ps1, ps2)
            except EOFError:
                break
            more = console.push(statement)
            assert not more
        except KeyboardInterrupt:
            console.write("\nKeyboardInterrupt\n")
            console.resetbuffer()

# ____________________________________________________________

if __name__ == '__main__':    # for testing
    import os
    if os.getenv('PYTHONSTARTUP'):
        execfile(os.getenv('PYTHONSTARTUP'))
    interactive_console()
