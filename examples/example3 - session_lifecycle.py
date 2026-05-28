import asyncio
import noble_tls
from noble_tls import Client, Protocol


async def main():
    await noble_tls.update_if_necessary()

    session = noble_tls.Session(
        client=Client.CHROME_133,
        random_tls_extension_order=True,
    )

    res = await session.get("https://tls.peet.ws/api/all")
    print(f"Protocol used: {res.used_protocol}")
    print(f"Status: {res.status_code}")

    if res.used_protocol == Protocol.HTTP_2:
        print("Negotiated HTTP/2")

    tls_info = res.json()
    print(f"JA3: {tls_info.get('tls', {}).get('ja3')}")
    print(f"H2 fingerprint: {tls_info.get('http2', {}).get('akamai_fingerprint')}")

    cookies = await session.get_cookies("https://tls.peet.ws")
    print(f"Session cookies: {cookies}")

    await session.add_cookies("https://tls.peet.ws", [
        {"name": "test", "value": "123", "domain": "tls.peet.ws", "path": "/"},
    ])
    updated = await session.get_cookies("https://tls.peet.ws")
    print(f"After adding: {updated}")

    await session.close()
    print("Session closed")

    # Or destroy all sessions at once
    # await noble_tls.Session.close_all()


asyncio.run(main())
