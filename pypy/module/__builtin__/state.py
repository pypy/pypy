
class State: 
    def __init__(self, space): 
        if space.config.objspace.uselibfile:
            self.w_file = space.builtin.get('__filestub')
        else: 
            self.w_file = space.wrap(file) 
        
def get(space): 
    return space.fromcache(State)
