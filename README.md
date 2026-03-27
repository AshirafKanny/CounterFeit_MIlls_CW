# Counterfeit Note Detector (AI Vision) - Starter Project

This project is a beginner-friendly Python starter for detecting possibly counterfeit notes from images.

## 1) What we built first

- A FastAPI backend with:
  - `GET /health` to verify server is running
  - `POST /predict` to upload a note image and get a baseline prediction
- A baseline detector using simple computer-vision features
- A test file to verify the API starts correctly

Important: this baseline is for learning and scaffolding. We will replace it with a trained model in later steps.

## 2) Install Python (Windows)

Install Python 3.12.x from python.org (recommended for this project right now).

After installing, open a terminal in this project folder and check:

```powershell
python --version
```

## 3) Create virtual environment and install packages

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Run the API

```powershell
uvicorn app.main:app --app-dir src --reload
```

Open docs in browser:

- http://127.0.0.1:8000/docs

## 5) Test quickly

In terminal:

```powershell
pytest -q
```

## 6) Try prediction endpoint

Use Swagger UI (`/docs`) and upload a JPG/PNG note image.

You will get JSON like:

```json
{
  "label": "likely_genuine",
  "confidence": 0.74,
  "details": {
    "laplacian_var": 98.4,
    "brightness": 122.7,
    "contrast": 41.2,
    "edge_density": 0.08
  }
}
```

## 7) Train your first real model

1. Put images in these folders:
  - `data/genuine`
  - `data/counterfeit`
2. Train model:

```powershell
python src/training/train_baseline_model.py
```

3. Restart API server after training so it loads `artifacts/counterfeit_detector.joblib`.

## 8) Enable note amount detection (denomination)

The app can estimate note amount using template matching.

Create folders like:

- `data/denominations/1000`
- `data/denominations/5000`
- `data/denominations/10000`

Add multiple clear template images in each folder. After adding templates, restart the API.

If no templates are provided, amount will show as `unknown`.

Quick calibration from live camera:

1. Start camera from the app home page.
2. Enter amount in "Teach amount" (example `2000`).
3. Hold note steady and click "Save Template" 4-8 times from different angles.
4. Repeat for other amounts.

The API now classifies authenticity in confidence bands:

- `original` for high-confidence genuine readings
- `fake` for high-confidence counterfeit readings
- `uncertain` for ambiguous frames

## 9) Next learning steps (we do these together)

1. Build a labeled dataset (`data/genuine`, `data/counterfeit`)
2. Train a real classifier model with augmentation
3. Evaluate with precision/recall and confusion matrix
4. Replace baseline heuristic with trained model inference
5. Add anti-spoof checks (blur, screen-recapture, print artifacts)

## 10) Prepare dataset folders now

```powershell
python src/training/prepare_dataset.py
```

That command creates:

- `data/genuine`
- `data/counterfeit`

You can then start collecting images for training.
