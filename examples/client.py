import asyncio

from tnetstring import Connection, NEED_DATA


async def main():
    reader, writer = await asyncio.open_connection(
        '127.0.0.1', 8888)
    conn = Connection()

    data = conn.send({
        "jsonrpc": "2.0",
        "method": "reverse",
        "params": ["hello"],
        "id": 1
    })
    writer.write(data)

    reply = NEED_DATA
    while reply is NEED_DATA:
        conn.receive(await reader.read(1024))
        reply = conn.next_event()
    print(f'Received: {reply}')

    print('Close the connection')
    writer.close()

asyncio.run(main())
