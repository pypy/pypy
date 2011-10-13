
class State:
    def __init__(self, space):
        self.w_open = space.appexec([], """():
                import io
                return io.open""")
        
def get(space):
    return space.fromcache(State)
