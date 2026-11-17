from io import BytesIO
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from .models import CONFIDENCE_THRESHOLD, combine_predictions, model_service
from .recipes import all_recipes, random_recipe, recipe, recommendations

app = FastAPI(title="SmartRecipe API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngredientRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1, max_length=30)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/recipes")
def list_recipes() -> list[dict]:
    return all_recipes()


@app.get("/api/recipes/random")
def get_random_recipe() -> dict:
    return random_recipe()


@app.get("/api/recipes/{dish_key}/{variant}")
def get_recipe(dish_key: str, variant: str) -> dict:
    result = recipe(dish_key, variant)
    if result is None:
        raise HTTPException(status_code=404, detail="Recipe not found.")
    return result


@app.post("/api/recommendations")
def get_recommendations(request: IngredientRequest) -> list[dict]:
    return recommendations(request.ingredients)


@app.post("/api/recognize")
async def recognize(file: Annotated[UploadFile, File()]) -> dict:
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image.")
    try:
        image = Image.open(BytesIO(await file.read())).convert("RGB")
    except UnidentifiedImageError as error:
        raise HTTPException(status_code=422, detail="The uploaded file is not a readable image.") from error
    try:
        predictions = model_service.predict(image)
    except (RuntimeError, NotImplementedError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if len(predictions) != 2:
        raise HTTPException(status_code=500, detail="Both recognition models must return a prediction.")
    decision = combine_predictions(predictions)
    if decision is None:
        return {"status": "uncertain", "threshold": CONFIDENCE_THRESHOLD, "predictions": [prediction.__dict__ for prediction in predictions]}
    dish_key, confidence = decision
    return {
        "status": "identified",
        "dish_key": dish_key,
        "confidence": confidence,
        "predictions": [prediction.__dict__ for prediction in predictions],
    }
