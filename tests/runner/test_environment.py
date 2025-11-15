from pathlib import Path

import pytest

from debug_server.runner import EnvironmentManager, EnvironmentRequest


@pytest.fixture()
def manager(tmp_path: Path) -> EnvironmentManager:
    return EnvironmentManager(tmp_path / "envs")


def test_environment_rebuilds_when_manifest_changes(
    manager: EnvironmentManager, tmp_path: Path
) -> None:
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("requests==2.31.0\n")
    request = EnvironmentRequest(name="demo", manifests=[manifest])
    handle1 = manager.ensure(request)
    marker = handle1.path / "marker.txt"
    marker.write_text("keep")

    manifest.write_text("requests==2.32.0\n")
    handle2 = manager.ensure(request)
    assert handle1.path == handle2.path
    assert not marker.exists(), "environment should be rebuilt"
    assert handle1.fingerprint != handle2.fingerprint


def test_force_rebuild(manager: EnvironmentManager, tmp_path: Path) -> None:
    manifest = tmp_path / "reqs.txt"
    manifest.write_text("anyio==4.0\n")
    request = EnvironmentRequest(name="force-demo", manifests=[manifest])
    handle = manager.ensure(request)
    marker = handle.path / "marker"
    marker.write_text("stale")

    handle2 = manager.ensure(request, force=True)
    assert not marker.exists()
    assert handle.path == handle2.path


def test_environment_without_manifests(manager: EnvironmentManager) -> None:
    request = EnvironmentRequest(name="blank")
    handle = manager.ensure(request)
    assert (handle.python_path).exists()
