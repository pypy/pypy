import py
import sys
from pypy.rlib.parsing.tree import Nonterminal, Symbol, RPythonVisitor

class BacktrackException(Exception):
    def __init__(self, error=None):
        self.error = error
        Exception.__init__(self, error)


class TreeOptimizer(RPythonVisitor):
    def visit_or(self, t):
        if len(t.children) == 1:
            return self.dispatch(t.children[0])
        return self.general_nonterminal_visit(t)

    visit_commands = visit_or
    visit_toplevel_or = visit_or

    def visit_negation(self, t):
        child = self.dispatch(t.children[0])
        if child.symbol == "negation":
            child.symbol = "lookahead"
            return child
        t.children[0] = child
        return t

    def general_nonterminal_visit(self, t):
        for i in range(len(t.children)):
            t.children[i] = self.dispatch(t.children[i])
        return t

    def general_visit(self, t):
        return t


syntax = r"""
NAME:
    `[a-zA-Z_][a-zA-Z0-9_]*`;

SPACE:
    ' ';

COMMENT:
    `( *#[^\n]*\n)+`;

IGNORE:
    `(#[^\n]*\n)|\n|\t| `;

newline:
    COMMENT
  | `( *\n *)*`;
    

REGEX:
    r = `\`[^\\\`]*(\\.[^\\\`]*)*\``
    return {Symbol('REGEX', r, None)};

QUOTE:
    r = `'[^\']*'`
    return {Symbol('QUOTE', r, None)};

PYTHONCODE:
    r = `\{[^\n\}]*\}`
    return {Symbol('PYTHONCODE', r, None)};

EOF:
    !__any__;

file:
    IGNORE*
    list
    [EOF];

list:
    content = production+
    return {Nonterminal('list', content)};

production:
    name = NAME
    SPACE*
    args = productionargs
    ':'
    IGNORE*
    what = or_
    IGNORE*
    ';'
    IGNORE*
    return {Nonterminal('production', [name, args, what])};

productionargs:
    '('
    IGNORE*
    args = (
        NAME
        [
            IGNORE*
            ','
            IGNORE*
        ]
    )*
    arg = NAME
    IGNORE*
    ')'
    IGNORE*
    return {Nonterminal('productionargs', args + [arg])}
  | return {Nonterminal('productionargs', [])};
        
    
or_:
    l = (commands ['|' IGNORE*])+
    last = commands
    return {Nonterminal('or', l + [last])}
  | commands;

commands:
    cmd = command
    newline
    cmds = (command [newline])+
    return {Nonterminal('commands', [cmd] + cmds)}
  | command;

command:
    simplecommand;

simplecommand:
    return_
  | if_
  | named_command
  | repetition
  | negation;

return_:
    'return'
    SPACE*
    code = PYTHONCODE
    IGNORE*
    return {Nonterminal('return', [code])};

if_:
    'do'
    newline
    cmd = command
    SPACE*
    'if'
    SPACE*
    condition = PYTHONCODE
    return {Nonterminal('if', [cmd, condition])};

commandchain:
    result = simplecommand+
    return {Nonterminal('commands', result)};

named_command:
    name = NAME
    SPACE*
    '='
    SPACE*
    cmd = command
    return {Nonterminal('named_command', [name, cmd])};

repetition:
    what = enclosed
    SPACE* '?' IGNORE*
    return {Nonterminal('maybe', [what])}
  | what = enclosed
    SPACE*
    repetition = ('*' | '+')
    IGNORE*
    return {Nonterminal('repetition', [repetition, what])};

negation:
    '!'
    SPACE*
    what = negation
    IGNORE*
    return {Nonterminal('negation', [what])}
  | enclosed;

enclosed:
    '<'
    IGNORE*
    what = primary
    IGNORE*
    '>'
    IGNORE*
    return {Nonterminal('exclusive', [what])}
  | '['
    IGNORE*
    what = or_
    IGNORE*
    ']'
    IGNORE*
    return {Nonterminal('ignore', [what])}
  | ['(' IGNORE*] or_ [')' IGNORE*]
  |  primary;

primary:
    call | REGEX [IGNORE*] | QUOTE [IGNORE*];

call:
    x = NAME 
    args = arguments
    IGNORE*
    return {Nonterminal("call", [x, args])};

arguments:
    '('
    IGNORE*
    args = (
        PYTHONCODE
        [IGNORE* ',' IGNORE*]
    )*
    last = PYTHONCODE
    ')'
    IGNORE*
    return {Nonterminal("args", args + [last])}
  | return {Nonterminal("args", [])};
"""

class ErrorInformation(object):
    def __init__(self, pos, expected=None):
        if expected is None:
            expected = []
        self.expected = expected
        self.pos = pos

    def __str__(self):
        return "ErrorInformation(%s, %s)" % (self.pos, self.expected)


class Status(object):
    # status codes:
    NORMAL = 0
    ERROR = 1
    INPROGRESS = 2
    LEFTRECURSION = 3
    SOMESOLUTIONS = 4
    def __repr__(self):
        return "Status(%s, %s, %s, %s)" % (self.pos, self.result, self.error,
                                           self.status)


class ParserBuilder(RPythonVisitor):
    def __init__(self):
        self.code = []
        self.blocks = []
        self.initcode = []
        self.namecount = 0
        self.names = {}
        self.matchers = {}

    def get_code(self):
        assert not self.blocks
        return "\n".join(self.code)

    def make_parser(self):
        m = {'_Status': Status,
             'Nonterminal': Nonterminal,
             'Symbol': Symbol,}
        exec py.code.Source(self.get_code()).compile() in m
        return m['Parser']

    def emit(self, line):
        for line in line.split("\n"):
            self.code.append(" " * (4 * len(self.blocks)) + line)

    def emit_initcode(self, line):
        for line in line.split("\n"):
            self.initcode.append(line)

    def start_block(self, blockstarter):
        assert blockstarter.endswith(":")
        self.emit(blockstarter)
        self.blocks.append(blockstarter)
        def BlockEnder():
            yield None
            self.end_block(blockstarter)
        return BlockEnder()

    def end_block(self, starterpart=""):
        block = self.blocks.pop()
        assert starterpart in block, "ended wrong block %s with %s" % (
            block, starterpart)

    def memoize_header(self, name, args):
        statusclassname = "self._Status_%s" % (name, )
        dictname = "_dict_%s" % (name, )
        self.emit_initcode("self.%s = {}" % (dictname, ))
        if args:
            self.emit("_key = (self._pos, %s)" % (", ".join(args)))
        else:
            self.emit("_key = self._pos")
        self.emit("_status = self.%s.get(_key, None)" % (dictname, ))
        for _ in self.start_block("if _status is None:"):
            self.emit("_status = self.%s[_key] = %s()" % (
                dictname, statusclassname))
        for _ in self.start_block("elif _status.status == _status.NORMAL:"):
            self.emit("self._pos = _status.pos")
            self.emit("return _status")
        for _ in self.start_block("elif _status.status == _status.ERROR:"):
            self.emit("raise self._BacktrackException(_status.error)")
        for _ in self.start_block(
            "elif (_status.status == _status.INPROGRESS or\n"
            "      _status.status == _status.LEFTRECURSION):"):
            self.emit("_status.status = _status.LEFTRECURSION")
            for _ in self.start_block("if _status.result is not None:"):
                self.emit("self._pos = _status.pos")
                self.emit("return _status")
            for _ in self.start_block("else:"):
                self.emit("raise self._BacktrackException(None)")
        for _ in self.start_block(
            "elif _status.status == _status.SOMESOLUTIONS:"):
            self.emit("_status.status = _status.INPROGRESS")
        self.emit("_startingpos = self._pos")
        self.start_block("try:")
        self.emit("_result = None")
        self.emit("_error = None")

    def memoize_footer(self, name):
        statusclassname = "self._Status_%s" % (name, )
        dictname = "_dict_%s" % (name, )
        for _ in self.start_block("if _status.status == _status.LEFTRECURSION:"):
            for _ in self.start_block("if _status.result is not None:"):
                for _ in self.start_block("if _status.pos >= self._pos:"):
                    self.emit("_status.status = _status.NORMAL")
                    self.emit("self._pos = _status.pos")
                    self.emit("return _status")
            self.emit("_status.pos = self._pos")
            self.emit("_status.status = _status.SOMESOLUTIONS")
            self.emit("_status.result = %s" % (self.resultname, ))
            self.emit("_status.error = _error")
            self.emit("self._pos = _startingpos")
            self.emit("return self._%s()" % (name, ))
        self.emit("_status.status = _status.NORMAL")
        self.emit("_status.pos = self._pos")
        self.emit("_status.result = %s" % (self.resultname, ))
        self.emit("_status.error = _error")
        self.emit("return _status")
        self.end_block("try")
        for _ in self.start_block("except self._BacktrackException, _exc:"):
            self.emit("_status.pos = -1")
            self.emit("_status.result = None")
            self.emit("_error = self._combine_errors(_error, _exc.error)")
            self.emit("_status.error = _error")
            self.emit("_status.status = _status.ERROR")
            self.emit("raise self._BacktrackException(_error)")

    def choice_point(self, name=None):
        var = "_choice%s" % (self.namecount, )
        self.namecount += 1
        self.emit("%s = self._pos" % (var, ))
        return var

    def revert(self, var):
        self.emit("self._pos = %s" % (var, ))

    def make_status_class(self, name):
        classname = "_Status_%s" % (name, )
        for _ in self.start_block("class %s(_Status):" % (classname, )):
            for _ in self.start_block("def __init__(self):"):
                self.emit("self.pos = 0")
                self.emit("self.error = None")
                self.emit("self.status = self.INPROGRESS")
                self.emit("self.result = None")
        return classname

    def visit_list(self, t):
        self.start_block("class Parser(object):")
        for elt in t.children:
            self.dispatch(elt)
        for _ in self.start_block("def __init__(self, inputstream):"):
            for line in self.initcode:
                self.emit(line)
            self.emit("self._pos = 0")
            self.emit("self._inputstream = inputstream")
        if self.matchers:
            self.emit_regex_code()
        self.end_block("class")

    def emit_regex_code(self):
        for regex, matcher in self.matchers.iteritems():
            for _ in  self.start_block(
                    "def _regex%s(self):" % (abs(hash(regex)), )):
                c = self.choice_point()
                self.emit("_runner = self._Runner(self._inputstream, self._pos)")
                self.emit("_i = _runner.recognize_%s(self._pos)" % (
                    abs(hash(regex)), ))
                self.start_block("if _runner.last_matched_state == -1:")
                self.revert(c)
                self.emit("raise self._BacktrackException")
                self.end_block("if")
                self.emit("_upto = _runner.last_matched_index + 1")
                self.emit("_result = self._inputstream[self._pos: _upto]")
                self.emit("self._pos = _upto")
                self.emit("return _result")

        for _ in self.start_block("class _Runner(object):"):
            for _ in self.start_block("def __init__(self, text, pos):"):
                self.emit("self.text = text")
                self.emit("self.pos = pos")
                self.emit("self.last_matched_state = -1")
                self.emit("self.last_matched_index = -1")
                self.emit("self.state = -1")
            for regex, matcher in self.matchers.iteritems():
                matcher = str(matcher).replace(
                    "def recognize(runner, i)",
                    "def recognize_%s(runner, i)" % (abs(hash(regex)), ))
                self.emit(str(matcher))

    def visit_production(self, t):
        name = t.children[0]
        if name in self.names:
            raise Exception("name %s appears twice" % (name, ))
        self.names[name] = True
        self.make_status_class(name)
        otherargs = t.children[1].children
        argswithself = ", ".join(["self"] + otherargs)
        argswithoutself = ", ".join(otherargs)
        for _ in self.start_block("def %s(%s):" % (name, argswithself)):
            self.emit("return self._%s(%s).result" % (name, argswithoutself))
        self.start_block("def _%s(%s):" % (name, argswithself, ))

        self.memoize_header(name, otherargs)
        #self.emit("print '%s', self._pos" % (name, ))
        self.resultname = "_result"
        self.dispatch(t.children[-1])
        self.memoize_footer(name)
        self.end_block("def")

    def visit_or(self, t):
        possibilities = t.children
        if len(possibilities) > 1:
            self.start_block("while 1:")
            self.emit("_error = None")
        for i, p in enumerate(possibilities):
            c = self.choice_point()
            for _ in self.start_block("try:"):
                self.dispatch(p)
                self.emit("break")
            for _ in self.start_block("except self._BacktrackException, _exc:"):
                self.emit("_error = self._combine_errors(_error, _exc.error)")
                self.revert(c)
                if i == len(possibilities) - 1:
                    self.emit("raise self._BacktrackException(_error)")
        self.dispatch(possibilities[-1])
        if len(possibilities) > 1:
            self.emit("break")
            self.end_block("while")
    visit_toplevel_or = visit_or

    def visit_commands(self, t):
        for elt in t.children:
            self.dispatch(elt)

    def visit_maybe(self, t):
        c = self.choice_point()
        for _ in self.start_block("try:"):
            self.dispatch(t.children[0])
        for _ in self.start_block("except self._BacktrackException:"):
            self.revert(c)

    def visit_repetition(self, t):
        name = "_all%s" % (self.namecount, )
        self.namecount += 1
        self.emit("%s = []" % (name, ))
        if t.children[0] == '+':
            self.dispatch(t.children[1])
            self.emit("%s.append(_result)"  % (name, ))
        for _ in self.start_block("while 1:"):
            c = self.choice_point()
            for _ in self.start_block("try:"):
                self.dispatch(t.children[1])
                self.emit("%s.append(_result)" % (name, ))
            for _ in self.start_block("except self._BacktrackException, _exc:"):
                self.emit("_error = self._combine_errors(_error, _exc.error)")
                self.revert(c)
                self.emit("break")
        self.emit("_result = %s" % (name, ))

    def visit_exclusive(self, t):
        self.resultname = "_enclosed"
        self.dispatch(t.children[0])
        self.emit("_enclosed = _result")

    def visit_ignore(self, t):
        resultname = "_before_discard%i" % (self.namecount, )
        self.namecount += 1
        self.emit("%s = _result" % (resultname, ))
        self.dispatch(t.children[0])
        self.emit("_result = %s" % (resultname, ))

    def visit_negation(self, t):
        c = self.choice_point()
        resultname = "_stored_result%i" % (self.namecount, )
        self.namecount += 1
        child = t.children[0]
        self.emit("%s = _result" % (resultname, ))
        for _ in self.start_block("try:"):
            self.dispatch(child)
        for _ in self.start_block("except self._BacktrackException:"):
            self.revert(c)
            self.emit("_result = %s" % (resultname, ))
        for _ in self.start_block("else:"):
            # heuristic to get nice error messages sometimes
            if isinstance(child, Symbol) and child.symbol == "QUOTE":

                error = "self._ErrorInformation(%s, ['NOT %s'])" % (
                        c, child.additional_info[1:-1], )
            else:
                error = "None"
            self.emit("raise self._BacktrackException(%s)" % (error, ))

    def visit_lookahead(self, t):
        resultname = "_stored_result%i" % (self.namecount, )
        self.emit("%s = _result" % (resultname, ))
        c = self.choice_point()
        self.dispatch(t.children[0])
        self.revert(c)
        self.emit("_result = %s" % (resultname, ))

    def visit_named_command(self, t):
        name = t.children[0]
        self.dispatch(t.children[1])
        self.emit("%s = _result" % (name, ))

    def visit_return(self, t):
        self.emit("_result = (%s)" % (t.children[0].additional_info[1:-1], ))

    def visit_if(self, t):
        self.dispatch(t.children[0])
        for _ in self.start_block("if not (%s):" % (
            t.children[1].additional_info[1:-1], )):
            self.emit("raise self._BacktrackException(")
            self.emit("    self._ErrorInformation(")
            self.emit("         _startingpos, ['condition not met']))")

    def visit_call(self, t):
        args = ", ".join(['(%s)' % (arg.additional_info[1:-1], )
                              for arg in t.children[1].children])
        if t.children[0].startswith("_"):
            callname = t.children[0]
            self.emit("_result = self.%s(%s)" % (callname, args))
        else:
            callname = "_" + t.children[0]
            self.emit("_call_status = self.%s(%s)" % (callname, args))
            self.emit("_result = _call_status.result")
            self.emit(
                "_error = self._combine_errors(_call_status.error, _error)")

    def visit_REGEX(self, t):
        r = t.additional_info[1:-1].replace('\\`', '`')
        matcher = self.get_regex(r)
        self.emit("_result = self._regex%s()" % (abs(hash(r)), ))
        
    def visit_QUOTE(self, t):
        self.emit("_result = self.__chars__(%r)" % (
                    str(t.additional_info[1:-1]), ))

    def get_regex(self, r):
        from pypy.rlib.parsing.regexparse import parse_regex
        if r in self.matchers:
            return self.matchers[r]
        regex = parse_regex(r)
        if regex is None:
            raise ValueError(
                "%s is not a valid regular expression" % regextext)
        automaton = regex.make_automaton().make_deterministic()
        automaton.optimize()
        matcher = automaton.make_lexing_code()
        self.matchers[r] = py.code.Source(matcher)
        return matcher

class MetaPackratParser(type):
    def __new__(cls, name_, bases, dct):
        if '__doc__' not in dct or dct['__doc__'] is None:
            return type.__new__(cls, name_, bases, dct)
        from pypackrat import PyPackratSyntaxParser
        import sys, new
        frame = sys._getframe(1)
        p = PyPackratSyntaxParser(dct['__doc__'])
        t = p.file()
        t = t.visit(TreeOptimizer())
        visitor = ParserBuilder()
        t.visit(visitor)
        pcls = visitor.make_parser()
        forbidden = dict.fromkeys(("__weakref__ __doc__ "
                                   "__dict__ __module__").split())
        initthere = "__init__" in dct

        for key, value in pcls.__dict__.iteritems():
            if isinstance(value, type(lambda: None)):
                value = new.function(value.func_code, frame.f_globals)
            if key not in dct and key not in forbidden:
                dct[key] = value
        dct['init_parser'] = pcls.__dict__['__init__']
        dct['_code'] = visitor.get_code()
        return type.__new__(cls, name_, bases, dct)

class PackratParser(object):
    __metaclass__ = MetaPackratParser

    _Status = Status
    _ErrorInformation = ErrorInformation
    _BacktrackException = BacktrackException

    def __chars__(self, chars):
        #print '__chars__(%s)' % (chars, ), self._pos
        try:
            for i in range(len(chars)):
                if self._inputstream[self._pos + i] != chars[i]:
                    raise self._BacktrackException(
                        self._ErrorInformation(self._pos, [chars]))
            self._pos += len(chars)
            return chars
        except IndexError:
            raise self._BacktrackException(
                self._ErrorInformation(self._pos, [chars]))

    def  __any__(self):
        try:
            result = self._inputstream[self._pos]
            self._pos += 1
            return result
        except IndexError:
            raise self._BacktrackException(
                self._ErrorInformation(self._pos, ['anything']))

    def _combine_errors(self, error1, error2):
        if error1 is None:
            return error2
        if (error2 is None or error1.pos > error2.pos or
            len(error2.expected) == 0):
            return error1
        elif error2.pos > error1.pos or len(error1.expected) == 0:
            return error2
        expected = []
        already_there = {}
        for ep in [error1.expected, error2.expected]:
            for reason in ep:
                if reason not in already_there:
                    already_there[reason] = True
                    expected.append(reason)
        return ErrorInformation(error1.pos, expected)


def test_generate():
    f = py.magic.autopath().dirpath().join("pypackrat.py")
    from pypackrat import PyPackratSyntaxParser
    p = PyPackratSyntaxParser(syntax)
    t = p.file()
    t = t.visit(TreeOptimizer())
    visitor = ParserBuilder()
    t.visit(visitor)
    code = visitor.get_code()
    content = """
from pypy.rlib.parsing.tree import Nonterminal, Symbol
from makepackrat import PackratParser, BacktrackException, Status as _Status
%s
class PyPackratSyntaxParser(PackratParser):
    def __init__(self, stream):
        self.init_parser(stream)
forbidden = dict.fromkeys(("__weakref__ __doc__ "
                           "__dict__ __module__").split())
initthere = "__init__" in PyPackratSyntaxParser.__dict__
for key, value in Parser.__dict__.iteritems():
    if key not in PyPackratSyntaxParser.__dict__ and key not in forbidden:
        setattr(PyPackratSyntaxParser, key, value)
PyPackratSyntaxParser.init_parser = Parser.__init__.im_func
""" % (code, )
    print content
    f.write(content)
