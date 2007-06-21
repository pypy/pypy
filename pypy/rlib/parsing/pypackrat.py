
from pypy.rlib.parsing.tree import Nonterminal, Symbol
from makepackrat import PackratParser, BacktrackException, Status as _Status
class Parser(object):
    class _Status_NAME(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def NAME(self):
        return self._NAME().result
    def _NAME(self):
        _status = self._dict_NAME.get(self._pos, None)
        if _status is None:
            _status = self._dict_NAME[self._pos] = self._Status_NAME()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self._regex1074651696()
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._NAME()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_SPACE(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def SPACE(self):
        return self._SPACE().result
    def _SPACE(self):
        _status = self._dict_SPACE.get(self._pos, None)
        if _status is None:
            _status = self._dict_SPACE[self._pos] = self._Status_SPACE()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self.__chars__(' ')
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._SPACE()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_COMMENT(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def COMMENT(self):
        return self._COMMENT().result
    def _COMMENT(self):
        _status = self._dict_COMMENT.get(self._pos, None)
        if _status is None:
            _status = self._dict_COMMENT[self._pos] = self._Status_COMMENT()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self._regex528667127()
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._COMMENT()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_IGNORE(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def IGNORE(self):
        return self._IGNORE().result
    def _IGNORE(self):
        _status = self._dict_IGNORE.get(self._pos, None)
        if _status is None:
            _status = self._dict_IGNORE[self._pos] = self._Status_IGNORE()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self._regex1979538501()
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._IGNORE()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_newline(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def newline(self):
        return self._newline().result
    def _newline(self):
        _status = self._dict_newline.get(self._pos, None)
        if _status is None:
            _status = self._dict_newline[self._pos] = self._Status_newline()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            while 1:
                _error = None
                _choice0 = self._pos
                try:
                    _call_status = self._COMMENT()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice0
                _choice1 = self._pos
                try:
                    _result = self._regex299149370()
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice1
                    raise self._BacktrackException(_error)
                _result = self._regex299149370()
                break
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._newline()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_REGEX(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def REGEX(self):
        return self._REGEX().result
    def _REGEX(self):
        _status = self._dict_REGEX.get(self._pos, None)
        if _status is None:
            _status = self._dict_REGEX[self._pos] = self._Status_REGEX()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self._regex1006631623()
            r = _result
            _result = (Symbol('REGEX', r, None))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._REGEX()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_QUOTE(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def QUOTE(self):
        return self._QUOTE().result
    def _QUOTE(self):
        _status = self._dict_QUOTE.get(self._pos, None)
        if _status is None:
            _status = self._dict_QUOTE[self._pos] = self._Status_QUOTE()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self._regex1124192327()
            r = _result
            _result = (Symbol('QUOTE', r, None))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._QUOTE()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_PYTHONCODE(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def PYTHONCODE(self):
        return self._PYTHONCODE().result
    def _PYTHONCODE(self):
        _status = self._dict_PYTHONCODE.get(self._pos, None)
        if _status is None:
            _status = self._dict_PYTHONCODE[self._pos] = self._Status_PYTHONCODE()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self._regex291086639()
            r = _result
            _result = (Symbol('PYTHONCODE', r, None))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._PYTHONCODE()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_EOF(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def EOF(self):
        return self._EOF().result
    def _EOF(self):
        _status = self._dict_EOF.get(self._pos, None)
        if _status is None:
            _status = self._dict_EOF[self._pos] = self._Status_EOF()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _choice2 = self._pos
            _stored_result3 = _result
            try:
                _result = self.__any__()
            except self._BacktrackException:
                self._pos = _choice2
                _result = _stored_result3
            else:
                raise self._BacktrackException(None)
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._EOF()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_file(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def file(self):
        return self._file().result
    def _file(self):
        _status = self._dict_file.get(self._pos, None)
        if _status is None:
            _status = self._dict_file[self._pos] = self._Status_file()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _all4 = []
            while 1:
                _choice5 = self._pos
                try:
                    _call_status = self._IGNORE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all4.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice5
                    break
            _result = _all4
            _call_status = self._list()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            _before_discard6 = _result
            _call_status = self._EOF()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            _result = _before_discard6
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._file()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_list(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def list(self):
        return self._list().result
    def _list(self):
        _status = self._dict_list.get(self._pos, None)
        if _status is None:
            _status = self._dict_list[self._pos] = self._Status_list()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _all7 = []
            _call_status = self._production()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            _all7.append(_result)
            while 1:
                _choice8 = self._pos
                try:
                    _call_status = self._production()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all7.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice8
                    break
            _result = _all7
            content = _result
            _result = (Nonterminal('list', content))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._list()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_production(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def production(self):
        return self._production().result
    def _production(self):
        _status = self._dict_production.get(self._pos, None)
        if _status is None:
            _status = self._dict_production[self._pos] = self._Status_production()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _call_status = self._NAME()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            name = _result
            _all9 = []
            while 1:
                _choice10 = self._pos
                try:
                    _call_status = self._SPACE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all9.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice10
                    break
            _result = _all9
            _result = self.__chars__(':')
            _all11 = []
            while 1:
                _choice12 = self._pos
                try:
                    _call_status = self._IGNORE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all11.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice12
                    break
            _result = _all11
            _call_status = self._or_()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            what = _result
            _all13 = []
            while 1:
                _choice14 = self._pos
                try:
                    _call_status = self._IGNORE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all13.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice14
                    break
            _result = _all13
            _result = self.__chars__(';')
            _all15 = []
            while 1:
                _choice16 = self._pos
                try:
                    _call_status = self._IGNORE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all15.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice16
                    break
            _result = _all15
            _result = (Nonterminal('production', [name, what]))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._production()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_or_(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def or_(self):
        return self._or_().result
    def _or_(self):
        _status = self._dict_or_.get(self._pos, None)
        if _status is None:
            _status = self._dict_or_[self._pos] = self._Status_or_()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            while 1:
                _error = None
                _choice17 = self._pos
                try:
                    _all18 = []
                    _call_status = self._commands()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _before_discard19 = _result
                    _result = self.__chars__('|')
                    _all20 = []
                    while 1:
                        _choice21 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all20.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice21
                            break
                    _result = _all20
                    _result = _before_discard19
                    _all18.append(_result)
                    while 1:
                        _choice22 = self._pos
                        try:
                            _call_status = self._commands()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _before_discard23 = _result
                            _result = self.__chars__('|')
                            _all24 = []
                            while 1:
                                _choice25 = self._pos
                                try:
                                    _call_status = self._IGNORE()
                                    _result = _call_status.result
                                    _error = self._combine_errors(_call_status.error, _error)
                                    _all24.append(_result)
                                except self._BacktrackException, _exc:
                                    _error = self._combine_errors(_error, _exc.error)
                                    self._pos = _choice25
                                    break
                            _result = _all24
                            _result = _before_discard23
                            _all18.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice22
                            break
                    _result = _all18
                    l = _result
                    _call_status = self._commands()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    last = _result
                    _result = (Nonterminal('or', l + [last]))
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice17
                _choice26 = self._pos
                try:
                    _call_status = self._commands()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice26
                    raise self._BacktrackException(_error)
                _call_status = self._commands()
                _result = _call_status.result
                _error = self._combine_errors(_call_status.error, _error)
                break
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._or_()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_commands(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def commands(self):
        return self._commands().result
    def _commands(self):
        _status = self._dict_commands.get(self._pos, None)
        if _status is None:
            _status = self._dict_commands[self._pos] = self._Status_commands()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            while 1:
                _error = None
                _choice27 = self._pos
                try:
                    _call_status = self._command()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    cmd = _result
                    _call_status = self._newline()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all28 = []
                    _call_status = self._command()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _before_discard29 = _result
                    _call_status = self._newline()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _result = _before_discard29
                    _all28.append(_result)
                    while 1:
                        _choice30 = self._pos
                        try:
                            _call_status = self._command()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _before_discard31 = _result
                            _call_status = self._newline()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _result = _before_discard31
                            _all28.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice30
                            break
                    _result = _all28
                    cmds = _result
                    _result = (Nonterminal('commands', [cmd] + cmds))
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice27
                _choice32 = self._pos
                try:
                    _call_status = self._command()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice32
                    raise self._BacktrackException(_error)
                _call_status = self._command()
                _result = _call_status.result
                _error = self._combine_errors(_call_status.error, _error)
                break
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._commands()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_command(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def command(self):
        return self._command().result
    def _command(self):
        _status = self._dict_command.get(self._pos, None)
        if _status is None:
            _status = self._dict_command[self._pos] = self._Status_command()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _call_status = self._simplecommand()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._command()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_simplecommand(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def simplecommand(self):
        return self._simplecommand().result
    def _simplecommand(self):
        _status = self._dict_simplecommand.get(self._pos, None)
        if _status is None:
            _status = self._dict_simplecommand[self._pos] = self._Status_simplecommand()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            while 1:
                _error = None
                _choice33 = self._pos
                try:
                    _call_status = self._return_()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice33
                _choice34 = self._pos
                try:
                    _call_status = self._if_()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice34
                _choice35 = self._pos
                try:
                    _call_status = self._named_command()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice35
                _choice36 = self._pos
                try:
                    _call_status = self._repetition()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice36
                _choice37 = self._pos
                try:
                    _call_status = self._negation()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice37
                    raise self._BacktrackException(_error)
                _call_status = self._negation()
                _result = _call_status.result
                _error = self._combine_errors(_call_status.error, _error)
                break
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._simplecommand()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_return_(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def return_(self):
        return self._return_().result
    def _return_(self):
        _status = self._dict_return_.get(self._pos, None)
        if _status is None:
            _status = self._dict_return_[self._pos] = self._Status_return_()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self.__chars__('return')
            _all38 = []
            while 1:
                _choice39 = self._pos
                try:
                    _call_status = self._SPACE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all38.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice39
                    break
            _result = _all38
            _call_status = self._PYTHONCODE()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            code = _result
            _all40 = []
            while 1:
                _choice41 = self._pos
                try:
                    _call_status = self._IGNORE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all40.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice41
                    break
            _result = _all40
            _result = (Nonterminal('return', [code]))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._return_()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_if_(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def if_(self):
        return self._if_().result
    def _if_(self):
        _status = self._dict_if_.get(self._pos, None)
        if _status is None:
            _status = self._dict_if_[self._pos] = self._Status_if_()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _result = self.__chars__('do')
            _call_status = self._newline()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            _call_status = self._command()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            cmd = _result
            _all42 = []
            while 1:
                _choice43 = self._pos
                try:
                    _call_status = self._SPACE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all42.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice43
                    break
            _result = _all42
            _result = self.__chars__('if')
            _all44 = []
            while 1:
                _choice45 = self._pos
                try:
                    _call_status = self._SPACE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all44.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice45
                    break
            _result = _all44
            _call_status = self._PYTHONCODE()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            condition = _result
            _result = (Nonterminal('if', [cmd, condition]))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._if_()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_commandchain(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def commandchain(self):
        return self._commandchain().result
    def _commandchain(self):
        _status = self._dict_commandchain.get(self._pos, None)
        if _status is None:
            _status = self._dict_commandchain[self._pos] = self._Status_commandchain()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _all46 = []
            _call_status = self._simplecommand()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            _all46.append(_result)
            while 1:
                _choice47 = self._pos
                try:
                    _call_status = self._simplecommand()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all46.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice47
                    break
            _result = _all46
            result = _result
            _result = (Nonterminal('commands', result))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._commandchain()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_named_command(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def named_command(self):
        return self._named_command().result
    def _named_command(self):
        _status = self._dict_named_command.get(self._pos, None)
        if _status is None:
            _status = self._dict_named_command[self._pos] = self._Status_named_command()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _call_status = self._NAME()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            name = _result
            _all48 = []
            while 1:
                _choice49 = self._pos
                try:
                    _call_status = self._SPACE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all48.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice49
                    break
            _result = _all48
            _result = self.__chars__('=')
            _all50 = []
            while 1:
                _choice51 = self._pos
                try:
                    _call_status = self._SPACE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all50.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice51
                    break
            _result = _all50
            _call_status = self._command()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            cmd = _result
            _result = (Nonterminal('named_command', [name, cmd]))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._named_command()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_repetition(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def repetition(self):
        return self._repetition().result
    def _repetition(self):
        _status = self._dict_repetition.get(self._pos, None)
        if _status is None:
            _status = self._dict_repetition[self._pos] = self._Status_repetition()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            while 1:
                _error = None
                _choice52 = self._pos
                try:
                    _call_status = self._enclosed()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    what = _result
                    _all53 = []
                    while 1:
                        _choice54 = self._pos
                        try:
                            _call_status = self._SPACE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all53.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice54
                            break
                    _result = _all53
                    _result = self.__chars__('?')
                    _all55 = []
                    while 1:
                        _choice56 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all55.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice56
                            break
                    _result = _all55
                    _result = (Nonterminal('maybe', [what]))
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice52
                _choice57 = self._pos
                try:
                    _call_status = self._enclosed()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    what = _result
                    _all58 = []
                    while 1:
                        _choice59 = self._pos
                        try:
                            _call_status = self._SPACE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all58.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice59
                            break
                    _result = _all58
                    while 1:
                        _error = None
                        _choice60 = self._pos
                        try:
                            _result = self.__chars__('*')
                            break
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice60
                        _choice61 = self._pos
                        try:
                            _result = self.__chars__('+')
                            break
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice61
                            raise self._BacktrackException(_error)
                        _result = self.__chars__('+')
                        break
                    repetition = _result
                    _all62 = []
                    while 1:
                        _choice63 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all62.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice63
                            break
                    _result = _all62
                    _result = (Nonterminal('repetition', [repetition, what]))
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice57
                    raise self._BacktrackException(_error)
                _call_status = self._enclosed()
                _result = _call_status.result
                _error = self._combine_errors(_call_status.error, _error)
                what = _result
                _all64 = []
                while 1:
                    _choice65 = self._pos
                    try:
                        _call_status = self._SPACE()
                        _result = _call_status.result
                        _error = self._combine_errors(_call_status.error, _error)
                        _all64.append(_result)
                    except self._BacktrackException, _exc:
                        _error = self._combine_errors(_error, _exc.error)
                        self._pos = _choice65
                        break
                _result = _all64
                while 1:
                    _error = None
                    _choice66 = self._pos
                    try:
                        _result = self.__chars__('*')
                        break
                    except self._BacktrackException, _exc:
                        _error = self._combine_errors(_error, _exc.error)
                        self._pos = _choice66
                    _choice67 = self._pos
                    try:
                        _result = self.__chars__('+')
                        break
                    except self._BacktrackException, _exc:
                        _error = self._combine_errors(_error, _exc.error)
                        self._pos = _choice67
                        raise self._BacktrackException(_error)
                    _result = self.__chars__('+')
                    break
                repetition = _result
                _all68 = []
                while 1:
                    _choice69 = self._pos
                    try:
                        _call_status = self._IGNORE()
                        _result = _call_status.result
                        _error = self._combine_errors(_call_status.error, _error)
                        _all68.append(_result)
                    except self._BacktrackException, _exc:
                        _error = self._combine_errors(_error, _exc.error)
                        self._pos = _choice69
                        break
                _result = _all68
                _result = (Nonterminal('repetition', [repetition, what]))
                break
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._repetition()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_negation(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def negation(self):
        return self._negation().result
    def _negation(self):
        _status = self._dict_negation.get(self._pos, None)
        if _status is None:
            _status = self._dict_negation[self._pos] = self._Status_negation()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            while 1:
                _error = None
                _choice70 = self._pos
                try:
                    _result = self.__chars__('!')
                    _all71 = []
                    while 1:
                        _choice72 = self._pos
                        try:
                            _call_status = self._SPACE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all71.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice72
                            break
                    _result = _all71
                    _call_status = self._negation()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    what = _result
                    _all73 = []
                    while 1:
                        _choice74 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all73.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice74
                            break
                    _result = _all73
                    _result = (Nonterminal('negation', [what]))
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice70
                _choice75 = self._pos
                try:
                    _call_status = self._enclosed()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice75
                    raise self._BacktrackException(_error)
                _call_status = self._enclosed()
                _result = _call_status.result
                _error = self._combine_errors(_call_status.error, _error)
                break
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._negation()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_enclosed(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def enclosed(self):
        return self._enclosed().result
    def _enclosed(self):
        _status = self._dict_enclosed.get(self._pos, None)
        if _status is None:
            _status = self._dict_enclosed[self._pos] = self._Status_enclosed()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            while 1:
                _error = None
                _choice76 = self._pos
                try:
                    _result = self.__chars__('<')
                    _all77 = []
                    while 1:
                        _choice78 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all77.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice78
                            break
                    _result = _all77
                    _call_status = self._primary()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    what = _result
                    _all79 = []
                    while 1:
                        _choice80 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all79.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice80
                            break
                    _result = _all79
                    _result = self.__chars__('>')
                    _all81 = []
                    while 1:
                        _choice82 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all81.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice82
                            break
                    _result = _all81
                    _result = (Nonterminal('exclusive', [what]))
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice76
                _choice83 = self._pos
                try:
                    _result = self.__chars__('[')
                    _all84 = []
                    while 1:
                        _choice85 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all84.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice85
                            break
                    _result = _all84
                    _call_status = self._or_()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    what = _result
                    _all86 = []
                    while 1:
                        _choice87 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all86.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice87
                            break
                    _result = _all86
                    _result = self.__chars__(']')
                    _all88 = []
                    while 1:
                        _choice89 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all88.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice89
                            break
                    _result = _all88
                    _result = (Nonterminal('ignore', [what]))
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice83
                _choice90 = self._pos
                try:
                    _before_discard91 = _result
                    _result = self.__chars__('(')
                    _all92 = []
                    while 1:
                        _choice93 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all92.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice93
                            break
                    _result = _all92
                    _result = _before_discard91
                    _call_status = self._or_()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _before_discard94 = _result
                    _result = self.__chars__(')')
                    _all95 = []
                    while 1:
                        _choice96 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all95.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice96
                            break
                    _result = _all95
                    _result = _before_discard94
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice90
                _choice97 = self._pos
                try:
                    _call_status = self._primary()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice97
                    raise self._BacktrackException(_error)
                _call_status = self._primary()
                _result = _call_status.result
                _error = self._combine_errors(_call_status.error, _error)
                break
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._enclosed()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_primary(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def primary(self):
        return self._primary().result
    def _primary(self):
        _status = self._dict_primary.get(self._pos, None)
        if _status is None:
            _status = self._dict_primary[self._pos] = self._Status_primary()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            while 1:
                _error = None
                _choice98 = self._pos
                try:
                    _call_status = self._call()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice98
                _choice99 = self._pos
                try:
                    _call_status = self._REGEX()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _before_discard100 = _result
                    _all101 = []
                    while 1:
                        _choice102 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all101.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice102
                            break
                    _result = _all101
                    _result = _before_discard100
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice99
                _choice103 = self._pos
                try:
                    _call_status = self._QUOTE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _before_discard104 = _result
                    _all105 = []
                    while 1:
                        _choice106 = self._pos
                        try:
                            _call_status = self._IGNORE()
                            _result = _call_status.result
                            _error = self._combine_errors(_call_status.error, _error)
                            _all105.append(_result)
                        except self._BacktrackException, _exc:
                            _error = self._combine_errors(_error, _exc.error)
                            self._pos = _choice106
                            break
                    _result = _all105
                    _result = _before_discard104
                    break
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice103
                    raise self._BacktrackException(_error)
                _call_status = self._QUOTE()
                _result = _call_status.result
                _error = self._combine_errors(_call_status.error, _error)
                _before_discard107 = _result
                _all108 = []
                while 1:
                    _choice109 = self._pos
                    try:
                        _call_status = self._IGNORE()
                        _result = _call_status.result
                        _error = self._combine_errors(_call_status.error, _error)
                        _all108.append(_result)
                    except self._BacktrackException, _exc:
                        _error = self._combine_errors(_error, _exc.error)
                        self._pos = _choice109
                        break
                _result = _all108
                _result = _before_discard107
                break
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._primary()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    class _Status_call(_Status):
        def __init__(self):
            self.pos = 0
            self.error = None
            self.status = self.INPROGRESS
            self.result = None
    def call(self):
        return self._call().result
    def _call(self):
        _status = self._dict_call.get(self._pos, None)
        if _status is None:
            _status = self._dict_call[self._pos] = self._Status_call()
        elif _status.status == _status.NORMAL:
            self._pos = _status.pos
            return _status
        elif _status.status == _status.ERROR:
            raise self._BacktrackException(_status.error)
        elif (_status.status == _status.INPROGRESS or
              _status.status == _status.LEFTRECURSION):
            _status.status = _status.LEFTRECURSION
            if _status.result is not None:
                self._pos = _status.pos
                return _status
            else:
                raise self._BacktrackException(None)
        elif _status.status == _status.SOMESOLUTIONS:
            _status.status = _status.INPROGRESS
        _startingpos = self._pos
        try:
            _result = None
            _error = None
            _call_status = self._NAME()
            _result = _call_status.result
            _error = self._combine_errors(_call_status.error, _error)
            x = _result
            _all110 = []
            while 1:
                _choice111 = self._pos
                try:
                    _call_status = self._IGNORE()
                    _result = _call_status.result
                    _error = self._combine_errors(_call_status.error, _error)
                    _all110.append(_result)
                except self._BacktrackException, _exc:
                    _error = self._combine_errors(_error, _exc.error)
                    self._pos = _choice111
                    break
            _result = _all110
            _result = (Nonterminal("call", [x]))
            if _status.status == _status.LEFTRECURSION:
                if _status.result is not None:
                    if _status.pos >= self._pos:
                        _status.status = _status.NORMAL
                        self._pos = _status.pos
                        return _status
                _status.pos = self._pos
                _status.status = _status.SOMESOLUTIONS
                _status.result = _result
                _status.error = _error
                self._pos = _startingpos
                return self._call()
            _status.status = _status.NORMAL
            _status.pos = self._pos
            _status.result = _result
            _status.error = _error
            return _status
        except self._BacktrackException, _exc:
            _status.pos = -1
            _status.result = None
            _error = self._combine_errors(_error, _exc.error)
            _status.error = _error
            _status.status = _status.ERROR
            raise self._BacktrackException(_error)
    def __init__(self, inputstream):
        self._dict_NAME = {}
        self._dict_SPACE = {}
        self._dict_COMMENT = {}
        self._dict_IGNORE = {}
        self._dict_newline = {}
        self._dict_REGEX = {}
        self._dict_QUOTE = {}
        self._dict_PYTHONCODE = {}
        self._dict_EOF = {}
        self._dict_file = {}
        self._dict_list = {}
        self._dict_production = {}
        self._dict_or_ = {}
        self._dict_commands = {}
        self._dict_command = {}
        self._dict_simplecommand = {}
        self._dict_return_ = {}
        self._dict_if_ = {}
        self._dict_commandchain = {}
        self._dict_named_command = {}
        self._dict_repetition = {}
        self._dict_negation = {}
        self._dict_enclosed = {}
        self._dict_primary = {}
        self._dict_call = {}
        self._pos = 0
        self._inputstream = inputstream
    def _regex299149370(self):
        _choice112 = self._pos
        _runner = self._Runner(self._inputstream, self._pos)
        _i = _runner.recognize_299149370(self._pos)
        if _runner.last_matched_state == -1:
            self._pos = _choice112
            raise self._BacktrackException
        _upto = _runner.last_matched_index + 1
        _result = self._inputstream[self._pos: _upto]
        self._pos = _upto
        return _result
    def _regex1006631623(self):
        _choice113 = self._pos
        _runner = self._Runner(self._inputstream, self._pos)
        _i = _runner.recognize_1006631623(self._pos)
        if _runner.last_matched_state == -1:
            self._pos = _choice113
            raise self._BacktrackException
        _upto = _runner.last_matched_index + 1
        _result = self._inputstream[self._pos: _upto]
        self._pos = _upto
        return _result
    def _regex528667127(self):
        _choice114 = self._pos
        _runner = self._Runner(self._inputstream, self._pos)
        _i = _runner.recognize_528667127(self._pos)
        if _runner.last_matched_state == -1:
            self._pos = _choice114
            raise self._BacktrackException
        _upto = _runner.last_matched_index + 1
        _result = self._inputstream[self._pos: _upto]
        self._pos = _upto
        return _result
    def _regex291086639(self):
        _choice115 = self._pos
        _runner = self._Runner(self._inputstream, self._pos)
        _i = _runner.recognize_291086639(self._pos)
        if _runner.last_matched_state == -1:
            self._pos = _choice115
            raise self._BacktrackException
        _upto = _runner.last_matched_index + 1
        _result = self._inputstream[self._pos: _upto]
        self._pos = _upto
        return _result
    def _regex1074651696(self):
        _choice116 = self._pos
        _runner = self._Runner(self._inputstream, self._pos)
        _i = _runner.recognize_1074651696(self._pos)
        if _runner.last_matched_state == -1:
            self._pos = _choice116
            raise self._BacktrackException
        _upto = _runner.last_matched_index + 1
        _result = self._inputstream[self._pos: _upto]
        self._pos = _upto
        return _result
    def _regex1124192327(self):
        _choice117 = self._pos
        _runner = self._Runner(self._inputstream, self._pos)
        _i = _runner.recognize_1124192327(self._pos)
        if _runner.last_matched_state == -1:
            self._pos = _choice117
            raise self._BacktrackException
        _upto = _runner.last_matched_index + 1
        _result = self._inputstream[self._pos: _upto]
        self._pos = _upto
        return _result
    def _regex1979538501(self):
        _choice118 = self._pos
        _runner = self._Runner(self._inputstream, self._pos)
        _i = _runner.recognize_1979538501(self._pos)
        if _runner.last_matched_state == -1:
            self._pos = _choice118
            raise self._BacktrackException
        _upto = _runner.last_matched_index + 1
        _result = self._inputstream[self._pos: _upto]
        self._pos = _upto
        return _result
    class _Runner(object):
        def __init__(self, text, pos):
            self.text = text
            self.pos = pos
            self.last_matched_state = -1
            self.last_matched_index = -1
            self.state = -1
        def recognize_299149370(runner, i):
            assert i >= 0
            input = runner.text
            state = 0
            while 1:
                if state == 0:
                    runner.last_matched_index = i - 1
                    runner.last_matched_state = state
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 0
                        return i
                    if char == '\n':
                        state = 1
                    elif char == ' ':
                        state = 2
                    else:
                        break
                if state == 1:
                    runner.last_matched_index = i - 1
                    runner.last_matched_state = state
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 1
                        return i
                    if char == '\n':
                        state = 1
                        continue
                    elif char == ' ':
                        state = 1
                        continue
                    else:
                        break
                if state == 2:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 2
                        return ~i
                    if char == '\n':
                        state = 1
                        continue
                    elif char == ' ':
                        state = 2
                        continue
                    else:
                        break
                runner.last_matched_state = state
                runner.last_matched_index = i - 1
                runner.state = state
                if i == len(input):
                    return i
                else:
                    return ~i
                break
            runner.state = state
            return ~i
        def recognize_1006631623(runner, i):
            assert i >= 0
            input = runner.text
            state = 0
            while 1:
                if state == 0:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 0
                        return ~i
                    if char == '`':
                        state = 3
                    else:
                        break
                if state == 2:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 2
                        return ~i
                    if '\x00' <= char <= '\xff':
                        state = 3
                    else:
                        break
                if state == 3:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 3
                        return ~i
                    if char == '`':
                        state = 1
                    elif char == '\\':
                        state = 2
                        continue
                    elif '\x00' <= char <= '[':
                        state = 3
                        continue
                    elif ']' <= char <= '_':
                        state = 3
                        continue
                    elif 'a' <= char <= '\xff':
                        state = 3
                        continue
                    else:
                        break
                runner.last_matched_state = state
                runner.last_matched_index = i - 1
                runner.state = state
                if i == len(input):
                    return i
                else:
                    return ~i
                break
            runner.state = state
            return ~i
        def recognize_528667127(runner, i):
            assert i >= 0
            input = runner.text
            state = 0
            while 1:
                if state == 0:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 0
                        return ~i
                    if char == ' ':
                        state = 0
                        continue
                    elif char == '#':
                        state = 2
                    else:
                        break
                if state == 1:
                    runner.last_matched_index = i - 1
                    runner.last_matched_state = state
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 1
                        return i
                    if char == ' ':
                        state = 0
                        continue
                    elif char == '#':
                        state = 2
                    else:
                        break
                if state == 2:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 2
                        return ~i
                    if char == '\n':
                        state = 1
                        continue
                    elif '\x00' <= char <= '\t':
                        state = 2
                        continue
                    elif '\x0b' <= char <= '\xff':
                        state = 2
                        continue
                    else:
                        break
                runner.last_matched_state = state
                runner.last_matched_index = i - 1
                runner.state = state
                if i == len(input):
                    return i
                else:
                    return ~i
                break
            runner.state = state
            return ~i
        def recognize_291086639(runner, i):
            assert i >= 0
            input = runner.text
            state = 0
            while 1:
                if state == 0:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 0
                        return ~i
                    if char == '{':
                        state = 2
                    else:
                        break
                if state == 2:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 2
                        return ~i
                    if char == '}':
                        state = 1
                    elif '\x00' <= char <= '\t':
                        state = 2
                        continue
                    elif '\x0b' <= char <= '|':
                        state = 2
                        continue
                    elif '~' <= char <= '\xff':
                        state = 2
                        continue
                    else:
                        break
                runner.last_matched_state = state
                runner.last_matched_index = i - 1
                runner.state = state
                if i == len(input):
                    return i
                else:
                    return ~i
                break
            runner.state = state
            return ~i
        def recognize_1074651696(runner, i):
            assert i >= 0
            input = runner.text
            state = 0
            while 1:
                if state == 0:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 0
                        return ~i
                    if 'A' <= char <= 'Z':
                        state = 1
                    elif char == '_':
                        state = 1
                    elif 'a' <= char <= 'z':
                        state = 1
                    else:
                        break
                if state == 1:
                    runner.last_matched_index = i - 1
                    runner.last_matched_state = state
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 1
                        return i
                    if '0' <= char <= '9':
                        state = 1
                        continue
                    elif 'A' <= char <= 'Z':
                        state = 1
                        continue
                    elif char == '_':
                        state = 1
                        continue
                    elif 'a' <= char <= 'z':
                        state = 1
                        continue
                    else:
                        break
                runner.last_matched_state = state
                runner.last_matched_index = i - 1
                runner.state = state
                if i == len(input):
                    return i
                else:
                    return ~i
                break
            runner.state = state
            return ~i
        def recognize_1124192327(runner, i):
            assert i >= 0
            input = runner.text
            state = 0
            while 1:
                if state == 0:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 0
                        return ~i
                    if char == "'":
                        state = 1
                    else:
                        break
                if state == 1:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 1
                        return ~i
                    if '\x00' <= char <= '&':
                        state = 1
                        continue
                    elif '(' <= char <= '\xff':
                        state = 1
                        continue
                    elif char == "'":
                        state = 2
                    else:
                        break
                runner.last_matched_state = state
                runner.last_matched_index = i - 1
                runner.state = state
                if i == len(input):
                    return i
                else:
                    return ~i
                break
            runner.state = state
            return ~i
        def recognize_1979538501(runner, i):
            assert i >= 0
            input = runner.text
            state = 0
            while 1:
                if state == 0:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 0
                        return ~i
                    if char == '#':
                        state = 1
                    elif char == '\t':
                        state = 2
                    elif char == '\n':
                        state = 2
                    elif char == ' ':
                        state = 2
                    else:
                        break
                if state == 1:
                    if i < len(input):
                        char = input[i]
                        i += 1
                    else:
                        runner.state = 1
                        return ~i
                    if '\x00' <= char <= '\t':
                        state = 1
                        continue
                    elif '\x0b' <= char <= '\xff':
                        state = 1
                        continue
                    elif char == '\n':
                        state = 2
                    else:
                        break
                runner.last_matched_state = state
                runner.last_matched_index = i - 1
                runner.state = state
                if i == len(input):
                    return i
                else:
                    return ~i
                break
            runner.state = state
            return ~i
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
