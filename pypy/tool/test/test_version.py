import os, sys
import py
from pypy.tool.version import get_repo_version_info

def test_get_repo_version_info():
    assert get_repo_version_info(None)
    assert get_repo_version_info(os.devnull) == ('PyPy', '?', '?')
    assert get_repo_version_info(sys.executable) == ('PyPy', '?', '?')
