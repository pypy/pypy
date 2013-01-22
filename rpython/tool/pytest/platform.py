import py
import pytest


def pytest_report_header():
    return "pytest-%s from %s" %(pytest.__version__, pytest.__file__)


def _set_platform(opt, opt_str, value, parser):
    from rpython.config.translationoption import PLATFORMS
    from rpython.translator.platform import set_platform
    if value not in PLATFORMS:
        raise ValueError("%s not in %s" % (value, PLATFORMS))
    set_platform(value, None)

def pytest_addoption(parser):
    group = parser.getgroup("rpython options")
    group.addoption('-P', '--platform', action="callback", type="string",
           default="host", callback=_set_platform,
           help="set up tests to use specified platform as compile/run target")

