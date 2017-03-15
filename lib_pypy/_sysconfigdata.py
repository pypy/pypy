import imp

so_ext = [s[0] for s in imp.get_suffixes() if s[2] == imp.C_EXTENSION][0]

build_time_vars = {
    "EXT_SUFFIX": so_ext,
    "SHLIB_SUFFIX": so_ext,
    "SO": so_ext  # deprecated in Python 3, for backward compatibility
}
