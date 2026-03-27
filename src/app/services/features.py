import cv2
import numpy as np


FEATURE_ORDER = ["laplacian_var", "brightness", "contrast", "edge_density"]


def decode_image_bytes(file_bytes: bytes) -> np.ndarray:
    image_array = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image file. Please upload a valid note photo.")
    return image


def extract_simple_features(image: np.ndarray) -> dict[str, float]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Sharpness and noise statistics help create a starter baseline detector.
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    contrast = float(gray.std())

    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(edges.mean() / 255.0)

    return {
        "laplacian_var": laplacian_var,
        "brightness": brightness,
        "contrast": contrast,
        "edge_density": edge_density,
    }


def features_to_vector(features: dict[str, float]) -> list[float]:
    return [features[name] for name in FEATURE_ORDER]
