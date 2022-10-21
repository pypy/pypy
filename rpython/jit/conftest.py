"""
This conftest adds options used by test/test_random and
x86/test/test_zll_random.
"""

import random

def pytest_addoption(parser):
    group = parser.getgroup("JIT options")
    group.addoption('--slow', action="store_true",
           default=False, dest="run_slow_tests",
           help="run all the compiled tests (instead of just a few)")

    group = parser.getgroup('random test options')
    group.addoption('--random-seed', action="store", type=int,
                    default=random.randrange(0, 10000),
                    dest="randomseed",
                    help="choose a fixed random seed")
    group.addoption('--backend', action="store",
                    default='llgraph',
                    choices=['llgraph', 'cpu'],
                    dest="backend",
                    help="select the backend to run the functions with")
    group.addoption('--block-length', action="store", type=int,
                    default=30,
                    dest="block_length",
                    help="insert up to this many operations in each test")
    group.addoption('--n-vars', action="store", type=int,
                    default=10,
                    dest="n_vars",
                    help="supply this many randomly-valued arguments to "
                         "the function")
    group.addoption('--repeat', action="store", type=int,
                    default=15,
                    dest="repeat",
                    help="run the test this many times"),
    group.addoption('--output', '-O', action="store", type=str,
                    default="", dest="output",
                    help="dump output to a file")
    group.addoption('--z3-timeout', action="store", type=int,
                    default=500, dest="z3timeout",
                    help="give timeout that Z3 should use for proving in milliseconds per condition")
