from pathlib import Path

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from groove.operations.concatenate import ConcatenateOperation


def make_op(tmp_path: Path, **kwargs: object) -> ConcatenateOperation:
    file_a = tmp_path / "a.mp4"
    file_b = tmp_path / "b.mp4"
    file_a.touch()
    file_b.touch()
    data: dict[str, object] = {
        "type": "concatenate",
        "inputs": [str(file_a), str(file_b)],
    }
    data.update(kwargs)
    return ConcatenateOperation.model_validate(data)


class TestConcatenateOperationValidation:
    def test_valid_config(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert len(op.inputs) == 2

    def test_requires_at_least_two_inputs(self, tmp_path: Path) -> None:
        file_a = tmp_path / "a.mp4"
        file_a.touch()
        with pytest.raises(ValidationError, match="at least two"):
            ConcatenateOperation(type="concatenate", inputs=[str(file_a)])

    def test_id_is_auto_generated(self, tmp_path: Path) -> None:
        op1 = make_op(tmp_path)
        op2 = make_op(tmp_path)
        assert op1.id != op2.id

    def test_name_defaults_to_none(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert op.name is None

    def test_output_defaults_to_none(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert op.output is None


class TestConcatenateOperationRun:
    def test_raises_when_input_file_missing(self, tmp_path: Path) -> None:
        op = ConcatenateOperation(
            type="concatenate",
            inputs=["/nonexistent/a.mp4", "/nonexistent/b.mp4"],
        )
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            op.run(output_dir=tmp_path)

    def test_run_calls_ffmpeg_with_correct_args(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        mock_run = mocker.patch("groove.operations.concatenate.subprocess.run")

        op = make_op(tmp_path, id="concat-id")
        result = op.run(output_dir=output_dir)

        assert result == output_dir / "a_concat.mp4"
        mock_run.assert_called_once()
        args = mock_run.call_args.args[0]
        assert args[0] == "ffmpeg"
        assert "-f" in args and "concat" in args
        assert "-safe" in args and "0" in args
        assert "-c" in args and "copy" in args
        assert str(output_dir / "concat-id.txt") in args
        assert args[-1] == str(output_dir / "a_concat.mp4")

    def test_run_uses_name_as_label_when_set(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        mocker.patch("groove.operations.concatenate.subprocess.run")

        op = make_op(tmp_path, name="Final merge", id="test-id")
        op.run(output_dir=output_dir)

        captured = capsys.readouterr()
        assert "Final merge" in captured.out
