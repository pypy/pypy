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


table_a2b_base64 = {
    'A': 0,
    'B': 1,
    'C': 2,
    'D': 3,
    'E': 4,
    'F': 5,
    'G': 6,
    'H': 7,
    'I': 8,
    'J': 9,
    'K': 10,
    'L': 11,
    'M': 12,
    'N': 13,
    'O': 14,
    'P': 15,
    'Q': 16,
    'R': 17,
    'S': 18,
    'T': 19,
    'U': 20,
    'V': 21,
    'W': 22,
    'X': 23,
    'Y': 24,
    'Z': 25,
    'a': 26,
    'b': 27,
    'c': 28,
    'd': 29,
    'e': 30,
    'f': 31,
    'g': 32,
    'h': 33,
    'i': 34,
    'j': 35,
    'k': 36,
    'l': 37,
    'm': 38,
    'n': 39,
    'o': 40,
    'p': 41,
    'q': 42,
    'r': 43,
    's': 44,
    't': 45,
    'u': 46,
    'v': 47,
    'w': 48,
    'x': 49,
    'y': 50,
    'z': 51,
    '0': 52,
    '1': 53,
    '2': 54,
    '3': 55,
    '4': 56,
    '5': 57,
    '6': 58,
    '7': 59,
    '8': 60,
    '9': 61,
    '+': 62,
    '/': 63,
}

def quadruplets_base64(s):
    while s:
        a, b, c, d = table_a2b_base64[s[0]], table_a2b_base64[s[1]], table_a2b_base64[s[2]], table_a2b_base64[s[3]]
        s = s[4:]
        yield a, b, c, d

def a2b_base64(s):
    s = s.rstrip()
    # clean out all invalid characters, this also strips the final '=' padding
    clean_s = []
    for item in s:
        if item in table_a2b_base64:
            clean_s.append(item)
    s = ''.join(clean_s)
    # Add '=' padding back into the string
    if len(s) % 4:
        s = s + ('=' * (4 - len(s) % 4))
     
    a = quadruplets_base64(s[:-4])
    result = [
        chr(A << 2 | ((B >> 4) & 0x3)) + 
        chr((B & 0xF) << 4 | ((C >> 2 ) & 0xF)) + 
        chr((C & 0x3) << 6 | D )
        for A, B, C, D in a]

    if s:
        final = s[-4:]
        if final[2] == '=':
            A = table_a2b_base64[final[0]]
            B = table_a2b_base64[final[1]]
            snippet =  chr(A << 2 | ((B >> 4) & 0x3))
        elif final[3] == '=':
            A = table_a2b_base64[final[0]]
            B = table_a2b_base64[final[1]]
            C = table_a2b_base64[final[2]]
            snippet =  chr(A << 2 | ((B >> 4) & 0x3)) + \
                    chr((B & 0xF) << 4 | ((C >> 2 ) & 0xF))
        else:
            A = table_a2b_base64[final[0]]
            B = table_a2b_base64[final[1]]
            C = table_a2b_base64[final[2]]
            D = table_a2b_base64[final[3]]
            snippet =  chr(A << 2 | ((B >> 4) & 0x3)) + \
                    chr((B & 0xF) << 4 | ((C >> 2 ) & 0xF)) + \
                    chr((C & 0x3) << 6 | D )
        result.append(snippet)

    return ''.join(result) 
    
table_b2a_base64 = \
"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

def b2a_base64(s):
    length = len(s)
    final_length = length % 3
    
    a = triples(s[ :length - final_length])

    result = [''.join(
        [table_b2a_base64[( A >> 2                    ) & 0x3F],
         table_b2a_base64[((A << 4) | ((B >> 4) & 0xF)) & 0x3F],
         table_b2a_base64[((B << 2) | ((C >> 6) & 0x3)) & 0x3F],
         table_b2a_base64[( C                         ) & 0x3F]])
              for A, B, C in a]

    final = s[length - final_length:]
    if final_length == 0:
        snippet = ''
    elif final_length == 1:
        a = ord(final[0])
        snippet = table_b2a_base64[(a >> 2 ) & 0x3F] + \
                  table_b2a_base64[(a << 4 ) & 0x3F] + '=='
    else:
        a = ord(final[0])
        b = ord(final[1])
        snippet = table_b2a_base64[(a >> 2) & 0x3F] + \
                  table_b2a_base64[((a << 4) | (b >> 4) & 0xF) & 0x3F] + \
                  table_b2a_base64[(b << 2) & 0x3F] + '='
    return ''.join(result) + snippet + '\n'



def a2b_qp(s):
    pass

def b2a_qp(s):
    def f(c):
        if '!' <= c <= '<' or '>' <= c <= '~':
            return c
        return '=' + str(hex(ord(c)))
    return ''.join([ f(c) for c in s])

hex_numbers = '0123456789ABCDEF'
def hex(n):
    if n == 0:
        return '0'
    
    if n < 0:
        n = -n
        sign = '-'
    else:
        sign = ''
    arr = []
    for nibble in hexgen(n):
        arr = [hex_numbers[nibble]] + arr
    return sign + ''.join(arr)
        
def hexgen(n):
    """ Yield a nibble at a time. """
    while n:
        remainder = n % 0x10
        n = n / 0x10
        yield remainder
