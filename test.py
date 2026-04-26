from sentence_transformers import SentenceTransformer, util

# --- 1. Chargement du modèle multilingue ---
# Ce modèle est optimisé pour comprendre que des phrases dans des langues 
# différentes peuvent avoir le même sens.
print("Chargement du modèle (cela peut prendre quelques secondes la première fois)...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# --- 2. Base de données de test (Résumés multilingues) ---
resumes_films = [
    "Le Parrain : Le patriarche vieillissant d'une dynastie de la mafia new-yorkaise transfère le contrôle de son empire clandestin à son fils réticent.", # Français
    "The Matrix: A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.", # Anglais
    "El Señor de los Anillos: Un hobbit dócil de la Comarca y ocho compañeros emprenden un viaje para destruir el poderoso Anillo Único y salvar la Tierra Media.", # Espagnol
    "Inception : Un voleur qui s'approprie les secrets de l'inconscient pendant l'état de rêve se voit offrir la chance d'effacer son casier criminel." # Français
]

# --- 3. Création des Embeddings ---
print("\nGénération des embeddings pour les résumés...")
embeddings_base = model.encode(resumes_films)
print(f"Dimension des vecteurs générés : {embeddings_base.shape[1]} dimensions.")

# --- 4. Test avec une requête ---
# On fait une recherche en français pour voir si le modèle trouve le bon film, 
# même si le résumé original est en anglais ou en espagnol.
requete_utilisateur = "Un pirate informatique qui découvre que son monde est virtuel."
print(f"\nRequête de recherche : '{requete_utilisateur}'")

# On vectorise la requête
embedding_requete = model.encode(requete_utilisateur)

# --- 5. Calcul de la similarité ---
# On calcule la similarité cosinus entre la requête et tous les résumés
similarites = util.cos_sim(embedding_requete, embeddings_base)[0]

# --- 6. Affichage des résultats triés ---
resultats = []
for i in range(len(resumes_films)):
    resultats.append({
        "score": similarites[i].item(),
        "texte": resumes_films[i]
    })

# Tri par score de pertinence décroissant
resultats_tries = sorted(resultats, key=lambda x: x["score"], reverse=True)

print("\n--- RÉSULTATS DE LA RECHERCHE ---")
for res in resultats_tries:
    # On affiche le score en pourcentage et les 75 premiers caractères du résumé
    print(f"Pertinence : {res['score']*100:.1f}% | Résumé : {res['texte'][:75]}...")