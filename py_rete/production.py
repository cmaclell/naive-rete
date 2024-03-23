from __future__ import annotations
from typing import TYPE_CHECKING
from itertools import product
from functools import update_wrapper
import inspect

from py_rete.conditions import ConditionalList
from py_rete.conditions import ConditionalElement
from py_rete.conditions import Cond
from py_rete.conditions import Ncc
from py_rete.conditions import Neg
from py_rete.conditions import NOT
from py_rete.conditions import Filter
from py_rete.conditions import Bind
from py_rete.conditions import AND
from py_rete.conditions import OR
from py_rete.fact import Fact
from py_rete.common import V
from py_rete.common import Token

if TYPE_CHECKING:  # pragma: no cover
    from typing import Optional
    from typing import Callable
    from typing import List
    from typing import Union
    from py_rete.pnode import PNode


def compile_disjuncts(it, nest: bool = True):
    if isinstance(it, OR):
        return tuple(compile_disjuncts(ele, nest=False) for ele in it)
    elif isinstance(it, (Production, AND)):
        inner = []
        for ele in it:
            if isinstance(ele, NOT):
                inner += compile_disjuncts(ele)
            else:
                inner.append(compile_disjuncts(ele))
        return tuple(product(*inner))
    elif isinstance(it, NOT):
        if len(it) > 1:
            inner = compile_disjuncts(AND(*[ele for ele in it]))
        else:
            inner = compile_disjuncts(it[0])
        return (tuple(NOT(*branch) if isinstance(branch, tuple) else
                      NOT(branch) for branch in inner),)
    elif nest:
        return (it,)
    else:
        return it


def get_rete_conds(it):
    for ele in it:
        if isinstance(ele, (Cond, Bind, Filter)):
            yield ele
        elif isinstance(ele, NOT):
            subcond = list(get_rete_conds(ele))
            if len(subcond) == 1 and isinstance(subcond[0], Cond):
                yield Neg(subcond[0].identifier,
                          subcond[0].attribute,
                          subcond[0].value)
            elif len(subcond) == 1 and isinstance(subcond[0], AND):
                yield Ncc(**subcond[0])
            else:
                # print(subcond)
                yield Ncc(*subcond)

        elif isinstance(ele, Fact):
            copy = ele.duplicate()
            copy.id = ele.id
            copy.gen_var = ele.gen_var

            for k in copy:
                if isinstance(copy[k], Fact):
                    for cond in get_rete_conds([copy[k]]):
                        yield cond

                    if copy[k].id is None:
                        copy[k] = copy[k].gen_var
                    else:
                        copy[k] = copy[k].id

            for cond in copy.conds:
                yield cond

        elif isinstance(ele, AND):
            for cond in get_rete_conds(ele):
                yield cond


class Production():
    """
    A production rule in py_rete. It is comprised of conditions and a function
    to execute once all conditions are bound.
    """
    conditions: Union[ConditionalElement, ConditionalList]

    def __init__(self, pattern: Optional[Union[ConditionalElement,
                                               ConditionalList]] = None):
        self.__wrapped__: Optional[Callable] = None
        self._wrapped_args: List[str] = []
        self._rete_net = None
        self.pattern: Optional[Union[ConditionalElement,
                                     ConditionalList]] = pattern

        self.id: Optional[str] = None
        self.p_nodes: List[PNode] = []

    @property
    def activations(self):
        for node in self.p_nodes:
            for token in node.activations:
                yield token

    @staticmethod
    def _get_rete_conds(pattern):
        if pattern is None:
            return ([],)
        disjuncts = compile_disjuncts(pattern)
        conds = []
        for disjunct in disjuncts:
            if isinstance(disjunct, tuple):
                conds.append(list(get_rete_conds(AND(*disjunct))))
            else:
                conds.append(list(get_rete_conds(AND(disjunct))))
        return conds

    def get_rete_conds(self):
        return self._get_rete_conds(self.pattern)

    def fire(self, token: Token):
        kwargs = {arg: self._rete_net if arg == 'net' else
                  self._rete_net.facts[token.binding[V(arg)]] if
                  token.binding[V(arg)] in self._rete_net.facts else
                  token.binding[V(arg)] for arg in self._wrapped_args}
        return self(**kwargs)

    def __call__(self, *args, **kwargs):
        if self.__wrapped__ is None:
            if not args:
                raise AttributeError("Apply Production as a decorator around a"
                                     " function to create a production.")
            else:
                func = args[0]
                signature = inspect.signature(func)
                if not any(p.kind == inspect.Parameter.VAR_KEYWORD
                           for p in signature.parameters.values()):
                    self._wrapped_args = set(signature.parameters.keys())
                return update_wrapper(self, func)

        else:
            if self._wrapped_args:
                kwargs = {k: v for k, v in kwargs.items()
                          if k in self._wrapped_args}
            return self.__wrapped__(*args, **kwargs)

    def __repr__(self) -> str:
        if self.__wrapped__ is None:
            raise ValueError("Not instantiated as a decorator.")

        signature = inspect.signature(self.__wrapped__)
        return "IF {} THEN {}{}".format(self.pattern.__repr__(),
                                        self.__wrapped__.__name__,
                                        signature)

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Production) and self.id == other.id)

    def __hash__(self):
        return hash("{}-{}".format(self.__class__.__name__, self.id))
