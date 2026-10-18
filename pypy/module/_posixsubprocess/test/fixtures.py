def tmpdir(space, config):
    tmpdir = config._tmpdirhandler.getbasetemp().ensure('_posixsubprocess',
                                                         dir=1)
    return space.newtext(str(tmpdir))
