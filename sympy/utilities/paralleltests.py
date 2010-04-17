"""Simple framework for testing SymPy on parallel processors. """

HAS_MULTIPROCESSING = True

try:
    from multiprocessing import Pool
except ImportError:
    HAS_MULTIPROCESSING = False

from sympy.utilities.runtests import sympy_dir, get_test_files_from_root, convert_to_native_paths
from inspect import isfunction, ismethod, getsourcefile, isgeneratorfunction

from timeit import default_timer as clock

import os, sys, fnmatch

def strip_root(path):
    """ """
    return path[len(sympy_dir)+1:]

TEST_INTERRUPT = 0
TEST_EXCEPTION = 1
TEST_PASS      = 2
TEST_FAIL      = 3
TEST_SKIP      = 4
TEST_XFAIL     = 5
TEST_XPASS     = 6

def test_func((test_file, func_name)):
    """ """
    def result(code, data=None):
        return code, test_file, func_name, None #data

    namespace = {'__file__': test_file}
    execfile(test_file, namespace)
    func = namespace[func_name]

    try:
        func()
    except KeyboardInterrupt:
        return result(INTERRUPT)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if exc_type is AssertionError:
            return result(TEST_FAIL, (exc_type, exc_value, exc_traceback))
        elif exc_type.__name__ == "Skipped":
            return result(TEST_SKIP)
        elif exc_type.__name__ == "XFail":
            return result(TEST_XFAIL)
        elif exc_type.__name__ == "XPass":
            return result(TEST_XPASS, exc_value)
        else:
            return result(TEST_EXCEPTION, (exc_type, exc_value, exc_traceback))
    else:
        return result(TEST_PASS)

def parallel_test(*paths, **kwargs):
    """ """
    if not HAS_MULTIPROCESSING:
        raise RuntimeError("'multiprocessing' package is not available on your system")

    print ">>> Collecting tests ...",
    sys.stdout.flush()

    _test_files = get_test_files_from_root(sympy_dir, 'sympy')

    if not paths:
        test_files = _test_files
    else:
        paths, test_files = convert_to_native_paths(paths), []

        for test_file in _test_files:
            basename = os.path.basename(test_file)

            for path in paths:
                if path in test_file or fnmatch.fnmatch(basename, path):
                    test_files.append(test_file)
                    break

    test_data = []

    for test_file in test_files:
        namespace = {'__file__': test_file}

        try:
            execfile(test_file, namespace)
        except (ImportError, SyntaxError):
            continue

        if "XFAIL" in namespace:
            py_test_file = getsourcefile(namespace["XFAIL"])
        else:
            py_test_file = ""

        disabled = namespace.get("disabled", False)

        if not disabled:
            for name, func in namespace.iteritems():
                if not name.startswith("test_"):
                    continue

                if not (isfunction(func) or ismethod(func)):
                    continue

                if not (getsourcefile(func) in [test_file, py_test_file]):
                    continue

                if not isgeneratorfunction(func) and func.__name__ != 'wrapper':
                    test_data.append((test_file, func.__name__))
                else:
                    pass # XXX: currently not supported due to pickling problems

    print "done"

    failed, skipped, xfailed, xpassed, exceptions = [], [], [], [], []

    pool = Pool(processes=kwargs.get('processes', 1))

    T_start = clock()

    try:
        for code, test_file, func_name, data in pool.imap(test_func, test_data):
            if code == TEST_INTERRUPT:
                raise KeyboardInterrupt

            if code == TEST_PASS:
                sys.stdout.write('.')
            elif code == TEST_FAIL:
                sys.stdout.write('F')
                failed.append((test_file, func_name, data))
            elif code == TEST_SKIP:
                sys.stdout.write('s')
                skipped.append((test_file, func_name, data))
            elif code == TEST_XFAIL:
                sys.stdout.write('f')
                xfailed.append((test_file, func_name, data))
            elif code == TEST_XPASS:
                sys.stdout.write('X')
                xpassed.append((test_file, func_name, data))
            elif code == TEST_EXCEPTION:
                sys.stdout.write('E')
                exceptions.append((test_file, func_name, data))

            sys.stdout.flush()
    except KeyboardInterrupt:
        print " interrupted by user"
        pool.terminate()
        pool.join()
        return

    T_end = clock()
    print

    for test_file, func_name, data in exceptions:
        print strip_root(test_file) + ": " + func_name

    for test_file, func_name, data in failed:
        print strip_root(test_file) + ": " + func_name

    for test_file, func_name, data in skipped:
        print strip_root(test_file) + ": " + func_name

    for test_file, func_name, data in xfailed:
        print strip_root(test_file) + ": " + func_name

    for test_file, func_name, data in xpassed:
        print strip_root(test_file) + ": " + func_name

    print "... in %.2f seconds" % (T_end - T_start)

    if failed or exceptions:
        print "DO *NOT* COMMIT!"

