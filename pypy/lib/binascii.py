class Error(Exception):
    pass

class Incomplete(Exception):
    pass

def a2b_uu(s):
    length = (ord(s[0]) - 0x20) % 64
    a = quadruplets(s[1:].rstrip())
    try:
        result = [''.join(
            [chr((A - 0x20) << 2 | (((B - 0x20) >> 4) & 0x3)),
            chr(((B - 0x20) & 0xF) << 4 | (((C - 0x20) >> 2) & 0xF)),
            chr(((C - 0x20) & 0x3) << 6 | ((D - 0x20) & 0x3F))
            ]) for A, B, C, D in a]
    except ValueError:
        raise Error, 'Illegal char'
    result = ''.join(result)
    trailingdata = result[length:]
    if trailingdata.strip('\x00'):
        raise Error, 'Trailing garbage'
    result = result[:length]
    if len(result) < length:
        result += ((length - len(result)) * '\x00')
    return result

def quadruplets(s):
    while s:
        try:
            a, b, c, d = s[0], s[1], s[2], s[3]
        except IndexError:
            s += '   '
            yield ord(s[0]), ord(s[1]), ord(s[2]), ord(s[3])
            return
        s = s[4:]
        yield ord(a), ord(b), ord(c), ord(d)
                               
def b2a_uu(s):
    length = len(s)
    if length > 45:
        raise Error, 'At most 45 bytes at once'

    a = triples(s)
    result = [''.join(
        [chr(0x20 + (( A >> 2                    ) & 0x3F)),
         chr(0x20 + (((A << 4) | ((B >> 4) & 0xF)) & 0x3F)),
         chr(0x20 + (((B << 2) | ((C >> 6) & 0x3)) & 0x3F)),
         chr(0x20 + (( C                         ) & 0x3F))]) for A, B, C in a]
    return chr(ord(' ') + (length & 077)) + ''.join(result) + '\n'

def triples(s):
    while s:
        try:
            a, b, c = s[0], s[1], s[2]
        except IndexError:
            s += '\0\0'
            yield ord(s[0]), ord(s[1]), ord(s[2])
            return
        s = s[3:]
        yield ord(a), ord(b), ord(c)

#print b2a_uu('1234567')
#print b2a_uu('123456789012345678901234567890123456789012345')
#print b2a_uu('1234567890123456789012345678901234567890123456')
#print '"%s"' % a2b_uu(b2a_uu('1234567'))
#print '"%s"' % a2b_uu(b2a_uu('123456789012345678901234567890123456789012345'))

