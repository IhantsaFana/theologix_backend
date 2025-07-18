# API Documentation - Theologix Backend

## Vue d'ensemble

API REST pour la génération de contenu ludopédagogique biblique via LLM.
Architecture stateless optimisée pour applications semi-offline.

## Configuration

### Variables d'environnement requises

```bash
# Copier .env.example vers .env et configurer :
SECRET_KEY=your-django-secret-key
DEBUG=True
OPENROUTER_API_KEY=your-openrouter-key
GEMINI_API_KEY=your-gemini-key
ALLOWED_HOSTS=localhost,127.0.0.1,10.0.2.2
```

### Installation

```bash
cd backend
pip install -r requirementnts.txt
python manage.py migrate
python manage.py runserver
```

## Endpoints

### 1. Génération de structure de niveaux

**GET** `/api/bulk_generate/`

Génère la structure complète des niveaux sans contenu.

**Paramètres :**
- `levels` (int, optionnel) : Nombre de niveaux (1-15, défaut: 10)
- `age` (int, optionnel) : Âge utilisateur (3-18, défaut: 8)

**Réponse :**
```json
[
  {
    "level": 1,
    "difficulty": "facile",
    "games": [
      {
        "type": "quiz",
        "consigne": "Quiz sur les personnages bibliques",
        "nombre_de_questions": 5
      },
      {
        "type": "wordgame",
        "consigne": "Trouve les mots cachés"
      }
    ]
  }
]
```

### 2. Génération de contenu pour un niveau

**GET** `/api/generate_level_content/`

Génère le contenu complet pour un niveau spécifique.

**Paramètres :**
- `level` (int, requis) : Numéro du niveau (1-20)
- `age` (int, optionnel) : Âge utilisateur (3-18, défaut: 8)
- `game_types` (list, optionnel) : Types de jeux spécifiques

**Réponse :**
```json
{
  "level": 1,
  "difficulty": "facile",
  "games": {
    "quiz": [
      "Quiz: Qui a construit l'arche?\nA) Noé B) Moïse C) David D) Abraham\nRéponse: A"
    ],
    "wordgame": [
      "Trouve ces mots bibliques: NOAH, DAVID, MOSES..."
    ]
  }
}
```

### 3. Génération complète avec contenu

**GET** `/api/bulk_generate_with_content/`

Génère structure ET contenu pour tous les niveaux (opération lourde).

**Paramètres :**
- `levels` (int, optionnel) : Nombre de niveaux (1-15, défaut: 10)
- `age` (int, optionnel) : Âge utilisateur (3-18, défaut: 8)

**Réponse :**
```json
[
  {
    "level": 1,
    "difficulty": "facile",
    "games": [
      {
        "type": "quiz",
        "consigne": "Quiz biblique niveau 1",
        "content": "Contenu généré du quiz..."
      }
    ]
  }
]
```

## Types de jeux supportés

- `quiz` : Questions à choix multiples
- `wordgame` : Jeux de mots, mots cachés
- `puzzle` : Puzzles logiques ou visuels
- `story` : Histoires interactives
- `treasure` : Chasses au trésor
- `memory` : Jeux de mémoire

## Gestion d'erreurs

### Codes de statut
- `200` : Succès
- `400` : Paramètres invalides
- `429` : Trop de requêtes (rate limiting)
- `500` : Erreur serveur

### Validation des paramètres
- `levels` : 1-15 (max 15 pour éviter timeouts)
- `age` : 3-18 ans
- `level` : 1-20
- `game_types` : Liste de types valides uniquement

## Rate Limiting

- 100 requêtes/heure par IP
- Recommandé : cache côté client
- Utilisation optimale : 1 appel initial pour tout le contenu

## Sécurité

- Clés API externalisées
- CORS configuré pour Flutter
- Validation stricte des entrées
- Logging des erreurs
- Pas de stockage de données utilisateur

## Optimisations

### Pour Flutter
1. Appeler `/bulk_generate_with_content/` une seule fois
2. Stocker tout en SQLite local
3. Mode offline complet après initialisation

### Timeouts
- Requêtes LLM : 20-30s max
- Limite jeux par niveau : 8-10 max
- Fallback entre plusieurs LLM

## Monitoring

Logs disponibles dans `logs/theologix.log` :
- Succès/échecs génération LLM
- Erreurs de validation
- Performance des requêtes