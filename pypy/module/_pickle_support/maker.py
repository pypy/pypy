from pypy.interpreter.nestedscope import Cell

#note: for now we don't use the actual value when creating the Cell.
#      (i.e. we assume it will be handled by __setstate__)
#      Stackless does use this so it might be needed here as well.

def cell_new(space):
    return space.wrap(Cell())
#cell_new.unwrap_spec = [...]
