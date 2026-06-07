"""Tests voor de vuurtafel-bibliotheek: koppeling shell→tafel + persistence."""
from __future__ import annotations

from importlib.resources import files

import pytest

from mortarcalc.ballistics import (
    FireTableLibrary, FireTableError, FireTableRepository,
    load_firetable, firetable_from_dict, firetable_to_dict,
)


@pytest.fixture
def he_table():
    return load_firetable(
        str(files("mortarcalc.data.firetables").joinpath("m821_81mm_he.json"))
    )


def test_dict_round_trip(he_table):
    again = firetable_from_dict(firetable_to_dict(he_table))
    assert again.shell == he_table.shell
    assert again.range_span_m == he_table.range_span_m
    assert len(again.charges) == len(he_table.charges)


def test_first_added_becomes_default(he_table):
    lib = FireTableLibrary()
    lib.add("HE", he_table)
    assert lib.default_shell == "HE"


def test_resolve_is_case_insensitive_and_falls_back(he_table):
    lib = FireTableLibrary()
    lib.add("HE", he_table)
    assert lib.resolve("he") is he_table          # genormaliseerd
    assert lib.resolve("ILLUM") is he_table        # geen eigen tafel → default


def test_resolve_prefers_own_table(he_table):
    smoke = firetable_from_dict(firetable_to_dict(he_table))  # aparte instantie
    lib = FireTableLibrary()
    lib.add("HE", he_table)
    lib.add("SMOKE", smoke)
    assert lib.resolve("SMOKE") is smoke
    assert lib.resolve("HE") is he_table


def test_empty_library_resolve_raises():
    with pytest.raises(FireTableError):
        FireTableLibrary().resolve("HE")


def test_remove_reassigns_default(he_table):
    lib = FireTableLibrary()
    lib.add("HE", he_table)
    lib.add("ILLUM", he_table)
    lib.set_default("ILLUM")
    lib.remove("ILLUM")
    assert lib.default_shell == "HE"
    lib.remove("HE")
    assert lib.default_shell is None


def test_set_default_unknown_raises(he_table):
    lib = FireTableLibrary()
    lib.add("HE", he_table)
    with pytest.raises(FireTableError):
        lib.set_default("WP")


def test_repository_round_trip(tmp_path, he_table):
    repo = FireTableRepository(tmp_path)
    assert not repo.exists()
    lib = FireTableLibrary()
    lib.add("HE", he_table)
    lib.add("SMOKE", he_table)
    lib.set_default("SMOKE")
    repo.save(lib)
    assert repo.exists()

    loaded = repo.load()
    assert set(loaded.shells()) == {"HE", "SMOKE"}
    assert loaded.default_shell == "SMOKE"
    assert loaded.resolve("HE").range_span_m == he_table.range_span_m


def test_repository_cleans_orphaned_files(tmp_path, he_table):
    repo = FireTableRepository(tmp_path)
    lib = FireTableLibrary()
    lib.add("HE", he_table)
    lib.add("SMOKE", he_table)
    repo.save(lib)
    lib.remove("SMOKE")
    repo.save(lib)
    assert not (tmp_path / "SMOKE.json").exists()
    assert sorted(p.name for p in tmp_path.glob("*.json")) == ["HE.json", "manifest.json"]


def test_repository_load_missing_is_empty(tmp_path):
    assert not FireTableRepository(tmp_path).load()


# ---------------------------------------------------------------- bundled tables
def test_every_bundled_firetable_parses():
    from mortarcalc.app import _BUNDLED_FIRETABLES
    for shell, filename in _BUNDLED_FIRETABLES:
        ft = load_firetable(
            str(files("mortarcalc.data.firetables").joinpath(filename))
        )
        assert ft.charges, f"{shell}: no charges"
        lo, hi = ft.range_span_m
        assert 0 < lo < hi, f"{shell}: bad range span {lo}-{hi}"
        for c in ft.charges:
            ranges = [r.range_m for r in c.rows]
            assert ranges == sorted(ranges), f"{shell} charge {c.id}: rows not ascending"


def test_build_library_seeds_all_bundled_natures(tmp_path):
    from mortarcalc.app import _build_library, _BUNDLED_FIRETABLES
    lib = _build_library(FireTableRepository(tmp_path))
    assert set(lib.shells()) == {s for s, _ in _BUNDLED_FIRETABLES}
    assert lib.default_shell == "HE"


def test_build_library_backfills_missing_natures(tmp_path, he_table):
    from mortarcalc.app import _build_library
    repo = FireTableRepository(tmp_path)
    seed = FireTableLibrary()
    seed.add("HE", he_table)        # existing install with only HE
    repo.save(seed)
    lib = _build_library(repo)
    assert {"HE", "SMOKE", "ILLUM", "WP"} <= set(lib.shells())
