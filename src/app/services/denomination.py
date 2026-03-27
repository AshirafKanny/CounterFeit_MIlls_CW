from pathlib import Path
import os

import cv2
import numpy as np


class TemplateDenominationEstimator:
    """Estimate note denomination from template matches.

    Place template images in: data/denominations/<amount_label>/*.jpg
    Example: data/denominations/1000/img1.jpg
    """

    def __init__(self, templates_root: Path) -> None:
        self.templates_root = templates_root
        self.orb = cv2.ORB_create(1200)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        self.templates: dict[str, list[np.ndarray]] = {}
        self._load_templates()

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return cv2.GaussianBlur(enhanced, (3, 3), 0)

    def _load_templates(self) -> None:
        self.templates = {}
        if not self.templates_root.exists():
            return

        for denom_dir in self.templates_root.iterdir():
            if not denom_dir.is_dir():
                continue

            desc_list: list[np.ndarray] = []
            for image_path in denom_dir.glob("*"):
                if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                    continue

                image = cv2.imread(str(image_path))
                if image is None:
                    continue

                processed = self._preprocess(image)
                _, descriptors = self.orb.detectAndCompute(processed, None)
                if descriptors is not None and len(descriptors) > 0:
                    desc_list.append(descriptors)

            if desc_list:
                self.templates[denom_dir.name] = desc_list

    def refresh_templates(self) -> None:
        self._load_templates()

    def template_stats(self) -> dict[str, int]:
        return {label: len(desc_list) for label, desc_list in self.templates.items()}

    def register_template(self, amount_label: str, image: np.ndarray) -> Path:
        target_dir = self.templates_root / amount_label
        target_dir.mkdir(parents=True, exist_ok=True)

        next_index = len(list(target_dir.glob("*.jpg"))) + 1
        output_file = target_dir / f"template_{next_index:03d}.jpg"
        cv2.imwrite(str(output_file), image)

        self.refresh_templates()
        return output_file

    def _score_match(self, query_desc: np.ndarray, template_desc: np.ndarray) -> int:
        knn_matches = self.matcher.knnMatch(query_desc, template_desc, k=2)
        good = []
        for pair in knn_matches:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < 0.75 * n.distance:
                good.append(m)
        return len(good)

    def predict_amount(self, image: np.ndarray) -> tuple[str, float]:
        if not self.templates:
            return "unknown", 0.0

        processed = self._preprocess(image)
        _, query_desc = self.orb.detectAndCompute(processed, None)
        if query_desc is None or len(query_desc) == 0:
            return "unknown", 0.0

        best_label = "unknown"
        best_score = 0

        for label, template_desc_list in self.templates.items():
            label_best = 0
            for template_desc in template_desc_list:
                label_best = max(label_best, self._score_match(query_desc, template_desc))

            if label_best > best_score:
                best_score = label_best
                best_label = label

        # Conservative threshold to avoid false denomination claims.
        if best_score < 25:
            return "unknown", min(best_score / 25.0, 1.0)

        confidence = min(best_score / 90.0, 1.0)
        return best_label, float(confidence)

project_root = Path(__file__).resolve().parents[3]
templates_dir = Path(os.getenv("DENOMINATION_TEMPLATES_DIR", str(project_root / "data" / "denominations")))
templates_dir.mkdir(parents=True, exist_ok=True)
denomination_estimator = TemplateDenominationEstimator(templates_dir)
