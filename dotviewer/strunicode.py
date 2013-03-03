RAW_ENCODING = "utf-8"


def forceunicode(name):
    return name if isinstance(name, unicode) else name.decode(RAW_ENCODING)


def forcestr(name):
    return name if isinstance(name, str) else name.encode(RAW_ENCODING)
