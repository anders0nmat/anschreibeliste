"""
A bare-bones toolset to handle and send Server-sent-events.

Capable of multiple channels.

Use send_event() to send a event and data to all listeners on a specified channel
Use EventstreamResponse() to allow for clients to listen on specified channels

See https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events


Q: Why not django-eventstream package?
A: It is quite bloated for this simple use-case, providing more features regarding
   syncing events across multiple server instances (e.g. with redis).
   It also has a lot of dependencies which seems unnecessary.
"""

from dataclasses import dataclass
from django.http import StreamingHttpResponse
from asyncio import Queue, QueueFull, CancelledError
from json import dumps
from typing import Any, Iterable, Callable
from collections import defaultdict

@dataclass
class StreamEvent:
    event: str | None = None
    # eventstream specifies than an event must at least contain a data field
    data: str = ""
    id: str | None = None

    def __str__(self) -> str:
        result = ''
        if self.event is not None:
            result += f'event: {self.event}\n'
        if self.id is not None:
            result += f'id: {self.id}\n'
        result += f'data: {self.data}\n'
        result += '\n'
        return result

class StreamListener:
    events: Queue[StreamEvent]
    def __init__(self) -> None:
        self.events = Queue()

    async def get_event(self) -> StreamEvent:
        return await self.events.get()

class EventstreamChannel:
    listeners: list[StreamListener]
    
    def __init__(self) -> None:
        self.listeners = []

    def add_listener(self, listener: StreamListener):
        self.listeners.append(listener)
    
    def remove_listener(self, listener: StreamListener):
        self.listeners.remove(listener)

    def post_event(self, event: StreamEvent):
        for listener in self.listeners:
            try:
                listener.events.put_nowait(event)
            except QueueFull:
                pass

eventstream_channels: defaultdict[str, EventstreamChannel] = defaultdict(EventstreamChannel)

def get_eventstream_channel(channel: str) -> EventstreamChannel:
    return eventstream_channels[channel]

def send_event(channel: str, event: str | None, data: Any | None, id: str | None = None):
    """
    Send an event to all listeners of specified channel.
    
    data is json-encoded before sending
    """
    eventstream_channels[channel].post_event(
       StreamEvent(
            event=event,
            data=dumps(data) if data is not None else None,
            id=id
        ) 
    )

async def listen(channel: str | Iterable[str], initial_event: Callable[[], StreamEvent] | StreamEvent = None):
    if isinstance(initial_event, StreamEvent):
        _initial_event = initial_event
        initial_event = lambda: _initial_event
    if isinstance(channel, str):
        channel = [channel]

    ev_channels = [get_eventstream_channel(ch) for ch in channel]
    try:
        listener = StreamListener()
        if initial_event:
            await listener.events.put(initial_event())
        for ch in ev_channels:
            ch.add_listener(listener)

        while True:
            event = await listener.get_event()
            yield str(event)
    except CancelledError:
        for ch in ev_channels:
            ch.remove_listener(listener)
    
class EventstreamResponse(StreamingHttpResponse):
    """
    Http response for connecting client to channels of a eventstream
    """
    def __init__(self, channel: str | Iterable[str], *args, initial_event: Callable[[], StreamEvent] | StreamEvent = None, **kwargs) -> None:
        """
        Requires a list of channels the client will receive events from
        """
        super().__init__(listen(channel, initial_event=initial_event), *args, content_type="text/event-stream", **kwargs)
        self['Cache-Control'] = 'no-cache'
        self['X-Accel-Buffering'] = 'no'

    
