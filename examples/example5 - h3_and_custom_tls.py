import asyncio
import noble_tls


async def main():
    await noble_tls.update_if_necessary()

    # Custom TLS with HTTP/3 settings and protocol racing
    # Go binary races H2 vs H3 with a 300ms Chrome-like delay, picks the winner
    session = noble_tls.Session(
        ja3_string="771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
        h2_settings={
            "HEADER_TABLE_SIZE": 65536,
            "MAX_CONCURRENT_STREAMS": 1000,
            "INITIAL_WINDOW_SIZE": 6291456,
            "MAX_HEADER_LIST_SIZE": 262144,
        },
        h2_settings_order=[
            "HEADER_TABLE_SIZE",
            "MAX_CONCURRENT_STREAMS",
            "INITIAL_WINDOW_SIZE",
            "MAX_HEADER_LIST_SIZE",
        ],
        h3_settings={
            "QPACK_MAX_TABLE_CAPACITY": 4096,
            "MAX_FIELD_SECTION_SIZE": 8192,
        },
        h3_settings_order=[
            "QPACK_MAX_TABLE_CAPACITY",
            "MAX_FIELD_SECTION_SIZE",
        ],
        h3_pseudo_header_order=[":method", ":authority", ":scheme", ":path"],
        h3_send_grease_frames=True,
        protocol_racing=True,
        supported_signature_algorithms=[
            "ECDSAWithP256AndSHA256",
            "PSSWithSHA256",
            "PKCS1WithSHA256",
            "ECDSAWithP384AndSHA384",
            "PSSWithSHA384",
            "PKCS1WithSHA384",
            "PSSWithSHA512",
            "PKCS1WithSHA512",
            "Ed25519",
        ],
        supported_versions=["GREASE", "1.3", "1.2"],
        key_share_curves=["GREASE", "X25519MLKEM768", "X25519"],
        cert_compression_algo="brotli",
        alps_protocols=["h2"],
        pseudo_header_order=[":method", ":authority", ":scheme", ":path"],
        connection_flow=15663105,
        header_order=["accept", "user-agent", "accept-encoding", "accept-language"],
    )

    res = await session.get("https://tls.peet.ws/api/all")
    print(f"Protocol: {res.used_protocol}")
    print(f"Status: {res.status_code}")

    tls_info = res.json()
    print(f"JA3: {tls_info.get('tls', {}).get('ja3')}")
    print(f"H2: {tls_info.get('http2', {}).get('akamai_fingerprint')}")
    print(f"IP: {tls_info.get('ip')}")
    await session.close()

    # Stream a response directly to file (useful for large downloads)
    download_session = noble_tls.Session(
        client=noble_tls.Client.CHROME_133,
        without_cookie_jar=True,
    )
    await download_session.get(
        "https://tls.peet.ws/api/all",
        stream_output_path="/tmp/tls_response.json",
        stream_output_block_size=4096,
        stream_output_eof_symbol="<EOF>",
    )
    print("Response streamed to /tmp/tls_response.json")
    await download_session.close()


asyncio.run(main())
