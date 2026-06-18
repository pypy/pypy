"""App-level helpers for _sre, ported from the Python code that CPython
removed from Lib/re when it moved template expansion to C (gh-91524)."""


class _SRETemplate:
    """Callable compiled replacement template returned by _sre.template()."""
    __slots__ = ('pattern', '_template')

    def __init__(self, pattern, template_list):
        self.pattern = pattern
        self._template = template_list

    def __call__(self, match):
        result = []
        template = self._template
        for item in template:
            if isinstance(item, int):
                s = match.group(item)
                if s is not None:
                    result.append(s)
            elif item:
                result.append(item)
        if not result:
            return template[0][:0] if template else ''
        return result[0][:0].join(result)


def template(pattern, template_list):
    """_sre.template(pattern, template_list) -> callable template object.

    template_list is the list returned by re._parser.parse_template():
    alternating string literals and integer group indices,
    e.g. ['prefix_', 1, '_suffix'].

    Raises TypeError for negative or non-integer group indices.
    """
    n = len(template_list)
    # odd positions (1, 3, ...) are group indices
    for i in range((n - 1) // 2):
        idx = template_list[2 * i + 1]
        if not isinstance(idx, int):
            raise TypeError(
                "an integer is required (got type %s)" % type(idx).__name__)
        if idx < 0:
            raise TypeError("invalid template")
    return _SRETemplate(pattern, template_list)
