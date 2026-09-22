from _pytest.tmpdir import TempdirFactory

def tmpdir(space, config):
    tmpdir = TempdirFactory(config).getbasetemp()
    return space.newtext(str(tmpdir))
