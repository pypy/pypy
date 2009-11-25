

def default_int_handler(signum, frame):
    """
    default_int_handler(...)

    The default handler for SIGINT installed by Python.
    It raises KeyboardInterrupt.
    """
    raise KeyboardInterrupt()
