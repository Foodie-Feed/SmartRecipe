from pathlib import Path
import sqlite3
from typing import Iterator

DATABASE_PATH = Path(__file__).resolve().parents[1] / "smartrecipe.db"


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialize() -> None:
    with connection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dish_key TEXT NOT NULL,
                name TEXT NOT NULL,
                region TEXT NOT NULL,
                variant TEXT NOT NULL,
                description TEXT NOT NULL,
                prep_minutes INTEGER NOT NULL,
                cook_minutes INTEGER NOT NULL,
                servings INTEGER NOT NULL,
                health_score INTEGER NOT NULL,
                calories INTEGER NOT NULL,
                protein REAL NOT NULL,
                carbohydrates REAL NOT NULL,
                fat REAL NOT NULL,
                ingredients TEXT NOT NULL,
                steps TEXT NOT NULL,
                UNIQUE(dish_key, variant)
            )
            """
        )
        db.commit()


def rows(query: str, parameters: tuple = ()) -> list[sqlite3.Row]:
    with connection() as db:
        return list(db.execute(query, parameters).fetchall())
