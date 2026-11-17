const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request(path, options) {
  const response = await fetch(`${API_URL}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "The request could not be completed.");
  return data;
}

export const getRecipes = () => request("/recipes");
export const getRandomRecipe = () => request("/recipes/random");
export const getRecipe = (dishKey, variant) => request(`/recipes/${dishKey}/${variant}`);
export const getRecommendations = (ingredients) =>
  request("/recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingredients }),
  });

export const recognizeImage = (file) => {
  const body = new FormData();
  body.append("file", file);
  return request("/recognize", { method: "POST", body });
};
