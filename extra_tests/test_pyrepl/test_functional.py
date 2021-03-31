#   Copyright 2000-2007 Michael Hudson-Doyle <micahel@gmail.com>
#                       Maciek Fijalkowski
# License: MIT
# some functional tests, to see if this is really working

import os
import signal
import sys
import textwrap

import pytest

try:
    import pexpect
except ImportError as exc:
    pytest.skip("could not import pexpect: {}".format(exc),
                allow_module_level=True)


@pytest.fixture
def start_child():
    ret = []

    def start_child_func(env_update=None):
        assert not ret, "child started already"

        env = {k: v for k, v in os.environ.items() if k in (
            "TERM",
        )}
        if env_update:
            env.update(env_update)
        child = pexpect.spawn(sys.executable, timeout=5, env=env)
        if sys.version_info >= (3, ):
            child.logfile = sys.stdout.buffer
        else:
            child.logfile = sys.stdout
        child.expect_exact(">>> ")
        child.sendline('from pyrepl.python_reader import main')
        # child.sendline('main()')
        ret.append(child)
        return child

    yield start_child_func

    assert ret, "child was not started"
    child = ret[0]

    child.sendeof()
    child.expect_exact(">>> ")
    # Verify there's no error, e.g. when signal.SIG_DFL would be called.
    before = child.before.decode()
    assert "Traceback (most recent call last):" not in before
    child.sendeof()
    assert child.wait() == 0


@pytest.fixture
def child(start_child):
    child = start_child()
    child.sendline("main()")
    return child


def test_basic(child):
    child.expect_exact("->> ")
    child.sendline('a = 40 + 2')
    child.expect_exact("->> ")
    child.sendline('a')
    child.expect_exact('42')
    child.expect_exact("->> ")


def test_sigwinch_default(child):
    child.expect_exact("->> ")
    os.kill(child.pid, signal.SIGWINCH)


def test_sigwinch_forwarded(start_child, tmpdir):
    with open(str(tmpdir.join("initfile")), "w") as initfile:
        initfile.write(textwrap.dedent(
            """
            import signal

            called = []

            def custom_handler(signum, frame):
                called.append([signum, frame])

            signal.signal(signal.SIGWINCH, custom_handler)

            print("PYREPLSTARTUP called")
            """
        ))

    child = start_child(env_update={"PYREPLSTARTUP": initfile.name})
    child.sendline("main()")
    child.expect_exact("PYREPLSTARTUP called")
    child.expect_exact("->> ")
    os.kill(child.pid, signal.SIGWINCH)
    child.sendline('"called={}".format(len(called))')
    child.expect_exact("called=1")
