"""
Configuration centralisée pour les APIs LLM
"""
from django.conf import settings
import logging

logger = logging.getLogger('api')

# Types de jeux supportés
GAME_TYPES = ['quiz', 'wordgame', 'puzzle', 'story', 'treasure', 'memory']

# Configuration des LLM avec clés sécurisées
def get_llm_configs():
    """Retourne la configuration des LLM avec les clés depuis les variables d'environnement"""
    configs = []
    
    # OpenRouter
    if settings.OPENROUTER_API_KEY:
        configs.append({
            'name': 'openrouter',
            'url': 'https://openrouter.ai/api/v1/chat/completions',
            'headers': {
                'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                'HTTP-Referer': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://theologix.app',
                'X-Title': 'Theologix - Biblical Educational Game',
                'Content-Type': 'application/json; charset=utf-8'
            },
            'model': 'moonshotai/kimi-k2:free',
            'body_builder': lambda prompt: {
                "model": "moonshotai/kimi-dev-72b:free", 
                "messages": [{"role": "user", "content": prompt}]
            },
            'extractor': lambda resp: resp.get('choices', [{}])[0].get('message', {}).get('content', None),
        })
    
    # Gemini
    if settings.GEMINI_API_KEY:
        configs.append({
            'name': 'gemini',
            'url': f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}',
            'headers': {},
            'model': 'gemini-2.0-flash',
            'body_builder': lambda prompt: {
                "contents": [{"parts": [{"text": prompt}]}]
            },
            'extractor': lambda resp: resp.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', None),
        })
    
    if not configs:
        logger.warning("No LLM API keys configured. Check your environment variables.")
    
    return configs

# Prompts optimisés par type de jeu
GAME_PROMPTS = {
    'quiz': """Generate a biblical multiple choice quiz with {questions} questions for level {level}.
Difficulty: {difficulty}, age: {age} years.
Format: Question, 4 choices (A,B,C,D), correct answer.
Biblical themes adapted to age. Be creative and educational.""",
    
    'wordgame': """Create a biblical word game for level {level}.
Difficulty: {difficulty}, age: {age} years.
Propose biblical words to guess with progressive clues.
Adapt word complexity to age.""",
    
    'puzzle': """Design a biblical puzzle for level {level}.
Difficulty: {difficulty}, age: {age} years.
Can be image, word, or logic puzzle.
Provide elements and solution.""",
    
    'story': """Tell an interactive biblical story for level {level}.
Difficulty: {difficulty}, age: {age} years.
Story with multiple choices and consequences.
Adapt vocabulary and length to age.""",
    
    'treasure': """Create a biblical treasure hunt for level {level}.
Difficulty: {difficulty}, age: {age} years.
Biblical clues leading to a "treasure" (verse, teaching).
Logical and educational progression.""",
    
    'memory': """Design a biblical memory game for level {level}.
Difficulty: {difficulty}, age: {age} years.
Pairs to match (characters/actions, verses/references, etc.).
Adapt number of pairs to age and level."""
}

def get_game_prompt(game_type, level, age, difficulty, **kwargs):
    """Generate an optimized prompt for a given game type"""
    if game_type not in GAME_PROMPTS:
        return f"Generate biblical content of type {game_type} for level {level}, difficulty {difficulty}, age {age} years."
    
    return GAME_PROMPTS[game_type].format(
        level=level,
        difficulty=difficulty,
        age=age,
        **kwargs
    )