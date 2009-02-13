
class Error(Exception):
    pass

def _fixup_ulcase():
    import string

    # create uppercase map string
    ul = []
    for c in xrange(256):
        c = chr(c)
        if c.isupper():
            ul.append(c)
    ul = ''.join(ul)
    string.uppercase = ul

    # create lowercase string
    ul = []
    for c in xrange(256):
        c = chr(c)
        if c.islower():
            ul.append(c)
    ul = ''.join(ul)
    string.lowercase = ul

    # create letters string
    ul = []
    for c in xrange(256):
        c = chr(c)
        if c.isalpha():
            ul.append(c)
    ul = ''.join(ul)
    string.letters = ul

