#!/bin/bash

# Script de démarrage pour Theologix Backend
echo "🚀 Démarrage de Theologix Backend..."

# Vérification de l'environnement virtuel
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Attention: Aucun environnement virtuel détecté"
    echo "   Recommandé: source venv/bin/activate"
fi

# Vérification du fichier .env
if [ ! -f .env ]; then
    echo "📝 Création du fichier .env depuis .env.example..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Configurez vos clés API dans le fichier .env"
    echo "   - OPENROUTER_API_KEY"
    echo "   - GEMINI_API_KEY"
fi

# Installation des dépendances
echo "📦 Installation des dépendances..."
pip install -r requirements.txt

# Migrations Django
echo "🗄️  Application des migrations..."
python manage.py migrate

# Création du dossier logs
mkdir -p logs

# Tests rapides
echo "🧪 Exécution des tests..."
python manage.py test api --verbosity=1

# Démarrage du serveur
echo "🌐 Démarrage du serveur Django..."
echo "   API disponible sur: http://127.0.0.1:8000/api/"
echo "   Documentation: http://127.0.0.1:8000/admin/"
echo ""
echo "📋 Endpoints disponibles:"
echo "   GET /api/bulk_generate/?levels=10&age=8"
echo "   GET /api/generate_level_content/?level=1&age=8"
echo "   GET /api/bulk_generate_with_content/?levels=5&age=8"
echo ""

python manage.py runserver