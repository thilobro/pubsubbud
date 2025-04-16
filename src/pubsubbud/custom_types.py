from typing import Any, Callable, Coroutine

HandlerPublishCallback = Callable[
    [str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]
]
"""Type alias for handler publish callback functions.

This type represents a callback function that handlers use to publish messages.
The function takes:
- A handler ID (str)
- Message content (dict[str, Any])
- Message header (dict[str, Any])

Returns:
    A coroutine that completes when the message is published.
"""

PubsubCallback = Callable[[dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]]
"""Type alias for pubsub callback functions.

This type represents a callback function that is called when messages are received.
The function takes:
- Message content (dict[str, Any])
- Message header (dict[str, Any])

Returns:
    A coroutine that completes when the callback processing is done.
"""
