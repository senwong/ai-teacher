from pathlib import Path

import cv2
import numpy as np
import qrcode

from app.vision.preprocess import prepare_answer_sheet


def test_prepare_answer_sheet_reads_qr(tmp_path: Path):
    worksheet_id = "abcdef123456"
    qr = qrcode.make(f"ai-teacher:worksheet:{worksheet_id}").convert("RGB")
    canvas = np.full((1000, 700, 3), 255, dtype=np.uint8)
    qr_np = cv2.cvtColor(np.array(qr.resize((220, 220))), cv2.COLOR_RGB2BGR)
    canvas[50:270, 430:650] = qr_np
    path = tmp_path / "sheet.jpg"
    cv2.imwrite(str(path), canvas)

    result = prepare_answer_sheet(path)

    assert result["worksheet_id"] == worksheet_id
    assert result["processed_path"].exists()


def test_prepare_answer_sheet_rejects_non_image(tmp_path: Path):
    path = tmp_path / "bad.jpg"
    path.write_text("not an image")
    try:
        prepare_answer_sheet(path)
    except ValueError as exc:
        assert "decode" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError")
