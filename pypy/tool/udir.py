import autopath

#__________________________________________________________
# udir (a unique human-readable directory path where unittests can store
#       files to their likening)

def make_udir():
    from vpath.local import Path, mkdtemp

    _newtmpdir = mkdtemp()
    _tmpdir = _newtmpdir.dirname()
    _newtmpdir.rmdir()

    name, num = 'usession', 0
    items = []
    for item in _tmpdir.listdir():
        if item.basename().startswith(name):
            xb = item.basename().split('-')
            try:
                name, num = xb[0], int(xb[1])
                items.append((name, num))
            except (TypeError,ValueError):
                continue
           
    if items:
        items.sort() 
        name, num = items[-1]
        num += 1

    udir = _tmpdir.join('-'.join([name, str(num)]))
    udir.mkdir()
    return udir

udir = make_udir()

#__________________________________________________________


if __name__ == '__main__':
    # test all of pypy
    print udir
