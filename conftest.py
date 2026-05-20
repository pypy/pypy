import pytest

@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_preparse(config, args):
    if not (set(args) & {'-D', '--direct-apptest'}):
        args.append('--assert=reinterp')
