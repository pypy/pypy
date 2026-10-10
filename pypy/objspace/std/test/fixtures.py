def tmpdir(space, config):
    tmpdir = config._tmpdirhandler.getbasetemp().ensure('objspace_std', dir=1)
    return space.newtext(str(tmpdir))
