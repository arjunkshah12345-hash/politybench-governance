from politybench_datasets import validate_license_registry, build_all_manifests


def test_build_and_validate():
    build_all_manifests()
    assert validate_license_registry() == []
