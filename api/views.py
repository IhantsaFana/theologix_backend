
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle

import httpx
import asyncio
import random
import logging
import json
import re

from .config import get_llm_configs, GAME_TYPES, get_game_prompt
from .serializers import BulkGenerateSerializer, GenerateLevelContentSerializer

logger = logging.getLogger('api')

async def fetch_llm_content(game_type, level, age, difficulty, index=1, total=1, quiz_questions=None):
    """Génère du contenu via LLM avec gestion d'erreurs et fallback"""
    llm_configs = get_llm_configs()
    
    if not llm_configs:
        logger.error("No LLM configuration available")
        return None
    
    # Utilise les prompts optimisés
    if game_type == 'quiz' and quiz_questions:
        prompt = get_game_prompt(game_type, level, age, difficulty, questions=quiz_questions)
    else:
        prompt = get_game_prompt(game_type, level, age, difficulty)
    
    logger.info(f"Generation {game_type} level {level} for age {age}")
    
    for config in llm_configs:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                body = config['body_builder'](prompt)
                response = await client.post(config['url'], json=body, headers=config['headers'])
                
                if response.status_code == 200:
                    data = response.json()
                    content = config['extractor'](data)
                    
                    if content and len(content.strip()) > 10:
                        logger.info(f"Content generated successfully via {config['name']}")
                        return content.strip()
                else:
                    logger.warning(f"API error {config['name']}: {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.warning(f"Timeout for {config['name']}")
        except Exception as e:
            logger.error(f"Error {config['name']}: {str(e)}")
            continue
    
    logger.error(f"Failed to generate {game_type} level {level}")
    return None

class BulkGenerateView(APIView):
    throttle_classes = [AnonRateThrottle]
    
    def get(self, request):
        serializer = BulkGenerateSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        max_level = serializer.validated_data['levels']
        age = serializer.validated_data['age']

        async def ask_llm_for_full_structure():
            llm_configs = get_llm_configs()
            if not llm_configs:
                return []
                
            prompt = (
                "Tu es un game designer expert en jeux éducatifs bibliques pour enfants. "
                f"Voici la liste des types de jeux disponibles : {', '.join(GAME_TYPES)}. "
                f"L'utilisateur a {age} ans. Génère une progression complète de {max_level} niveaux, "
                "où chaque niveau contient une alternance variée et logique de jeux, avec difficulté, nombre de jeux, nombre de questions pour les quiz, etc. "
                "Adapte la structure à l'âge, propose des niveaux équilibrés, ludiques et progressifs. "
                "Pour chaque niveau, donne un JSON structuré : level, difficulty, games (liste ordonnée d'objets avec type, consigne, nombre de questions si quiz, etc.). "
                "N'invente pas de nouveaux types de jeux. Ne mets pas de fallback. Ne donne que la structure, pas le contenu des jeux."
            )
            
            for config in llm_configs:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        body = config['body_builder'](prompt)
                        response = await client.post(config['url'], json=body, headers=config['headers'])
                        if response.status_code == 200:
                            data = response.json()
                            content = config['extractor'](data)
                            if content:
                                # Extraction robuste du JSON
                                match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", content)
                                if match:
                                    content = match.group(1)
                                
                                if not content.strip().startswith('['):
                                    start = content.find('[')
                                    end = content.rfind(']')
                                    if start != -1 and end != -1:
                                        content = content[start:end+1]
                                
                                try:
                                    result = json.loads(content)
                                    logger.info(f"Structure generated successfully via {config['name']}")
                                    return result
                                except json.JSONDecodeError:
                                    continue
                except Exception as e:
                    logger.error(f"Error generating structure via {config['name']}: {str(e)}")
                    continue
            return []

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        structure = loop.run_until_complete(ask_llm_for_full_structure())
        loop.close()
        return Response(structure)

class GenerateLevelContentView(APIView):
    throttle_classes = [AnonRateThrottle]
    
    def get(self, request):
        serializer = GenerateLevelContentSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        level = serializer.validated_data['level']
        age = serializer.validated_data['age']
        specific_game_types = serializer.validated_data.get('game_types')

        def get_difficulty(level, age):
            if level <= 2:
                return 'facile' if age < 10 else 'normal'
            elif level <= 5:
                return 'normal' if age < 12 else 'difficile'
            else:
                return 'difficile'

        def random_game_sequence(level, specific_types=None):
            if specific_types:
                return specific_types
                
            sequence = []
            total_games = min(random.randint(4 + level, 6 + level), 10)  # Limite pour éviter timeouts
            
            if level == 1:
                sequence += ['quiz'] * random.randint(2, 3)
                sequence += ['wordgame'] * random.randint(1, 2)
            elif level == 2:
                sequence += ['quiz'] * random.randint(2, 3)
                sequence += ['wordgame'] * random.randint(1, 2)
                sequence += [random.choice(['story', 'memory'])]
            else:
                for _ in range(total_games):
                    sequence.append(random.choice(GAME_TYPES))
            
            random.shuffle(sequence)
            # Évite les répétitions consécutives
            for i in range(1, len(sequence)):
                if sequence[i] == sequence[i-1]:
                    alt = [g for g in GAME_TYPES if g != sequence[i]]
                    if alt:
                        sequence[i] = random.choice(alt)
            return sequence

        difficulty = get_difficulty(level, age)
        sequence = random_game_sequence(level, specific_game_types)
        quiz_sizes = [random.randint(3, 8) for _ in sequence if _ == 'quiz']  # Réduit pour éviter timeouts
        quiz_idx = 0

        async def generate_level():
            tasks = []
            current_quiz_idx = 0
            for idx, game in enumerate(sequence):
                if game == 'quiz' and current_quiz_idx < len(quiz_sizes):
                    qsize = quiz_sizes[current_quiz_idx]
                    current_quiz_idx += 1
                    tasks.append(fetch_llm_content(game, level, age, difficulty, idx+1, len(sequence), quiz_questions=qsize))
                else:
                    tasks.append(fetch_llm_content(game, level, age, difficulty, idx+1, len(sequence)))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            filtered = []
            
            for game, result in zip(sequence, results):
                if isinstance(result, Exception):
                    logger.error(f"Error generating {game}: {str(result)}")
                elif result:
                    filtered.append((game, result))
            
            games = {}
            for g, r in filtered:
                games.setdefault(g, []).append(r)
            return games

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            games = loop.run_until_complete(generate_level())
        finally:
            loop.close()
            
        return Response({'level': level, 'difficulty': difficulty, 'games': games})

class BulkGenerateWithContentView(APIView):
    throttle_classes = [AnonRateThrottle]
    
    def get(self, request):
        serializer = BulkGenerateSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        max_level = serializer.validated_data['levels']
        age = serializer.validated_data['age']

        async def ask_llm_for_full_structure():
            llm_configs = get_llm_configs()
            if not llm_configs:
                return []
                
            prompt = (
                "Tu es un game designer expert en jeux éducatifs bibliques pour enfants. "
                f"Voici la liste des types de jeux disponibles : {', '.join(GAME_TYPES)}. "
                f"L'utilisateur a {age} ans. Génère une progression complète de {max_level} niveaux, "
                "où chaque niveau contient une alternance variée et logique de jeux, avec difficulté, nombre de jeux, nombre de questions pour les quiz, etc. "
                "Adapte la structure à l'âge, propose des niveaux équilibrés, ludiques et progressifs. "
                "Pour chaque niveau, donne un JSON structuré : level, difficulty, games (liste ordonnée d'objets avec type, consigne, nombre de questions si quiz, etc.). "
                "N'invente pas de nouveaux types de jeux. Ne mets pas de fallback. Ne donne que la structure, pas le contenu des jeux."
            )
            
            for config in llm_configs:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        body = config['body_builder'](prompt)
                        response = await client.post(config['url'], json=body, headers=config['headers'])
                        if response.status_code == 200:
                            data = response.json()
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
                                    result = json.loads(content)
                                    logger.info(f"Complete structure generated via {config['name']}")
                                    return result
                                except json.JSONDecodeError:
                                    continue
                except Exception as e:
                    logger.error(f"Error generating complete structure via {config['name']}: {str(e)}")
                    continue
            return []

        async def fetch_content_for_game(game, level, age, difficulty):
            llm_configs = get_llm_configs()
            if not llm_configs:
                return None
                
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
            
            for config in llm_configs:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        body = config['body_builder'](prompt)
                        response = await client.post(config['url'], json=body, headers=config['headers'])
                        if response.status_code == 200:
                            data = response.json()
                            content = config['extractor'](data)
                            if content and len(content.strip()) > 10:
                                return content.strip()
                except Exception as e:
                    logger.error(f"Error generating game content via {config['name']}: {str(e)}")
                    continue
            return None

        async def generate_full():
            structure = await ask_llm_for_full_structure()
            if not structure:
                return []
                
            # structure = [ {level, difficulty, games: [ ... ]}, ... ]
            for level_obj in structure:
                level = level_obj.get('level')
                difficulty = level_obj.get('difficulty')
                games = level_obj.get('games', [])
                
                # Limite le nombre de jeux pour éviter les timeouts
                if len(games) > 8:
                    games = games[:8]
                    level_obj['games'] = games
                
                # Pour compatibilité, accepter liste d'objets ou liste de dicts
                for game in games:
                    content = await fetch_content_for_game(game, level, age, difficulty)
                    game['content'] = content
            return structure

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(generate_full())
        finally:
            loop.close()
        return Response(result)
