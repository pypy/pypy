import sys
import io
import scratchbox_runner

def test_scratchbox(tmpdir):
    out = io.BytesIO()
    param = scratchbox_runner.ScratchboxRunParam(tmpdir, out)
    expected = ['/scratchbox/login', '-d', tmpdir.strpath, sys.executable]
    assert param.interp == expected
