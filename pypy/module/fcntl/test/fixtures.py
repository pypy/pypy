def tmpdir(space, config):
    tmpdir = config._tmpdirhandler.getbasetemp().ensure('fcntl', dir=1)
    return space.newtext(str(tmpdir))
