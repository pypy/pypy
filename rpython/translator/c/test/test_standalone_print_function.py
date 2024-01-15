"""In which we test py3 print function syntax
(incompatible with py2 syntax in the same file)"""

from __future__ import print_function

from rpython.translator.c.test import test_standalone

setup_module = test_standalone.setup_module
teardown_module = test_standalone.teardown_module


class TestStandalonePrintFunction(test_standalone.StandaloneTestsVerified):

    def test_print_function(self):
        def entry_point(argv):
            print("hello simpler world")
            argv = argv[1:]
            print("argument count:", len(argv))
            print("arguments:", argv)
            # with a space
            print("argument lengths:", end=" ")
            print([len(s) for s in argv])
            # with no space
            print("argument lengths:", end="")
            print([len(s) for s in argv])
            # strange ending
            print("end", "is", end="\nstrange!\r\n")
            return 0

        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec("hi there")
        assert data.startswith(
            "hello simpler world\n"
            "argument count: 2\n"
            "arguments: [hi, there]\n"
            "argument lengths: [2, 5]\n"
            "argument lengths:[2, 5]\n"
            "end is\nstrange!\n"
        )
        # NB. RPython has only str, not repr, so str() on a list of strings
        # gives the strings unquoted in the list
