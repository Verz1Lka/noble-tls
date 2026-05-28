import pytest
from requests.exceptions import HTTPError
from ..response import Response, Protocol, build_response


def test_response_initialization():
    response = Response()
    assert response.url is None
    assert response.status_code is None
    assert response.text is None
    assert response.history == []
    assert response.cookies is not None
    assert response.used_protocol is None


def test_response_content_consumed():
    response = Response()
    response.text = "Hello, World!"
    response.status_code = 200

    _ = response.content

    response._content = None
    response._content_consumed = True

    with pytest.raises(RuntimeError):
        _ = response.content


def test_response_json_parsing():
    response = Response()
    response.text = '{"message": "Hello, World!"}'
    json_data = response.json()
    assert json_data['message'] == "Hello, World!"


def test_build_response_function():
    res_data = {
        "target": "https://example.com",
        "status": 200,
        "body": '{"message": "Success"}',
        "headers": {"Content-Type": ["application/json"]}
    }

    response = build_response(res_data, None)

    assert response.url == "https://example.com"
    assert response.status_code == 200
    assert response.text == '{"message": "Success"}'
    assert response.headers['Content-Type'] == "application/json"
    assert response.json()['message'] == "Success"


def test_build_response_with_used_protocol():
    res_data = {
        "target": "https://example.com",
        "status": 200,
        "body": "ok",
        "headers": {},
        "usedProtocol": "HTTP/2.0",
    }
    response = build_response(res_data, None)
    assert response.used_protocol == Protocol.HTTP_2


def test_build_response_without_used_protocol():
    res_data = {"target": "https://example.com", "status": 200, "body": "", "headers": {}}
    response = build_response(res_data, None)
    assert response.used_protocol is None


def test_protocol_enum_values():
    assert Protocol.HTTP_1_1.value == "HTTP/1.1"
    assert Protocol.HTTP_2.value == "HTTP/2.0"
    assert Protocol.HTTP_3.value == "HTTP/3.0"


def test_protocol_from_string():
    assert Protocol.from_string("HTTP/1.1") == Protocol.HTTP_1_1
    assert Protocol.from_string("HTTP/2.0") == Protocol.HTTP_2
    assert Protocol.from_string("HTTP/3.0") == Protocol.HTTP_3
    assert Protocol.from_string("unknown") is None
    assert Protocol.from_string(None) is None
    assert Protocol.from_string("") is None


def test_raise_for_status_client_error():
    response = Response()
    response.status_code = 404
    response.url = "https://example.com"
    with pytest.raises(HTTPError, match="Client Error: 404"):
        response.raise_for_status()


def test_raise_for_status_server_error():
    response = Response()
    response.status_code = 500
    response.url = "https://example.com"
    with pytest.raises(HTTPError, match="Server Error: 500"):
        response.raise_for_status()


def test_raise_for_status_ok():
    response = Response()
    response.status_code = 200
    response.url = "https://example.com"
    response.raise_for_status()  # should not raise
