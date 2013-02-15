
def signals_enter(space):
    space.threadlocals.enable_signals()

def signals_exit(space):
    space.threadlocals.disable_signals()
