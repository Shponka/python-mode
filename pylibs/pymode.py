import vim


def check_file():
    filename = vim.current.buffer.name
    checkers = vim.eval('g:pymode_lint_checker').split(',')
    ignore = vim.eval("g:pymode_lint_ignore")
    ignore = ignore and ignore.split(',') or []
    select = vim.eval("g:pymode_lint_select")
    select = select and select.split(',') or []
    errors = []

    for c in checkers:
        checker = globals().get(c)
        if checker:
            errors += checker(filename)

    for e in errors:
        e.update(
            filename = filename,
            bufnr = vim.current.buffer.number,
        )

    def ignore_error(e):
        for s in select:
            if e['text'].startswith(s):
                return True
        for i in ignore:
            if e['text'].startswith(i):
                return False
        return True

    errors = filter(ignore_error, errors)
    errors = sorted(errors, key=lambda x: x['lnum'])

    vim.command('let b:qf_list = %s' % repr(errors))


def mccabe(filename):
    import mccabe as mc
    return mc.get_module_complexity(filename)


def pep8(filename):
    _ = PEP8 or _init_pep8()
    checker = PEP8['module'].Checker(filename)
    checker.check_all()
    return checker.errors


def pylint(filename):

    import StringIO
    from logilab.astng.builder import MANAGER
    _ = PYLINT or _init_pylint()
    linter = PYLINT['lint']

    MANAGER.astng_cache.clear()
    linter.reporter.out = StringIO.StringIO()
    linter.check(filename)
    errors, linter.reporter.errors = linter.reporter.errors, []
    return errors


def pyflakes(filename):
    from pyflakes import checker
    import _ast

    codeString = file(filename, 'U').read() + '\n'
    errors = []
    try:
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)

    except SyntaxError, value:
        msg = value.args[0]
        if codeString is None:
            vim.command('echoerr "%s: problem decoding source"' % filename)
        else:
            lnum, col, _ = value.lineno, value.offset, value.text
            errors.append(dict(
                lnum = lnum,
                col = col,
                text = msg,
                type = 'E'
            ))

    else:
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for w in w.messages:
            errors.append(dict(
                lnum = w.lineno,
                col = w.offset,
                text = w.message % w.message_args,
                type = 'E'
            ))
    return errors


PYLINT = dict()
def _init_pylint():

    from pylint import lint, checkers
    import re

    class VimReporter(object):
        def __init__(self):
            self.errors = []

        def add_message(self, msg_id, location, msg):
            _, _, line, col = location[1:]
            self.errors.append(dict(
                lnum = line,
                col = col,
                text = "%s %s" % (msg_id, msg),
                type = msg_id[0]
            ))


    PYLINT['lint'] = lint.PyLinter()
    PYLINT['re'] = re.compile('^(?:.:)?[^:]+:(\d+): \[([EWRCI]+)[^\]]*\] (.*)$')

    checkers.initialize(PYLINT['lint'])
    PYLINT['lint'].load_file_configuration(vim.eval("g:pymode_lint_config"))
    PYLINT['lint'].set_option("output-format", "parseable")
    PYLINT['lint'].set_option("include-ids", 1)
    PYLINT['lint'].set_option("reports", 0)
    PYLINT['lint'].reporter = VimReporter()


PEP8 = dict()
def _init_pep8():

    import pep8 as p8

    class _PEP8Options(object):
        # Default options taken from pep8.process_options()
        max_complexity = -1
        verbose = False
        quiet = False
        no_repeat = False
        exclude = [exc.rstrip('/') for exc in p8.DEFAULT_EXCLUDE.split(',')]
        filename = ['*.py']
        select = []
        ignore = p8.DEFAULT_IGNORE.split(',')  # or []?
        show_source = False
        show_pep8 = False
        statistics = False
        count = False
        benchmark = False
        testsuite = ''
        doctest = False
        logical_checks = physical_checks = None
        messages = counters = None

    # default p8 setup
    p8.options = _PEP8Options()
    p8.options.physical_checks = p8.find_checks('physical_line')
    p8.options.logical_checks = p8.find_checks('logical_line')
    p8.options.counters = dict.fromkeys(p8.BENCHMARK_KEYS, 0)
    p8.options.messages = {}
    p8.args = []

    PEP8['init'] = True
    PEP8['module'] = p8
