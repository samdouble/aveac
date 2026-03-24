import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

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


class TestCutOperationRun:
    def test_raises_when_input_file_missing(self) -> None:
        op = CutOperation(type="cut", input="/nonexistent/file.mp4", start="0", end="10")
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            op.run()

    def test_run_calls_ffmpeg_with_correct_args(
        self, mocker: MockerFixture, tmp_path: pytest.TempPathFactory
    ) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()

        mock_stream = mocker.MagicMock()
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream
        mocker.patch("groove.operations.cut.ffmpeg.input", return_value=mock_stream)

        op = CutOperation(type="cut", input=str(input_file), start="0", end="30")
        op.run()

        mocker.patch("groove.operations.cut.ffmpeg.input")
        mock_stream.output.assert_called_once_with(
            str(input_file.with_stem("video_cut")),
            c="copy",
        )
        mock_stream.overwrite_output.assert_called_once()
        mock_stream.run.assert_called_once()

    def test_output_filename_has_cut_suffix(
        self, mocker: MockerFixture, tmp_path: pytest.TempPathFactory
    ) -> None:
        input_file = tmp_path / "my_song.mp3"
        input_file.touch()

        mock_stream = mocker.MagicMock()
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream
        mocker.patch("groove.operations.cut.ffmpeg.input", return_value=mock_stream)

        op = CutOperation(type="cut", input=str(input_file), start="1:00", end="2:00")
        op.run()

        call_args = mock_stream.output.call_args
        assert call_args.args[0].endswith("my_song_cut.mp3")

    def test_ffmpeg_input_receives_ss_and_duration(
        self, mocker: MockerFixture, tmp_path: pytest.TempPathFactory
    ) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()

        mock_stream = mocker.MagicMock()
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream
        mock_ffmpeg_input = mocker.patch(
            "groove.operations.cut.ffmpeg.input", return_value=mock_stream
        )

        op = CutOperation(type="cut", input=str(input_file), start="1:00", end="1:30")
        op.run()

        mock_ffmpeg_input.assert_called_once_with(str(input_file), ss=60.0, t=30.0)

    def test_run_uses_name_as_label_when_set(
        self,
        mocker: MockerFixture,
        tmp_path: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        input_file = tmp_path / "video.mp4"
        input_file.touch()

        mock_stream = mocker.MagicMock()
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream
        mocker.patch("groove.operations.cut.ffmpeg.input", return_value=mock_stream)

        op = CutOperation(
            type="cut", input=str(input_file), start="0", end="10", name="Intro", id="test-id"
        )
        op.run()

        captured = capsys.readouterr()
        assert "Intro" in captured.out
