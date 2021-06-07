# -*- coding: utf-8 -*-
#
# This file is part of the pytnetstring project
#
# Copyright (c) 2021 Tiago Coutinho
# Distributed under the GPLv3 license. See LICENSE for more info.

__version__ = "0.3.0"

NEED_DATA = object()
CONNECTION_CLOSED = object()

NULL = b"0:~"
TRUE = b"4:true!"
FALSE = b"5:false!"


def encode(data, encoding="utf-8", errors="strict"):
    """encode python data into a tnetstring bytes"""
    if data is None:
        return NULL
    elif data is True:
        return TRUE
    elif data is False:
        return FALSE
    elif isinstance(data, int):
        data = str(data).encode()
        tail = b"#"
    elif isinstance(data, float):
        data = str(data).encode()
        tail = b"^"
    elif isinstance(data, bytes):
        tail = b","
    elif isinstance(data, dict):
        result = []
        for k, v in data.items():
            result.append(encode(k, encoding, errors))
            result.append(encode(v, encoding, errors))
        data = b"".join(result)
        tail = b"}"
    elif isinstance(data, (tuple, list)):
        data = b"".join(encode(i, encoding, errors) for i in data)
        tail = b"]"
    elif isinstance(data, str):
        if not encoding:
            raise TypeError(f"Cannot encode value of type {type(data)}")
        return encode(data.encode(encoding, errors), encoding, errors)
    else:
        raise TypeError(f"Cannot encode value of type {type(data)}")
    return f"{len(data)}:".encode() + data + tail


def decode_pair(data):
    key, extra = decode(data)
    if not extra:
        raise ValueError("Unbalanced dictionary")
    value, extra = decode(extra)
    return key, value, extra


def decode(data):
    """Decode tnetstring encoded binary data"""
    if not data:
        return NEED_DATA, data
    try:
        idx = data.index(b":")
    except ValueError:
        return NEED_DATA, data
    n = int(data[0:idx])
    ndig = len(str(n))
    start = ndig + 1
    end = start + n + 1
    if len(data) < end:
        return NEED_DATA, data
    payload, dtype = data[start:end - 1], data[end - 1:end]
    if dtype == b"~":
        result = None
    elif dtype == b"#":
        result = int(payload)
    elif dtype == b"^":
        result = float(payload)
    elif dtype == b"!":
        if payload == b"true":
            result = True
        elif payload == b"false":
            result = False
        else:
            raise ValueError(f"Invalid boolean value {payload!r}")
    elif dtype == b",":
        result = payload
    elif dtype == b"}":
        if  payload:
            key, value, extra = decode_pair(payload)
            result = {key: value}
            while extra:
                key, value, extra = decode_pair(extra)
                result[key] = value
        else:
            result = {}
    elif dtype == b"]":
        if payload:
            value, extra = decode(payload)
            result = [value]
            while extra:
                value, extra = decode(extra)
                result.append(value)
        else:
            result = []
    else:
        raise TypeError(f"Unknown data type code {dtype!r}")
    return result, data[end:]


class Connection:

    def __init__(self, encoding="utf-8", encoding_errors="strict"):
        self._encoding = encoding
        self._encoding_errors = encoding_errors
        self._receive_buffer = b""
        self._receive_buffer_closed = False
        self._send_buffer = []

    @property
    def trailing_data(self):
        """Data that has been received, but not yet processed, represented as
        a tuple with two elements, where the first is a byte-string containing
        the unprocessed data itself, and the second is a bool that is True if
        the receive connection was closed.
        """
        return self._receive_buffer, self._receive_buffer_closed

    def send_data(self, event):
        """Convert a high-level event into bytes that can be sent to the peer
        and stores it for future consumption by `data_to_send()`
        """
        data = encode(event, encoding=self._encoding, errors=self._encoding_errors)
        self._send_buffer.append(data)

    def data_to_send(self):
        """Consumes data previously feed by `send_data()` as `bytes`"""
        data = b"".join(self._send_buffer)
        self._send_buffer = []
        return data

    def receive_data(self, data):
        """Feed network data into the connection instance.

        This does not actually do any processing on the data, just stores
        it. To trigger processing, you have to call `event()`/`next_event()`
        """
        if data:
            if self._receive_buffer_closed:
                raise RuntimeError("received close, then received more data?")
            self._receive_buffer += data
        else:
            self._receive_buffer_closed = True

    def next_event(self):
        """Parse the next event out of our receive buffer, update our internal
        state, and return it.

        This is a mutating operation -- think of it like calling :func:`next`
        on an iterator.

        Returns one of two things:
            1) An event object.
            2) The special constant `NEED_DATA`, which indicates that
               you need to read more data from your stream and pass it to
               `receive_data` before this method will be able to return
               any more events.

        Raises ValueError or TypeError if the data feed is malformed
        """
        result, self._receive_buffer = decode(self._receive_buffer)
        if result is NEED_DATA and self._receive_buffer_closed:
            result = CONNECTION_CLOSED
        return result

    def events(self):
        """A generator that yields pending events."""
        while True:
            event = self.next_event()
            if event is NEED_DATA or event is CONNECTION_CLOSED:
                break
            yield event
