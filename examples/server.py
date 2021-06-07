import asyncio

async def handle(reader, writer):
    while True:
        data = await reader.read(5)
        if not data:
            break
        print(f"Sending chunk {data!r}...")
        writer.write(data)
        await writer.drain()
        await asyncio.sleep(0.05)

    print("Close the connection")
    writer.close()

async def main():
    server = await asyncio.start_server(handle, '127.0.0.1', 8888)
    async with server:
        await server.serve_forever()

asyncio.run(main())
