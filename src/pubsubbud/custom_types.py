from typing import Any, Callable, Coroutine

HandlerPublishCallback = Callable[
    [str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]
]
PubsubCallback = Callable[[dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]]
