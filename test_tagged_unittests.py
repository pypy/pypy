# Copyright (c) 2019, 2021, Oracle and/or its affiliates. All rights reserved.
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
#
# The Universal Permissive License (UPL), Version 1.0
#
# Subject to the condition set forth below, permission is hereby granted to any
# person obtaining a copy of this software, associated documentation and/or
# data (collectively the "Software"), free of charge and under any and all
# copyright rights in the Software, and any and all patent rights owned or
# freely licensable by each licensor hereunder covering either (i) the
# unmodified Software as contributed to or provided by such licensor, or (ii)
# the Larger Works (as defined below), to deal in both
#
# (a) the Software, and
#
# (b) any piece of software and/or hardware listed in the lrgrwrks.txt file if
# one is included with the Software each a "Larger Work" to which the Software
# is contributed by such licensors),
#
# without restriction, including without limitation the rights to copy, create
# derivative works of, display, perform, and distribute the Software and make,
# use, sell, offer for sale, import, export, have made, and have sold the
# Software and the Larger Work(s), and to sublicense the foregoing rights on
# either these or other terms.
#
# This license is subject to the following condition:
#
# The above copyright notice and either this complete permission notice or at a
# minimum a reference to the UPL must be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys


RUNNER_ENV = "RUN_TAGGED_CPYTHON_TESTS"


try:
    __graalpython__
except NameError:
    __graalpython__ = False


if os.environ.get("ENABLE_CPYTHON_TAGGED_UNITTESTS") == "true" or __name__ == "__main__":
    TAGS_DIR = os.path.join(os.path.dirname(__file__), "unittest_tags")
else:
    TAGS_DIR = "null"


def working_selectors(tagfile):
    if os.path.exists(tagfile):
        with open(tagfile) as f:
            return [line.strip() for line in f if line]
    else:
        return None


def collect_working_tests():
    working_tests = []
    glob_pattern = os.path.join(TAGS_DIR, "*.txt")
    for arg in sys.argv:
        if arg.startswith("--tagfile="):
            glob_pattern = os.path.join(TAGS_DIR, arg.partition("=")[2])
            sys.argv.remove(arg)
            break
    for tagfile in glob.glob(glob_pattern):
        test = os.path.splitext(os.path.basename(tagfile))[0]
        working_tests.append((test, working_selectors(tagfile)))
    return sorted(working_tests)


def make_test_function(working_test):
    testmod = working_test[0].rpartition(".")[2]

    def test_tagged():
        cmd = [sys.executable]
        if "--inspect" in sys.argv:
            cmd.append("--inspect")
        if "-debug-java" in sys.argv:
            cmd.append("-debug-java")
        cmd += [__file__]
        for testpattern in working_test[1]:
            cmd.extend(["-k", testpattern])
        print("Running test:", working_test[0])
        testfile = os.path.join(os.path.dirname(test.__file__), "%s.py" % testmod)
        if not os.path.isfile(testfile):
            testfile = os.path.join(os.path.dirname(test.__file__), "%s/__init__.py" % testmod)
        cmd.append(testfile)
        env = os.environ.copy()
        env[RUNNER_ENV] = "1"
        subprocess.check_call(cmd, env=env)
        print(working_test[0], "was finished.")

    if testmod.startswith('test_'):
        test_tagged.__name__ = testmod
    else:
        test_tagged.__name__ = 'test_' + testmod
    return test_tagged


def make_tests_class():
    global TestTaggedUnittests

    class TestTaggedUnittests(unittest.TestCase):
        pass

    partial = os.environ.get('TAGGED_UNITTEST_PARTIAL')
    if partial:
        selected_str, total_str = partial.split('/', 1)
        selected = int(selected_str) - 1
        total = int(total_str)
    else:
        selected = 0
        total = 1
    assert selected < total

    working_tests = collect_working_tests()[selected::total]
    for idx, working_test in enumerate(working_tests):
        fn = make_test_function(working_test)
        fn.__name__ = "%s[%d/%d]" % (fn.__name__, idx + 1, len(working_tests))
        fn.__qualname__ = "%s.%s" % (TestTaggedUnittests.__name__, fn.__name__)
        setattr(TestTaggedUnittests, fn.__name__, staticmethod(fn))


# This function has a unittest in test_tagger
def parse_unittest_output(output):
    # The whole reason for this function's complexity is that we want to consume arbitrary
    # warnings after the '...' part without accidentally consuming the next test result
    import re
    re_test_result = re.compile(r"""\b(test\S+) \(([^\s]+)\)(?:\n.*?)?? \.\.\. """, re.MULTILINE | re.DOTALL)
    re_test_status = re.compile(r"""\b(ok|skipped (?:'[^']*'|"[^"]*")|FAIL|ERROR)$""", re.MULTILINE | re.DOTALL)
    pos = 0
    current_result = None
    while True:
        result_match = re_test_result.search(output, pos)
        status_match = re_test_status.search(output, pos)
        if current_result and status_match and (not result_match or status_match.start() < result_match.start()):
            yield current_result.group(1), current_result.group(2), status_match.group(1)
            current_result = None
            pos = status_match.end()
        elif result_match:
            current_result = result_match
            pos = result_match.end()
        else:
            return


def main():
    executable = sys.executable.split(" ")  # HACK: our sys.executable on Java is a cmdline
    env = os.environ.copy()
    env[RUNNER_ENV] = "1"
    kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True, "check": False, "env": env}

    glob_pattern = os.path.join(os.path.dirname(test.__file__), "test_*.py")
    retag = False
    maxrepeats = 4
    tout = "240"
    for arg in sys.argv[1:]:
        if arg == "--retag":
            retag = True
        elif arg.startswith("--maxrepeats="):
            maxrepeats = int(arg.partition("=")[2])
        elif arg.startswith("--timeout="):
            tout = arg.partition("=")[2]
        elif arg == "--help":
            print(sys.argv[0] + " [--retag] [--maxrepeats=n] [glob]")
        else:
            if not (arg.endswith(".py") or arg.endswith("*")):
                arg += ".py"
            glob_pattern = os.path.join(os.path.dirname(test.__file__), arg)

    p = subprocess.run(["/usr/bin/which", "timeout" if sys.platform != 'darwin' else 'gtimeout'], **kwargs)
    if p.returncode != 0:
        print("Cannot find the 'timeout' GNU tool. Do you have coreutils installed?")
        sys.exit(1)
    timeout = p.stdout.strip()

    testfiles = glob.glob(glob_pattern)
    testfiles += glob.glob(glob_pattern.replace(".py", "/__init__.py"))

    for idx, testfile in enumerate(testfiles):
        for repeat in range(maxrepeats):
            # we always do this multiple times, because sometimes the tagging
            # doesn't quite work e.g. we create a tags file that'll still fail
            # when we use it. Thus, when we run this multiple times, we'll just
            # use the tags and if it fails in the last run, we assume something
            # sad is happening and delete the tags file to skip the tests
            # entirely
            if testfile.endswith("__init__.py"):
                testfile_stem = os.path.basename(os.path.dirname(testfile))
            else:
                testfile_stem = os.path.splitext(os.path.basename(testfile))[0]
            testmod = "test." + testfile_stem
            cmd = [timeout, "-s", "9", tout] + executable
            if repeat == 0 and __graalpython__:
                # Allow catching Java exceptions in the first iteration only, so that subsequent iterations
                # (there will be one even if everything succeeds) filter out possible false-passes caused by
                # the tests catching all exceptions somewhere
                cmd += ['--experimental-options', '--python.CatchAllExceptions']
            cmd += [__file__, "-v"]
            tagfile = os.path.join(TAGS_DIR, testfile_stem + ".txt")
            if retag and repeat == 0:
                test_selectors = []
            else:
                test_selectors = working_selectors(tagfile)

            if test_selectors is None:
                # there's no tagfile for this, so it's not working at all (or
                # shouldn't be tried).
                continue

            print("[%d/%d, Try %d] Testing %s" % (idx + 1, len(testfiles), repeat + 1, testmod))
            for selector in test_selectors:
                cmd += ["-k", selector]
            cmd.append(testfile)

            print(" ".join(cmd))
            p = subprocess.run(cmd, errors='backslashreplace', **kwargs)
            print("*stdout*")
            print(p.stdout)
            print("*stderr*")
            print(p.stderr)

            passing_tests = []

            # n.b.: we add a '*' in the front, so that unittests doesn't add
            # its own asterisks, because now this is already a pattern
            for funcname, classname, result in parse_unittest_output(p.stderr):
                # We consider skipped tests as passing in order to avoid a situation where a Linux run
                # untags a Darwin-only test and vice versa
                if result == 'ok' or result.startswith('skipped'):
                    passing_tests.append(f"*{classname}.{funcname}")

            with open(tagfile, "w") as f:
                for passing_test in sorted(passing_tests):
                    f.write(passing_test)
                    f.write("\n")
            if not passing_tests:
                os.unlink(tagfile)
                print("No successful tests detected (you can try to increase the timeout by using --timeout=NNN)")
                break

            if p.returncode == 0:
                if repeat == 0 and maxrepeats > 1:
                    print(f"Suite succeeded with {len(passing_tests)} tests, retrying to confirm tags are correct")
                    continue
                print(f"Suite succeeded with {len(passing_tests)} tests")
                break
            elif p.returncode == -9:
                print(
                    f"\nTimeout (return code -9)\nyou can try to increase the current timeout {tout}s by using --timeout=NNN")
                break
            else:
                print(f"Suite failed, retrying with {len(passing_tests)} tests")

        else:
            # we tried the last time and failed, so our tags don't work for
            # some reason
            print("The suite failed even in the last attempt, untagging completely")
            try:
                os.unlink(tagfile)
            except Exception:
                pass


if __name__ == '__main__':
    if os.environ.get(RUNNER_ENV, None):
        import unittest

        sys.path.insert(0, os.getcwd())

        class TestLoader(unittest.TestLoader):

            def prepare_test_decimal(self, module):
                # Taken from test_main() in test_decimal.py
                module.init(module.C)
                module.init(module.P)
                module.TEST_ALL = True
                module.DEBUG = None
                for filename in os.listdir(module.directory):
                    if '.decTest' not in filename or filename.startswith("."):
                        continue
                    head, tail = filename.split('.')
                    tester = lambda self, f=filename: self.eval_file(module.directory + f)
                    setattr(module.CIBMTestCases, 'test_' + head, tester)
                    setattr(module.PyIBMTestCases, 'test_' + head, tester)
                    del filename, head, tail, tester
                return self.suiteClass(self.loadTestsFromTestCase(cls) for cls in module.all_tests)

            def loadTestsFromModule(self, module, pattern=None):
                if module.__name__.endswith('test_decimal'):
                    return self.prepare_test_decimal(module)
                suite = super().loadTestsFromModule(module, pattern=pattern)
                test_main = getattr(module, 'test_main', None)
                if callable(test_main):
                    class TestMain(unittest.TestCase):
                        pass

                    TestMain.__module__ = test_main.__module__
                    TestMain.__qualname__ = TestMain.__name__
                    TestMain.test_main = staticmethod(test_main)
                    suite.addTests(self.loadTestsFromTestCase(TestMain))
                return suite


        # We would normmally just pass the loader to the main, but there are
        # tests for the framework itself (test_unittest) that interact weirdly
        # with non-default loaders
        unittest.defaultTestLoader = TestLoader()
        unittest.main(module=None, testLoader=unittest.defaultTestLoader)
    else:
        import glob
        import subprocess
        import test
        main()
else:
    import glob
    import subprocess
    import test
    import unittest
    make_tests_class()
