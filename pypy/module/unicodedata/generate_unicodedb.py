#!/usr/bin/env python
import sys

class Unicodechar:
    def __init__(self, data):
        if not data[1] or data[1][0] == '<' and data[1][-1] == '>':
            self.name = None
        else:
            self.name = data[1]
        self.category = data[2]
        self.combining = 0
        if data[3]:
            self.combining = int(data[3])
        self.bidirectional = data[4]
        self.raw_decomposition = ''
        self.decomposition = []
        self.isCompatibility = False
        self.canonical_decomp = None
        self.compat_decomp = None
        self.excluded = False
        self.decompositionTag = ''
        if data[5]:
            self.raw_decomposition = data[5]
            if data[5][0] == '<':
                self.isCompatibility = True
                self.decompositionTag, decomp = data[5].split(None, 1)
            else:
                decomp = data[5]
            self.decomposition = map(lambda x:int(x, 16), decomp.split())
        self.decimal = None
        if data[6]:
            self.decimal = int(data[6])
        self.digit = None
        if data[7]:
            self.digit = int(data[7])
        self.numeric = None
        if data[8]:
            try:
                numerator, denomenator = data[8].split('/')
                self.numeric = float(numerator) / float(denomenator)
            except ValueError:
                self.numeric = float(data[8])
        self.mirrored = (data[9] == 'Y')
        self.upper = None
        if data[12]:
            self.upper = int(data[12], 16)
        self.lower = None
        if data[13]:
            self.lower = int(data[13], 16) 
        self.title = None
        if data[14]:
            self.title = int(data[14], 16)
        

def get_compat_decomposition(table, code):
    if not table[code].decomposition:
        return [code]
    if not table[code].compat_decomp:
        result = []
        for decomp in table[code].decomposition:
            result.extend(get_compat_decomposition(table, decomp))
        table[code].compat_decomp = result
    return table[code].compat_decomp

def get_canonical_decomposition(table, code):
    if not table[code].decomposition or table[code].isCompatibility:
        return [code]
    if not table[code].canonical_decomp:
        result = []
        for decomp in table[code].decomposition:
            result.extend(get_canonical_decomposition(table, decomp))
        table[code].canonical_decomp = result
    return table[code].canonical_decomp

def read_unicodedata(unicodedata_file, exclusions_file):
    rangeFirst = {}
    rangeLast = {}
    table = [Unicodechar(['0000', None, 'Cn'] + [''] * 12)] * (sys.maxunicode + 1)
    for line in unicodedata_file:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        data = [ v.strip() for v in line.split(';') ]
        if data[1].endswith(', First>'):
            code = int(data[0], 16)
            name = data[1][1:-len(', First>')]
            rangeFirst[name] = (code, data)
            continue
        if data[1].endswith(', Last>'):
            code = int(data[0], 16)
            rangeLast[name]  = code
            continue
        code = int(data[0], 16)
        u = Unicodechar(data)
        table[code] = u

    # Expand ranges
    for name, (start, data) in rangeFirst.iteritems():
        end = rangeLast[name]
        unichar = Unicodechar(['0000', None] + data[2:])
        for code in range(start, end + 1):
            table[code] = unichar
    # Read exclusions
    for line in exclusions_file:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        table[int(line, 16)].excluded = True
        
    # Compute full decompositions.
    for code in range(len(table)):
        get_canonical_decomposition(table, code)
        get_compat_decomposition(table, code)

    return table

def writeDict(outfile, name, dictionary):
    print >> outfile, '%s = {' % name
    keys = dictionary.keys()
    keys.sort()
    for key in keys:
        print >> outfile, '%r: %r,'%(key, dictionary[key])
    print >> outfile, '}'
    print >> outfile

class Cache:
    def __init__(self):
        self._cache = {}
        self._strings = []
    def get(self, string):
        try:
            return self._cache[string]
        except KeyError:
            index = len(self._cache)
            self._cache[string] = index
            self._strings.append(string)
            return index

def writeCategory(outfile, table, name, categoryNames):
    pgbits = 8
    chunksize = 64
    pgsize = 1 << pgbits
    bytemask = ~(-1 << pgbits)
    pages = []
    print >> outfile, '_%s_names = %r' % (name, categoryNames)
    print >> outfile, '_%s_pgtbl = "".join([' % name
    line = []
    for i in range(0, len(table), pgsize):
        result = []
        for char in table[i:i + pgsize]:
            result.append(chr(categoryNames.index(getattr(char, name))))
        categorytbl = ''.join(result)
        try:
            page = pages.index(categorytbl)
        except ValueError:
            page = len(pages)
            pages.append(categorytbl)
            assert len(pages) < 256, 'Too many unique pages for category %s.' % name
        line.append(chr(page))
        if len(line) >= chunksize:
            print >> outfile, repr(''.join(line))
            line = []
    if len(line) > 0:
        print >> outfile, repr(''.join(line))
    print >> outfile, '])'

    # Dump pgtbl
    print >> outfile, '_%s = ( ' % name
    for page_string in pages:
        print >> outfile, '"".join(['
        for index in range(0, len(page_string), chunksize):
            print >> outfile, repr(page_string[index:index + chunksize])
        print >> outfile, ']),'
    print >> outfile, ')'
    print >> outfile, '''
def %s(code):
    return _%s_names[ord(_%s[ord(_%s_pgtbl[code >> %d])][code & %d])]
'''%(name, name, name, name, pgbits, bytemask)

def writeUnicodedata(version, table, outfile):
    # Version
    print >> outfile, 'version = %r' % version
    print >> outfile

    cjk_end = 0x9FA5
    if version >= "4.1":
        cjk_end = 0x9FBB

    # Character names
    print >> outfile, '_charnames = {'
    for code in range(len(table)):
        if table[code].name:
            print >> outfile, '%r: %r,'%(code, table[code].name)
    print >> outfile, '''}
    
_code_by_name = dict(zip(_charnames.itervalues(), _charnames.iterkeys()))

_cjk_prefix = "CJK UNIFIED IDEOGRAPH-"
_hangul_prefix = 'HANGUL SYLLABLE '

_hangul_L = ['G', 'GG', 'N', 'D', 'DD', 'R', 'M', 'B', 'BB',
            'S', 'SS', '', 'J', 'JJ', 'C', 'K', 'T', 'P', 'H']
_hangul_V = ['A', 'AE', 'YA', 'YAE', 'EO', 'E', 'YEO', 'YE', 'O', 'WA', 'WAE',
            'OE', 'YO', 'U', 'WEO', 'WE', 'WI', 'YU', 'EU', 'YI', 'I']
_hangul_T = ['', 'G', 'GG', 'GS', 'N', 'NJ', 'NH', 'D', 'L', 'LG', 'LM',
            'LB', 'LS', 'LT', 'LP', 'LH', 'M', 'B', 'BS', 'S', 'SS',
            'NG', 'J', 'C', 'K', 'T', 'P', 'H']

def _lookup_hangul(syllables):
    l_code = v_code = t_code = -1
    for i in range(len(_hangul_L)):
        jamo = _hangul_L[i]
        if (syllables[:len(jamo)] == jamo and
            (l_code < 0 or len(jamo) > len(_hangul_L[l_code]))):
            l_code = i
    if l_code < 0:
        raise KeyError
    start = len(_hangul_L[l_code])

    for i in range(len(_hangul_V)):
        jamo = _hangul_V[i]
        if (syllables[start:start + len(jamo)] == jamo and
            (v_code < 0 or len(jamo) > len(_hangul_V[v_code]))):
            v_code = i
    if v_code < 0:
        raise KeyError
    start += len(_hangul_V[v_code])

    for i in range(len(_hangul_T)):
        jamo = _hangul_T[i]
        if (syllables[start:start + len(jamo)] == jamo and
            (t_code < 0 or len(jamo) > len(_hangul_T[t_code]))):
            t_code = i
    if t_code < 0:
        raise KeyError
    start += len(_hangul_T[t_code])

    if len(syllables[start:]):
        raise KeyError
    return 0xAC00 + (l_code * 21 + v_code) * 28 + t_code

_hexdigits = "0123456789ABCDEF"
def _lookup_cjk(cjk_code):
    if len(cjk_code) not in  (4,5):
        raise KeyError
    for c in cjk_code:
        if c not in _hexdigits:
            raise KeyError
    code = int(cjk_code, 16)
    if (0x3400 <= code <= 0x4DB5 or
        0x4E00 <= code <= 0x%X or 0x9FA5 or # 9FBB in Unicode 4.1
        0x20000 <= code <= 0x2A6D6):
        return code
    raise KeyError

def lookup(name):
    if name[:len(_cjk_prefix)] == _cjk_prefix:
        return _lookup_cjk(name[len(_cjk_prefix):])
    if name[:len(_hangul_prefix)] == _hangul_prefix:
        return _lookup_hangul(name[len(_hangul_prefix):])
    return _code_by_name[name]

def name(code):
    if (0x3400 <= code <= 0x4DB5 or
        0x4E00 <= code <= 0x9FA5):
        return "CJK UNIFIED IDEOGRAPH-" + (_hexdigits[(code >> 12) & 0xf] +
                                           _hexdigits[(code >> 8) & 0xf] +
                                           _hexdigits[(code >> 4) & 0xf] +
                                           _hexdigits[code & 0xf])
    
    if 0x20000 <= code <= 0x2A6D6:
        return "CJK UNIFIED IDEOGRAPH-2" + (_hexdigits[(code >> 12) & 0xf] +
                                            _hexdigits[(code >> 8) & 0xf] +
                                            _hexdigits[(code >> 4) & 0xf] +
                                            _hexdigits[code & 0xf])
    if 0xAC00 <= code <= 0xD7A3:
        vl_code, t_code = divmod(code - 0xAC00, len(_hangul_T))
        l_code, v_code = divmod(vl_code,  len(_hangul_V))
        return ("HANGUL SYLLABLE " + _hangul_L[l_code] +
                _hangul_V[v_code] + _hangul_T[t_code])
    
    return _charnames[code]
''' % cjk_end

    # Categories
    categories = {}
    bidirs = {}
    for char in table:
        categories[char.category] = 1
        bidirs[char.bidirectional] = 1
    category_names = categories.keys()
    category_names.sort()
    if len(category_names) > 32:
        raise RuntimeError('Too many general categories defined.')
    bidirectional_names = bidirs.keys()
    bidirectional_names.sort()
    if len(bidirectional_names) > 32:
        raise RuntimeError('Too many bidirectional categories defined.')

    writeCategory(outfile, table, 'category', category_names)
    writeCategory(outfile, table, 'bidirectional', bidirectional_names)
    print >> outfile, '''
def isspace(code):
    return category(code) == "Zs" or bidirectional(code) in ("WS", "B", "S")
def islower(code):
    return category(code) == "Ll"
def isupper(code):
    return category(code) == "Lu"
def istitle(code):
    return category(code) == "Lt"
def iscased(code):
    return category(code) in ("Ll", "Lu", "Lt")
def isalpha(code):
    return category(code) in ("Lm", "Lt", "Lu", "Ll", "Lo")
def islinebreak(code):
    return category(code) == "Zl" or bidirectional(code) == "B"
'''
    
    # Numeric characters
    decimal = {}
    digit = {}
    numeric = {}
    for code in range(len(table)):
        if table[code].decimal is not None:
            decimal[code] = table[code].decimal
        if table[code].digit is not None:
            digit[code] = table[code].digit
        if table[code].numeric is not None:
            numeric[code] = table[code].numeric
            
    writeDict(outfile, '_decimal', decimal)
    writeDict(outfile, '_digit', digit)
    writeDict(outfile, '_numeric', numeric)
    print >> outfile, '''
def decimal(code):
    return _decimal[code]

def isdecimal(code):
    return code in _decimal

def digit(code):
    return _digit[code]

def isdigit(code):
    return code in _digit

def numeric(code):
    return _numeric[code]

def isnumeric(code):
    return code in _numeric

'''
    # Combining
    combining = {}
    for code in range(len(table)):
        if table[code].combining:
            combining[code] = table[code].combining
    writeDict(outfile, '_combining', combining)
    print >> outfile, '''
def combining(code):
    return _combining.get(code, 0)

'''
    # Mirrored
    mirrored = {}
    for code in range(len(table)):
        if table[code].mirrored:
            mirrored[code] = 1
    writeDict(outfile, '_mirrored', mirrored)
    print >> outfile, '''
def mirrored(code):
    return _mirrored.get(code, 0)

'''
    # Case conversion
    toupper = {}
    tolower = {}
    totitle = {}
    for code in range(len(table)):
        if table[code].upper:
            toupper[code] = table[code].upper
        if table[code].lower:
            tolower[code] = table[code].lower
        if table[code].title:
            totitle[code] = table[code].title
    writeDict(outfile, '_toupper', toupper)
    writeDict(outfile, '_tolower', tolower)
    writeDict(outfile, '_totitle', totitle)
    print >> outfile, '''
def toupper(code):
    return _toupper.get(code, code)
def tolower(code):
    return _tolower.get(code, code)
def totitle(code):
    return _totitle.get(code, code)
'''
    # Decomposition
    decomposition = {}
    for code in range(len(table)):
        if table[code].raw_decomposition:
            decomposition[code] = table[code].raw_decomposition
    writeDict(outfile, '_raw_decomposition', decomposition)
    print >> outfile, '''
def decomposition(code):
    return _raw_decomposition.get(code,'')

'''
    # Collect the composition pairs.
    compositions = {}
    for code in range(len(table)):
        unichar = table[code]
        if (not unichar.decomposition or
            unichar.isCompatibility or
            unichar.excluded or
            len(unichar.decomposition) != 2 or
            table[unichar.decomposition[0]].combining):
            continue
        compositions[tuple(unichar.decomposition)] = code
    writeDict(outfile, '_composition', compositions)

    decomposition = {}
    for code in range(len(table)):
        if table[code].canonical_decomp:
            decomposition[code] = table[code].canonical_decomp
    writeDict(outfile, '_canon_decomposition', decomposition)

    decomposition = {}
    for code in range(len(table)):
        if table[code].compat_decomp:
            decomposition[code] = table[code].compat_decomp
    writeDict(outfile, '_compat_decomposition', decomposition)


if __name__ == '__main__':
    import getopt, re
    infile = None
    outfile = sys.stdout
    unidata_version = None
    options, args = getopt.getopt(sys.argv[1:], 'o:v:',
                                  ('output=', 'version='))
    for opt, val in options:
        if opt in ('-o', '--output'):
            outfile = open(val, 'w')
        if opt in ('-v', '--version'):
            unidata_version = val

    if len(args) != 2:
        raise RuntimeError('Usage: %s [-o outfile] [-v version] UnicodeDataFile CompositionExclutionsFile')
    
    infilename = args[0]
    infile = open(infilename, 'r')
    exclusions = open(args[1])
    if unidata_version is None:
        m = re.search(r'-([0-9]+\.)+', infilename)
        if m:
            unidata_version = infilename[m.start() + 1:m.end() - 1]
    
    if unidata_version is None:
        raise ValueError('No version specified')

    table = read_unicodedata(infile, exclusions)
    print >> outfile, '# UNICODE CHARACTER DATABASE'
    print >> outfile, '# This file was generated with the command:'
    print >> outfile, '#    ', ' '.join(sys.argv)
    print >> outfile
    writeUnicodedata(unidata_version, table, outfile)
