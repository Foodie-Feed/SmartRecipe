# SmartRecipe

SmartRecipe is a no-account recipe discovery app for Indian regional dishes. It
supports image recognition, ingredient matching, random discovery, recipe
variants, nutrition details, and browser-local saved recipes.

## Project structure

- `src/`: React/Vite frontend.
- `backend/app/`: FastAPI API, SQLite setup, recipe seed data, and model adapter.
- `ml_work/`: existing dataset and training notebooks.

## Run locally

### Frontend

```bash
npm install
npm run dev
```

### API

Python 3.11+ is recommended.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The frontend expects the API at `http://localhost:8000/api`. Set
`VITE_API_URL` before starting Vite to use another API URL.

Install `requirements-ml.txt` and train both models with the shared class map:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-ml.txt
python -m app.train_models \
  --data-dir "../ml_work/dataset/Food Classification" \
  --output-dir weights \
  --epochs 5
```

The training command writes `custom_cnn.pt`, `resnet50.pt`, `labels.json`, and
`metrics.json`. The metrics file contains accuracy, macro precision, macro
recall, macro F1-score, a 20x20 confusion matrix, and precision/recall/F1
support for every class.
These binary checkpoints are intentionally ignored by Git and must be generated
or supplied by the deployment environment. The API refuses checkpoints with a
different label order or image size, and returns `uncertain` below the 70%
confidence threshold.

## Image recognition weights

The recognition endpoint intentionally returns an explicit `503` until exported
Custom CNN and ResNet50 weights are placed in `backend/weights/` and the model
loading code in `backend/app/models.py` is configured for those files. This
prevents the application from presenting a guessed label as a reliable
prediction. Both models must use the shared `LABELS` order and the same
preprocessing before being enabled.
