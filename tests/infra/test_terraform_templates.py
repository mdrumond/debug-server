from __future__ import annotations

from pathlib import Path


def test_module_and_stacks_exist() -> None:
    module_root = Path("infra/terraform/modules/docker_node")
    assert module_root.exists()
    assert (module_root / "main.tf").is_file()

    hetzner = Path("infra/terraform/hetzner_docker_node/main.tf")
    contabo = Path("infra/terraform/contabo_docker_node/main.tf")
    assert hetzner.is_file()
    assert contabo.is_file()

    content = (module_root / "main.tf").read_text()
    assert "docker_container" in content
    assert "docker_host" in content


def test_stacks_reference_shared_module() -> None:
    hetzner = Path("infra/terraform/hetzner_docker_node/main.tf").read_text()
    contabo = Path("infra/terraform/contabo_docker_node/main.tf").read_text()
    assert "modules/docker_node" in hetzner
    assert "modules/docker_node" in contabo
