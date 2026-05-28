import asyncio
import noble_tls
from noble_tls import Client


async def main():
    await noble_tls.update_if_necessary()

    # IPv4-only with local address binding (host:port, use port 0 for auto)
    session = noble_tls.Session(
        client=Client.CHROME_133_PSK,
        disable_ipv6=True,
        local_address="0.0.0.0:0",
    )

    res = await session.get(
        "https://tls.peet.ws/api/all",
        insecure_skip_verify=True,
    )
    print(f"Status: {res.status_code}")
    print(f"Protocol: {res.used_protocol}")
    await session.close()

    # Certificate pinning — rejects unless the SHA256 pin matches
    pinned = noble_tls.Session(
        client=Client.CHROME_133,
        certificate_pinning={
            "tls.peet.ws": [
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            ],
        },
    )
    try:
        await pinned.get("https://tls.peet.ws/api/all")
    except Exception as e:
        print(f"Pinning rejected (expected with fake pin): {e}")
    await pinned.close()

    # Rotating proxy — forces a new connection per request
    proxy_session = noble_tls.Session(
        client=Client.FIREFOX_135,
        is_rotating_proxy=True,
    )
    proxy_session.proxies = {"http": "http://user:pass@proxy.example.com:8080"}
    try:
        await proxy_session.get("https://tls.peet.ws/api/all", timeout_milliseconds=5000)
    except Exception as e:
        print(f"Proxy request failed (expected without real proxy): {e}")
    await proxy_session.close()

    # Host header override + SNI override
    direct = noble_tls.Session(
        client=Client.CHROME_131,
        server_name_overwrite="tls.peet.ws",
    )
    res = await direct.get(
        "https://tls.peet.ws/api/all",
        request_host_override="custom.host.example.com",
    )
    print(f"Status: {res.status_code}")
    print(f"Protocol: {res.used_protocol}")
    await direct.close()


asyncio.run(main())
