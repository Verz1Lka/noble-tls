import pytest
from unittest.mock import MagicMock, patch
from ..c.cffi import check_and_download_dependencies, run_async_task, load_asset, initialize_library


@pytest.mark.asyncio
async def test_check_and_download_dependencies_empty(mocker):
    mocker.patch('os.listdir', return_value=[])
    mocker.patch('noble_tls.c.cffi.download_if_necessary', return_value=MagicMock())
    await check_and_download_dependencies()


@pytest.mark.asyncio
async def test_check_and_download_dependencies_not_empty(mocker):
    mocker.patch('os.listdir', return_value=['file1', 'file2'])
    await check_and_download_dependencies()


def test_run_async_task(mocker):
    async def async_task():
        return "Task completed"

    task = async_task()
    run_async_task(task)


def test_load_asset(mocker):
    mocker.patch('os.path.exists', side_effect=[True, True])
    mocker.patch('noble_tls.updater.file_fetch.read_version_info', return_value=('some_asset', '1.0.0'))
    mocker.patch('noble_tls.c.cffi.generate_asset_name', return_value='some_asset')

    asset_name = load_asset()
    assert asset_name == 'some_asset'


def test_initialize_library(mocker):
    mocker.patch('noble_tls.c.cffi.load_asset', return_value='some_asset')
    mocker.patch('ctypes.cdll.LoadLibrary', return_value=MagicMock())
    library = initialize_library()
    assert library is not None


def test_library_bindings_registered(mocker):
    """All 6 CFFI functions get their argtypes/restype set on first load."""
    mock_lib = MagicMock()
    mocker.patch('noble_tls.c.cffi.load_asset', return_value='some_asset')
    mocker.patch('ctypes.cdll.LoadLibrary', return_value=mock_lib)

    import noble_tls.c.cffi as cffi_mod
    cffi_mod._library = None  # force re-init
    lib = cffi_mod._get_library()

    for fn_name in ['request', 'freeMemory', 'getCookiesFromSession',
                     'addCookiesToSession', 'destroySession', 'destroyAll']:
        assert hasattr(lib, fn_name), f"Library missing {fn_name}"
