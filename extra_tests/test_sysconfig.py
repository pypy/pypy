import os
import sys
import sysconfig

def test_libdirs():
    # Make sure the schemes are all valid, issue 3954
    schemes = sysconfig.get_scheme_names()
    names = ["stdlib", "platstdlib", "platlib", "purelib"]
    candidates = {sysconfig.get_path(name, scheme) for scheme in schemes for name in names}
    paths = [path for path in candidates if path in sys.path]
    in_venv = sys.prefix != sys.base_prefix
    if sys.platform == 'win32' and not in_venv:
        assert len(paths) == 0
    else:
        # a venv puts its site-packages, which is the nt_venv/venv scheme's
        # purelib, on sys.path
        assert len(paths) > 0
