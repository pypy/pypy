import imp

build_time_vars = {
    "SO": [s[0] for s in imp.get_suffixes() if s[2] == imp.C_EXTENSION][0]
}
