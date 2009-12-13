"""Tools for analyzing and improving unit tests in SymPy. """

import os, sys, re, glob, inspect, timeit, coverage, math

from sympy.utilities.pytest import Skipped

_scales = [1e0, 1e3, 1e6, 1e9]
_units  = [u's', u'ms', u'\u03bcs', u'ns']

def timed(func):
    """Adaptively measure execution time a function. """
    timer = timeit.Timer(func)

    repeat, number = 3, 1

    for i in range(1, 10):
        if timer.timeit(number) >= 0.2:
            break
        else:
            number *= 10

    return min(timer.repeat(repeat, number)) / number

def scaled(time):
    """Scale time and return an appropriate SI unit. """
    if time > 0.0:
        order = min(-int(math.floor(math.log10(time)) // 3), 3)
    else:
        order = 3

    return time*_scales[order], _units[order]

def covered(executed, executable):
    """Compute coverage percentage using sets of lines. """
    if type(executed) != int:
        executed = len(executed)

    if type(executable) != int:
        executable = len(executable)

    return float(executed)/executable * 100

def filter_paths(paths, root='sympy'):
    """Select only paths starting with `root` (absolute path). """
    root, filtered = os.path.abspath(root), {}

    for path, index in paths.items():
        if path.startswith(root):
            filtered[index] = path

    return filtered

def rev_dict(mapping):
    """Reverse a dict iff the original dict is an isomorphism. """
    return dict([ (v, k) for (k, v) in mapping.items() ])

_pattern = re.compile('^test_.*\.py$')

def find_tests(root='sympy'):
    """Scan recursively a directory and retrive all tests. """
    tests = []

    def rec_find_tests(root):
        print ">>> Entering: %s" % root

        for path in glob.glob(root + '/*'):
            if os.path.isdir(path):
                rec_find_tests(path)
            else:
                name = os.path.split(path)[1]

                if _pattern.match(name) is None:
                    continue

                print "--- Scanning: %s" % path

                path = os.path.abspath(path)
                namespace = {'__file__': path}

                execfile(path, namespace)

                for name, obj in namespace.iteritems():
                    if not name.startswith("test_"):
                        continue

                    if not (inspect.getsourcefile(obj) == path):
                        continue

                    if not (inspect.isfunction(obj) or inspect.ismethod(obj)):
                        continue

                    if inspect.isgeneratorfunction(obj):
                        for i, f in enumerate(obj()):
                            g = lambda: f[0](*f[1:])
                            g.__name__ = "%s__%03i" % (obj.__name__, i)
                            tests.append((g, path))
                    else:
                        tests.append((obj, path))

    rec_find_tests(root)
    return tests

def analyze_tests(tests):
    """Measure execution time and coverage for all given tests. """
    cover = coverage.coverage()

    analysis, executable = {}, {}
    paths, path_index = {}, 0
    slots, items = 0, 0

    for i, (test, _) in enumerate(tests):
        print ">>> (%i) Eval: %s" % (i, test.__name__),

        sys.stdout.flush()

        try:
            time = timed(test)
        except (NameError, Skipped):
            print "--> SKIP"
            continue
        except Exception:
            print "--> FAIL"
            continue

        print "--> OK (avg: %.1f %s)" % scaled(time)

        cover.start()
        test()
        cover.stop()

        executed_lines = {}

        for path, executed in cover.data.lines.iteritems():
            if os.path.split(path)[1].startswith('test_'):
                continue

            try:
                index = paths[path]
            except KeyError:
                index = paths[path] = path_index
                path_index += 1

            executed_lines[index] = set(executed.keys())
            items += len(executed_lines[index])

            if index not in executable:
                executable[index] = set(cover.analysis(path)[1])

            print "--- %5.1f%% -- %s" % (covered(executed, executable[index]), path)

        slots += len(executed_lines)
        cover.erase()

        print "+++ Stat: slots=%i, items=%i, paths=%i" % (slots, items, len(paths))

        analysis[test] = (time, executed_lines)

    mapping = sorted(analysis.keys(), key=lambda x: x.__name__)

    return mapping, analysis, executable, paths

def measure_tests(bits, (mapping, analysis, executable, file_paths)):
    """ """
    file_coverage = {}
    file_executed = {}

    total_executable = 0
    total_executed = 0

    total_time = 0.0

    for i, bit in enumerate(bits):
        if not bit:
            continue

        _, time, covered = analysis[mapping[i]]

        for index, executed in covered.items():
            if index not in paths:
                continue

            if index not in file_executed:
                file_executed[index] = executed
            else:
                file_executed[index] |= executed

        total_time += time

    for file_index, executed in file_executed.items():
        coverage = covered(executed, executable[file_index])
        file_coverage[file_index] = coverage

        total_executable += len(executable[file_index])
        total_executed += len(executed)

    for file_path, file_index in file_paths.items():
        if file_index in file_paths and file_index not in file_coverage:
            total_executable += len(executable[file_index])
            file_coverage[file_index] = 0.0

    total_coverage = covered(total_executed, total_executable)

    return total_time, total_coverage, file_coverage

def analyze_tests(root='sympy', filtered=True):
    """ """
    analysis, executable, paths = eval_tests(find_tests(root))
    tests = sorted(analysis.keys(), key=lambda x: x.__name__)

class Optimizer(object):
    """ """

    def __init__(self, N, M, fitness, **flags):
        self.population = Population(N, M)
        self.fitness    = fitness

        self.current = 0;

        #self.pc = pc
        #self.pm = pm

    def step(self):
        pass

    def more(self, steps):
        for _ in xrange(steps):
            self.step()

class Population(list):
    """ """

    def __init__(self, N, M):
        super(Population, self).__init__([
            Individual(N) for _ in xrange(0, M)
        ])

class Individual(list):
    """ """

    def __init__(self, N):
        super(Individual, self).__init__([
            random.randint(0, 1) for _ in xrange(0, N)
        ])

    def random(self):
        return random.randrange(0, len(self))

    def invert(self, item):
        self[item] = ~self[item] & 1

    def mutate(self, prob):
        if random.random() < prob:
            self.invert(self.random())

