"""
Reviewed 03-06-21
This isn't used at all, nor tested, and is totally cheating.
It even has a syntax error...!
There isn't even any corresponding longtype.  Should perhaps
be just removed.
"""

def long_getattr(i, attr):
    if attr == "__class__":
        return int
    raise AttributeError, ....

def long_long(value):
    return long(value)
