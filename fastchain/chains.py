"""
This module contains the implementation of the chain object (the main object used by fastchain),
together with some useful functions to create and customize those chains.
"""

import itertools
import re
from operator import countOf
from typing import Any, Pattern, Callable, TypeAlias, Union
from .nodes import Node, Chainable
from .factory import parse
from .reporter import Reporter, Report, print_report, failures_logger

ChainRegistry: TypeAlias = dict[str, Union['Chain', dict]]
ReportHandler: TypeAlias = Callable[[Report], None]

_registry_: ChainRegistry = {}
VALID_NAME: Pattern[str] = re.compile(r'^[a-z](?:\w+[_-]?)*?$', re.IGNORECASE)


class Chain:
    __slots__ = ('__name',
                 '__core',
                 '__required_nodes',
                 '__total_nodes',
                 '__nodes',
                 '__report_handlers')

    def __init__(
            self,
            core: Node,
            name: str | None = None,
            nodes: frozenset[Chainable] | None = None,
            required_nodes: int | None = None
    ) -> None:
        """
        Initializes the new chain with a pre parsed core

        :param core: A Node or NodeGroup subclass instance
        :param name: An optional chain name (default 'unregistered')
        """
        self.__name: str = name if name is not None else 'unregistered'
        self.__core: Node = core
        self.__nodes: frozenset = nodes
        self.__total_nodes: int = len(nodes)
        self.__required_nodes: int = required_nodes
        self.__report_handlers: dict[bool, list[ReportHandler]] = {True: [], False: []}

    def add_report_handler(self, handler: ReportHandler, always: bool = False) -> None:
        """Adds a function to capture the execution report.

        :param handler: A callable that only takes the report dict as parameter.
        :param always: If True, the handler will always be called, otherwise,
                       It will only be called in case of failures.
        """
        if always:
            self.__report_handlers[True].append(handler)
        self.__report_handlers[False].append(handler)

    def clear_report_handlers(self) -> None:
        """Removes all the previously registered handlers, including the default ones"""
        self.__report_handlers = {True: [], False: []}

    @property
    def name(self) -> str:
        """Gets the name of the chain (readonly)"""
        return self.__name

    def __repr__(self) -> str:
        """String representation of the chain"""
        return (f'{self.__class__.__name__}(name={self.__name!r}, '
                f'nodes/required={self.__total_nodes}/{self.__required_nodes})')

    def __len__(self) -> int:
        """Chain size in nodes"""
        return self.__total_nodes

    def __call__(self, input: Any) -> Any:
        """Processes the input through the chain's nodes and returns the result."""
        reporter = Reporter()
        success, result = self.__core(input, reporter)
        handlers = self.__report_handlers[success]
        if handlers:
            report = reporter.report(self.__nodes, self.__required_nodes)
            for handler in handlers:
                handler(report)
        return result


def _get_components(source: None | Chain | ChainRegistry) -> list[Chain]:
    """Gets all chains from the given registry"""
    if source is None:
        return []
    if isinstance(source, dict):
        return list(itertools.chain(*map(_get_components, source.values())))
    return [source]


def _register(names: list[str], chain: Chain) -> None:
    """Registers the chain to the main tree under the hierarchical list of names"""
    last = len(names) - 1
    reg = _registry_
    for pos, name_part in enumerate(names):
        if name_part in reg and (pos == last or not isinstance(reg[name_part], dict)):
            raise ValueError(f"The name {'.'.join(names[:pos + 1])!r} is already registered")
        elif pos == last:
            reg[name_part] = chain
            return
        if name_part not in reg:
            reg[name_part] = {}
        reg = reg[name_part]


def get(name: str | None = None) -> list[Chain]:
    """
    Gets all the previously created chain by their dot-separated hierarchical name,
    or gets all the chains registered chains if no name is given
    """
    if name is None:
        names = []
    elif isinstance(name, str):
        names = name.split('.')
    else:
        raise TypeError("The name must be str")
    target = _registry_
    for pos, name_part in enumerate(names):
        target = target.get(name_part)
        if not isinstance(target, dict) and pos < (len(names) - 1):
            return []
    return _get_components(target)


def make(
        *components,
        name: str | None = None,
        log_failures: bool = True,
        logger: str | None = 'fastchain',
        print_stats: bool = False,
        register: bool = True
        ) -> Chain:
    """
    Creates a chain by composing the given components and optionally
    registers it if a name was given.

    :param components: Functions, dict, list or tuple of functions.
    :param name: The chain (unique) name, it can be a hierarchical
                by separating multiple names with dots
                The names (or each name) must start with a letter
                and only contain letters, digits, _ and -
    :param log_failures: whether to log failures or not (default True)
    :param logger: The name of the logger that will be used, (default: fastchain)
    :param print_stats: Whether to print process statistics (default: False)
    :param register: Whether to register the chain globally (default: True)
    """
    if name is None:
        register = False
    else:
        if not isinstance(name, str):
            raise TypeError("The name must be str")
        if not name:
            raise ValueError("The name cannot be empty")
        names = name.split('.')
        for name_part in names:
            if not VALID_NAME.match(name_part):
                raise ValueError(f"{name_part!r} is not a valid name")
    core = parse(components)
    nodes = core.expose
    if not nodes:
        raise ValueError("Cannot create a chain without nodes")
    elif not any(nodes.values()):
        raise ValueError("Cannot create a chain with only optional nodes")
    core.set_title(name)
    chain = Chain(core, name, frozenset(nodes), countOf(nodes.values(), True))
    if log_failures:
        chain.add_report_handler(failures_logger(logger), True)
    if print_stats:
        chain.add_report_handler(print_report, True)
    if register:
        _register(names, chain)  # noqa
    return chain


def add_report_handler(name: str, handler: ReportHandler, always: bool = False) -> None:
    """
    Adds the report handler to every chain under the name tree

    :param name: The name of the chain or group of chains
    :param handler: The function to be called with the report (dict)
    :param always: If True, it will be called even when the execution is successful,
                    otherwise it will be called only when it fails
    """
    for chain in get(name):
        chain.add_report_handler(handler, always)


def clear_report_handlers(name: str) -> None:
    """
    Removes all the previously registered handlers, including the default ones

    :param name: The name of the chain or group of chains
    """
    for chain in get(name):
        chain.clear_report_handlers()
