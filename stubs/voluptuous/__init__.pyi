from typing import Any, Callable, Collection, Dict, Optional as Opt, Type, Union

ALLOW_EXTRA: int

class Schema:
    def __init__(
        self,
        schema: Dict[Union[str, Marker], Any],
        required: bool = False,
        extra: int = 0,
    ): ...
    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    def extend(
        self,
        schema: Dict[Union[str, Marker], Any],
        required: Opt[Collection[str]] = None,
        extra: Opt[int] = None,
    ) -> Schema: ...

class Marker(object):
    def __init__(
        self, schema_: str, msg: Opt[str] = None, description: Opt[str] = None,
    ): ...

class Optional(Marker):
    def __init__(
        self,
        schema: str,
        msg: Opt[str] = None,
        default: Opt[Any] = None,
        description: Opt[str] = None,
    ): ...

class Required(Marker): ...

class In(object):
    def __init__(self, container: Collection[Any], msg: Opt[str] = None): ...

class Coerce(object):
    def __init__(self, type: Type[Any], msg: Opt[str] = None): ...
