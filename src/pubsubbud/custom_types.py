from typing import Any, Callable, Coroutine

IFPublishCallback = Callable[
    [str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]
]
CBHandlerCallback = Callable[[dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]]
ProcessMessageCallback = Callable[[str, dict[str, Any], bool], Coroutine[Any, Any, Any]]
SubscriptionCallback = Callable[[str, str, str], Coroutine[Any, Any, Any]]
UnsubscriptionCallback = Callable[[str, str, str], Coroutine[Any, Any, Any]]
