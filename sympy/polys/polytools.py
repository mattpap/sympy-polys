"""User-friendly public interface to polynomial functions. """

from sympy import (
    S, Basic, I, Integer, Add, Mul, sympify, ask,
)

from sympy.core.decorators import (
    _sympifyit,
)

from sympy.polys.polyclasses import (
    DMP, ANP, DMF,
)

from sympy.polys.polyutils import (
    dict_from_basic,
    basic_from_dict,
    _sort_gens,
    _unify_gens,
    _analyze_gens,
    _dict_reorder,
    _dict_from_basic_no_gens,
    parallel_dict_from_basic,
)

from sympy.polys.rootisolation import (
    dup_isolate_real_roots_list,
)

from sympy.polys.groebnertools import (
    sdp_from_dict, sdp_div, sdp_groebner,
)

from sympy.polys.monomialtools import (
    Monomial, monomial_key,
)

from sympy.polys.polyerrors import (
    OperationNotSupported, DomainError,
    CoercionFailed, UnificationFailed,
    GeneratorsNeeded, PolynomialError,
    PolificationFailed,
)

from sympy.polys.polycontext import (
    register_context,
)

from sympy.mpmath import (
    polyroots as npolyroots,
)

from sympy.utilities import (
    any, all, group, numbered_symbols,
)

from sympy.ntheory import isprime

import sympy.polys

from sympy.polys.domains import FF, QQ
from sympy.polys.constructor import construct_domain

from sympy.polys import polyoptions as options

def init_poly_from_dict(dict_rep, **args):
    opt = options.build_options(**args)
    return _init_poly_from_dict(dict_rep, opt)

def _init_poly_from_dict(dict_rep, opt):
    """Initialize a Poly given a dict instance. """
    gens = opt.gens
    domain = opt.domain

    if domain is not None:
        for k, v in dict_rep.iteritems():
            dict_rep[k] = domain.convert(v)
    else:
        domain, dict_rep = construct_domain(dict_rep, opt=opt)

    return DMP(dict_rep, domain, len(gens)-1)

def init_poly_from_list(list_rep, **args):
    opt = options.build_options(**args)
    return _init_poly_from_list(list_rep, opt)

def _init_poly_from_list(list_rep, opt):
    """Initialize a Poly given a list instance. """
    if len(opt.gens) != 1:
        raise PolynomialError("can't create a multivariate polynomial from a list")

    gens = opt.gens
    domain = opt.domain

    if domain is not None:
        list_rep = map(domain.convert, list_rep)
    else:
        domain, list_rep = construct_domain(list_rep, opt=opt)

    return DMP(list_rep, domain, len(gens)-1)

def init_poly_from_poly(poly_rep, **args):
    opt = options.build_options(**args)
    return _init_poly_from_poly(poly_rep, opt)

def _init_poly_from_poly(poly_rep, opt):
    """Initialize a Poly given a Poly instance. """
    gens = opt.gens
    field = opt.field
    domain = opt.domain

    if isinstance(poly_rep.rep, DMP):
        if not gens or poly_rep.gens == gens:
            if domain is not None or field is not None:
                rep = poly_rep.rep
            else:
                return poly_rep
        else:
            if set(gens) != set(poly_rep.gens):
                return Poly(poly_rep.as_basic(), opt=opt)
            else:
                dict_rep = dict(zip(*_dict_reorder(
                    poly_rep.rep.to_dict(), poly_rep.gens, gens)))

                rep = DMP(dict_rep, poly_rep.rep.dom, len(gens)-1)

        if domain is not None:
            rep = rep.convert(domain)
        elif field is not None and field:
            rep = rep.convert(rep.dom.get_field())
    else:
        raise PolynomialError("unknown polynomial representation")

    return (rep, gens or poly_rep.gens)

def init_poly_from_basic(basic_rep, **args):
    opt = options.build_options(**args)
    return _init_poly_from_basic(basic_rep, opt)

def _init_poly_from_basic(basic_rep, opt):
    """Initialize a Poly given a Basic expression. """
    try:
        dict_rep, gens = dict_from_basic(basic_rep, opt=opt)
    except GeneratorsNeeded:
        return basic_rep

    def _dict_set_domain(rep, domain):
        result = {}

        for k, v in rep.iteritems():
            result[k] = domain.from_sympy(v)

        return result

    domain = opt.domain

    if domain is not None:
        dict_rep = _dict_set_domain(dict_rep, domain)
    else:
        domain, dict_rep = construct_domain(dict_rep, opt=opt)

    return (DMP(dict_rep, domain, len(gens)-1), gens)

class Poly(Basic):
    """Generic class for representing polynomials in SymPy. """

    __slots__ = ['rep', 'gens']

    is_Poly = True

    def __new__(cls, rep, *gens, **args):
        """Create a new polynomial instance out of something useful. """
        if gens or len(args) != 1 or 'opt' not in args:
            opt = options.Options(gens, args)
        else:
            opt = args['opt']

        if 'order' in opt:
            raise NotImplementedError("'order' keyword is not implemented yet")

        if isinstance(rep, DMP):
            if rep.lev != len(opt.gens)-1 or opt.args:
                raise PolynomialError("invalid arguments to construct a polynomial")
        else:
            if isinstance(rep, (dict, list)):
                if not opt.gens:
                    raise GeneratorsNeeded("can't initialize from %s without generators" % type(rep).__name__)

                if isinstance(rep, dict):
                    rep = _init_poly_from_dict(rep, opt)
                else:
                    rep = _init_poly_from_list(rep, opt)
            else:
                rep = sympify(rep)

                if rep.is_Poly:
                    result = _init_poly_from_poly(rep, opt)
                else:
                    result = _init_poly_from_basic(rep, opt)

                if type(result) is tuple:
                    rep, opt['gens'] = result
                else:
                    if result.is_Poly or not opt.strict:
                        return result
                    else:
                        raise GeneratorsNeeded("can't initialize from %s without generators" % rep)

        obj = Basic.__new__(cls)

        obj.rep = rep
        obj.gens = opt.gens

        return obj

    @classmethod
    def new(cls, rep, gens):
        """Construct :class:`Poly` instance from raw representation. """
        if not isinstance(rep, DMP):
            raise PolynomialError("invalid polynomial representation: %s" % rep)

        obj = Basic.__new__(cls)

        obj.rep = rep
        obj.gens = tuple(gens)

        return obj

    def __getnewargs__(self):
        """Data used by pickling protocol version 2. """
        return (self.rep, self.gens)

    def _hashable_content(self):
        """Allow SymPy to hash Poly instances. """
        return (self.rep, self.gens)

    @property
    def args(self):
        """Don't mess up with the core. """
        return [self.as_basic()]

    @property
    def gen(self):
        """Return principal generator. """
        return self.gens[0]

    def unify(f, g):
        """Make `f` and `g` belong to the same domain. """
        _, per, F, G = f._unify(g)
        return per(F), per(G)

    def _unify(f, g):
        g = sympify(g)

        if not g.is_Poly:
            try:
                return f.rep.dom, f.per, f.rep, f.rep.per(f.rep.dom.from_sympy(g))
            except CoercionFailed:
                raise UnificationFailed("can't unify %s with %s" % (f, g))

        if isinstance(f.rep, DMP) and isinstance(g.rep, DMP):
            gens = _unify_gens(f.gens, g.gens)

            dom, lev = f.rep.dom.unify(g.rep.dom, gens), len(gens)-1

            if f.gens != gens:
                f_monoms, f_coeffs = _dict_reorder(f.rep.to_dict(), f.gens, gens)

                if f.rep.dom != dom:
                    f_coeffs = [ dom.convert(c, f.rep.dom) for c in f_coeffs ]

                F = DMP(dict(zip(f_monoms, f_coeffs)), dom, lev)
            else:
                F = f.rep.convert(dom)

            if g.gens != gens:
                g_monoms, g_coeffs = _dict_reorder(g.rep.to_dict(), g.gens, gens)

                if g.rep.dom != dom:
                    g_coeffs = [ dom.convert(c, g.rep.dom) for c in g_coeffs ]

                G = DMP(dict(zip(g_monoms, g_coeffs)), dom, lev)
            else:
                G = g.rep.convert(dom)
        else:
            raise UnificationFailed("can't unify %s with %s" % (f, g))

        def per(rep, dom=dom, gens=gens, remove=None):
            if remove is not None:
                gens = gens[:remove]+gens[remove+1:]

                if not gens:
                    return dom.to_sympy(rep)

            return Poly(rep, *gens)

        return dom, per, F, G

    def per(f, rep, gens=None, remove=None):
        """Create a Poly out of the given representation. """
        if gens is None:
            gens = f.gens

        if remove is not None:
            gens = gens[:remove]+gens[remove+1:]

            if not gens:
                return f.rep.dom.to_sympy(rep)

        return Poly(rep, *gens)

    def unit(f):
        """Return unit of `f`'s polynomial algebra. """
        return f.per(f.rep.unit())

    def set_domain(f, domain):
        """Set the ground domain of `f`. """
        domain = options.Domain.preprocess(domain)
        return f.per(f.rep.convert(domain))

    def get_domain(f):
        """Get the ground domain of `f`. """
        return f.rep.dom

    def set_modulus(f, modulus):
        """Set the modulus of `f`. """
        modulus = options.Modulus.preprocess(modulus)
        return f.set_domain(FF(modulus))

    def get_modulus(f):
        """Get the modulus of `f`. """
        domain = f.get_domain()

        if not domain.has_CharacteristicZero:
            return Integer(domain.characteristic())
        else:
            raise PolynomialError("not a polynomial over a finite field")

    def _eval_subs(f, old, new):
        """Internal implementation of :func:`subs`. """
        if old in f.gens:
            if new.is_number:
                return f.eval(old, new)
            else:
                try:
                    return f.replace(old, new)
                except PolynomialError:
                    pass

        return f.as_basic().subs(old, new)

    def replace(f, x, y=None):
        """Replace `x` with `y` in generators list. """
        if y is None:
            if f.is_univariate:
                x, y = f.gen, x
            else:
                raise PolynomialError("syntax supported only in univariate case")

        if x == y:
            return f

        if x in f.gens and y not in f.gens:
            dom = f.get_domain()

            if not dom.is_Composite or y not in dom.gens:
                gens = list(f.gens)
                gens[gens.index(x)] = y
                return f.per(f.rep, gens=gens)

        raise PolynomialError("can't replace %s with %s in %s" % (x, y, f))

    def reorder(f, *gens, **args):
        """Efficiently apply new order of generators. """
        opt = options.Options((), args)

        if not gens:
            gens = _sort_gens(f.gens, opt=opt)
        elif set(f.gens) != set(gens):
            raise PolynomialError("generators list can differ only up to order of elements")

        rep = dict(zip(*_dict_reorder(f.rep.to_dict(), f.gens, gens)))

        return f.per(DMP(rep, f.rep.dom, len(gens)-1), gens=gens)

    def to_ring(f):
        """Make the ground domain a ring. """
        try:
            result = f.rep.to_ring()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'to_ring')

        return f.per(result)

    def to_field(f):
        """Make the ground domain a field. """
        try:
            result = f.rep.to_field()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'to_field')

        return f.per(result)

    def to_exact(f):
        """Make the ground domain exact. """
        try:
            result = f.rep.to_exact()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'to_exact')

        return f.per(result)

    def slice(f, x, m, n=None):
        """Take a continuous subsequence of terms of `f`. """
        if n is None:
            j, m, n = 0, x, m
        else:
            j = f._gen_to_level(x)

        m, n = int(m), int(n)

        try:
            result = f.rep.slice(m, n, j)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'slice')

        return f.per(result)

    def coeffs(f, order=None):
        """Returns all non-zero coefficients from `f` in lex order. """
        return [ f.rep.dom.to_sympy(c) for c in f.rep.coeffs(order=order) ]

    def monoms(f, order=None):
        """Returns all non-zero monomials from `f` in lex order. """
        return f.rep.monoms(order=order)

    def terms(f, order=None):
        """Returns all non-zero terms from `f` in lex order. """
        return [ (m, f.rep.dom.to_sympy(c)) for m, c in f.rep.terms(order=order) ]

    def all_coeffs(f):
        """Returns all coefficients from a univariate polynomial `f`. """
        return [ f.rep.dom.to_sympy(c) for c in f.rep.all_coeffs() ]

    def all_monoms(f):
        """Returns all monomials from a univariate polynomial `f`. """
        return f.rep.all_monoms()

    def all_terms(f):
        """Returns all terms from a univariate polynomial `f`. """
        return [ (m, f.rep.dom.to_sympy(c)) for m, c in f.rep.all_terms() ]

    def length(f):
        """Returns the number of non-zero terms in `f`. """
        return len(f.as_dict())

    def as_dict(f):
        """Switch to a dict representation with SymPy coefficients. """
        return f.rep.to_sympy_dict()

    def as_basic(f, *gens):
        """Convert a polynomial instance to a SymPy expression. """
        return basic_from_dict(f.rep.to_sympy_dict(), *(gens or f.gens))

    def lift(f):
        """Convert algebraic coefficients to rationals. """
        try:
            result = f.rep.lift()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'lift')

        return f.per(result)

    def deflate(f):
        """Reduce degree of `f` by mapping `x_i**m` to `y_i`. """
        try:
            J, result = f.rep.deflate()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'deflate')

        return J, f.per(result)

    def terms_gcd(f):
        """Remove GCD of terms from the polynomial `f`. """
        try:
            J, result = f.rep.terms_gcd()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'terms_gcd')

        return J, f.per(result)

    def abs(f):
        """Make all coefficients in `f` positive. """
        try:
            result = f.rep.abs()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'abs')

        return f.per(result)

    def neg(f):
        """Negate all cefficients in `f`. """
        try:
            result = f.rep.neg()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'neg')

        return f.per(result)

    def add(f, g):
        """Add two polynomials `f` and `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.add(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'add')

        return per(result)

    def sub(f, g):
        """Subtract two polynomials `f` and `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.sub(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'sub')

        return per(result)

    def mul(f, g):
        """Multiply two polynomials `f` and `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.mul(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'mul')

        return per(result)

    def sqr(f):
        """Square a polynomial `f`. """
        try:
            result = f.rep.sqr()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'sqr')

        return f.per(result)

    def pow(f, n):
        """Raise `f` to a non-negative power `n`. """
        n = int(n)

        try:
            result = f.rep.pow(n)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'pow')

        return f.per(result)

    def pdiv(f, g):
        """Polynomial pseudo-division of `f` by `g`. """
        _, per, F, G = f._unify(g)

        try:
            q, r = F.pdiv(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'pdiv')

        return per(q), per(r)

    def prem(f, g):
        """Polynomial pseudo-remainder of `f` by `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.prem(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'prem')

        return per(result)

    def pquo(f, g):
        """Polynomial pseudo-quotient of `f` by `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.pquo(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'pquo')

        return per(result)

    def pexquo(f, g):
        """Polynomial exact pseudo-quotient of `f` by `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.pexquo(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'pexquo')

        return per(result)

    def div(f, g):
        """Polynomial division with remainder of `f` by `g`. """
        _, per, F, G = f._unify(g)

        try:
            q, r = F.div(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'div')

        return per(q), per(r)

    def rem(f, g):
        """Computes polynomial remainder of `f` by `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.rem(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'rem')

        return per(result)

    def quo(f, g):
        """Computes polynomial quotient of `f` by `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.quo(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'quo')

        return per(result)

    def exquo(f, g):
        """Computes polynomial exact quotient of `f` by `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.exquo(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'exquo')

        return per(result)

    def _gen_to_level(f, gen):
        """Returns level associated with the given generator. """
        if isinstance(gen, int):
            length = len(f.gens)

            if -length <= gen < length:
                if gen < 0:
                    return length + gen
                else:
                    return gen
            else:
                raise PolynomialError("-%s <= gen < %s expected, got %s" % (length, length, gen))
        else:
            try:
                return list(f.gens).index(sympify(gen))
            except ValueError:
                raise PolynomialError("a valid generator expected, got %s" % gen)

    def degree(f, gen=0):
        """Returns degree of `f` in `x_j`. """
        j = f._gen_to_level(gen)

        try:
            return f.rep.degree(j)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'degree')

    def degree_list(f):
        """Returns a list of degrees of `f`. """
        try:
            return f.rep.degree_list()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'degree_list')

    def total_degree(f):
        """Returns the total degree of `f`. """
        try:
            return f.rep.total_degree()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'total_degree')

    def LC(f, order=None):
        """Returns the leading coefficent of `f`. """
        if order is not None:
            return f.coeffs(order)[0]

        try:
            result = f.rep.LC()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'LC')

        return f.rep.dom.to_sympy(result)

    def TC(f):
        """Returns the trailing coefficent of `f`. """
        try:
            result = f.rep.TC()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'TC')

        return f.rep.dom.to_sympy(result)

    def EC(f, order=None):
        """Returns the last non-zero coefficent of `f`. """
        try:
            return f.coeffs(order)[-1]
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'EC')

    def nth(f, *N):
        """Returns the `n`-th coefficient of `f`. """
        try:
            result = f.rep.nth(*map(int, N))
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'nth')

        return f.rep.dom.to_sympy(result)

    def LM(f, order=None):
        """Returns the leading monomial of `f`. """
        return f.monoms(order)[0]

    def EM(f, order=None):
        """Returns the last non-zero monomial of `f`. """
        return f.monoms(order)[-1]

    def LT(f, order=None):
        """Returns the leading term of `f`. """
        return f.terms(order)[0]

    def ET(f, order=None):
        """Returns the last non-zero term of `f`. """
        return f.terms(order)[-1]

    def max_norm(f):
        """Returns maximum norm of `f`. """
        try:
            result = f.rep.max_norm()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'max_norm')

        return f.rep.dom.to_sympy(result)

    def l1_norm(f):
        """Returns l1 norm of `f`. """
        try:
            result = f.rep.l1_norm()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'l1_norm')

        return f.rep.dom.to_sympy(result)

    def clear_denoms(f, convert=False):
        """Clear denominators, but keep the ground domain. """
        try:
            coeff, result = f.rep.clear_denoms()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'clear_denoms')

        coeff, f = f.rep.dom.to_sympy(coeff), f.per(result)

        if not convert:
            return coeff, f
        else:
            return coeff, f.to_ring()

    def integrate(f, *specs, **args):
        """Computes indefinite integral of `f`. """
        if args.get('auto', True) and f.rep.dom.has_Ring:
            f = f.to_field()

        try:
            if not specs:
                return f.per(f.rep.integrate(m=1))

            rep = f.rep

            for spec in specs:
                if type(spec) is tuple:
                    gen, m = spec
                else:
                    gen, m = spec, 1

                rep = rep.integrate(int(m), f._gen_to_level(gen))

            return f.per(rep)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'integrate')

    def diff(f, *specs):
        """Computes partial derivative of `f`. """
        try:
            if not specs:
                return f.per(f.rep.diff(m=1))

            rep = f.rep

            for spec in specs:
                if type(spec) is tuple:
                    gen, m = spec
                else:
                    gen, m = spec, 1

                rep = rep.diff(int(m), f._gen_to_level(gen))

            return f.per(rep)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'diff')

    def eval(f, x, a=None):
        """Evaluates `f` at `a` in the given variable. """
        if a is None:
            if isinstance(x, dict):
                raise NotImplementedError('dict syntax')
            else:
                j, a = 0, x
        else:
            j = f._gen_to_level(x)

        # XXX: use DomainError when not convertible

        try:
            result = f.rep.eval(a, j)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'eval')

        return f.per(result, remove=j)

    def half_gcdex(f, g, auto=True):
        """Half extended Euclidean algorithm of `f` and `g`. """
        dom, per, F, G = f._unify(g)

        if auto and dom.has_Ring:
            F, G = F.to_field(), G.to_field()

        try:
            s, h = F.half_gcdex(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'half_gcdex')

        return per(s), per(h)

    def gcdex(f, g, auto=True):
        """Extended Euclidean algorithm of `f` and `g`. """
        dom, per, F, G = f._unify(g)

        if auto and dom.has_Ring:
            F, G = F.to_field(), G.to_field()

        try:
            s, t, h = F.gcdex(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'gcdex')

        return per(s), per(t), per(h)

    def invert(f, g, auto=True):
        """Invert `f` modulo `g`, if possible. """
        dom, per, F, G = f._unify(g)

        if auto and dom.has_Ring:
            F, G = F.to_field(), G.to_field()

        try:
            result = F.invert(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'invert')

        return per(result)

    def revert(f, n):
        """Compute `f**(-1)` mod `x**n`. """
        try:
            result = f.rep.revert(int(n))
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'revert')

        return f.per(result)

    def subresultants(f, g):
        """Computes subresultant PRS sequence of `f` and `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.subresultants(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'subresultants')

        return map(per, result)

    def resultant(f, g):
        """Computes resultant of `f` and `g` via PRS. """
        _, per, F, G = f._unify(g)

        try:
            result = F.resultant(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'resultant')

        return per(result, remove=0)

    def discriminant(f):
        """Computes discriminant of `f`. """
        try:
            result = f.rep.discriminant()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'discriminant')

        return f.per(result, remove=0)

    def cofactors(f, g):
        """Returns GCD of `f` and `g` and their cofactors. """
        _, per, F, G = f._unify(g)

        try:
            h, cff, cfg = F.cofactors(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'cofactors')

        return per(h), per(cff), per(cfg)

    def gcd(f, g):
        """Returns polynomial GCD of `f` and `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.gcd(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'gcd')

        return per(result)

    def lcm(f, g):
        """Returns polynomial LCM of `f` and `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.lcm(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'lcm')

        return per(result)

    def trunc(f, p):
        """Reduce `f` modulo a constant `p`. """
        p = f.rep.dom.convert(p)

        try:
            result = f.rep.trunc(p)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'trunc')

        return f.per(result)

    def monic(f, auto=True):
        """Divides all coefficients by `LC(f)`. """
        if auto and f.rep.dom.has_Ring:
            f = f.to_field()

        try:
            result = f.rep.monic()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'monic')

        return f.per(result)

    def content(f):
        """Returns GCD of polynomial coefficients. """
        try:
            result = f.rep.content()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'content')

        return f.rep.dom.to_sympy(result)

    def primitive(f):
        """Returns content and a primitive form of `f`. """
        try:
            cont, result = f.rep.primitive()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'primitive')

        return f.rep.dom.to_sympy(cont), f.per(result)

    def compose(f, g):
        """Computes functional composition of `f` and `g`. """
        _, per, F, G = f._unify(g)

        try:
            result = F.compose(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'compose')

        return per(result)

    def decompose(f):
        """Computes functional decomposition of `f`. """
        try:
            result = f.rep.decompose()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'decompose')

        return map(f.per, result)

    def sturm(f, auto=True):
        """Computes the Sturm sequence of `f`. """
        if auto and f.rep.dom.has_Ring:
            f = f.to_field()

        try:
            result = f.rep.sturm()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'sturm')

        return map(f.per, result)

    def gff_list(f):
        """Computes greatest factorial factorization of `f`. """
        try:
            result = f.rep.gff_list()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'gff_list')

        return [ (f.per(g), k) for g, k in result ]

    def sqf_norm(f):
        """Computes square-free norm of `f`. """
        try:
            s, g, r = f.rep.sqf_norm()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'sqf_norm')

        return s, f.per(g), f.per(r)

    def sqf_part(f):
        """Computes square-free part of `f`. """
        try:
            result = f.rep.sqf_part()
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'sqf_part')

        return f.per(result)

    def sqf_list(f, all=False):
        """Returns a list of square-free factors of `f`. """
        try:
            coeff, factors = f.rep.sqf_list(all)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'sqf_list')

        return f.rep.dom.to_sympy(coeff), [ (f.per(g), k) for g, k in factors ]

    def sqf_list_include(f, all=False):
        """Returns a list of square-free factors of `f`. """
        try:
            factors = f.rep.sqf_list_include(all)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'sqf_list_include')

        return [ (f.per(g), k) for g, k in factors ]

    def factor_list(f):
        """Returns a list of irreducible factors of `f`. """
        try:
            coeff, factors = f.rep.factor_list()
        except DomainError:
            return S.One, [(f, 1)]
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'factor_list')

        return f.rep.dom.to_sympy(coeff), [ (f.per(g), k) for g, k in factors ]

    def factor_list_include(f):
        """Returns a list of irreducible factors of `f`. """
        try:
            factors = f.rep.factor_list_include()
        except DomainError:
            return [(f, 1)]
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'factor_list_include')

        return [ (f.per(g), k) for g, k in factors ]

    def intervals(f, all=False, eps=None, inf=None, sup=None, fast=False, sqf=False):
        """Compute isolating intervals for roots of `f`. """
        if eps is not None:
            eps = QQ.convert(eps)

        if inf is not None:
            inf = QQ.convert(inf)
        if sup is not None:
            sup = QQ.convert(sup)

        try:
            result = f.rep.intervals(all=all, eps=eps, inf=inf, sup=sup, fast=fast, sqf=sqf)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'intervals')

        if sqf:
            def _real((s, t)):
                return (QQ.to_sympy(s), QQ.to_sympy(t))

            if not all:
                return map(_real, result)

            def _complex(((u, v), (s, t))):
                return (QQ.to_sympy(u) + I*QQ.to_sympy(v),
                        QQ.to_sympy(s) + I*QQ.to_sympy(t))

            real_part, complex_part = result

            return map(_real, real_part), map(_complex, complex_part)
        else:
            def _real(((s, t), k)):
                return ((QQ.to_sympy(s), QQ.to_sympy(t)), k)

            if not all:
                return map(_real, result)

            def _complex((((u, v), (s, t)), k)):
                return ((QQ.to_sympy(u) + I*QQ.to_sympy(v),
                         QQ.to_sympy(s) + I*QQ.to_sympy(t)), k)

            real_part, complex_part = result

            return map(_real, real_part), map(_complex, complex_part)

    def refine_root(f, s, t, eps=None, steps=None, fast=False, check_sqf=False):
        """Refine an isolating interval of a root to the given precision. """
        if check_sqf and not f.is_sqf:
            raise PolynomialError("only square-free polynomials supported")

        s, t = QQ.convert(s), QQ.convert(t)

        if eps is not None:
            eps = QQ.convert(eps)

        if steps is not None:
            steps = int(steps)
        elif eps is None:
            steps = 1

        try:
            S, T = f.rep.refine_root(s, t, eps=eps, steps=steps, fast=fast)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'refine_root')

        return QQ.to_sympy(S), QQ.to_sympy(T)

    def count_roots(f, inf=None, sup=None):
        """Return the number of roots of ``f`` in ``[inf, sup]`` interval. """
        inf_real, sup_real = True, True

        if inf is not None:
            inf = sympify(inf)

            if inf is S.NegativeInfinity:
                inf = None
            else:
                re, im = inf.as_real_imag()

                if not im:
                    inf = QQ.convert(inf)
                else:
                    inf, inf_real = map(QQ.convert, (re, im)), False

        if sup is not None:
            sup = sympify(sup)

            if sup is S.Infinity:
                sup = None
            else:
                re, im = sup.as_real_imag()

                if not im:
                    sup = QQ.convert(sup)
                else:
                    sup, sup_real = map(QQ.convert, (re, im)), False

        if inf_real and sup_real:
            try:
                count = f.rep.count_real_roots(inf=inf, sup=sup)
            except AttributeError: # pragma: no cover
                raise OperationNotSupported(f, 'count_real_roots')
        else:
            if inf_real and inf is not None:
                inf = (inf, QQ.zero)

            if sup_real and sup is not None:
                sup = (sup, QQ.zero)

            try:
                count = f.rep.count_complex_roots(inf=inf, sup=sup)
            except AttributeError: # pragma: no cover
                raise OperationNotSupported(f, 'count_complex_roots')

        return Integer(count)

    def real_roots(f, multiple=True):
        """Return a list of real roots with multiplicities. """
        reals = sympy.polys.rootoftools.RootOf(f)

        if multiple:
            return reals
        else:
            return group(reals, multiple=False)

    def nroots(f, maxsteps=50, cleanup=True, error=False):
        """Compute numerical approximations of roots of `f`. """
        if f.is_multivariate:
            raise PolynomialError("can't compute numerical roots of a multivariate polynomial")

        if f.degree() <= 0:
            return []

        try:
            coeffs = [ complex(c) for c in f.all_coeffs() ]
        except ValueError:
            raise DomainError("numerical domain expected, got %s" % f.rep.dom)

        return sympify(npolyroots(coeffs, maxsteps=maxsteps, cleanup=cleanup, error=error))

    def cancel(f, g):
        """Cancel common factors in a rational function `f/g`.  """
        dom, per, F, G = f._unify(g)

        if F.is_zero or G.is_zero:
            return S.One, per(F), per(G)

        if dom.has_Field and dom.has_assoc_Ring:
            cF, F = F.clear_denoms()
            cG, G = G.clear_denoms()

            F = F.to_ring()
            G = G.to_ring()

        try:
            _, P, Q = F.cofactors(G)
        except AttributeError: # pragma: no cover
            raise OperationNotSupported(f, 'cofactors')

        if dom.has_Field and dom.has_assoc_Ring:
            P, Q = P.to_field(), Q.to_field()

            cF = dom.to_sympy(cF)
            cG = dom.to_sympy(cG)

            coeff = cG/cF
        else:
            coeff = S.One

        p_neg = dom.is_negative(P.LC())
        q_neg = dom.is_negative(Q.LC())

        if p_neg and q_neg:
            P, Q = -P, -Q
        elif p_neg:
            coeff, P = -coeff, -P
        elif q_neg:
            coeff, Q = -coeff, -Q

        return coeff, per(P), per(Q)

    @property
    def is_zero(f):
        """Returns `True` if `f` is a zero polynomial. """
        return f.rep.is_zero

    @property
    def is_one(f):
        """Returns `True` if `f` is a unit polynomial. """
        return f.rep.is_one

    @property
    def is_sqf(f):
        """Returns `True` if `f` is a square-free polynomial. """
        return f.rep.is_sqf

    @property
    def is_monic(f):
        """Returns `True` if the leading coefficient of `f` is one. """
        return f.rep.is_monic

    @property
    def is_primitive(f):
        """Returns `True` if GCD of coefficients of `f` is one. """
        return f.rep.is_primitive

    @property
    def is_ground(f):
        """Returns `True` if `f` is an element of the ground domain. """
        return f.rep.is_ground

    @property
    def is_linear(f):
        """Returns `True` if `f` is linear in all its variables. """
        return f.rep.is_linear

    @property
    def is_monomial(f):
        """Returns `True` if `f` is zero or has only one term. """
        return f.length() <= 1

    @property
    def is_homogeneous(f):
        """Returns `True` if `f` has zero trailing coefficient. """
        return f.rep.is_homogeneous

    @property
    def is_irreducible(f):
        """Returns `True` if `f` has no factors over its domain. """
        return f.rep.is_irreducible

    @property
    def is_univariate(f):
        """Returns `True` if `f` is an univariate polynomial. """
        return len(f.gens) == 1

    @property
    def is_multivariate(f):
        """Returns `True` if `f` is a multivariate polynomial. """
        return len(f.gens) != 1

    def __abs__(f):
        return f.abs()

    def __neg__(f):
        return f.neg()

    @_sympifyit('g', NotImplemented)
    def __add__(f, g):
        if not g.is_Poly:
            try:
                g = Poly(g, *f.gens)
            except PolynomialError:
                return f.as_basic() + g

        return f.add(g)

    @_sympifyit('g', NotImplemented)
    def __radd__(f, g):
        if not g.is_Poly:
            try:
                g = Poly(g, *f.gens)
            except PolynomialError:
                return g + f.as_basic()

        return g.add(f)

    @_sympifyit('g', NotImplemented)
    def __sub__(f, g):
        if not g.is_Poly:
            try:
                g = Poly(g, *f.gens)
            except PolynomialError:
                return f.as_basic() - g

        return f.sub(g)

    @_sympifyit('g', NotImplemented)
    def __rsub__(f, g):
        if not g.is_Poly:
            try:
                g = Poly(g, *f.gens)
            except PolynomialError:
                return g - f.as_basic()

        return g.sub(f)

    @_sympifyit('g', NotImplemented)
    def __mul__(f, g):
        if not g.is_Poly:
            try:
                g = Poly(g, *f.gens)
            except PolynomialError:
                return f.as_basic()*g

        return f.mul(g)

    @_sympifyit('g', NotImplemented)
    def __rmul__(f, g):
        if not g.is_Poly:
            try:
                g = Poly(g, *f.gens)
            except PolynomialError:
                return g*f.as_basic()

        return g.mul(f)

    @_sympifyit('n', NotImplemented)
    def __pow__(f, n):
        if n.is_Integer and n >= 0:
            return f.pow(n)
        else:
            return f.as_basic()**n

    @_sympifyit('g', NotImplemented)
    def __divmod__(f, g):
        if not g.is_Poly:
            g = Poly(g, *f.gens)

        return f.div(g)

    @_sympifyit('g', NotImplemented)
    def __rdivmod__(f, g):
        if not g.is_Poly:
            g = Poly(g, *f.gens)

        return g.div(f)

    @_sympifyit('g', NotImplemented)
    def __mod__(f, g):
        if not g.is_Poly:
            g = Poly(g, *f.gens)

        return f.rem(g)

    @_sympifyit('g', NotImplemented)
    def __rmod__(f, g):
        if not g.is_Poly:
            g = Poly(g, *f.gens)

        return g.rem(f)

    @_sympifyit('g', NotImplemented)
    def __floordiv__(f, g):
        if not g.is_Poly:
            g = Poly(g, *f.gens)

        return f.exquo(g)

    @_sympifyit('g', NotImplemented)
    def __rfloordiv__(f, g):
        if not g.is_Poly:
            g = Poly(g, *f.gens)

        return g.exquo(f)

    @_sympifyit('g', NotImplemented)
    def __div__(f, g):
        return f.as_basic()/g.as_basic()

    @_sympifyit('g', NotImplemented)
    def __rdiv__(f, g):
        return g.as_basic()/f.as_basic()

    __truediv__ = __div__
    __rtruediv__ = __rdiv__

    @_sympifyit('g', NotImplemented)
    def __eq__(f, g):
        if not g.is_Poly:
            try:
                g = Poly(g, *f.gens, **{'domain': f.get_domain()})
            except (PolynomialError, DomainError, CoercionFailed):
                return False

        if f.gens != g.gens:
            return False

        if f.rep.dom != g.rep.dom:
            try:
                dom = f.rep.dom.unify(g.rep.dom, f.gens)
            except UnificationFailed:
                return False

            f = f.set_domain(dom)
            g = g.set_domain(dom)

        return f.rep == g.rep

    @_sympifyit('g', NotImplemented)
    def __ne__(f, g):
        return not f.__eq__(g)

    def __hash__(self):
        return super(Poly, self).__hash__()

    def __nonzero__(f):
        return not f.is_zero

def parallel_poly_from_expr(exprs, *gens, **args):
    """Construct polynomials from expressions. """
    opt = options.Options(gens, args)

    origs, exprs = list(exprs), []
    _exprs, _polys = [], []

    for i, expr in enumerate(origs):
        expr = sympify(expr)

        if expr.is_Poly:
            _polys.append(i)
        else:
            _exprs.append(i)

            if opt.expand:
                expr = expr.expand()

        exprs.append(expr)

    if _polys:
        # XXX: this is a temporary solution
        for i in _polys:
            exprs[i] = exprs[i].as_basic()

    try:
        reps, gens = parallel_dict_from_basic(exprs, opt=opt)
    except GeneratorsNeeded:
        raise PolificationFailed(origs, exprs)

    coeffs_list, lengths = [], []

    all_monoms = []
    all_coeffs = []

    for rep in reps:
        monoms, coeffs = zip(*rep.items())

        coeffs_list.extend(coeffs)
        all_monoms.append(monoms)

        lengths.append(len(coeffs))

    domain = opt.domain

    if domain is None:
        domain, coeffs_list = construct_domain(coeffs_list, opt=opt)
    else:
        coeffs_list = map(domain.from_sympy, coeffs_list)

    for k in lengths:
        all_coeffs.append(coeffs_list[:k])
        coeffs_list = coeffs_list[k:]

    polys, level = [], len(gens)-1

    for monoms, coeffs in zip(all_monoms, all_coeffs):
        rep = DMP.from_monoms_coeffs(monoms, coeffs, level, domain)
        polys.append(Poly.new(rep, gens))

    opt['gens'] = gens
    opt['domain'] = domain

    if opt.polys is None:
        opt['polys'] = bool(_polys)

    return polys, opt

def NonStrictPoly(f, *gens, **args):
    """Create a Poly instance with `strict` keyword set.  """
    args = dict(args)
    args['strict'] = False
    return Poly(f, *gens, **args)

def _polify_basic(f, g, *gens, **args):
    """Cooperatively make polynomials out of `f` and `g`. """
    if gens:
        F = NonStrictPoly(f, *gens, **args)
        G = NonStrictPoly(g, *gens, **args)

        if not F.is_Poly or not G.is_Poly:
            raise CoercionFailed(F, G) # pragma: no cover
        else:
            return F, G
    else:
        F = NonStrictPoly(f, **args)
        G = NonStrictPoly(g, **args)

        if F.is_Poly:
            if G.is_Poly:
                return F, G
            else:
                return F, Poly(g, *F.gens, **args)
        else:
            if G.is_Poly:
                return Poly(f, *G.gens, **args), G
            else:
                raise CoercionFailed(F, G)

def _update_args(args, key, value):
    """Add a new `(key, value)` pair to arguments dict. """
    args = dict(args)

    if not args.has_key(key):
        args[key] = value

    return args

def _filter_args(args, *keys):
    """Filter the given keys from the args dict. """
    if not keys:
        return {}

    keys, result = set(keys), {}

    for key, value in args.items():
        if key in keys:
            result[key] = value

    return result

def _should_return_basic(*polys, **args):
    """Figure out if results should be returned as basic. """
    query = args.get('polys')

    if query is not None:
        return not query
    else:
        return not all(isinstance(poly, Poly) for poly in polys)

def _keep_coeff(coeff, factors):
    """Return ``coeff*factors`` unevaluated if necessary. """
    if coeff == 1:
        return factors
    elif coeff == -1:
        return -factors
    elif not factors.is_Add:
        return coeff*factors
    else:
        return Mul(coeff, factors, evaluate=False)

def degree(f, *gens, **args):
    """Returns degree of `f` in the given generator. """
    try:
        F = Poly(f, *_analyze_gens(gens), **args)
    except GeneratorsNeeded:
        raise GeneratorsNeeded("can't compute degree of %s without generators" % f)

    degree = F.degree(args.get('gen', 0))

    return Integer(degree)

def degree_list(f, *gens, **args):
    """Returns a list of degrees of `f` in all generators. """
    try:
        F = Poly(f, *_analyze_gens(gens), **args)
    except GeneratorsNeeded:
        raise GeneratorsNeeded("can't compute degrees list of %s without generators" % f)

    degrees = F.degree_list()

    return tuple(map(Integer, degrees))

def LC(f, *gens, **args):
    """Returns the leading coefficient of `f`. """
    order = args.pop('order', None)

    try:
        return Poly(f, *gens, **args).LC(order=order)
    except GeneratorsNeeded:
        raise GeneratorsNeeded("can't compute the leading coefficient of %s without generators" % f)

def LM(f, *gens, **args):
    """Returns the leading monomial of `f`. """
    order = args.pop('order', None)

    try:
        f = Poly(f, *gens, **args)
    except GeneratorsNeeded:
        raise GeneratorsNeeded("can't compute the leading monomial of %s without generators" % f)

    return Monomial(*f.LM(order=order)).as_basic(*f.gens)

def LT(f, *gens, **args):
    """Returns the leading term of `f`. """
    order = args.pop('order', None)

    try:
        f = Poly(f, *gens, **args)
    except GeneratorsNeeded:
        raise GeneratorsNeeded("can't compute the leading term of %s without generators" % f)

    monom, coeff = f.LT(order=order)

    return coeff*Monomial(*monom).as_basic(*f.gens)

def pdiv(f, g, *gens, **args):
    """Polynomial pseudo-division of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute pseudo division of %s and %s without generators" % (f, g))

    q, r = F.pdiv(G)

    if _should_return_basic(f, g, **args):
        return q.as_basic(), r.as_basic()
    else:
        return q, r

def prem(f, g, *gens, **args):
    """Polynomial pseudo-remainder of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute pseudo remainder of %s and %s without generators" % (f, g))

    r = F.prem(G)

    if _should_return_basic(f, g, **args):
        return r.as_basic()
    else:
        return r

def pquo(f, g, *gens, **args):
    """Polynomial pseudo-quotient of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute pseudo quotient of %s and %s without generators" % (f, g))

    q = F.pquo(G)

    if _should_return_basic(f, g, **args):
        return q.as_basic()
    else:
        return q

def pexquo(f, g, *gens, **args):
    """Polynomial exact pseudo-quotient of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute pseudo quotient of %s and %s without generators" % (f, g))

    q = F.pexquo(G)

    if _should_return_basic(f, g, **args):
        return q.as_basic()
    else:
        return q

def div(f, g, *gens, **args):
    """Polynomial division with remainder of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute division of %s and %s without generators" % (f, g))

    q, r = F.div(G)

    if _should_return_basic(f, g, **args):
        return q.as_basic(), r.as_basic()
    else:
        return q, r

def rem(f, g, *gens, **args):
    """Computes polynomial remainder of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute remainder of %s and %s without generators" % (f, g))

    r = F.rem(G)

    if _should_return_basic(f, g, **args):
        return r.as_basic()
    else:
        return r

def quo(f, g, *gens, **args):
    """Computes polynomial quotient of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute quotient of %s and %s without generators" % (f, g))

    q = F.quo(G)

    if _should_return_basic(f, g, **args):
        return q.as_basic()
    else:
        return q

def exquo(f, g, *gens, **args):
    """Computes polynomial exact quotient of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute quotient of %s and %s without generators" % (f, g))

    q = F.exquo(G)

    if _should_return_basic(f, g, **args):
        return q.as_basic()
    else:
        return q

def half_gcdex(f, g, *gens, **args):
    """Half extended Euclidean algorithm of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        try:
            return f.half_gcdex(g)
        except (AttributeError, TypeError): # pragma: no cover
            raise GeneratorsNeeded("can't compute half extended GCD of %s and %s without generators" % (f, g))

    s, h = F.half_gcdex(G, **_filter_args(args, 'auto'))

    if _should_return_basic(f, g, **args):
        return s.as_basic(), h.as_basic()
    else:
        return s, h

def gcdex(f, g, *gens, **args):
    """Extended Euclidean algorithm of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        try:
            return f.gcdex(g)
        except (AttributeError, TypeError): # pragma: no cover
            raise GeneratorsNeeded("can't compute extended GCD of %s and %s without generators" % (f, g))

    s, t, h = F.gcdex(G, **_filter_args(args, 'auto'))

    if _should_return_basic(f, g, **args):
        return s.as_basic(), t.as_basic(), h.as_basic()
    else:
        return s, t, h

def invert(f, g, *gens, **args):
    """Invert `f` modulo `g`, if possible. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        try:
            return f.invert(g)
        except (AttributeError, TypeError): # pragma: no cover
            raise GeneratorsNeeded("can't compute inversion of %s modulo %s without generators" % (f, g))

    h = F.invert(G, **_filter_args(args, 'auto'))

    if _should_return_basic(f, g, **args):
        return h.as_basic()
    else:
        return h

def subresultants(f, g, *gens, **args):
    """Computes subresultant PRS sequence of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute subresultants of %s and %s without generators" % (f, g))

    result = F.subresultants(G)

    if _should_return_basic(f, g, **args):
        return [ r.as_basic() for r in result ]
    else:
        return result

def resultant(f, g, *gens, **args):
    """Computes resultant of `f` and `g` via PRS. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute resultant of %s and %s without generators" % (f, g))

    result = F.resultant(G)

    if _should_return_basic(f, g, **args):
        return result.as_basic()
    else:
        return result

def discriminant(f, *gens, **args):
    """Computes discriminant of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute discriminant of %s without generators" % f)

    result = F.discriminant()

    if _should_return_basic(f, **args):
        return result.as_basic()
    else:
        return result

def cofactors(f, g, *gens, **args):
    """Returns GCD of `f` and `g` and their cofactors. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        try:
            return f.cofactors(g)
        except (AttributeError, TypeError): # pragma: no cover
            raise GeneratorsNeeded("can't compute cofactors of %s and %s without generators" % (f, g))

    h, cff, cfg = F.cofactors(G)

    if _should_return_basic(f, g, **args):
        return h.as_basic(), cff.as_basic(), cfg.as_basic()
    else:
        return h, cff, cfg

def gcd(f, g, *gens, **args):
    """Returns polynomial GCD of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        try:
            return f.gcd(g)
        except (AttributeError, TypeError): # pragma: no cover
            raise GeneratorsNeeded("can't compute GCD of %s and %s without generators" % (f, g))

    result = F.gcd(G)

    if _should_return_basic(f, g, **args):
        return result.as_basic()
    else:
        return result

def lcm(f, g, *gens, **args):
    """Returns polynomial LCM of `f` and `g`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        try:
            return f.lcm(g)
        except (AttributeError, TypeError): # pragma: no cover
            raise GeneratorsNeeded("can't compute LCM of %s and %s without generators" % (f, g))

    result = F.lcm(G)

    if _should_return_basic(f, g, **args):
        return result.as_basic()
    else:
        return result

def terms_gcd(f, *gens, **args):
    """Remove GCD of terms from the polynomial `f`. """
    try:
        f = Poly(f, *_analyze_gens(gens), **args)
    except GeneratorsNeeded:
        return f

    (J, f), dom = f.terms_gcd(), f.get_domain()

    if dom.has_Ring:
        if dom.has_Field:
            denom, f = f.clear_denoms(convert=True)

        coeff, f = f.primitive()

        if dom.has_Field:
            coeff /= denom
    else:
        coeff = 1

    term = Mul(*[ x**j for x, j in zip(f.gens, J) ])

    return _keep_coeff(coeff, term*f.as_basic())

def trunc(f, p, *gens, **args):
    """Reduce `f` modulo a constant `p`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        return F % p

    if _should_return_basic(f, **args):
        return F.trunc(p).as_basic()
    else:
        return F.trunc(p)

def monic(f, *gens, **args):
    """Divides all coefficients by `LC(f)`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute monic polynomial of %s without generators" % f)

    G = F.monic(**_filter_args(args, 'auto'))

    if _should_return_basic(f, **args):
        return G.as_basic()
    else:
        return G

def content(f, *gens, **args):
    """Returns GCD of polynomial coefficients. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute content of %s without generators" % f)
    else:
        return F.content()

def primitive(f, *gens, **args):
    """Returns content and a primitive form of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute primitive part of %s without generators" % f)

    cont, result = F.primitive()

    if _should_return_basic(f, **args):
        return cont, result.as_basic()
    else:
        return cont, result

def compose(f, g, *gens, **args):
    """Returns functional composition `f(g)`. """
    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(f, g, *gens, **args)
    except CoercionFailed, (f, g):
        raise GeneratorsNeeded("can't compute composition of %s and %s without generators" % (f, g))

    result = F.compose(G)

    if _should_return_basic(f, g, **args):
        return result.as_basic()
    else:
        return result

def decompose(f, *gens, **args):
    """Computes functional decomposition of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute functional decomposition of %s without generators" % f)

    result = F.decompose()

    if _should_return_basic(f, **args):
        return [ r.as_basic() for r in result ]
    else:
        return result

def sturm(f, *gens, **args):
    """Computes the Sturm sequence of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute Sturm sequence of %s without generators" % f)

    result = F.sturm(**_filter_args(args, 'auto'))

    if _should_return_basic(f, **args):
        return [ r.as_basic() for r in result ]
    else:
        return result

def gff_list(f, *gens, **args):
    """Returns a list of greatest factorial factors of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        return []

    factors = F.gff_list()

    if _should_return_basic(f, **args):
        return [ (g.as_basic(), k) for g, k in factors ]
    else:
        return factors

def gff(f, *gens, **args):
    """Computes greatest factorial factorization of `f`. """
    raise NotImplementedError('symbolic falling factorial')

def sqf_norm(f, *gens, **args):
    """Computes square-free norm of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute square-free norm of %s without generators" % f)

    s, g, r = F.sqf_norm()

    if _should_return_basic(f, **args):
        return Integer(s), g.as_basic(), r.as_basic()
    else:
        return Integer(s), g, r

def sqf_part(f, *gens, **args):
    """Computes square-free part of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute square-free part of %s without generators" % f)

    result = F.sqf_part()

    if _should_return_basic(f, **args):
        return result.as_basic()
    else:
        return result

def sqf_list(f, *gens, **args):
    """Returns a list of square-free factors of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute square-free decomposition of %s without generators" % f)

    all = args.get('all', False)

    if not args.get('include', False):
        coeff, factors = result = F.sqf_list(all)

        if _should_return_basic(f, **args):
            return coeff, [ (g.as_basic(), k) for g, k in factors ]
        else:
            return coeff, factors
    else:
        factors = F.sqf_list_include()

        if _should_return_basic(f, **args):
            return [ (g.as_basic(), k) for g, k in factors ]
        else:
            return factors

def sqf(f, *gens, **args):
    """Returns square-free decomposition of `f`. """
    frac = args.get('frac', False)
    gens = _analyze_gens(gens)

    def _sqf(f):
        """Squaqre-free factor a true polynomial expression. """
        F = NonStrictPoly(f, *gens, **args)

        if not F.is_Poly:
            return (S.One, F)

        (coeff, factors), result = F.sqf_list(), S.One

        for g, k in factors:
            result *= g.as_basic()**k

        return (coeff, result)

    if not frac:
        coeff, factors = _sqf(f)
    else:
        p, q = cancel(f).as_numer_denom()

        coeff_p, factors_p = _sqf(p)
        coeff_q, factors_q = _sqf(q)

        coeff = coeff_p / coeff_q
        factors = factors_p / factors_q

    return _keep_coeff(coeff, factors)

def factor_list(f, *gens, **args):
    """Returns a list of irreducible factors of `f`. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        raise GeneratorsNeeded("can't compute factorization of %s without generators" % f)

    if not args.get('include', False):
        coeff, factors = result = F.factor_list()

        if _should_return_basic(f, **args):
            return coeff, [ (g.as_basic(), k) for g, k in factors ]
        else:
            return coeff, factors
    else:
        factors = F.factor_list_include()

        if _should_return_basic(f, **args):
            return [ (g.as_basic(), k) for g, k in factors ]
        else:
            return factors

@register_context
def factor(f, *gens, **args):
    """Returns factorization into irreducibles of `f`. """
    frac = args.get('frac', False)

    def _factor(f):
        """Factor a true polynomial expression. """
        F = NonStrictPoly(f, *gens, **args)

        if not F.is_Poly:
            return (S.One, F)

        (coeff, factors), result = F.factor_list(), S.One

        for g, k in factors:
            result *= g.as_basic()**k

        return (coeff, result)

    if not frac:
        coeff, factors = _factor(f)
    else:
        p, q = cancel(f).as_numer_denom()

        coeff_p, factors_p = _factor(p)
        coeff_q, factors_q = _factor(q)

        coeff = coeff_p / coeff_q
        factors = factors_p / factors_q

    return _keep_coeff(coeff, factors)

def intervals(F, all=False, eps=None, inf=None, sup=None, strict=False, fast=False, sqf=False):
    """Compute isolating intervals for roots of `f`. """
    if not hasattr(F, '__iter__'):
        try:
            F = Poly(F)
        except GeneratorsNeeded:
            return []

        return F.intervals(all=all, eps=eps, inf=inf, sup=sup, fast=fast, sqf=sqf)
    else:
        polys, opt = parallel_poly_from_expr(F, domain='QQ')

        if len(opt.gens) > 1:
            raise MultivariatePolynomialError

        for i, poly in enumerate(polys):
            polys[i] = poly.rep.rep

        if eps is not None:
            eps = opt.domain.convert(eps)
        if inf is not None:
            inf = opt.domain.convert(inf)
        if sup is not None:
            sup = opt.domain.convert(sup)

        intervals = dup_isolate_real_roots_list(polys, opt.domain,
            eps=eps, inf=inf, sup=sup, strict=strict, fast=fast)

        result = []

        for (s, t), indices in intervals:
            s, t = opt.domain.to_sympy(s), opt.domain.to_sympy(t)
            result.append(((s, t), indices))

        return result

def refine_root(f, s, t, eps=None, steps=None, fast=False, check_sqf=False):
    """Refine an isolating interval of a root to the given precision. """
    try:
        F = Poly(f)
    except GeneratorsNeeded:
        raise PolynomialError("can't refine a root of %s, not a polynomial" % f)

    return F.refine_root(s, t, eps=eps, steps=steps, fast=fast, check_sqf=check_sqf)

def count_roots(f, inf=None, sup=None):
    """Return the number of roots of ``f`` in ``[inf, sup]`` interval. """
    try:
        F = Poly(f, greedy=False)
    except GeneratorsNeeded:
        raise PolynomialError("can't count roots of %s, not a polynomial" % f)

    return F.count_roots(inf=inf, sup=sup)

def real_roots(f, multiple=True):
    """Return a list of real roots with multiplicities of ``f``. """
    try:
        F = Poly(f, greedy=False)
    except GeneratorsNeeded:
        raise PolynomialError("can't compute real roots of %s, not a polynomial" % f)

    return F.real_roots(multiple=multiple)

def nroots(f, maxsteps=50, cleanup=True, error=False):
    """Compute numerical approximations of roots of `f`. """
    try:
        F = Poly(f, greedy=False)
    except GeneratorsNeeded:
        raise PolynomialError("can't compute numerical roots of %s, not a polynomial" % f)

    return F.nroots(maxsteps=maxsteps, cleanup=cleanup, error=error)

def cancel(f, *gens, **args):
    """Cancel common factors in a rational function `f`.  """
    f = sympify(f)

    if type(f) is not tuple:
        if f.is_Number:
            return f
        else:
            p, q = f.as_numer_denom()
    else:
        p, q = f

    gens = _analyze_gens(gens)

    try:
        F, G = _polify_basic(p, q, *gens, **args)
    except CoercionFailed:
        if type(f) is not tuple:
            return f
        else:
            return S.One, p, q

    c, P, Q = F.cancel(G)

    if type(f) is not tuple:
        return c*(P.as_basic()/Q.as_basic())
    else:
        if _should_return_basic(p, q, **args):
            return c, P.as_basic(), Q.as_basic()
        else:
            return c, P, Q

def reduced(f, G, *gens, **args):
    """Reduces a polynomial `f` modulo a set of polynomials `G`. """
    polys, opt = parallel_poly_from_expr([f] + list(G), *gens, **args)

    for i, poly in enumerate(polys):
        polys[i] = sdp_from_dict(poly.rep.to_dict(), opt.order)

    level = len(opt.gens)-1

    Q, r = sdp_div(polys[0], polys[1:], level, opt.order, opt.domain)

    Q = [ Poly(DMP(dict(q), opt.domain, level), *opt.gens) for q in Q ]
    r =   Poly(DMP(dict(r), opt.domain, level), *opt.gens)

    if not opt.polys:
        return [ q.as_basic() for q in Q ], r.as_basic()
    else:
        return Q, r

def groebner(F, *gens, **args):
    """Computes reduced Groebner basis for a set of polynomials. """
    args = _update_args(args, 'field', True)

    polys, opt = parallel_poly_from_expr(F, *gens, **args)

    for i, poly in enumerate(polys):
        polys[i] = sdp_from_dict(poly.rep.to_dict(), opt.order)

    level = len(opt.gens)-1

    G = sdp_groebner(polys, level, opt.order, opt.domain, monic=opt.monic)
    G = [ Poly(DMP(dict(g), opt.domain, level), *opt.gens) for g in G ]

    if not opt.polys:
        return [ g.as_basic() for g in G ]
    else:
        return G

def symmetrize(f, *gens, **args):
    """Rewrite a polynomial in terms of elementary symmetric polynomials. """
    try:
        f = Poly(f, *_analyze_gens(gens), **args)
    except GeneratorsNeeded:
        if args.get('formal', False):
            return (f, S.Zero, {})
        else:
            return (f, S.Zero)

    from sympy.polys.specialpolys import symmetric_poly

    polys, symbols = [], numbered_symbols('s', start=1)

    gens, dom = f.gens, f.get_domain()

    for i in range(0, len(f.gens)):
        poly = symmetric_poly(i+1, gens, polys=True)
        polys.append((symbols.next(), poly.set_domain(dom)))

    indices = range(0, len(gens) - 1)
    weights = range(len(gens), 0, -1)

    symmetric = []

    if not f.is_homogeneous:
        symmetric.append(f.TC())
        f -= f.TC()

    while f:
        _height, _monom, _coeff = -1, None, None

        for i, (monom, coeff) in enumerate(f.terms()):
            if all(monom[i] >= monom[i+1] for i in indices):
                height = max([ n*m for n, m in zip(weights, monom) ])

                if height > _height:
                    _height, _monom, _coeff = height, monom, coeff

        if _height != -1:
            monom, coeff = _monom, _coeff
        else:
            break

        exponents = []

        for m1, m2 in zip(monom, monom[1:] + (0,)):
            exponents.append(m1 - m2)

        term = [ s**n for (s, _), n in zip(polys, exponents) ]
        poly = [ p**n for (_, p), n in zip(polys, exponents) ]

        symmetric.append(Mul(coeff, *term))

        product = poly[0].mul(coeff)

        for p in poly[1:]:
            product = product.mul(p)

        f -= product

    polys = [ (s, p.as_basic()) for s, p in polys ]

    if args.get('formal', False):
        return (Add(*symmetric), f.as_basic(), dict(polys))
    else:
        return (Add(*symmetric).subs(polys), f.as_basic())

def horner(f, *gens, **args):
    """Apply Horner's rule to put a polynomial in Horner form. """
    F = NonStrictPoly(f, *_analyze_gens(gens), **args)

    if not F.is_Poly:
        return F

    form, gen = S.Zero, F.gen

    if F.is_univariate:
        for coeff in F.all_coeffs():
            form = form*gen + coeff
    else:
        F, gens = Poly(F, gen), gens[1:]

        for coeff in F.all_coeffs():
            form = form*gen + horner(coeff, *gens, **args)

    return form

def poly(expr, **args):
    """Efficiently transform an expression into a polynomial. """
    expr = sympify(expr)

    if expr.is_Poly:
        return expr.reorder(**args)

    terms, poly_terms = [], []

    for term in Add.make_args(expr):
        factors, poly_factors = [], []

        for factor in Mul.make_args(term):
            if factor.is_Add:
                poly_factors.append(poly(factor))
            elif factor.is_Pow and factor.base.is_Add and factor.exp.is_Integer:
                poly_factors.append(poly(factor.base).pow(factor.exp))
            else:
                factors.append(factor)

        if not poly_factors:
            terms.append(term)
        else:
            product = poly_factors[0]

            for factor in poly_factors[1:]:
                product = product.mul(factor)

            if factors:
                factor = Mul(*factors)

                if factor.is_Number:
                    product = product.mul(factor)
                else:
                    product = product.mul(Poly(factor, expand=False))

            poly_terms.append(product)

    if not poly_terms:
        result = Poly(expr, expand=False)
    else:
        result = poly_terms[0]

        for term in poly_terms[1:]:
            result = result.add(term)

        if terms:
            term = Add(*terms)

            if term.is_Number:
                result = result.add(term)
            else:
                result = result.add(Poly(term, expand=False))

    return result.reorder(**args)

