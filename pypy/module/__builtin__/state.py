
class State:
    def __init__(self, space):
        self.w_file = space.appexec([], """():
                import _file;
                return _file.file""")
        
def get(space):
    return space.fromcache(State)
