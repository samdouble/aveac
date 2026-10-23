from pathlib import Path

import pytest
from pydantic import ValidationError

from groove.operations.cut import CutOperation, _parse_timestamp


class TestParseTimestamp:
    def test_bare_seconds(self) -> None:
        assert _parse_timestamp("90") == 90.0

    def test_mm_ss(self) -> None:
        assert _parse_timestamp("1:30") == 90.0

    def test_hh_mm_ss(self) -> None:
        assert _parse_timestamp("1:01:30") == 3690.0

    def test_fractional_seconds(self) -> None:
        assert _parse_timestamp("1:30.5") == 90.5

    def test_hh_mm_ss_with_milliseconds(self) -> None:
        assert _parse_timestamp("00:00:00.500") == 0.5
        assert _parse_timestamp("00:00:02.250") == 2.25


class TestCutOperationValidation:
    def test_valid_config(self) -> None:
        op = CutOperation(type="cut", input="/file.mp4", start="0", end="10")
        assert op.start == "0"
        assert op.end == "10"

    def test_invalid_start_raises(self) -> None:
        with pytest.raises(ValidationError, match="Invalid timestamp"):
            CutOperation(type="cut", input="/file.mp4", start="abc", end="10")

    def test_invalid_end_raises(self) -> None:
        with pytest.raises(ValidationError, match="Invalid timestamp"):
            CutOperation(type="cut", input="/file.mp4", start="0", end="xyz")

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be after start"):
            CutOperation(type="cut", input="/file.mp4", start="30", end="10")

    def test_end_equal_to_start_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be after start"):
            CutOperation(type="cut", input="/file.mp4", start="10", end="10")

    def test_id_is_auto_generated(self) -> None:
        op1 = CutOperation(type="cut", input="/file.mp4", start="0", end="10")
        op2 = CutOperation(type="cut", input="/file.mp4", start="0", end="10")
        assert op1.id != op2.id

    def test_name_defaults_to_none(self) -> None:
        op = CutOperation(type="cut", input="/file.mp4", start="0", end="10")
        assert op.name is None

    def test_output_defaults_to_none(self) -> None:
        op = CutOperation(type="cut", input="/file.mp4", start="0", end="10")
        assert op.output is None


class TestCutOperationRun:
    def test_raises_when_input_file_missing(self, tmp_path: Path) -> None:
        op = CutOperation(type="cut", input="/nonexistent/file.mp4", start="0", end="10")
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            op.build_invocation(output_dir=tmp_path)

    def test_build_invocation_calls_ffmpeg_with_correct_args(self, tmp_path: Path) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = CutOperation(type="cut", input=str(input_file), start="0", end="30")
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.output_path == output_dir / "video_cut.mp4"
        assert invocation.command == [
            "ffmpeg",
            "-y",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-i",
            str(input_file),
            "-c",
            "copy",
            str(output_dir / "video_cut.mp4"),
        ]

    def test_build_invocation_reencodes_audio_for_subsecond_precision(
        self, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "clip.mp3"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = CutOperation(
            type="cut", input=str(input_file), start="00:00:00", end="00:00:00.500"
        )
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.command == [
            "ffmpeg",
            "-y",
            "-ss",
            "0.0",
            "-t",
            "0.5",
            "-i",
            str(input_file),
            "-vn",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-b:a",
            "192k",
            "-f",
            "mp3",
            str(output_dir / "clip_cut.mp3"),
        ]

    def test_build_invocation_outputs_mp3_for_m4a_input(self, tmp_path: Path) -> None:
        input_file = tmp_path / "clip.m4a"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = CutOperation(type="cut", input=str(input_file), start="0", end="1")
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.output_path == output_dir / "clip_cut.mp3"
        assert invocation.command[-1].endswith("clip_cut.mp3")
        assert "-f" in invocation.command and "mp3" in invocation.command

    def test_output_filename_has_cut_suffix(self, tmp_path: Path) -> None:
        input_file = tmp_path / "my_song.mp3"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = CutOperation(type="cut", input=str(input_file), start="1:00", end="2:00")
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.command[-1].endswith("my_song_cut.mp3")

    def test_ffmpeg_invocation_receives_ss_and_duration(self, tmp_path: Path) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = CutOperation(type="cut", input=str(input_file), start="1:00", end="1:30")
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.command[2:6] == ["-ss", "60.0", "-t", "30.0"]

    def test_build_invocation_uses_name_as_label_when_set(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = CutOperation(
            type="cut", input=str(input_file), start="0", end="10", name="Intro", id="test-id"
        )
        op.build_invocation(output_dir=output_dir)

        captured = capsys.readouterr()
        assert "Intro" in captured.out
