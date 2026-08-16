from _pytest.tmpdir import TempdirFactory

def tmpdir(space, config):
    tmpdir = TempdirFactory(config).getbasetemp().ensure('_posixsubprocess',
                                                         dir=1)
    return space.newtext(str(tmpdir))
