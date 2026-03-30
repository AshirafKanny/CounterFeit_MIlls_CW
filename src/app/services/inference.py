from pathlib import Path

import joblib

from app.services.features import extract_simple_features, features_to_vector


class BaselineCounterfeitDetector:
    """A baseline detector using handcrafted features.

    This is NOT production-grade counterfeit detection.
    It is a teaching-friendly placeholder until we train a real model.
    """

    def predict(self, image) -> tuple[str, float, dict[str, float]]:
        features = extract_simple_features(image)

        # Simple heuristic score; replaced later with ML model output.
        score = (
            0.35 * min(features["laplacian_var"] / 150.0, 1.0)
            + 0.25 * (1.0 - abs(features["brightness"] - 128.0) / 128.0)
            + 0.25 * min(features["contrast"] / 64.0, 1.0)
            + 0.15 * min(features["edge_density"] / 0.15, 1.0)
        )

        confidence = float(max(min(score, 1.0), 0.0))
        label = "likely_genuine" if confidence >= 0.62 else "possible_counterfeit"
        return label, confidence, features


baseline_detector = BaselineCounterfeitDetector()


class TrainedModelDetector:
    def __init__(self, artifact_path: Path) -> None:
        self.artifact_path = artifact_path
        self.model = None
        self._load_model_if_available()

    def _load_model_if_available(self) -> None:
        if self.artifact_path.exists():
            self.model = joblib.load(self.artifact_path)

    def reload_model(self) -> bool:
        if not self.artifact_path.exists():
            self.model = None
            return False
        self.model = joblib.load(self.artifact_path)
        return True

    def predict(self, image) -> tuple[str, float, dict[str, float]]:
        features = extract_simple_features(image)

        if self.model is None:
            return baseline_detector.predict(image)

        vector = [features_to_vector(features)]
        probability_genuine = float(self.model.predict_proba(vector)[0][1])
        label = "likely_genuine" if probability_genuine >= 0.5 else "possible_counterfeit"
        return label, probability_genuine, features


artifact_file = Path(__file__).resolve().parents[3] / "artifacts" / "counterfeit_detector.joblib"
detector = TrainedModelDetector(artifact_file)
