from typing import Callable, Any, Coroutine


IFPublishCallback = Callable[[str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]]
CBHandlerCallback = Callable[[dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]]
ProcessMessageCallback = Callable[[str, dict[str, Any], bool], Coroutine[Any, Any, Any]]
