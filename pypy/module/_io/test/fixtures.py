def tempfile(space, config):
    tmpdir = config._tmpdirhandler.getbasetemp()
    tempfile = (tmpdir / 'tempfile').ensure()
    return space.newtext(str(tempfile))
