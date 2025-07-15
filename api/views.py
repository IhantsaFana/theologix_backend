
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import httpx
import asyncio
import random
import itertools

# API endpoints et clés pour chaque LLM
LLM_CONFIGS = [
    {
        'name': 'openrouter',
        'url': 'https://openrouter.ai/api/v1/chat/completions',
        'headers': {'Authorization': 'Bearer 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'},
        'model': 'mistral:free',
        'prompt_key': 'messages',
        'body_builder': lambda prompt: {"model": "mistral:free", "messages": [{"role": "user", "content": prompt}]},
        'extractor': lambda resp: resp.get('choices', [{}])[0].get('message', {}).get('content', None),
    },
    {
        'name': 'gemini',
        'url': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=AIzaSyAdhq0m5qD0FGNIJQx56ApoS8wkDQelLYU',
        'headers': {},
        'model': 'gemini-2.0-flash',
        'prompt_key': 'contents',
        'body_builder': lambda prompt: {"contents": [{"parts": [{"text": prompt}]}]},
        'extractor': lambda resp: resp.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', None),
    },
]

GAME_TYPES = ['quiz', 'wordgame', 'puzzle', 'story', 'treasure', 'memory']

async def fetch_llm_content(game_type, level, age, difficulty, index=1, total=1, quiz_questions=None):
    # Ajout d'une consigne spéciale pour les quiz
    if game_type == 'quiz' and quiz_questions:
        prompt = (
            f"Génère un quiz biblique de type QCM avec {quiz_questions} questions pour le niveau {level}, "
            f"difficulté: {difficulty}, âge utilisateur: {age}, jeu n°{index} sur {total}. "
            f"Le quiz doit être cohérent, adapté à l'âge, original, et donner les réponses à la fin."
        )
    else:
        prompt = (
            f"Génère un contenu biblique de type {game_type} pour le niveau {level}, "
            f"difficulté: {difficulty}, âge utilisateur: {age}, "
            f"jeu n°{index} sur {total} pour ce type. "
            f"Le contenu doit être cohérent, adapté à l'âge, et original."
        )
    for config in LLM_CONFIGS:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                body = config['body_builder'](prompt)
                response = await client.post(config['url'], json=body, headers=config['headers'])
                if response.status_code == 200:
                    data = response.json() if callable(getattr(response, 'json', None)) else response.json
                    content = config['extractor'](data)
                    # On ne retourne que si le contenu est non vide et ne ressemble pas à un fallback
                    if content and not content.strip().startswith('[Fallback'):
                        return content
        except Exception:
            continue
    return None  # Ne retourne rien si fallback

class BulkGenerateView(APIView):
    def get(self, request):
        try:
            max_level = int(request.query_params.get('levels', 10))
        except (TypeError, ValueError):
            return Response({'error': 'Paramètre levels invalide'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            age = int(request.query_params.get('age', 8))
        except (TypeError, ValueError):
            age = 8

        async def ask_llm_for_full_structure():
            prompt = (
                "Tu es un game designer expert en jeux éducatifs bibliques pour enfants. "
                f"Voici la liste des types de jeux disponibles : {', '.join(GAME_TYPES)}. "
                f"L'utilisateur a {age} ans. Génère une progression complète de {max_level} niveaux, "
                "où chaque niveau contient une alternance variée et logique de jeux, avec difficulté, nombre de jeux, nombre de questions pour les quiz, etc. "
                "Adapte la structure à l'âge, propose des niveaux équilibrés, ludiques et progressifs. "
                "Pour chaque niveau, donne un JSON structuré : level, difficulty, games (liste ordonnée d'objets avec type, consigne, nombre de questions si quiz, etc.). "
                "N'invente pas de nouveaux types de jeux. Ne mets pas de fallback. Ne donne que la structure, pas le contenu des jeux."
            )
            import re, json
            for config in LLM_CONFIGS:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        body = config['body_builder'](prompt)
                        response = await client.post(config['url'], json=body, headers=config['headers'])
                        if response.status_code == 200:
                            data = response.json() if callable(getattr(response, 'json', None)) else response.json
                            content = config['extractor'](data)
                            if content:
                                # Extraction robuste du JSON
                                # 1. Chercher un bloc JSON dans ``` ou ```json
                                match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", content)
                                if match:
                                    content = match.group(1)
                                # 2. Sinon, chercher le premier [ et le dernier ]
                                if not content.strip().startswith('['):
                                    start = content.find('[')
                                    end = content.rfind(']')
                                    if start != -1 and end != -1:
                                        content = content[start:end+1]
                                # 3. Essayer de parser
                                try:
                                    return json.loads(content)
                                except Exception:
                                    continue
                except Exception:
                    continue
            return []

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        structure = loop.run_until_complete(ask_llm_for_full_structure())
        loop.close()
        return Response(structure)

class GenerateLevelContentView(APIView):
    def get(self, request):
        try:
            level = int(request.query_params.get('level', 1))
        except (TypeError, ValueError):
            return Response({'error': 'Paramètre level invalide'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            age = int(request.query_params.get('age', 8))
        except (TypeError, ValueError):
            age = 8

        def get_difficulty(level, age):
            if level <= 2:
                return 'facile' if age < 10 else 'normal'
            elif level <= 5:
                return 'normal' if age < 12 else 'difficile'
            else:
                return 'difficile'

        def random_game_sequence(level):
            sequence = []
            total_games = random.randint(5 + level, 8 + level * 2)
            if level == 1:
                sequence += ['quiz'] * random.randint(2, 3)
                sequence += ['wordgame'] * random.randint(2, 3)
            elif level == 2:
                sequence += ['quiz'] * random.randint(2, 4)
                sequence += ['wordgame'] * random.randint(2, 4)
            else:
                for _ in range(total_games):
                    sequence.append(random.choice(GAME_TYPES))
            random.shuffle(sequence)
            for i in range(1, len(sequence)):
                if sequence[i] == sequence[i-1]:
                    alt = [g for g in GAME_TYPES if g != sequence[i]]
                    if alt:
                        sequence[i] = random.choice(alt)
            return sequence

        difficulty = get_difficulty(level, age)
        sequence = random_game_sequence(level)
        quiz_sizes = [random.randint(3, 10) for _ in sequence if _ == 'quiz']
        quiz_idx = 0

        async def generate_level():
            tasks = []
            for idx, game in enumerate(sequence):
                if game == 'quiz':
                    qsize = quiz_sizes[quiz_idx]
                    quiz_idx += 1
                    tasks.append(fetch_llm_content(game, level, age, difficulty, idx+1, len(sequence), quiz_questions=qsize))
                else:
                    tasks.append(fetch_llm_content(game, level, age, difficulty, idx+1, len(sequence)))
            results = await asyncio.gather(*tasks)
            filtered = [(g, r) for g, r in zip(sequence, results) if r]
            games = {}
            for g, r in filtered:
                games.setdefault(g, []).append(r)
            return games

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        games = loop.run_until_complete(generate_level())
        loop.close()
        return Response({'level': level, 'difficulty': difficulty, 'games': games})

class BulkGenerateWithContentView(APIView):
    def get(self, request):
        try:
            max_level = int(request.query_params.get('levels', 10))
        except (TypeError, ValueError):
            return Response({'error': 'Paramètre levels invalide'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            age = int(request.query_params.get('age', 8))
        except (TypeError, ValueError):
            age = 8

        import re, json

        async def ask_llm_for_full_structure():
            prompt = (
                "Tu es un game designer expert en jeux éducatifs bibliques pour enfants. "
                f"Voici la liste des types de jeux disponibles : {', '.join(GAME_TYPES)}. "
                f"L'utilisateur a {age} ans. Génère une progression complète de {max_level} niveaux, "
                "où chaque niveau contient une alternance variée et logique de jeux, avec difficulté, nombre de jeux, nombre de questions pour les quiz, etc. "
                "Adapte la structure à l'âge, propose des niveaux équilibrés, ludiques et progressifs. "
                "Pour chaque niveau, donne un JSON structuré : level, difficulty, games (liste ordonnée d'objets avec type, consigne, nombre de questions si quiz, etc.). "
                "N'invente pas de nouveaux types de jeux. Ne mets pas de fallback. Ne donne que la structure, pas le contenu des jeux."
            )
            for config in LLM_CONFIGS:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        body = config['body_builder'](prompt)
                        response = await client.post(config['url'], json=body, headers=config['headers'])
                        if response.status_code == 200:
                            data = response.json() if callable(getattr(response, 'json', None)) else response.json
                            content = config['extractor'](data)
                            if content:
                                match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", content)
                                if match:
                                    content = match.group(1)
                                if not content.strip().startswith('['):
                                    start = content.find('[')
                                    end = content.rfind(']')
                                    if start != -1 and end != -1:
                                        content = content[start:end+1]
                                try:
                                    return json.loads(content)
                                except Exception:
                                    continue
                except Exception:
                    continue
            return []

        async def fetch_content_for_game(game, level, age, difficulty):
            # Compose un prompt contextuel pour chaque jeu
            prompt = f"Tu es un assistant IA pour un jeu éducatif biblique. Génère le contenu complet pour ce jeu :\n"
            prompt += f"- Type de jeu : {game.get('type')}\n"
            if 'instruction' in game:
                prompt += f"- Consigne : {game['instruction']}\n"
            if 'consigne' in game:
                prompt += f"- Consigne : {game['consigne']}\n"
            if 'number_of_questions' in game:
                prompt += f"- Nombre de questions : {game['number_of_questions']}\n"
            if 'nombre_de_questions' in game:
                prompt += f"- Nombre de questions : {game['nombre_de_questions']}\n"
            if 'word_length' in game:
                prompt += f"- Longueur des mots : {game['word_length']}\n"
            if 'nombre_de_mots' in game:
                prompt += f"- Nombre de mots : {game['nombre_de_mots']}\n"
            if 'nombre_de_paires' in game:
                prompt += f"- Nombre de paires : {game['nombre_de_paires']}\n"
            if 'nombre_de_pièces' in game:
                prompt += f"- Nombre de pièces : {game['nombre_de_pièces']}\n"
            if 'nombre_d_indices' in game:
                prompt += f"- Nombre d'indices : {game['nombre_d_indices']}\n"
            prompt += f"- Niveau : {level}\n- Difficulté : {difficulty}\n- Âge utilisateur : {age}\n"
            prompt += "Le contenu doit être original, adapté à l'âge, cohérent, et prêt à être utilisé dans le jeu. Réponds uniquement par le contenu, sans explication."
            for config in LLM_CONFIGS:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        body = config['body_builder'](prompt)
                        response = await client.post(config['url'], json=body, headers=config['headers'])
                        if response.status_code == 200:
                            data = response.json() if callable(getattr(response, 'json', None)) else response.json
                            content = config['extractor'](data)
                            if content and not content.strip().startswith('[Fallback'):
                                return content.strip()
                except Exception:
                    continue
            return None

        async def generate_full():
            structure = await ask_llm_for_full_structure()
            # structure = [ {level, difficulty, games: [ ... ]}, ... ]
            for level_obj in structure:
                level = level_obj.get('level')
                difficulty = level_obj.get('difficulty')
                games = level_obj.get('games', [])
                # Pour compatibilité, accepter liste d'objets ou liste de dicts
                for game in games:
                    content = await fetch_content_for_game(game, level, age, difficulty)
                    game['content'] = content
            return structure

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_full())
        loop.close()
        return Response(result)
