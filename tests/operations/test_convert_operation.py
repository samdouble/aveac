from pathlib import Path

import pytest
from pydantic import ValidationError

from groove.operations.convert import ConvertOperation


def make_op(tmp_path: Path, **kwargs: object) -> ConvertOperation:
    return ConvertOperation(type="convert", input=str(tmp_path), **kwargs)


class TestConvertOperationValidation:
    def test_valid_config(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert op.output_format == "mp3"
        assert op.audio_bitrate == "192k"

    def test_invalid_output_format_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            ConvertOperation(type="convert", input=str(tmp_path), output_format="avi")

    def test_id_is_auto_generated(self, tmp_path: Path) -> None:
        op1 = make_op(tmp_path)
        op2 = make_op(tmp_path)
        assert op1.id != op2.id

    def test_explicit_id_is_preserved(self, tmp_path: Path) -> None:
        op = make_op(tmp_path, id="my-id")
        assert op.id == "my-id"

    def test_name_defaults_to_none(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert op.name is None


class TestConvertOperationRun:
    def test_output_defaults_to_none(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert op.output is None

    def test_raises_when_input_file_missing(self, tmp_path: Path) -> None:
        op = ConvertOperation(type="convert", input="/nonexistent/file.mp4")
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            op.build_invocation(output_dir=tmp_path)

    def test_build_invocation_calls_ffmpeg_with_correct_args(self, tmp_path: Path) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = ConvertOperation(type="convert", input=str(input_file))
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.output_path == output_dir / "video.mp3"
        assert invocation.command == [
            "ffmpeg",
            "-y",
            "-i",
            str(input_file),
            "-vn",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-f",
            "mp3",
            "-b:a",
            "192k",
            str(output_dir / "video.mp3"),
        ]

    def test_output_path_uses_input_stem(self, tmp_path: Path) -> None:
        input_file = tmp_path / "my_song.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = ConvertOperation(type="convert", input=str(input_file))
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.command[-1].endswith("my_song.mp3")

    def test_build_invocation_uses_name_as_label_when_set(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = ConvertOperation(type="convert", input=str(input_file), name="My Song", id="test-id")
        op.build_invocation(output_dir=output_dir)

        captured = capsys.readouterr()
        assert "My Song" in captured.out
