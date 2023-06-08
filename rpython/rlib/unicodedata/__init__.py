# This is the default unicodedb used in various places:
# - the unicode type
# - the regular expression engine
from rpython.rlib.unicodedata import unicodedb_5_2_0 as unicodedb

# to get information about individual unicode chars look at:
# http://www.fileformat.info/info/unicode/char/search.htm

# the following externally usable functions are defined in each of the
# unicodedb files.

# all code arguments are integers


"""
lookup(name, with_named_sequence=False, with_alias=False)
    Look up character by name.

    If a character with the given name is found, return the
    corresponding character.  If not found, KeyError is raised.

    If with_named_sequence is True, named sequences are also searched. They are
    returned into the form of a code point in a private use area and must be
    converted with lookup_named_sequence and lookup_named_sequence_length

    with_alias should not be set to True, use lookup_with_alias instead.

lookup_with_alias(name, with_named_sequence=False)
    Like lookup, but will also search the name aliases.

lookup_named_sequence(code)
    Turns a code point that is the result of lookup or lookup_with_alias with
    argument with_named_sequence=True and returns a utf-8 encoded unicode
    string, if the code point is in the right range of the private use area
    that lookup uses for named sequences. Otherwise None is returned.

lookup_named_sequence_length(code)
    Like lookup_named_sequence, but returns the number of code points of the
    named sequence that code represents.

name(code)
    Returns the name assigned to the character code as a string.
    If no name is defined, KeyError is raised.

composition(current, next)
    Composes two code points current and next into a new one. Raises KeyError
    if that's not possible.

decomposition(code)
    Returns the character decomposition mapping assigned to the character code
    as string.
    An empty string is returned in case no such mapping is defined.

canon_decomposition(code)
    Returns the canonical decomposition of code as a list of integers.
    Returns an empty list if the code point is not decomposable.

compat_decomposition(code)
    Returns the compatibility decomposition of code as a list of integers.
    Returns an empty list if the code point is not decomposable.

combining(code)
    Returns the canonical combining class assigned to the character code as integer.
    Returns 0 if no combining class is defined.

category(code)
    Returns the general category assigned to the character code as string.

bidirectional(code)
    Returns the bidirectional class assigned to the character code as string.
    If no such value is defined, an empty string is returned.

east_asian_width(code)
    Returns the east asian width assigned to the character code as string.


The following functions all check various properties of characters:

isspace(code)
isalpha(code)
islinebreak(code)
isnumeric(code)
isdigit(code)
isdecimal(code)
isalnum(code)
isupper(code)
istitle(code)
islower(code)
iscased(code)
isxidstart(code)
isxidcontinue(code)
isprintable(code)
iscaseignorable(code)

mirrored(code)
    Returns the mirrored property assigned to the character code as integer.

decimal(code)
    Converts a Unicode character into its equivalent decimal value.

    Returns the decimal value assigned to the character code as integer.
    Otherwise a KeyError is raised.

digit(code)
    Converts a Unicode character into its equivalent digit value.

    Returns the digit value assigned to the character code as integer.
    Otherwise a KeyError is raised.

numeric(code)
    Converts a Unicode character into its equivalent numeric value.

    Returns the numeric value assigned to the character code as float.
    Otherwise a KeyError is raised.

toupper(code)
    Return the upper case version of the code point, or just the argument
    itself, if it is not cased. This uses the "simple" case folding rules,
    where every code point maps to one code point only.

tolower(code)
    Return the lower case version of the code point, or just the argument
    itself, if it is not cased. This uses the "simple" case folding rules,
    where every code point maps to one code point only.

totitle(code)
    Return the title case version of the code point, or just the argument
    itself, if it is not cased. This uses the "simple" case folding rules,
    where every code point maps to one code point only.

toupper_full(code)
    Return the upper case version of the code point, or just the argument
    itself, if it is not cased. This uses the "full" case folding rules,
    thus it returns a list of code points.

tolower_full(code)
    Return the lower case version of the code point, or just the argument
    itself, if it is not cased. This uses the "full" case folding rules,
    thus it returns a list of code points.

totitle_full(code)
    Return the title case version of the code point, or just the argument
    itself, if it is not cased. This uses the "full" case folding rules,
    thus it returns a list of code points.

casefold_lookup(code)
    Return a version of the code point suitable for caseless
    comparisons. Returns a list of code points.

"""
