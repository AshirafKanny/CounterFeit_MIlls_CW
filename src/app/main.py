from pathlib import Path
import re
from datetime import datetime

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.schemas import PredictionResponse
from app.services.denomination import denomination_estimator
from app.services.features import decode_image_bytes
from app.services.inference import detector
from training.train_baseline_model import dataset_counts, train_counterfeit_model

app = FastAPI(title=settings.app_name, version=settings.app_version)

project_root = Path(__file__).resolve().parents[2]
web_root = project_root / "web"

app.mount("/assets", StaticFiles(directory=web_root), name="assets")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(web_root / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _sanitize_amount_label(amount: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_-]", "", amount.strip())
    return cleaned[:30]


def _sanitize_authenticity_label(label: str) -> str:
    cleaned = label.strip().lower()
    if cleaned not in {"genuine", "counterfeit"}:
        raise HTTPException(status_code=400, detail="Label must be genuine or counterfeit.")
    return cleaned


@app.post("/predict", response_model=PredictionResponse)
async def predict_note(file: UploadFile = File(...)) -> PredictionResponse:
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/jpeg", "image/jpg", "image/png"}:
        raise HTTPException(status_code=400, detail="Upload JPG or PNG image only.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        image = decode_image_bytes(file_bytes)
        label, confidence, details = detector.predict(image)
        amount, amount_confidence = denomination_estimator.predict_amount(image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if confidence >= 0.60:
        note_state = "original"
        recommendation = "High confidence genuine reading."
    elif confidence <= 0.30:
        note_state = "fake"
        recommendation = "High risk counterfeit reading. Verify with manual security features."
    else:
        note_state = "uncertain"
        recommendation = "Uncertain reading. Hold note steady in better lighting and rescan."

    return PredictionResponse(
        label=label,
        note_state=note_state,
        recommendation=recommendation,
        amount=amount,
        amount_confidence=amount_confidence,
        confidence=confidence,
        details=details,
    )


@app.post("/denomination/template")
async def add_denomination_template(
    amount: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, str]:
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/jpeg", "image/jpg", "image/png"}:
        raise HTTPException(status_code=400, detail="Upload JPG or PNG image only.")

    amount_label = _sanitize_amount_label(amount)
    if not amount_label:
        raise HTTPException(status_code=400, detail="Amount label is invalid.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        image = decode_image_bytes(file_bytes)
        output_path = denomination_estimator.register_template(amount_label, image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "ok",
        "amount": amount_label,
        "saved": str(output_path),
    }


@app.get("/denomination/templates")
def list_denomination_templates() -> dict[str, object]:
    stats = denomination_estimator.template_stats()
    return {
        "status": "ok",
        "templates": stats,
    }


@app.post("/authenticity/sample")
async def add_authenticity_sample(
    label: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, str]:
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/jpeg", "image/jpg", "image/png"}:
        raise HTTPException(status_code=400, detail="Upload JPG or PNG image only.")

    class_label = _sanitize_authenticity_label(label)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    image = decode_image_bytes(file_bytes)

    class_dir = project_root / "data" / class_label
    class_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f") + ".jpg"
    output_file = class_dir / filename

    import cv2

    cv2.imwrite(str(output_file), image)
    return {
        "status": "ok",
        "label": class_label,
        "saved": str(output_file),
    }


@app.get("/authenticity/dataset")
def get_authenticity_dataset_stats() -> dict[str, object]:
    counts = dataset_counts(project_root / "data")
    return {"status": "ok", "samples": counts}


@app.post("/authenticity/train")
def train_authenticity_model() -> dict[str, object]:
    try:
        metrics = train_counterfeit_model(project_root / "data", project_root / "artifacts")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    loaded = detector.reload_model()

    return {
        "status": "ok",
        "model_reloaded": loaded,
        "samples": metrics["samples"],
        "train_size": metrics["train_size"],
        "test_size": metrics["test_size"],
        "report_text": metrics["report_text"],
        "model_path": metrics["model_path"],
    }
