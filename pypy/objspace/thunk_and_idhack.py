import thunk, idhack

def Space():
    space = thunk.Space()
    space = idhack.Space(space)
    return space
