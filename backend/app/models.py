from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

LABELS = [
    "burger",
    "butter_naan",
    "chai",
    "chapati",
    "chole_bhature",
    "dal_makhani",
    "dhokla",
    "fried_rice",
    "idli",
    "jalebi",
    "kaathi_rolls",
    "kadai_paneer",
    "kulfi",
    "masala_dosa",
    "momos",
    "paani_puri",
    "pakode",
    "pav_bhaji",
    "pizza",
    "samosa",
]
IMAGE_SIZE = 224
CONFIDENCE_THRESHOLD = 0.70
DEFAULT_TEMPERATURE = 1.0


@dataclass(frozen=True)
class Prediction:
    model: str
    dish_key: str
    confidence: float


def combine_predictions(predictions: list[Prediction]) -> tuple[str, float] | None:
    """Apply the documented two-model decision rule.

    Agreement uses the mean confidence. For disagreement, the more confident
    model wins only when its confidence clears the API threshold.
    """
    if len(predictions) != 2:
        raise ValueError("Exactly two model predictions are required.")
    first, second = predictions
    if first.dish_key == second.dish_key:
        return first.dish_key, (first.confidence + second.confidence) / 2
    winner = max(predictions, key=lambda prediction: prediction.confidence)
    if winner.confidence < CONFIDENCE_THRESHOLD:
        return None
    return winner.dish_key, winner.confidence


class ModelService:
    def __init__(self, weights_dir: Path | None = None) -> None:
        self.weights_dir = weights_dir or Path(__file__).resolve().parents[1] / "weights"
        self._models: dict[str, Any] | None = None
        self._torch: Any | None = None
        self._transforms: Any | None = None

    def _load(self) -> None:
        if self._models is not None:
            return
        checkpoint_paths = {
            "custom_cnn": self.weights_dir / "custom_cnn.pt",
            "resnet50": self.weights_dir / "resnet50.pt",
        }
        missing = [str(path) for path in checkpoint_paths.values() if not path.is_file()]
        if missing:
            raise RuntimeError(
                "Model weights are missing. Run "
                "`python -m app.train_models --data-dir ../ml_work/dataset/'Food Classification'` "
                f"to export them into {self.weights_dir}. Missing: {', '.join(missing)}"
            )
        try:
            import torch
            from torchvision import models, transforms
        except ImportError as error:
            raise RuntimeError(
                "PyTorch and torchvision are required for image recognition. "
                "Install backend/requirements-ml.txt."
            ) from error

        self._torch = torch
        self._transforms = transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=(0.485, 0.456, 0.406),
                    std=(0.229, 0.224, 0.225),
                ),
            ]
        )
        loaded: dict[str, Any] = {}
        for model_name, path in checkpoint_paths.items():
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
            if checkpoint.get("labels") != LABELS:
                raise RuntimeError(f"{path} does not use the shared SmartRecipe label mapping.")
            if checkpoint.get("image_size") != IMAGE_SIZE:
                raise RuntimeError(f"{path} was exported for an incompatible image size.")
            network = self._build_network(model_name, models, torch)
            network.load_state_dict(checkpoint["state_dict"])
            network.eval()
            loaded[model_name] = {
                "network": network,
                "temperature": max(float(checkpoint.get("temperature", DEFAULT_TEMPERATURE)), 0.1),
            }
        self._models = loaded

    @staticmethod
    def _build_network(model_name: str, models: Any, torch: Any) -> Any:
        if model_name == "custom_cnn":
            from .train_models import CustomCNN

            return CustomCNN(len(LABELS))
        network = models.resnet50(weights=None)
        network.fc = torch.nn.Linear(network.fc.in_features, len(LABELS))
        return network

    def _predict_one(self, model_name: str, image: Image.Image) -> Prediction:
        self._load()
        assert self._models is not None and self._torch is not None and self._transforms is not None
        payload = self._transforms(image).unsqueeze(0)
        loaded = self._models[model_name]
        with self._torch.inference_mode():
            logits = loaded["network"](payload) / loaded["temperature"]
            probabilities = self._torch.softmax(logits, dim=1)[0]
        index = int(self._torch.argmax(probabilities).item())
        return Prediction(model=model_name, dish_key=LABELS[index], confidence=float(probabilities[index].item()))

    def predict(self, image: Image.Image) -> list[Prediction]:
        return [
            self._predict_one("custom_cnn", image),
            self._predict_one("resnet50", image),
        ]


model_service = ModelService()
