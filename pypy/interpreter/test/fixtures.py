def tempfile(space, config):
    tmpdir = config._tmpdirhandler.getbasetemp()
    return space.newtext(str(tmpdir / 'tempfile1'))

def tmpdir(space, config):
    tmpdir = TempdirFactory(config).getbasetemp()
    return space.newtext(str(tmpdir))
