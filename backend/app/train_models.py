from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from torch import nn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms

from .models import IMAGE_SIZE, LABELS

SEED = 42
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


class CustomCNN(nn.Module):
    def __init__(self, class_count: int) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.25),
            nn.Linear(128, class_count),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(inputs))


def _dataset(data_dir: Path, augment: bool) -> datasets.ImageFolder:
    operations = [transforms.Resize((IMAGE_SIZE, IMAGE_SIZE))]
    if augment:
        operations.append(transforms.RandomHorizontalFlip())
    operations.extend(
        [
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]
    )
    transform = transforms.Compose(
        operations
    )
    dataset = datasets.ImageFolder(data_dir, transform=transform)
    if dataset.classes != LABELS:
        raise ValueError(f"Dataset classes {dataset.classes} do not match shared labels {LABELS}.")
    return dataset


def _train(network: nn.Module, loader: DataLoader, epochs: int, device: torch.device) -> nn.Module:
    network.to(device)
    optimizer = torch.optim.Adam(network.parameters(), lr=1e-3)
    loss_function = nn.CrossEntropyLoss()
    network.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = loss_function(network(images), labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"epoch {epoch + 1}/{epochs}: loss={total_loss / max(len(loader), 1):.4f}")
    return network.cpu().eval()


def _evaluate(network: nn.Module, loader: DataLoader, device: torch.device) -> dict:
    network.to(device).eval()
    actual: list[int] = []
    predicted: list[int] = []
    with torch.inference_mode():
        for images, labels in loader:
            outputs = network(images.to(device))
            actual.extend(labels.tolist())
            predicted.extend(torch.argmax(outputs, dim=1).cpu().tolist())
    network.cpu()
    matrix = confusion_matrix(actual, predicted, labels=list(range(len(LABELS))))
    report = classification_report(
        actual,
        predicted,
        labels=list(range(len(LABELS))),
        target_names=LABELS,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": accuracy_score(actual, predicted),
        "macro_precision": report["macro avg"]["precision"],
        "macro_recall": report["macro avg"]["recall"],
        "macro_f1": report["macro avg"]["f1-score"],
        "per_class": {
            label: {
                "precision": report[label]["precision"],
                "recall": report[label]["recall"],
                "f1": report[label]["f1-score"],
                "support": report[label]["support"],
            }
            for label in LABELS
        },
        "confusion_matrix": matrix.tolist(),
    }


def _save(network: nn.Module, path: Path, architecture: str, metrics: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "architecture": architecture,
            "state_dict": network.state_dict(),
            "labels": LABELS,
            "image_size": IMAGE_SIZE,
            "temperature": 1.0,
            "validation_metrics": metrics,
        },
        path,
    )


def train(data_dir: Path, output_dir: Path, epochs: int, batch_size: int) -> None:
    random.seed(SEED)
    torch.manual_seed(SEED)
    training_dataset = _dataset(data_dir, augment=True)
    validation_dataset = _dataset(data_dir, augment=False)
    validation_size = max(1, int(len(training_dataset) * 0.2))
    indices = torch.randperm(len(training_dataset), generator=torch.Generator().manual_seed(SEED)).tolist()
    validation_indices = indices[:validation_size]
    training_indices = indices[validation_size:]
    training = Subset(training_dataset, training_indices)
    validation = Subset(validation_dataset, validation_indices)
    loader = DataLoader(training, batch_size=batch_size, shuffle=True, num_workers=0)
    validation_loader = DataLoader(validation, batch_size=batch_size, shuffle=False, num_workers=0)
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"training device: {device}")

    custom_cnn = _train(CustomCNN(len(LABELS)), loader, epochs, device)
    custom_metrics = _evaluate(custom_cnn, validation_loader, device)
    _save(custom_cnn, output_dir / "custom_cnn.pt", "custom_cnn", custom_metrics)
    print(json.dumps({"custom_cnn": custom_metrics}, indent=2))

    resnet = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    for parameter in resnet.parameters():
        parameter.requires_grad = False
    resnet.fc = nn.Linear(resnet.fc.in_features, len(LABELS))
    resnet = _train(resnet, loader, epochs, device)
    resnet_metrics = _evaluate(resnet, validation_loader, device)
    _save(resnet, output_dir / "resnet50.pt", "resnet50", resnet_metrics)
    metrics = {"custom_cnn": custom_metrics, "resnet50": resnet_metrics}
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps({"resnet50": resnet_metrics}, indent=2))
    (output_dir / "labels.json").write_text(json.dumps(LABELS, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and export SmartRecipe image classifiers.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("weights"))
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    train(args.data_dir, args.output_dir, args.epochs, args.batch_size)


if __name__ == "__main__":
    main()
