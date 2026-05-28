import asyncio
import json

import pytest
from unittest.mock import MagicMock, patch
from ..sessions import Session
from ..utils.structures import CaseInsensitiveDict
from ..utils.identifiers import Client


@pytest.mark.asyncio
async def test_session_initialization():
    session = Session()
    assert session.timeout_seconds == 30
    assert isinstance(session.headers, CaseInsensitiveDict)


@pytest.mark.asyncio
async def test_session_new_params_defaults():
    session = Session()
    assert session.disable_http3 is False
    assert session.protocol_racing is False
    assert session.disable_ipv6 is False
    assert session.disable_ipv4 is False
    assert session.is_rotating_proxy is False
    assert session.without_cookie_jar is False
    assert session.local_address is None
    assert session.server_name_overwrite is None
    assert session.certificate_pinning is None
    assert session.default_headers is None
    assert session.h3_settings is None
    assert session.alps_protocols is None
    assert session.ech_candidate_payloads is None
    assert session.allow_http is None
    assert session.record_size_limit is None
    assert session.stream_id is None


@pytest.mark.asyncio
async def test_session_new_params_set():
    session = Session(
        client=Client.CHROME_133,
        disable_http3=True,
        protocol_racing=True,
        disable_ipv6=True,
        disable_ipv4=False,
        is_rotating_proxy=True,
        local_address="0.0.0.0:0",
        server_name_overwrite="override.example.com",
        certificate_pinning={"example.com": ["pin1", "pin2"]},
        without_cookie_jar=True,
        default_headers={"Accept": ["*/*"]},
        h3_settings={"QPACK_MAX_TABLE_CAPACITY": 4096},
        h3_settings_order=["QPACK_MAX_TABLE_CAPACITY"],
        h3_pseudo_header_order=[":method", ":path"],
        h3_priority_param=42,
        h3_send_grease_frames=True,
        alps_protocols=["h2"],
        ech_candidate_payloads=[256],
        ech_candidate_cipher_suites=[{"kdfId": "HKDF_SHA256", "aeadId": "AEAD_AES_128_GCM"}],
        allow_http=True,
        record_size_limit=16384,
        stream_id=1,
    )
    assert session.disable_http3 is True
    assert session.protocol_racing is True
    assert session.disable_ipv6 is True
    assert session.is_rotating_proxy is True
    assert session.local_address == "0.0.0.0:0"
    assert session.server_name_overwrite == "override.example.com"
    assert session.certificate_pinning == {"example.com": ["pin1", "pin2"]}
    assert session.without_cookie_jar is True
    assert session.default_headers == {"Accept": ["*/*"]}
    assert session.h3_settings == {"QPACK_MAX_TABLE_CAPACITY": 4096}
    assert session.h3_send_grease_frames is True
    assert session.alps_protocols == ["h2"]
    assert session.ech_candidate_payloads == [256]
    assert session.allow_http is True
    assert session.record_size_limit == 16384
    assert session.stream_id == 1


@pytest.mark.asyncio
async def test_session_execute_request(mocker):
    mocker.patch('ctypes.string_at', return_value=b'{"status": 200, "body": "OK", "headers": {}, "id": "mock_id"}')
    mocker.patch('ctypes.cdll.LoadLibrary')
    mocker.patch('noble_tls.sessions.free_memory')

    session = Session()

    mock_response = '{"status": 200, "body": "OK", "headers": {}, "id": "mock_id"}'.encode('utf-8')

    mock_loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=mock_loop)

    mock_future = asyncio.Future()
    mock_future.set_result(mock_response)

    mock_loop.run_in_executor = MagicMock(return_value=mock_future)

    response = await session.get('http://example.com')

    assert response.status_code == 200
    assert response.text == 'OK'


@pytest.mark.asyncio
async def test_execute_request_payload_includes_new_fields(mocker):
    """Verify new fields appear in the JSON payload sent to the Go binary."""
    mocker.patch('ctypes.string_at',
                 return_value=b'{"status": 200, "body": "OK", "headers": {}, "id": "x", "usedProtocol": "HTTP/2.0"}')
    mocker.patch('noble_tls.sessions.free_memory')

    captured_payloads = []
    original_request = None

    def capture_request(payload):
        captured_payloads.append(json.loads(payload.decode('utf-8')))
        return b'{"status": 200, "body": "OK", "headers": {}, "id": "x", "usedProtocol": "HTTP/2.0"}'

    mocker.patch('noble_tls.sessions.request', side_effect=capture_request)

    mock_loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=mock_loop)

    async def fake_executor(_, func, *args):
        return func(*args)

    mock_loop.run_in_executor = MagicMock(side_effect=fake_executor)

    session = Session(
        client=Client.CHROME_133,
        disable_http3=True,
        disable_ipv6=True,
        is_rotating_proxy=True,
        certificate_pinning={"example.com": ["pin"]},
        server_name_overwrite="sni.example.com",
        local_address="0.0.0.0:0",
        default_headers={"X-Custom": ["val"]},
    )

    response = await session.get(
        'http://example.com',
        timeout_milliseconds=2500,
        request_host_override="override.host",
        stream_output_path="/tmp/out.json",
    )

    assert len(captured_payloads) == 1
    payload = captured_payloads[0]

    assert payload["disableHttp3"] is True
    assert payload["disableIPV6"] is True
    assert payload["isRotatingProxy"] is True
    assert payload["withProtocolRacing"] is False
    assert payload["certificatePinningHosts"] == {"example.com": ["pin"]}
    assert payload["serverNameOverwrite"] == "sni.example.com"
    assert payload["localAddress"] == "0.0.0.0:0"
    assert payload["defaultHeaders"] == {"X-Custom": ["val"]}
    assert payload["timeoutMilliseconds"] == 2500
    assert "timeoutSeconds" not in payload
    assert payload["requestHostOverride"] == "override.host"
    assert payload["streamOutputPath"] == "/tmp/out.json"
    assert payload["tlsClientIdentifier"] == "chrome_133"


@pytest.mark.asyncio
async def test_execute_request_custom_tls_includes_new_fields(mocker):
    """Verify ECH/ALPS/H3 fields appear in customTlsClient when using custom JA3."""
    mocker.patch('ctypes.string_at',
                 return_value=b'{"status": 200, "body": "OK", "headers": {}, "id": "x"}')
    mocker.patch('noble_tls.sessions.free_memory')

    captured = []

    def capture(payload):
        captured.append(json.loads(payload.decode('utf-8')))
        return b'{"status": 200, "body": "OK", "headers": {}, "id": "x"}'

    mocker.patch('noble_tls.sessions.request', side_effect=capture)

    mock_loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=mock_loop)

    async def fake_executor(_, func, *args):
        return func(*args)

    mock_loop.run_in_executor = MagicMock(side_effect=fake_executor)

    session = Session(
        ja3_string="771,4865-4866,0-23,29-23,0",
        alps_protocols=["h2"],
        ech_candidate_payloads=[256],
        ech_candidate_cipher_suites=[{"kdfId": "HKDF_SHA256", "aeadId": "AEAD_AES_128_GCM"}],
        allow_http=True,
        record_size_limit=16384,
        stream_id=3,
        h3_settings={"QPACK_MAX_TABLE_CAPACITY": 4096},
        h3_settings_order=["QPACK_MAX_TABLE_CAPACITY"],
        h3_pseudo_header_order=[":method", ":path"],
        h3_priority_param=42,
        h3_send_grease_frames=True,
    )

    await session.get('http://example.com')
    custom = captured[0]["customTlsClient"]

    assert custom["alpsProtocols"] == ["h2"]
    assert custom["eCHCandidatePayloads"] == [256]
    assert custom["eCHCandidateCipherSuites"] == [{"kdfId": "HKDF_SHA256", "aeadId": "AEAD_AES_128_GCM"}]
    assert custom["allowHttp"] is True
    assert custom["recordSizeLimit"] == 16384
    assert custom["streamId"] == 3
    assert custom["h3Settings"] == {"QPACK_MAX_TABLE_CAPACITY": 4096}
    assert custom["h3SettingsOrder"] == ["QPACK_MAX_TABLE_CAPACITY"]
    assert custom["h3PseudoHeaderOrder"] == [":method", ":path"]
    assert custom["h3PriorityParam"] == 42
    assert custom["h3SendGreaseFrames"] is True


@pytest.mark.asyncio
async def test_session_close(mocker):
    mocker.patch('ctypes.string_at',
                 return_value=b'{"id": "resp_1", "success": true}')
    mocker.patch('noble_tls.sessions.free_memory')

    captured = []

    def capture(payload):
        captured.append(json.loads(payload.decode('utf-8')))
        return b'{"id": "resp_1", "success": true}'

    mocker.patch('noble_tls.sessions.destroy_session', side_effect=capture)

    mock_loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=mock_loop)

    async def fake_executor(_, func, *args):
        return func(*args)

    mock_loop.run_in_executor = MagicMock(side_effect=fake_executor)

    session = Session()
    result = await session.close()

    assert result is True
    assert captured[0]["sessionId"] == session._session_id


@pytest.mark.asyncio
async def test_session_close_all(mocker):
    mocker.patch('ctypes.string_at',
                 return_value=b'{"id": "resp_1", "success": true}')
    mocker.patch('noble_tls.sessions.free_memory')
    mocker.patch('noble_tls.sessions.destroy_all',
                 return_value=b'{"id": "resp_1", "success": true}')

    mock_loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=mock_loop)

    async def fake_executor(_, func, *args):
        return func(*args)

    mock_loop.run_in_executor = MagicMock(side_effect=fake_executor)

    result = await Session.close_all()
    assert result is True


@pytest.mark.asyncio
async def test_session_get_cookies(mocker):
    cookies_response = b'{"id": "r1", "cookies": [{"name": "sid", "value": "abc", "domain": "example.com", "path": "/"}]}'
    mocker.patch('ctypes.string_at', return_value=cookies_response)
    mocker.patch('noble_tls.sessions.free_memory')

    captured = []

    def capture(payload):
        captured.append(json.loads(payload.decode('utf-8')))
        return cookies_response

    mocker.patch('noble_tls.sessions.get_cookies_from_session', side_effect=capture)

    mock_loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=mock_loop)

    async def fake_executor(_, func, *args):
        return func(*args)

    mock_loop.run_in_executor = MagicMock(side_effect=fake_executor)

    session = Session()
    cookies = await session.get_cookies("https://example.com")

    assert len(cookies) == 1
    assert cookies[0]["name"] == "sid"
    assert captured[0]["sessionId"] == session._session_id
    assert captured[0]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_session_add_cookies(mocker):
    resp = b'{"id": "r1", "cookies": [{"name": "sid", "value": "abc"}, {"name": "new", "value": "val"}]}'
    mocker.patch('ctypes.string_at', return_value=resp)
    mocker.patch('noble_tls.sessions.free_memory')

    captured = []

    def capture(payload):
        captured.append(json.loads(payload.decode('utf-8')))
        return resp

    mocker.patch('noble_tls.sessions.add_cookies_to_session', side_effect=capture)

    mock_loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=mock_loop)

    async def fake_executor(_, func, *args):
        return func(*args)

    mock_loop.run_in_executor = MagicMock(side_effect=fake_executor)

    session = Session()
    result = await session.add_cookies("https://example.com", [
        {"name": "new", "value": "val", "domain": "example.com", "path": "/"},
    ])

    assert len(result) == 2
    assert captured[0]["cookies"] == [{"name": "new", "value": "val", "domain": "example.com", "path": "/"}]
