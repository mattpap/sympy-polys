"""Unevaluated versions of core classes and helper functions. """

from basic import S
from expr import Expr
from add import Add
from mul import Mul
from power import Pow
from sympify import sympify

class HoldExpr(Expr):
    """Overrides functionality of expression class. """

    def __neg__(self):
        return HoldMul(S.NegativeOne, self)

class HoldAdd(HoldExpr, Add):
    """Class for representing unevaluated sum of terms. """
    __slots__ = ['is_commutative']

    _unhold_cls = Add
    is_Hold = True

    def __new__(cls, *args):
        args = map(sympify, args)

        if len(args) <= 1:
            if not args:
                return S.Zero
            else:
                return args[0]

        terms = []

        for arg in args:
            if arg.is_Add:
                terms.extend(arg.args)
            else:
                terms.append(arg)

        commutative = True

        for term in terms:
            if not term.is_commutative:
                commutative = False
                break

        obj = Expr.__new__(cls, *terms)
        obj.is_commutative = commutative

        return obj

class HoldMul(HoldExpr, Mul):
    """Class for representing unevaluated product of factors. """
    __slots__ = ['is_commutative']

    _unhold_cls = Mul
    is_Hold = True

    def __new__(cls, *args):
        args = map(sympify, args)

        if len(args) <= 1:
            if not args:
                return S.One
            else:
                return args[0]

        factors = []

        for arg in args:
            if arg.is_Mul and arg.is_commutative:
                factors.extend(arg.args)
            else:
                factors.append(arg)

        commutative = True

        for factor in factors:
            if not factor.is_commutative:
                commutative = False
                break

        obj = Expr.__new__(cls, *factors)
        obj.is_commutative = commutative

        return obj

    def __neg__(self):
        head, tail = self.args[0], self.args[1:]

        if head.is_Number:
            return self._new_rawargs(*((-head,) + tail))
        else:
            return HoldMul(S.NegativeOne, self)

class HoldPow(HoldExpr, Pow):
    """Class for representing unevaluated power operator. """
    __slots__ = ['is_commutative']

    _unhold_cls = Pow
    is_Hold = True

    def __new__(cls, base, exp):
        base, exp = sympify(base), sympify(exp)

        obj = Expr.__new__(cls, base, exp)
        obj.is_commutative = base.is_commutative and exp.is_commutative

        return obj

def hold_sqrt(arg):
    """Unevaluated version of :func:`sqrt` function. """
    return HoldPow(sympify(arg), S.Half)

