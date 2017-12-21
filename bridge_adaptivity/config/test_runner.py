import pytest


class PytestTestRunner(object):
    """Runs pytest to discover and run tests."""

    def __init__(self, verbosity=1, failfast=False, keepdb=False, **kwargs):
        self.verbosity = verbosity
        self.failfast = failfast
        self.keepdb = keepdb
        self.kw = kwargs

    def run_tests(self, test_labels):
        """Run pytest and return the exitcode.

        It translates some of Django's test command option to pytest's.
        """
        argv = []
        if self.verbosity == 0:
            argv.append('--quiet')
        if self.verbosity == 2:
            argv.append('--verbose')
        if self.verbosity == 3:
            argv.append('-vv')
        if self.failfast:
            argv.append('--exitfirst')
        if self.keepdb:
            argv.append('--reuse-db')

        if self.kw.get('create-db'):
            argv.append('--create-db')
        if self.kw.get('no-migrations'):
            argv.append('--no-migrations')
        if self.kw.get('migrations'):
            argv.append('--migrations')
        if self.kw.get('liveserver'):
            argv.append('--liveserver')
        if self.kw.get('ds'):
            argv.append('--ds {}'.format(self.kw.get('ds')))

        argv.extend(test_labels)
        return pytest.main(argv)
