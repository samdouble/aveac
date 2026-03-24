from pathlib import Path

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

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
            op.run(output_dir=tmp_path)

    def test_run_calls_ffmpeg_with_correct_args(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        mock_stream = mocker.MagicMock()
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream
        mocker.patch("groove.operations.convert.ffmpeg.input", return_value=mock_stream)

        op = ConvertOperation(type="convert", input=str(input_file))
        result = op.run(output_dir=output_dir)

        assert result == output_dir / "video.mp3"
        mock_stream.output.assert_called_once_with(
            str(output_dir / "video.mp3"),
            format="mp3",
            **{"b:a": "192k"},
            vn=None,
        )
        mock_stream.overwrite_output.assert_called_once()
        mock_stream.run.assert_called_once()

    def test_output_path_uses_input_stem(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "my_song.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        mock_stream = mocker.MagicMock()
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream
        mocker.patch("groove.operations.convert.ffmpeg.input", return_value=mock_stream)

        op = ConvertOperation(type="convert", input=str(input_file))
        op.run(output_dir=output_dir)

        call_args = mock_stream.output.call_args
        assert call_args.args[0].endswith("my_song.mp3")

    def test_run_uses_name_as_label_when_set(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        mock_stream = mocker.MagicMock()
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream
        mocker.patch("groove.operations.convert.ffmpeg.input", return_value=mock_stream)

        op = ConvertOperation(type="convert", input=str(input_file), name="My Song", id="test-id")
        op.run(output_dir=output_dir)

        captured = capsys.readouterr()
        assert "My Song" in captured.out
