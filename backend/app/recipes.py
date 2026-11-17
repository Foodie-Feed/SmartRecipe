import json
import random
from typing import Any

from .database import initialize, rows

DISHES = {
    "burger": ("Burger", "Modern Indian", ["bun", "potato patty", "lettuce", "tomato", "onion"]),
    "butter_naan": ("Butter Naan", "Punjab", ["flour", "yogurt", "butter", "salt", "water"]),
    "chai": ("Chai", "Maharashtra", ["tea leaves", "milk", "water", "sugar", "cardamom"]),
    "chapati": ("Chapati", "Maharashtra", ["whole wheat flour", "water", "salt", "ghee"]),
    "chole_bhature": ("Chole Bhature", "Punjab", ["chickpeas", "flour", "onion", "tomato", "spices"]),
    "dal_makhani": ("Dal Makhani", "Punjab", ["black lentils", "kidney beans", "tomato", "cream", "butter"]),
    "dhokla": ("Dhokla", "Gujarat", ["gram flour", "yogurt", "ginger", "mustard seeds", "lemon"]),
    "fried_rice": ("Fried Rice", "Indo-Chinese", ["rice", "carrot", "beans", "spring onion", "soy sauce"]),
    "idli": ("Idli", "Tamil Nadu", ["rice", "urad dal", "fenugreek", "salt", "water"]),
    "jalebi": ("Jalebi", "North India", ["flour", "yogurt", "sugar", "saffron", "ghee"]),
    "kaathi_rolls": ("Kaathi Rolls", "West Bengal", ["flatbread", "paneer", "onion", "capsicum", "spices"]),
    "kadai_paneer": ("Kadai Paneer", "Punjab", ["paneer", "capsicum", "tomato", "onion", "coriander"]),
    "kulfi": ("Kulfi", "North India", ["milk", "sugar", "cardamom", "pistachio", "saffron"]),
    "masala_dosa": ("Masala Dosa", "Karnataka", ["rice", "urad dal", "potato", "onion", "mustard seeds"]),
    "momos": ("Momos", "Himalayan", ["flour", "cabbage", "carrot", "ginger", "soy sauce"]),
    "paani_puri": ("Paani Puri", "Maharashtra", ["semolina", "potato", "chickpeas", "mint", "tamarind"]),
    "pakode": ("Pakode", "Maharashtra", ["gram flour", "onion", "chilli", "coriander", "oil"]),
    "pav_bhaji": ("Pav Bhaji", "Maharashtra", ["potato", "cauliflower", "peas", "tomato", "pav"]),
    "pizza": ("Pizza", "Modern Indian", ["flour", "tomato", "mozzarella", "onion", "capsicum"]),
    "samosa": ("Samosa", "North India", ["flour", "potato", "peas", "cumin", "oil"]),
}

VARIANT_ADJUSTMENTS = {
    "authentic": ("Traditional preparation with balanced seasoning.", 0, 0, 0, 0),
    "spicy": ("A bolder version with extra chilli and warming spices.", -2, 8, 2, 3),
    "healthy": ("A lighter version with less oil and more whole ingredients.", 10, -70, 2, -6),
}


def _seed() -> None:
    initialize()
    existing = rows("SELECT id FROM recipes LIMIT 1")
    if existing:
        return
    import sqlite3
    from .database import connection

    with connection() as db:
        for dish_key, (name, region, ingredients) in DISHES.items():
            for variant, (description, health_delta, calorie_delta, protein_delta, fat_delta) in VARIANT_ADJUSTMENTS.items():
                db.execute(
                    """
                    INSERT INTO recipes (
                        dish_key, name, region, variant, description, prep_minutes,
                        cook_minutes, servings, health_score, calories, protein,
                        carbohydrates, fat, ingredients, steps
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dish_key, name, region, variant, description, 15, 30, 4,
                        max(1, min(100, 68 + health_delta)),
                        max(50, 360 + calorie_delta), max(1, 12 + protein_delta),
                        42, max(1, 16 + fat_delta),
                        json.dumps([f"{item}, as needed" for item in ingredients]),
                        json.dumps([
                            "Prepare and measure the ingredients.",
                            "Cook the base ingredients until fragrant and tender.",
                            "Add the remaining ingredients and simmer until the flavours come together.",
                            "Taste, adjust seasoning, and serve warm.",
                        ]),
                    ),
                )
        db.commit()


def all_recipes() -> list[dict[str, Any]]:
    _seed()
    return [dict(row) for row in rows("SELECT * FROM recipes WHERE variant = 'authentic' ORDER BY name")]


def recipe(dish_key: str, variant: str = "authentic") -> dict[str, Any] | None:
    _seed()
    found = rows("SELECT * FROM recipes WHERE dish_key = ? AND variant = ?", (dish_key, variant))
    if not found:
        return None
    result = dict(found[0])
    result["ingredients"] = json.loads(result["ingredients"])
    result["steps"] = json.loads(result["steps"])
    return result


def random_recipe() -> dict[str, Any]:
    choices = all_recipes()
    return recipe(random.choice(choices)["dish_key"])  # type: ignore[return-value]


def recommendations(ingredients: list[str]) -> list[dict[str, Any]]:
    _seed()
    normalized = {item.strip().lower() for item in ingredients if item.strip()}
    results = []
    for item in all_recipes():
        dish_ingredients = set(json.loads(item["ingredients"]))
        item["match_count"] = sum(any(needle in haystack for haystack in dish_ingredients) for needle in normalized)
        if item["match_count"]:
            results.append(item)
    return sorted(results, key=lambda item: item["match_count"], reverse=True)

