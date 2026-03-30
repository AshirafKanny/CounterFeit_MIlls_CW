from pathlib import Path
from typing import Any

import cv2
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from app.services.features import extract_simple_features, features_to_vector


def load_labeled_vectors(data_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    vectors: list[list[float]] = []
    labels: list[int] = []

    class_map = {
        "counterfeit": 0,
        "genuine": 1,
    }

    for class_name, label in class_map.items():
        class_dir = data_dir / class_name
        if not class_dir.exists():
            continue

        for image_path in class_dir.glob("*"):
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue

            image = cv2.imread(str(image_path))
            if image is None:
                continue

            features = extract_simple_features(image)
            vectors.append(features_to_vector(features))
            labels.append(label)

    if not vectors:
        raise ValueError("No training images found. Add images to data/genuine and data/counterfeit.")

    return np.array(vectors, dtype=np.float32), np.array(labels, dtype=np.int32)


def dataset_counts(data_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for class_name in ["genuine", "counterfeit"]:
        class_dir = data_dir / class_name
        if not class_dir.exists():
            counts[class_name] = 0
            continue

        images = [
            p for p in class_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ]
        counts[class_name] = len(images)
    return counts


def train_counterfeit_model(data_dir: Path, artifacts_dir: Path) -> dict[str, Any]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    x, y = load_labeled_vectors(data_dir)

    if len(np.unique(y)) < 2:
        raise ValueError("Need both classes. Add images to both data/genuine and data/counterfeit.")

    if len(y) < 10:
        raise ValueError("Need at least 10 total samples before training.")

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(n_estimators=400, random_state=42, class_weight="balanced")
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    report = classification_report(
        y_test,
        predictions,
        target_names=["counterfeit", "genuine"],
        output_dict=True,
    )
    report_text = classification_report(y_test, predictions, target_names=["counterfeit", "genuine"])

    output_file = artifacts_dir / "counterfeit_detector.joblib"
    joblib.dump(model, output_file)
    return {
        "model_path": str(output_file),
        "report": report,
        "report_text": report_text,
        "samples": dataset_counts(data_dir),
        "train_size": int(len(x_train)),
        "test_size": int(len(x_test)),
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    artifacts_dir = project_root / "artifacts"

    metrics = train_counterfeit_model(data_dir, artifacts_dir)
    print("Validation Report:")
    print(metrics["report_text"])
    print(f"Saved model to: {metrics['model_path']}")


if __name__ == "__main__":
    main()
