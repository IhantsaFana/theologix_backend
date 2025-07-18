# Theologix Backend

Backend Django REST API pour la plateforme ludopédagogique biblique Theologix.

## 🎯 Vue d'ensemble

API stateless optimisée pour la génération de contenu éducatif biblique via LLM (Large Language Models). Conçue pour supporter une architecture semi-offline avec Flutter.

### Fonctionnalités principales
- Génération dynamique de 6 types de jeux bibliques
- Support multi-LLM (OpenRouter, Gemini) avec fallback
- Architecture stateless (pas de stockage utilisateur)
- Rate limiting et sécurisation des API
- Validation stricte des paramètres
- Logging complet des opérations

## 🚀 Installation rapide

```bash
# Cloner et configurer
cd backend
cp .env.example .env
# Éditer .env avec vos clés API

# Installer et démarrer
chmod +x start.sh
./start.sh
```

## 📋 Configuration

### Variables d'environnement (.env)
```bash
SECRET_KEY=your-django-secret-key
DEBUG=True
OPENROUTER_API_KEY=your-openrouter-key  # Requis
GEMINI_API_KEY=your-gemini-key          # Requis
ALLOWED_HOSTS=localhost,127.0.0.1,10.0.2.2
```

### Dépendances
- Django 5.2.4 + DRF
- httpx (requêtes async LLM)
- python-decouple (config)
- django-cors-headers (Flutter)

## 🎮 Types de jeux supportés

1. **Quiz** - Questions à choix multiples
2. **Wordgame** - Jeux de mots, mots cachés
3. **Puzzle** - Puzzles logiques/visuels
4. **Story** - Histoires interactives
5. **Treasure** - Chasses au trésor
6. **Memory** - Jeux de mémoire

## 🔗 Endpoints API

### Génération de structure
```
GET /api/bulk_generate/?levels=10&age=8
```

### Contenu d'un niveau
```
GET /api/generate_level_content/?level=1&age=8
```

### Génération complète
```
GET /api/bulk_generate_with_content/?levels=5&age=8
```

## 🏗️ Architecture

```
Frontend Flutter (SQLite local)
        ↕ HTTP
Backend Django (Stateless)
        ↕ API
LLM Services (OpenRouter/Gemini)
```

### Flux de données
1. **Initialisation** : Flutter → Django → LLM → Contenu massif
2. **Stockage** : Tout en SQLite local Flutter
3. **Gameplay** : 100% offline depuis cache local

## 🔒 Sécurité

- ✅ Clés API externalisées
- ✅ CORS configuré pour Flutter
- ✅ Rate limiting (100 req/h)
- ✅ Validation stricte des entrées
- ✅ Pas de stockage données utilisateur
- ✅ Logging sécurisé

## 🧪 Tests

```bash
python manage.py test api
```

Tests couvrent :
- Validation des paramètres
- Configuration LLM
- Rate limiting
- Gestion d'erreurs

## 📊 Monitoring

Logs dans `logs/theologix.log` :
- Succès/échecs génération LLM
- Performance des requêtes
- Erreurs de validation

## 🚀 Déploiement

### Développement
```bash
python manage.py runserver
```

### Production
```bash
export DJANGO_SETTINGS_MODULE=theologix_backend.settings_prod
gunicorn theologix_backend.wsgi:application
```

## 📖 Documentation complète

Voir [API_DOCUMENTATION.md](API_DOCUMENTATION.md) pour :
- Détails des endpoints
- Exemples de réponses
- Gestion d'erreurs
- Optimisations Flutter

## 🎯 Roadmap

- [ ] Cache Redis pour optimisation
- [ ] Webhooks pour sync Flutter
- [ ] Métriques de performance
- [ ] Support multilingue
- [ ] API versioning

---

## 📋 Spécifications originales

### Description Projet
Plateforme ludopédagogique biblique, multi-niveaux, fonctionnant en mode semi-offline, via une architecture Flutter (front-end cross-platform) et Django (back-end RESTful). Les contenus ludiques sont générés dynamiquement par des modèles de langage avancés (LLM) accessibles sur des API tierces (Gemini, OpenRouter, etc.), puis mis en cache local grâce à la persistance Flutter pour garantir la jouabilité hors connexion.

### Critères d'acceptation
- **ac1** : Onboarding simple (prénom + âge uniquement)
- **ac2** : Session locale avec adaptation difficulté
- **ac3** : Génération LLM complète niveau 1-10 en cache
- **ac4** : Déblocage séquentiel des niveaux
- **ac5** : Validation complète niveau pour débloquer suivant
- **ac6** : Fonctionnement offline complet
- **ac7** : Dashboard gamification (scores, badges)
- **ac8** : Architecture extensible pour fonctionnalités connectées