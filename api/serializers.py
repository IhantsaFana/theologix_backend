"""
Serializers pour la validation des données d'entrée
"""
from rest_framework import serializers
from .config import GAME_TYPES

class BulkGenerateSerializer(serializers.Serializer):
    levels = serializers.IntegerField(min_value=1, max_value=20, default=10)
    age = serializers.IntegerField(min_value=3, max_value=18, default=8)
    
    def validate_levels(self, value):
        if value > 15:
            raise serializers.ValidationError("Maximum 15 niveaux supportés pour éviter les timeouts.")
        return value

class GenerateLevelContentSerializer(serializers.Serializer):
    level = serializers.IntegerField(min_value=1, max_value=20)
    age = serializers.IntegerField(min_value=3, max_value=18, default=8)
    game_types = serializers.ListField(
        child=serializers.ChoiceField(choices=GAME_TYPES),
        required=False,
        help_text="Types de jeux spécifiques à générer (optionnel)"
    )
    
    def validate_game_types(self, value):
        if value and len(value) > 10:
            raise serializers.ValidationError("Maximum 10 types de jeux par niveau.")
        return value

class GameContentSerializer(serializers.Serializer):
    """Serializer pour la réponse de contenu de jeu"""
    type = serializers.CharField()
    content = serializers.CharField()
    level = serializers.IntegerField()
    difficulty = serializers.CharField()
    
class LevelResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse d'un niveau complet"""
    level = serializers.IntegerField()
    difficulty = serializers.CharField()
    games = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )