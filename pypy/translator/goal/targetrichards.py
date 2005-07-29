from pypy.translator.goal import richards

entry_point = richards.entry_point

# _____ Define and setup target ___

def target():
    return entry_point, []

def get_llinterp_args():
    return []

# _____ Run translated _____
def run(c_entry_point):
    print "Translated:"
    richards.main(c_entry_point)
    print "CPython:"
    richards.main()

    
