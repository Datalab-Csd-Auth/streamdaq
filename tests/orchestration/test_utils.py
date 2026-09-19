import pytest

from streamdaq.api.registries import MEASURE_REGISTRY
from streamdaq.orchestration.utils import load_additional_files

_MEASURE_FILE = """
from streamdaq.custom import measure

@measure(["x"], name="{name}")
def _compute(d):
    return sum(d["x"])
"""


def _write_measure_file(path, name):
    path.write_text(_MEASURE_FILE.format(name=name))


def _single_file(tmp_path):
    _write_measure_file(tmp_path / "single.py", "_LoadedSingle")
    return str(tmp_path / "single.py"), {"_LoadedSingle"}, set()


def _directory_glob(tmp_path):
    _write_measure_file(tmp_path / "alpha.py", "_LoadedAlpha")
    _write_measure_file(tmp_path / "beta.py", "_LoadedBeta")
    return str(tmp_path), {"_LoadedAlpha", "_LoadedBeta"}, set()


def _underscore_prefixed_skipped(tmp_path):
    _write_measure_file(tmp_path / "kept.py", "_LoadedKept")
    _write_measure_file(tmp_path / "_ignored.py", "_LoadedIgnored")
    return str(tmp_path), {"_LoadedKept"}, {"_LoadedIgnored"}


class TestLoadAdditionalFiles:
    """``load_additional_files`` registers the measures it finds, for real."""

    @pytest.mark.parametrize(
        "writer",
        [_single_file, _directory_glob, _underscore_prefixed_skipped],
        ids=["single-file", "dir-glob", "underscore-skip"],
    )
    def test_registers_expected_measures(self, tmp_path, writer):
        target, expected_present, expected_absent = writer(tmp_path)

        load_additional_files(target)

        for name in expected_present:
            assert name in MEASURE_REGISTRY
        for name in expected_absent:
            assert name not in MEASURE_REGISTRY

    def test_missing_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            load_additional_files(str(tmp_path / "does_not_exist"))
