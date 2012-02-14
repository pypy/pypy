"""
This conftest adds an option to run the translation tests which by default will
be disabled.
"""

def pytest_addoption(parser):
    group = parser.getgroup('translation test options')
    group.addoption('--run-translation-tests',
                    action="store_true",
                    default=False,
                    dest="run_translation_tests",
                    help="run tests that translate code")
