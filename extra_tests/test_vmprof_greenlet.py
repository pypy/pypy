import time
import pytest
import sys
vmprof = pytest.importorskip('vmprof')
greenlet = pytest.importorskip('greenlet')

IS_32_BIT = sys.maxint == 2**31-1

def count_samples(filename):
    stats = vmprof.read_profile(filename)
    return len(stats.profiles)

def cpuburn(duration):
    end = time.time() + duration
    while time.time() < end:
        pass

# See https://github.com/vmprof/vmprof-python/issues/274
@pytest.mark.skipif(IS_32_BIT, "vmprof fails to write profiles with negative addresses")
def test_sampling_inside_callback(tmpdir):
    # see also test_sampling_inside_callback inside
    # pypy/module/_continuation/test/test_stacklet.py
    #
    G = greenlet.greenlet(cpuburn)
    fname = tmpdir.join('log.vmprof')
    with fname.open('w+b') as f:
        vmprof.enable(f.fileno(), 1/250.0)
        G.switch(0.1)
        vmprof.disable()

    samples = count_samples(str(fname))
    # 0.1 seconds at 250Hz should be 25 samples
    assert 23 < samples < 27
