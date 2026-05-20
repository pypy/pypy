import pytest

@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_preparse(config, args):
    if set(args) & {'-D', '--direct-apptest'}:
        try:
            args.remove('--assert=reinterp')
        except ValueError:
            pass
