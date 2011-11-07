from __future__ import print_function
import autopath


class AppTestRawInput():

    def test_input_and_raw_input(self):
        import sys, io
        for prompt, expected in [("def:", "abc/def:/ghi\n"),
                                 ("", "abc//ghi\n"),
                                 (42, "abc/42/ghi\n"),
                                 (None, "abc/None/ghi\n"),
                                 (Ellipsis, "abc//ghi\n")]:
            for inputfn, inputtext, gottext in [
                    (input, "foo\nbar\n", "foo")]:
                save = sys.stdin, sys.stdout
                try:
                    sys.stdin = io.StringIO(inputtext)
                    out = sys.stdout = io.StringIO()
                    print("abc", end='')
                    out.write('/')
                    if prompt is Ellipsis:
                        got = inputfn()
                    else:
                        got = inputfn(prompt)
                    out.write('/')
                    print("ghi")
                finally:
                    sys.stdin, sys.stdout = save
                assert out.getvalue() == expected
                assert got == gottext

    def test_softspace(self):
        import sys
        import io
        fin = io.StringIO()
        fout = io.StringIO()

        fin.write("Coconuts\n")
        fin.seek(0)

        sys_stdin_orig = sys.stdin
        sys_stdout_orig = sys.stdout

        sys.stdin = fin
        sys.stdout = fout

        print("test", end='')
        input("test")

        sys.stdin = sys_stdin_orig
        sys.stdout = sys_stdout_orig

        fout.seek(0)
        assert fout.read() == "testtest"

    def test_softspace_carryover(self):
        import sys
        import io
        fin = io.StringIO()
        fout = io.StringIO()

        fin.write("Coconuts\n")
        fin.seek(0)

        sys_stdin_orig = sys.stdin
        sys_stdout_orig = sys.stdout

        sys.stdin = fin
        sys.stdout = fout

        print("test", end='')
        input("test")
        print("test", end='')

        sys.stdin = sys_stdin_orig
        sys.stdout = sys_stdout_orig

        fout.seek(0)
        assert fout.read() == "testtesttest"
