from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.basestringtype import basestring_typedef

from sys import maxint
from pypy.rlib.objectmodel import specialize

def wrapstr(space, s):
    from pypy.objspace.std.stringobject import W_StringObject
    from pypy.objspace.std.ropeobject import rope, W_RopeObject
    if space.config.objspace.std.sharesmallstr:
        if space.config.objspace.std.withprebuiltchar:
            # share characters and empty string
            if len(s) <= 1:
                if len(s) == 0:
                    if space.config.objspace.std.withrope:
                        return W_RopeObject.EMPTY
                    return W_StringObject.EMPTY
                else:
                    s = s[0]     # annotator hint: a single char
                    return wrapchar(space, s)
        else:
            # only share the empty string
            if len(s) == 0:
                if space.config.objspace.std.withrope:
                    return W_RopeObject.EMPTY
                return W_StringObject.EMPTY
    if space.config.objspace.std.withrope:
        return W_RopeObject(rope.LiteralStringNode(s))
    return W_StringObject(s)

def wrapchar(space, c):
    from pypy.objspace.std.stringobject import W_StringObject
    from pypy.objspace.std.ropeobject import rope, W_RopeObject
    if space.config.objspace.std.withprebuiltchar:
        if space.config.objspace.std.withrope:
            return W_RopeObject.PREBUILT[ord(c)]
        return W_StringObject.PREBUILT[ord(c)]
    else:
        if space.config.objspace.std.withrope:
            return W_RopeObject(rope.LiteralStringNode(c))
        return W_StringObject(c)

def sliced(space, s, start, stop, orig_obj):
    assert start >= 0
    assert stop >= 0 
    assert not space.config.objspace.std.withrope
    if start == 0 and stop == len(s) and space.is_w(space.type(orig_obj), space.w_str):
        return orig_obj
    if space.config.objspace.std.withstrslice:
        from pypy.objspace.std.strsliceobject import W_StringSliceObject
        # XXX heuristic, should be improved!
        if (stop - start) > len(s) * 0.20 + 40:
            return W_StringSliceObject(s, start, stop)
    return wrapstr(space, s[start:stop])

def joined(space, strlist):
    assert not space.config.objspace.std.withrope
    if space.config.objspace.std.withstrjoin:
        from pypy.objspace.std.strjoinobject import W_StringJoinObject
        return W_StringJoinObject(strlist)
    else:
        return wrapstr(space, "".join(strlist))

def joined2(space, str1, str2):
    assert not space.config.objspace.std.withrope
    if space.config.objspace.std.withstrjoin:
        from pypy.objspace.std.strjoinobject import W_StringJoinObject
        return W_StringJoinObject([str1, str2])
    else:
        return wrapstr(space, str1 + str2)

str_join    = SMM('join', 2,
                  doc='S.join(sequence) -> string\n\nReturn a string which is'
                      ' the concatenation of the strings in the\nsequence. '
                      ' The separator between elements is S.')
str_split   = SMM('split', 3, defaults=(None,-1),
                  doc='S.split([sep [,maxsplit]]) -> list of strings\n\nReturn'
                      ' a list of the words in the string S, using sep as'
                      ' the\ndelimiter string.  If maxsplit is given, at most'
                      ' maxsplit\nsplits are done. If sep is not specified or'
                      ' is None, any\nwhitespace string is a separator.')
str_rsplit  = SMM('rsplit', 3, defaults=(None,-1),
                  doc='S.rsplit([sep [,maxsplit]]) -> list of'
                      ' strings\n\nReturn a list of the words in the string S,'
                      ' using sep as the\ndelimiter string, starting at the'
                      ' end of the string and working\nto the front.  If'
                      ' maxsplit is given, at most maxsplit splits are\ndone.'
                      ' If sep is not specified or is None, any whitespace'
                      ' string\nis a separator.')
str_isdigit    = SMM('isdigit', 1,
                     doc='S.isdigit() -> bool\n\nReturn True if all characters'
                         ' in S are digits\nand there is at least one'
                         ' character in S, False otherwise.')
str_isalpha    = SMM('isalpha', 1,
                     doc='S.isalpha() -> bool\n\nReturn True if all characters'
                         ' in S are alphabetic\nand there is at least one'
                         ' character in S, False otherwise.')
str_isspace    = SMM('isspace', 1,
                     doc='S.isspace() -> bool\n\nReturn True if all characters'
                         ' in S are whitespace\nand there is at least one'
                         ' character in S, False otherwise.')
str_isupper    = SMM('isupper', 1,
                     doc='S.isupper() -> bool\n\nReturn True if all cased'
                         ' characters in S are uppercase and there is\nat'
                         ' least one cased character in S, False otherwise.')
str_islower    = SMM('islower', 1,
                     doc='S.islower() -> bool\n\nReturn True if all cased'
                         ' characters in S are lowercase and there is\nat'
                         ' least one cased character in S, False otherwise.')
str_istitle    = SMM('istitle', 1,
                     doc='S.istitle() -> bool\n\nReturn True if S is a'
                         ' titlecased string and there is at least'
                         ' one\ncharacter in S, i.e. uppercase characters may'
                         ' only follow uncased\ncharacters and lowercase'
                         ' characters only cased ones. Return'
                         ' False\notherwise.')
str_isalnum    = SMM('isalnum', 1,
                     doc='S.isalnum() -> bool\n\nReturn True if all characters'
                         ' in S are alphanumeric\nand there is at least one'
                         ' character in S, False otherwise.')
str_ljust      = SMM('ljust', 3, defaults=(' ',),
                     doc='S.ljust(width[, fillchar]) -> string\n\nReturn S'
                         ' left justified in a string of length width. Padding'
                         ' is\ndone using the specified fill character'
                         ' (default is a space).')
str_rjust      = SMM('rjust', 3, defaults=(' ',),
                     doc='S.rjust(width[, fillchar]) -> string\n\nReturn S'
                         ' right justified in a string of length width.'
                         ' Padding is\ndone using the specified fill character'
                         ' (default is a space)')
str_upper      = SMM('upper', 1,
                     doc='S.upper() -> string\n\nReturn a copy of the string S'
                         ' converted to uppercase.')
str_lower      = SMM('lower', 1,
                     doc='S.lower() -> string\n\nReturn a copy of the string S'
                         ' converted to lowercase.')
str_swapcase   = SMM('swapcase', 1,
                     doc='S.swapcase() -> string\n\nReturn a copy of the'
                         ' string S with uppercase characters\nconverted to'
                         ' lowercase and vice versa.')
str_capitalize = SMM('capitalize', 1,
                     doc='S.capitalize() -> string\n\nReturn a copy of the'
                         ' string S with only its first'
                         ' character\ncapitalized.')
str_title      = SMM('title', 1,
                     doc='S.title() -> string\n\nReturn a titlecased version'
                         ' of S, i.e. words start with uppercase\ncharacters,'
                         ' all remaining cased characters have lowercase.')
str_find       = SMM('find', 4, defaults=(0, maxint),
                     doc='S.find(sub [,start [,end]]) -> int\n\nReturn the'
                         ' lowest index in S where substring sub is'
                         ' found,\nsuch that sub is contained within'
                         ' s[start,end].  Optional\narguments start and end'
                         ' are interpreted as in slice notation.\n\nReturn -1'
                         ' on failure.')
str_rfind      = SMM('rfind', 4, defaults=(0, maxint),
                     doc='S.rfind(sub [,start [,end]]) -> int\n\nReturn the'
                         ' highest index in S where substring sub is'
                         ' found,\nsuch that sub is contained within'
                         ' s[start,end].  Optional\narguments start and end'
                         ' are interpreted as in slice notation.\n\nReturn -1'
                         ' on failure.')
str_partition  = SMM('partition', 2,
                     doc='S.partition(sep) -> (head, sep, tail)\n\nSearches'
                         ' for the separator sep in S, and returns the part before'
                         ' it,\nthe separator itself, and the part after it.  If'
                         ' the separator is not\nfound, returns S and two empty'
                         ' strings.')
str_rpartition = SMM('rpartition', 2,
                     doc='S.rpartition(sep) -> (tail, sep, head)\n\nSearches'
                         ' for the separator sep in S, starting at the end of S,'
                         ' and returns\nthe part before it, the separator itself,'
                         ' and the part after it.  If the\nseparator is not found,'
                         ' returns two empty strings and S.')
str_index      = SMM('index', 4, defaults=(0, maxint),
                     doc='S.index(sub [,start [,end]]) -> int\n\nLike S.find()'
                         ' but raise ValueError when the substring is not'
                         ' found.')
str_rindex     = SMM('rindex', 4, defaults=(0, maxint),
                     doc='S.rindex(sub [,start [,end]]) -> int\n\nLike'
                         ' S.rfind() but raise ValueError when the substring'
                         ' is not found.')
str_replace    = SMM('replace', 4, defaults=(-1,),
                     doc='S.replace (old, new[, count]) -> string\n\nReturn a'
                         ' copy of string S with all occurrences of'
                         ' substring\nold replaced by new.  If the optional'
                         ' argument count is\ngiven, only the first count'
                         ' occurrences are replaced.')
str_zfill      = SMM('zfill', 2,
                     doc='S.zfill(width) -> string\n\nPad a numeric string S'
                         ' with zeros on the left, to fill a field\nof the'
                         ' specified width.  The string S is never truncated.')
str_strip      = SMM('strip',  2, defaults=(None,),
                     doc='S.strip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with leading and'
                         ' trailing\nwhitespace removed.\nIf chars is given'
                         ' and not None, remove characters in chars'
                         ' instead.\nIf chars is unicode, S will be converted'
                         ' to unicode before stripping')
str_rstrip     = SMM('rstrip', 2, defaults=(None,),
                     doc='S.rstrip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with trailing whitespace'
                         ' removed.\nIf chars is given and not None, remove'
                         ' characters in chars instead.\nIf chars is unicode,'
                         ' S will be converted to unicode before stripping')
str_lstrip     = SMM('lstrip', 2, defaults=(None,),
                     doc='S.lstrip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with leading whitespace'
                         ' removed.\nIf chars is given and not None, remove'
                         ' characters in chars instead.\nIf chars is unicode,'
                         ' S will be converted to unicode before stripping')
str_center     = SMM('center', 3, defaults=(' ',),
                     doc='S.center(width[, fillchar]) -> string\n\nReturn S'
                         ' centered in a string of length width. Padding'
                         ' is\ndone using the specified fill character'
                         ' (default is a space)')
str_count      = SMM('count', 4, defaults=(0, maxint),
                     doc='S.count(sub[, start[, end]]) -> int\n\nReturn the'
                         ' number of occurrences of substring sub in'
                         ' string\nS[start:end].  Optional arguments start and'
                         ' end are\ninterpreted as in slice notation.')
str_endswith   = SMM('endswith', 4, defaults=(0, maxint),
                     doc='S.endswith(suffix[, start[, end]]) -> bool\n\nReturn'
                         ' True if S ends with the specified suffix, False'
                         ' otherwise.\nWith optional start, test S beginning'
                         ' at that position.\nWith optional end, stop'
                         ' comparing S at that position.')
str_expandtabs = SMM('expandtabs', 2, defaults=(8,),
                     doc='S.expandtabs([tabsize]) -> string\n\nReturn a copy'
                         ' of S where all tab characters are expanded using'
                         ' spaces.\nIf tabsize is not given, a tab size of 8'
                         ' characters is assumed.')
str_splitlines = SMM('splitlines', 2, defaults=(0,),
                     doc='S.splitlines([keepends]) -> list of'
                         ' strings\n\nReturn a list of the lines in S,'
                         ' breaking at line boundaries.\nLine breaks are not'
                         ' included in the resulting list unless keepends\nis'
                         ' given and true.')
str_startswith = SMM('startswith', 4, defaults=(0, maxint),
                     doc='S.startswith(prefix[, start[, end]]) ->'
                         ' bool\n\nReturn True if S starts with the specified'
                         ' prefix, False otherwise.\nWith optional start, test'
                         ' S beginning at that position.\nWith optional end,'
                         ' stop comparing S at that position.')
str_translate  = SMM('translate', 3, defaults=('',), #unicode mimic not supported now
                     doc='S.translate(table [,deletechars]) -> string\n\n'
                         'Return a copy of the string S, where all characters'
                         ' occurring\nin the optional argument deletechars are'
                         ' removed, and the\nremaining characters have been'
                         ' mapped through the given\ntranslation table, which'
                         ' must be a string of length 256.')
str_decode     = SMM('decode', 3, defaults=(None, None),
                     doc='S.decode([encoding[,errors]]) -> object\n\nDecodes S'
                         ' using the codec registered for encoding. encoding'
                         ' defaults\nto the default encoding. errors may be'
                         ' given to set a different error\nhandling scheme.'
                         " Default is 'strict' meaning that encoding errors"
                         ' raise\na UnicodeDecodeError. Other possible values'
                         " are 'ignore' and 'replace'\nas well as any other"
                         ' name registerd with codecs.register_error that'
                         ' is\nable to handle UnicodeDecodeErrors.')
str_encode     = SMM('encode', 3, defaults=(None, None),
                     doc='S.encode([encoding[,errors]]) -> object\n\nEncodes S'
                         ' using the codec registered for encoding. encoding'
                         ' defaults\nto the default encoding. errors may be'
                         ' given to set a different error\nhandling scheme.'
                         " Default is 'strict' meaning that encoding errors"
                         ' raise\na UnicodeEncodeError. Other possible values'
                         " are 'ignore', 'replace' and\n'xmlcharrefreplace' as"
                         ' well as any other name registered'
                         ' with\ncodecs.register_error that is able to handle'
                         ' UnicodeEncodeErrors.')

# ____________________________________________________________

def descr__new__(space, w_stringtype, w_object=''):
    # NB. the default value of w_object is really a *wrapped* empty string:
    #     there is gateway magic at work
    from pypy.objspace.std.stringobject import W_StringObject
    w_obj = space.str(w_object)
    if space.is_w(w_stringtype, space.w_str):
        return w_obj  # XXX might be reworked when space.str() typechecks
    value = space.str_w(w_obj)
    if space.config.objspace.std.withrope:
        from pypy.objspace.std.ropeobject import rope, W_RopeObject
        w_obj = space.allocate_instance(W_RopeObject, w_stringtype)
        W_RopeObject.__init__(w_obj, rope.LiteralStringNode(value))
        return w_obj
    else:
        w_obj = space.allocate_instance(W_StringObject, w_stringtype)
        W_StringObject.__init__(w_obj, value)
        return w_obj

# ____________________________________________________________

str_typedef = StdTypeDef("str", basestring_typedef,
    __new__ = newmethod(descr__new__),
    __doc__ = '''str(object) -> string

Return a nice string representation of the object.
If the argument is a string, the return value is the same object.'''
    )

str_typedef.registermethods(globals())

# ____________________________________________________________

# Helpers for several string implementations

@specialize.argtype(0)
def stringendswith(u_self, suffix, start, end):
    begin = end - len(suffix)
    if begin < start:
        return False
    for i in range(len(suffix)):
        if u_self[begin+i] != suffix[i]:
            return False
    return True

@specialize.argtype(0)
def stringstartswith(u_self, prefix, start, end):
    stop = start + len(prefix)
    if stop > end:
        return False
    for i in range(len(prefix)):
        if u_self[start+i] != prefix[i]:
            return False
    return True
    
