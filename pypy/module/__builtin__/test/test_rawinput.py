import autopath


class AppTestRawInput():

    def test_input_and_raw_input(self):
        import sys, StringIO
        for prompt, expected in [("def:", "abc/ def:/ghi\n"),
                                 ("", "abc/ /ghi\n"),
                                 (42, "abc/ 42/ghi\n"),
                                 (None, "abc/ None/ghi\n"),
                                 (Ellipsis, "abc/ /ghi\n")]:
            for inputfn, inputtext, gottext in [
                    (raw_input, "foo\nbar\n", "foo"),
                    (input, "40+2\n", 42)]:
                save = sys.stdin, sys.stdout
                try:
                    sys.stdin = StringIO.StringIO(inputtext)
                    out = sys.stdout = StringIO.StringIO()
                    print "abc",    # softspace = 1
                    out.write('/')
                    if prompt is Ellipsis:
                        got = inputfn()
                    else:
                        got = inputfn(prompt)
                    out.write('/')
                    print "ghi"
                finally:
                    sys.stdin, sys.stdout = save
                assert out.getvalue() == expected
                assert got == gottext

    def test_softspace(self):
        import sys
        import StringIO
        fin = StringIO.StringIO()
        fout = StringIO.StringIO()

        fin.write("Coconuts\n")
        fin.seek(0)

        sys_stdin_orig = sys.stdin
        sys_stdout_orig = sys.stdout

        sys.stdin = fin
        sys.stdout = fout

        print "test",
        raw_input("test")

        sys.stdin = sys_stdin_orig
        sys.stdout = sys_stdout_orig

        fout.seek(0)
        assert fout.read() == "test test"

    def test_softspace_carryover(self):
        import sys
        import StringIO
        fin = StringIO.StringIO()
        fout = StringIO.StringIO()

        fin.write("Coconuts\n")
        fin.seek(0)

        sys_stdin_orig = sys.stdin
        sys_stdout_orig = sys.stdout

        sys.stdin = fin
        sys.stdout = fout

        print "test",
        raw_input("test")
        print "test",

        sys.stdin = sys_stdin_orig
        sys.stdout = sys_stdout_orig

        fout.seek(0)
        assert fout.read() == "test testtest"
