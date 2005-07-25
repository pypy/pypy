import py

import os

from pypy.rpython.module.ll_os_path import *
from pypy.rpython.module.support import to_rstr, from_rstr, ll_strcpy

def test_exists():
    filename = to_rstr(str(py.magic.autopath()))
    assert ll_os_path_exists(filename) == True
    assert not ll_os_path_exists(to_rstr(
        "strange_filename_that_looks_improbable.sde"))
