""""
The foundational Fact used in Productions.

TODO:: Replace __fact_type__ as an attribute name
    This avoids *potential* conflict with Python internals.
    Use "_fact_type" to provide all the privacy that's needed.
    The built-in __class__.__name__ attribute me be sufficient.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from itertools import chain

from py_rete.conditions import ComposableCond
from py_rete.conditions import Cond
from py_rete.common import gen_variable
from py_rete.common import WME
from py_rete.common import V

if TYPE_CHECKING:  # pragma: no cover
    from typing import Generator
    from typing import Optional


class Fact(ComposableCond, dict):
    """
    A dictionary class that decomposes into individual conditions or wmes
    depending on the context.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.id: Optional[str] = None
        self.gen_var = gen_variable()
        self.bound = False
        self.update(dict(chain(enumerate(args), kwargs.items())))

        if '__fact_type__' in self:
            raise ValueError("`__fact_type__` cannot be used, it is a reserved"
                             " keyword for matching type internally.")

    def __rlshift__(self, other: V):
        if not isinstance(other, V):
            raise ValueError("Can only assign facts to variables")
        self.gen_var = other
        self.bound = True
        return self

    def duplicate(self) -> Fact:
        """
        Returns a copy of the fact without the ID set. This is basically a
        shallow copy, if the fact contains other facts, they are not copied,
        references to those facts are used.
        """
        new = Fact()
        new.update(self)
        return new

    @property
    def conds(self) -> Generator[Cond, None, None]:
        if self.id is None:
            fact_id = self.gen_var
        else:
            fact_id = self.id

        for k in self:
            yield Cond(fact_id, k, self[k])

        # This cuts off dict, ComposableCond, and object types, don't need
        # these to be added to the rete, just Fact and its subclasses.
        for class_name in self.__class__.mro()[:-3]:
            yield Cond(fact_id, '__fact_type__', class_name)

    @property
    def wmes(self) -> Generator[WME, None, None]:
        if self.id is None:
            raise ValueError("No id assigned to fact, add to network first.")

        for k in self:
            if isinstance(k, V) or isinstance(self[k], V):
                raise ValueError("Facts converted into wmes cannot have"
                                 " variables.")

        yield WME(self.id, '__fact_type__', self.__class__)

        for k in self:
            yield WME(self.id, k, self[k])

    def __repr__(self):
        kvs = []
        for k in self:
            kvs.append("{}={}".format(k, self[k]))

        if self.bound:
            return "{} << {}({})".format(self.gen_var, self.__class__.__name__,
                                         ", ".join(kvs))

        return "{}({})".format(self.__class__.__name__, ", ".join(kvs))

    def __hash__(self):
        return hash("{}-{}".format(self.__class__.__name__, self.id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Fact) or self.id != other.id:
            return NotImplemented

        keys = set()
        keys.update(self)
        keys.update(other)

        for k in keys:
            if k not in self:
                return False
            if k not in other:
                return False
            if self[k] != other[k]:
                return False

        return True
