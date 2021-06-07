# -*- coding: utf-8 -*-
#
# This file is part of the pytnetstring project
#
# Copyright (c) 2021 Tiago Coutinho
# Distributed under the GPLv3 license. See LICENSE for more info.


import pytest
from hypothesis import given, example, assume
from hypothesis.strategies import none, binary, integers, booleans, floats, dictionaries, lists, text

from tnetstring import Connection, NEED_DATA


def BasicTypes():
    return none() | integers() | floats(allow_nan=False) | booleans() | binary() | text()


def Dicts(values):
    return dictionaries(keys=binary(), values=values)


def Types():
    return BasicTypes() | \
      Dicts(BasicTypes() | Dicts(BasicTypes() | lists(BasicTypes())) | lists(BasicTypes())) | \
      lists(BasicTypes() | lists(BasicTypes() | Dicts(BasicTypes())) | Dicts(BasicTypes()))


def cmp(result, expected):
    if isinstance(expected, str):
        assert isinstance(result, bytes)
        assert result == expected.encode()
    elif isinstance(expected, (list, tuple)):
        assert len(result) == len(expected)
        [cmp(ri, ei) for ri, ei in zip(result, expected)]
    elif isinstance(expected, dict):
        assert len(result) == len(expected)
        for k, v in expected.items():
            if isinstance(k, str):
                k = k.encode()
            cmp(result[k], v)
    else:
        assert result == expected


@given(Types())
def test_tnetstring(payload):
#    assume(not isinstance(payload, float) or not math.isnan(payload))
    conn = Connection()

    assert conn.trailing_data == (b"", False)
    assert conn.next_event() is NEED_DATA
    assert conn.trailing_data == (b"", False)
    conn.send_data(payload)
    data = conn.data_to_send()
    assert conn.trailing_data == (b"", False)
    conn.receive_data(data)
    assert conn.trailing_data == (data, False)
    cmp(conn.next_event(), payload)
    assert conn.trailing_data == (b"", False)
    assert conn.next_event() is NEED_DATA
    assert conn.trailing_data == (b"", False)

    conn.send_data(payload)
    data = conn.data_to_send()
    assert conn.trailing_data == (b"", False)
    conn.receive_data(data)
    assert conn.trailing_data == (data, False)
    cmp(conn.next_event(), payload)
    assert conn.trailing_data == (b"", False)

    conn.receive_data(b"")
    assert conn.trailing_data == (b"", True)
    with pytest.raises(RuntimeError):
        conn.receive_data(b"Hello, world!")


@given(BasicTypes())
@example(b"Hello, world!")
def test_incomplete(payload):
    conn = Connection()

    assert conn.trailing_data == (b"", False)
    assert conn.next_event() is NEED_DATA
    conn.send_data(payload)
    data = conn.data_to_send()
    assert conn.trailing_data == (b"", False)

    conn.receive_data(data[0:1])
    assert conn.trailing_data == (data[0:1], False)
    assert conn.next_event() is NEED_DATA
    assert conn.trailing_data == (data[0:1], False)

    assume(len(data) > 4)
    conn.receive_data(data[1:3])
    assert conn.trailing_data == (data[0:3], False)
    assert conn.next_event() is NEED_DATA
    assert conn.trailing_data == (data[0:3], False)
    conn.receive_data(data[3:-1])
    assert conn.trailing_data == (data[0:-1], False)
    assert conn.next_event() is NEED_DATA
    assert conn.trailing_data == (data[0:-1], False)
    conn.receive_data(data[-1:])
    assert conn.trailing_data == (data, False)
    cmp(conn.next_event(), payload)
    assert conn.trailing_data == (b"", False)
    assert conn.next_event() is NEED_DATA
    assert conn.trailing_data == (b"", False)


def test_close():
    conn = Connection()

    assert conn.next_event() is NEED_DATA
    conn.receive_data(b"")
    with pytest.raises(RuntimeError):
        conn.receive_data(b"Hello, world!")


@pytest.mark.parametrize(
    "data, error",
    [(b"1:a@", TypeError), (b"4:data#", ValueError), (b"4:data^", ValueError), (b"4:data!", ValueError),
     (b"8:5:abcde,}", ValueError)],
    ids=["dtype", "int","float", "bool", "dict"])
def test_receive_bad_data(data, error):
    conn = Connection()
    conn.receive_data(data)

    with pytest.raises(error):
        conn.next_event()


@pytest.mark.parametrize(
    "data, encoding, error",
    [("hello", None, TypeError), (object(), "utf-8", TypeError)],
    ids=["str-noenc", "object"])
def test_send_bad_data(data, encoding, error):
    conn = Connection(encoding=encoding)
    with pytest.raises(error):
        conn.send_data(data)
