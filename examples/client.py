import asyncio

from tnetstring import Connection, NEED_DATA


async def main():
    reader, writer = await asyncio.open_connection(
        '127.0.0.1', 8888)
    conn = Connection()

    data = {b"message": b"The quick brown fox jumps over the lazy dog."}
    conn.send_data(data)
    writer.write(conn.data_to_send())

    reply = NEED_DATA
    while reply is NEED_DATA:
        conn.receive_data(await reader.read(1024))
        reply = conn.next_event()
    print(f'Received: {reply}')
    assert reply == data
    writer.close()

asyncio.run(main())
