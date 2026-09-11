import re
from pathlib import Path

import cv2
import numpy as np

QR_PREFIX = "ai-teacher:worksheet:"


def _order_points(points: np.ndarray) -> np.ndarray:
    pts = points.reshape(4, 2).astype("float32")
    ordered = np.zeros((4, 2), dtype="float32")
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).reshape(-1)
    ordered[0] = pts[np.argmin(sums)]
    ordered[2] = pts[np.argmax(sums)]
    ordered[1] = pts[np.argmin(diffs)]
    ordered[3] = pts[np.argmax(diffs)]
    return ordered


def _warp_page(image: np.ndarray, contour: np.ndarray) -> np.ndarray:
    rect = _order_points(contour)
    tl, tr, br, bl = rect
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    width = max(width, 1)
    height = max(height, 1)
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (width, height))


def _detect_page(image: np.ndarray) -> tuple[np.ndarray, bool]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = image.shape[0] * image.shape[1]
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
        area = cv2.contourArea(contour)
        if area < image_area * 0.25:
            continue
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4:
            return _warp_page(image, approx), True
    return image, False


def _decode_qr(image: np.ndarray) -> tuple[str | None, str | None]:
    detector = cv2.QRCodeDetector()
    raw, _, _ = detector.detectAndDecode(image)
    raw = (raw or "").strip()
    if not raw:
        return None, None
    if raw.startswith(QR_PREFIX):
        worksheet_id = raw[len(QR_PREFIX):].strip()
        if re.fullmatch(r"[a-f0-9]{12}", worksheet_id):
            return worksheet_id, raw
    return None, raw


def prepare_answer_sheet(image_path: Path) -> dict:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError("Unable to decode uploaded image")

    original_id, original_qr = _decode_qr(image)
    processed, page_detected = _detect_page(image)
    processed_id, processed_qr = _decode_qr(processed)

    output = image_path.with_name(f"{image_path.stem}.processed.jpg")
    cv2.imwrite(str(output), processed, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

    return {
        "processed_path": output,
        "worksheet_id": processed_id or original_id,
        "qr_raw": processed_qr or original_qr,
        "page_detected": page_detected,
        "width": int(processed.shape[1]),
        "height": int(processed.shape[0]),
    }
