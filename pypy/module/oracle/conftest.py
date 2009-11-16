from pypy.rpython.tool.rffi_platform import CompilationError
import py
import os

def pytest_addoption(parser):
    group = parser.getgroup("Oracle module options")
    group.addoption('--oracle-home', dest="oracle_home",
                    help="Home directory of Oracle client installation",
                    default=os.environ.get("ORACLE_HOME"))
    group.addoption('--oracle-connect', dest="oracle_connect",
                    help="connect string (user/pwd@db) used for tests")
