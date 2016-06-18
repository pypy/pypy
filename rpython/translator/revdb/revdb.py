#!/usr/bin/env python

import sys, os


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Reverse debugger')
    parser.add_argument('log', metavar='LOG', help='log file name')
    parser.add_argument('-x', '--executable', dest='executable',
                        help='name of the executable file '
                             'that recorded the log')
    options = parser.parse_args(sys.argv[1:])

    sys.path.insert(0, os.path.abspath(
        os.path.join(__file__, '..', '..', '..', '..')))

    from rpython.translator.revdb.interact import RevDebugControl
    ctrl = RevDebugControl(options.log, executable=options.executable)
    ctrl.interact()
