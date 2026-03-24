from __future__ import annotations

from seedr_tg.direct.renamer import FilenameRenamer, RegexSubstitutionRule, RenameRequest


def test_extension_preserved_when_renaming(tmp_path):
    renamer = FilenameRenamer(max_filename_bytes=255)

    result = renamer.build_name(
        original_name="movie.mkv",
        request=RenameRequest(explicit_name="my custom upload"),
        target_directory=tmp_path,
    )

    assert result == "my custom upload.mkv"


def test_regex_substitution_case_insensitive_by_default(tmp_path):
    renamer = FilenameRenamer(max_filename_bytes=255)

    result = renamer.build_name(
        original_name="My.Show.S01E01.mkv",
        request=RenameRequest(
            substitutions=[
                RegexSubstitutionRule(pattern="show", replacement="series"),
                RegexSubstitutionRule(pattern="\\.", replacement=" "),
            ]
        ),
        target_directory=tmp_path,
    )

    assert result == "My series S01E01.mkv"


def test_regex_substitution_case_sensitive_mode(tmp_path):
    renamer = FilenameRenamer(max_filename_bytes=255)

    result = renamer.build_name(
        original_name="WEB.Release.mkv",
        request=RenameRequest(
            substitutions=[
                RegexSubstitutionRule(
                    pattern="web",
                    replacement="scene",
                    case_sensitive=True,
                )
            ]
        ),
        target_directory=tmp_path,
    )

    assert result == "WEB.Release.mkv"


def test_long_name_truncated_to_byte_limit(tmp_path):
    renamer = FilenameRenamer(max_filename_bytes=40)

    result = renamer.build_name(
        original_name="a" * 80 + ".mp4",
        request=RenameRequest(prefix="[Tag] "),
        target_directory=tmp_path,
    )

    assert len(result.encode("utf-8")) <= 40
    assert result.endswith(".mp4")


def test_duplicate_filename_gets_numeric_suffix(tmp_path):
    renamer = FilenameRenamer(max_filename_bytes=255)
    existing = tmp_path / "sample.mp4"
    existing.write_bytes(b"x")

    result = renamer.build_name(
        original_name="sample.mp4",
        request=RenameRequest(),
        target_directory=tmp_path,
    )

    assert result == "sample (1).mp4"


def test_invalid_rename_output_falls_back_to_safe_original(tmp_path):
    renamer = FilenameRenamer(max_filename_bytes=255)

    result = renamer.build_name(
        original_name="safe_name.mp4",
        request=RenameRequest(explicit_name="\\/:*?\"<>|"),
        target_directory=tmp_path,
    )

    assert result == "safe_name.mp4"


def test_auto_strips_leading_1tamilmv_domain_prefix(tmp_path):
    renamer = FilenameRenamer(max_filename_bytes=255)

    result = renamer.build_name(
        original_name="www.1TamilMV.immo - Sabdham (2025) Tamil HQ HDRip - x264 - AAC - 400MB - ESub.mkv",
        request=RenameRequest(),
        target_directory=tmp_path,
    )

    assert result == "Sabdham (2025) Tamil HQ HDRip - x264 - AAC - 400MB - ESub.mkv"


def test_auto_strips_leading_1tamilmv_prefix_for_other_domains(tmp_path):
    renamer = FilenameRenamer(max_filename_bytes=255)

    io_result = renamer.build_name(
        original_name="www.1TamilMV.io - Movie Title (2026).mp4",
        request=RenameRequest(),
        target_directory=tmp_path,
    )
    com_result = renamer.build_name(
        original_name="www.1TamilMV.com - Another Title (2024).mkv",
        request=RenameRequest(),
        target_directory=tmp_path,
    )

    assert io_result == "Movie Title (2026).mp4"
    assert com_result == "Another Title (2024).mkv"
