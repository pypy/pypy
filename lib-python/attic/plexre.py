from StringIO import StringIO
from Pyrex.Plex import Scanner, Lexicon, Traditional, Errors
class Pattern:
    def __init__(self, pattern, flags):
        compiled = Traditional.re(pattern)
        lexicon = Lexicon([(compiled, None)])
        self.lexicon = lexicon
    def match(self, string):
        stream = StringIO(string)
        scanner = Scanner(self.lexicon, stream)
        try:
            scanner.read()
            return 1
        except Errors.UnrecognizedInput:
            return 0
