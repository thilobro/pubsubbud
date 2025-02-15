from typing import Any, Callable, Coroutine

IFPublishCallback = Callable[
    [str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]
]
CBHandlerCallback = Callable[[dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]]
