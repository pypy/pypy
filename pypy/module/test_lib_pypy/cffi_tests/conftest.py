
def pytest_ignore_collect(path, config):
    if config.option.runappdirect:
        return False
    # only run if -A is specified
    return True
