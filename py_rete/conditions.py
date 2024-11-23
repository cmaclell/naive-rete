from __future__ import annotations
from typing import TYPE_CHECKING
from itertools import chain
from dataclasses import dataclass

from py_rete.common import V

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Union
    from typing import Tuple
    from typing import Callable
    from typing import Hashable
    from py_rete.common import WME


class ConditionalElement():
    """
    A single conditional element (e.g., Test, Condition, Neg, Bind). Does not
    include list conditionals. Used for type checking primarily.
    """
    pass


class ConditionalList(tuple):
    """
    A conditional that consists of a list of other conditionals.
    """
    def __new__(cls, *args: List[Union[ConditionalList, ConditionalElement]]):
        return super().__new__(cls, args)

    def __repr__(self):
        return "{}{}".format(self.__class__.__name__, super().__repr__())

    def __hash__(self):
        return hash((self.__class__.__name__, tuple(self)))


class ComposableCond:
    """
    A Mixin for making a conditional compositional using bitwise operators.
    """

    def __and__(self, other: ComposableCond):
        if isinstance(self, AND) and isinstance(other, AND):
            return AND(*[x for x in chain(self, other)])
        elif isinstance(self, AND):
            return AND(*[x for x in self]+[other])
        elif isinstance(other, AND):
            return AND(*[self]+[x for x in other])
        else:
            return AND(self, other)

    def __or__(self, other: ComposableCond):
        if isinstance(self, OR) and isinstance(other, OR):
            return OR(*[x for x in chain(self, other)])
        elif isinstance(self, OR):
            return OR(*[x for x in self]+[other])
        elif isinstance(other, OR):
            return OR(*[self]+[x for x in other])
        else:
            return OR(self, other)

    def __invert__(self):
        return NOT(self)


class AND(ConditionalList, ComposableCond):
    pass


class OR(ConditionalList, ComposableCond):
    pass


class NOT(ConditionalList, ComposableCond):
    pass


@dataclass(eq=True, frozen=True)
class Cond(ConditionalElement, ComposableCond):
    """
    Essentially a pattern/condition to match, can have variables.
    """
    __slots__ = ['identifier', 'attribute', 'value']
    identifier: Hashable
    attribute: Hashable
    value: Hashable

    def __repr__(self):
        return "(%s ^%s %s)" % (self.identifier, self.attribute, self.value)

    @property
    def vars(self) -> List[Tuple[str, V]]:
        """
        Returns a list of tuples (field, var) that contains the slot names as a
        string and the variable object it maps to.
        """
        return [(field, getattr(self, field))
                for field in ('identifier', 'attribute', 'value')
                if isinstance(getattr(self, field), V)]

    def contain(self, v: V) -> str:
        """
        Checks if a variable is in the condition. Returns as string with the
        name of the field if it is, otherwise an empty string.
        """
        assert isinstance(v, V)

        for f in ['identifier', 'attribute', 'value']:
            _v = getattr(self, f)
            if _v == v:
                return f
        return ""

    def test(self, w: WME) -> bool:
        """
        Checks if a pattern matches a working memory element.
        """
        for f in ['identifier', 'attribute', 'value']:
            v = getattr(self, f)
            if isinstance(v, V):
                continue
            if v != getattr(w, f):
                return False
        return True

    def __hash__(self):
        # TODO: If self.__class__.__name__ used instead of a literal,
        # this may be properly inheritable.
        return hash(('cond', self.identifier, self.attribute, self.value))


class Neg(Cond):
    """
    A negated pattern.
    """
    def __repr__(self):
        return "-(%s ^%s %s)" % (self.identifier, self.attribute, self.value)

    def __hash__(self):
        return hash(('neg', self.identifier, self.attribute, self.value))


class Ncc(ConditionalList, ComposableCond):
    """
    A negated conjunction of conditions.
    """
    def __repr__(self):
        return "-{}".format(super(Ncc, self).__repr__())

    @property
    def number_of_conditions(self) -> int:
        return len(self)

    def __hash__(self):
        return hash(('ncc', tuple(self)))


@dataclass(eq=True, frozen=True)
class Filter(ConditionalElement, ComposableCond):
    """
    This is a test, it includes a function that might include variables.
    When employed in rete, the variable bindings are passed in as keyword args
    and the function is exectued. The function must return a boolean and if it
    evaluates to true, then the condition matches otherwise it does not.
    """
    __slots__ = ['func']
    func: Callable

    def __repr__(self):
        return "Filter({})".format(repr(self.func))

    def __hash__(self):
        return hash(('filter', self.func))


@dataclass(eq=True, frozen=True)
class Bind(ConditionalElement, ComposableCond):
    """
    Similar to Filter, but binds the result of a function execution to a new
    variable.
    """
    __slots__ = ['func', 'to']
    func: Callable
    to: V

    def __repr__(self):
        return "Bind({}, {})".format(repr(self.func), repr(self.to))

    def __hash__(self):
        return hash(('bind', self.func, self.to))
