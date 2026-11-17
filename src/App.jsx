import { useEffect, useMemo, useRef, useState } from "react";
import { getRandomRecipe, getRecipe, getRecipes, getRecommendations, recognizeImage } from "./api";

const savedKey = "smartrecipe-saved";

function useSavedRecipes() {
  const [saved, setSaved] = useState(() => JSON.parse(localStorage.getItem(savedKey) || "[]"));
  const update = (next) => {
    setSaved(next);
    localStorage.setItem(savedKey, JSON.stringify(next));
  };
  return {
    saved,
    toggle: (recipe) =>
      update(saved.some((item) => item.id === recipe.id)
        ? saved.filter((item) => item.id !== recipe.id)
        : [...saved, recipe]),
    isSaved: (recipe) => saved.some((item) => item.id === recipe.id),
  };
}

function App() {
  const [page, setPage] = useState("home");
  const [recipes, setRecipes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState("");
  const saved = useSavedRecipes();

  useEffect(() => {
    getRecipes().then(setRecipes).catch((error) => setNotice(error.message));
  }, []);

  const openRecipe = async (dishKey, variant = "authentic") => {
    try {
      setSelected(await getRecipe(dishKey, variant));
      setPage("recipe");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const randomize = async () => {
    try {
      setSelected(await getRandomRecipe());
      setPage("recipe");
    } catch (error) {
      setNotice(error.message);
    }
  };

  return (
    <div className="app-shell">
      <header className="site-header">
        <button className="brand" onClick={() => setPage("home")} aria-label="SmartRecipe home">
          <span className="brand-mark">SR</span>
          <span>Smart<span className="brand-accent">Recipe</span></span>
        </button>
        <nav className="desktop-nav" aria-label="Primary navigation">
          <button className={page === "home" ? "active" : ""} onClick={() => setPage("home")}>Home</button>
          <button className={page === "discover" ? "active" : ""} onClick={() => setPage("discover")}>Discover</button>
          <button className={page === "ingredients" ? "active" : ""} onClick={() => setPage("ingredients")}>Use ingredients</button>
          <button className={page === "saved" ? "active" : ""} onClick={() => setPage("saved")}>Saved <span className="count">{saved.saved.length}</span></button>
        </nav>
        <button className="outline-button" onClick={() => setPage("recognize")}>Identify a dish</button>
      </header>

      {notice && <div className="notice" role="alert">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div>}

      {page === "home" && <Home onStart={() => setPage("recognize")} onIngredients={() => setPage("ingredients")} onRandom={randomize} />}
      {page === "recognize" && <Recognition onResult={(result) => openRecipe(result.dish_key)} onError={setNotice} />}
      {page === "discover" && <Discover recipes={recipes} onOpen={openRecipe} onRandom={randomize} />}
      {page === "ingredients" && <Ingredients onOpen={openRecipe} onError={setNotice} />}
      {page === "saved" && <Saved recipes={saved.saved} onOpen={openRecipe} onRemove={saved.toggle} />}
      {page === "recipe" && selected && <RecipeDetail recipe={selected} onOpen={openRecipe} saved={saved} onBack={() => setPage("discover")} />}

      <footer><span>SmartRecipe</span><span>Regional Indian recipes, built for everyday cooking.</span><button onClick={() => setPage("home")}>Privacy and terms</button></footer>
    </div>
  );
}

function Home({ onStart, onIngredients, onRandom }) {
  return <main>
    <section className="hero">
      <div className="eyebrow">A practical guide to Indian food</div>
      <h1>Know the dish.<br /><em>Make it your own.</em></h1>
      <p>Identify a dish from a photo, find recipes for what you already have, or choose something unexpected for dinner.</p>
      <div className="hero-actions"><button className="primary-button" onClick={onStart}>Identify a dish <span>→</span></button><button className="text-button" onClick={onRandom}>Let God Decide <span>↗</span></button></div>
      <div className="hero-note"><span className="signal">●</span> Two-model recognition workflow <span className="divider">/</span> Recipes stored locally in SQLite</div>
    </section>
    <section className="feature-strip">
      <Feature number="01" title="From a photo" text="Upload a food image and compare predictions from a custom CNN and ResNet50." action="Try recognition" onClick={onStart} />
      <Feature number="02" title="From your pantry" text="Enter ingredients you have and find dishes that make practical use of them." action="Find recipes" onClick={onIngredients} />
      <Feature number="03" title="By instinct" text="Let a random regional dish decide what you cook next, without the endless scrolling." action="Surprise me" onClick={onRandom} />
    </section>
  </main>;
}

function Feature({ number, title, text, action, onClick }) {
  return <article className="feature-card"><span className="feature-number">{number}</span><h2>{title}</h2><p>{text}</p><button onClick={onClick}>{action} <span>→</span></button></article>;
}

function Recognition({ onResult, onError }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);
  const choose = (next) => {
    const selected = next?.[0];
    if (!selected) return;
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
  };
  const submit = async () => {
    if (!file) return;
    setBusy(true);
    try { onResult(await recognizeImage(file)); } catch (error) { onError(error.message); } finally { setBusy(false); }
  };
  return <main className="page"><div className="page-heading"><div className="eyebrow">Image recognition</div><h1>What’s on your plate?</h1><p>Upload a clear photo. SmartRecipe sends the same prepared image to both models and only accepts a result above the confidence threshold.</p></div>
    <div className="recognition-layout">
      <button className="upload-card" onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); choose(event.dataTransfer.files); }}>
        {preview ? <img src={preview} alt="Selected food" /> : <><span className="upload-symbol">+</span><strong>Drop an image here</strong><span>or choose a JPEG, PNG, or WebP file</span></>}
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => choose(event.target.files)} />
      </button>
      <aside className="process-card"><span className="eyebrow">Before you begin</span><h2>A careful answer beats a confident guess.</h2><p>Predictions are compared only after both models use compatible preprocessing. Uncertain results are sent back for another photo instead of being presented as fact.</p><div className="model-list"><span>Custom CNN <b>01</b></span><span>ResNet50 <b>02</b></span><span>Threshold <b>70%</b></span></div><button className="primary-button full" disabled={!file || busy} onClick={submit}>{busy ? "Analysing..." : "Identify this dish →"}</button></aside>
    </div>
  </main>;
}

function Discover({ recipes, onOpen, onRandom }) {
  return <main className="page"><div className="page-heading compact"><div><div className="eyebrow">Recipe library</div><h1>Start with a dish.</h1></div><button className="outline-button" onClick={onRandom}>Let God Decide ↗</button></div><div className="recipe-grid">{recipes.map((item) => <RecipeCard key={item.id} recipe={item} onOpen={onOpen} />)}</div></main>;
}

function RecipeCard({ recipe, onOpen }) {
  return <article className="recipe-card" onClick={() => onOpen(recipe.dish_key)}><div className={`dish-color color-${recipe.dish_key}`}><span>{recipe.name.slice(0, 2).toUpperCase()}</span></div><div className="recipe-card-content"><div className="card-meta">{recipe.region}<span>{recipe.health_score}/100</span></div><h2>{recipe.name}</h2><p>{recipe.description}</p><button>View recipe →</button></div></article>;
}

function Ingredients({ onOpen, onError }) {
  const [value, setValue] = useState("");
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    const items = value.split(",").map((item) => item.trim()).filter(Boolean);
    if (!items.length) return;
    setBusy(true);
    try { setResults(await getRecommendations(items)); } catch (error) { onError(error.message); } finally { setBusy(false); }
  };
  return <main className="page"><div className="page-heading"><div className="eyebrow">Ingredient search</div><h1>What do you have at home?</h1><p>Separate ingredients with commas. We’ll show dishes with a useful match, not a generic list.</p></div><form className="ingredient-form" onSubmit={submit}><input value={value} onChange={(event) => setValue(event.target.value)} placeholder="potato, onion, tomato" /><button className="primary-button" disabled={busy}>{busy ? "Searching..." : "Find recipes →"}</button></form>{results.length > 0 && <div className="recipe-grid">{results.map((item) => <RecipeCard key={item.id} recipe={item} onOpen={onOpen} />)}</div>}{!busy && value && !results.length && <div className="empty-state">No matching dishes yet. Try adding one more ingredient.</div>}</main>;
}

function Saved({ recipes, onOpen, onRemove }) {
  return <main className="page"><div className="page-heading compact"><div><div className="eyebrow">Your collection</div><h1>Saved recipes.</h1></div></div>{recipes.length ? <div className="recipe-grid">{recipes.map((item) => <div key={item.id} className="saved-wrap"><RecipeCard recipe={item} onOpen={onOpen} /><button className="remove-button" onClick={() => onRemove(item)}>Remove from saved</button></div>)}</div> : <div className="empty-state"><h2>Nothing saved yet.</h2><p>Save a recipe from its detail page and it will stay here in this browser.</p></div>}</main>;
}

function RecipeDetail({ recipe, onOpen, saved, onBack }) {
  const [copyState, setCopyState] = useState("");
  const copy = async (text, label) => { await navigator.clipboard.writeText(text); setCopyState(label); setTimeout(() => setCopyState(""), 1600); };
  return <main className="page recipe-detail"><button className="back-button" onClick={onBack}>← Back to recipes</button><div className="detail-heading"><div><div className="eyebrow">{recipe.region} / {recipe.variant}</div><h1>{recipe.name}</h1><p>{recipe.description}</p></div><button className={saved.isSaved(recipe) ? "save-button saved" : "save-button"} onClick={() => saved.toggle(recipe)}>{saved.isSaved(recipe) ? "Saved" : "Save recipe"}</button></div><div className="stats-row"><span><b>{recipe.prep_minutes + recipe.cook_minutes} min</b> total</span><span><b>{recipe.servings}</b> servings</span><span><b>{recipe.health_score}</b> health score</span><span><b>{recipe.calories}</b> kcal / serving</span></div><div className="variant-tabs">{["authentic", "spicy", "healthy"].map((variant) => <button key={variant} className={recipe.variant === variant ? "selected" : ""} onClick={() => onOpen(recipe.dish_key, variant)}>{variant}</button>)}</div><div className="detail-columns"><section className="detail-box"><div className="box-heading"><h2>Ingredients</h2><button onClick={() => copy(recipe.ingredients.join("\n"), "ingredients")}>{copyState === "ingredients" ? "Copied" : "Copy"}</button></div><ul>{recipe.ingredients.map((item) => <li key={item}>{item}</li>)}</ul></section><section className="detail-box"><div className="box-heading"><h2>Method</h2><button onClick={() => copy(recipe.steps.map((item, index) => `${index + 1}. ${item}`).join("\n"), "method")}>{copyState === "method" ? "Copied" : "Copy"}</button></div><ol>{recipe.steps.map((item) => <li key={item}>{item}</li>)}</ol></section></div></main>;
}

export default App;
