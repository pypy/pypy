
""" Simplified optimize.py
"""

def optimize_loop(options, old_loops, loop, cpu=None):
    if old_loops:
        return old_loops[0]
    else:
        return None

def optimize_bridge(options, old_loops, loop, cpu=None):
    return old_loops[0]


