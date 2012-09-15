import sys
import scratchbox_runner

def test_scratchbox(tmpdir):
    out = tmpdir.join('out').open('w')

    param = scratchbox_runner.ScratchboxRunParam(tmpdir, out)
    expected = ['/scratchbox/login', '-d', tmpdir.strpath, sys.executable]
    assert param.interp == expected
