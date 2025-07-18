"""
Tests unitaires pour l'API Theologix
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, AsyncMock
from .config import get_llm_configs, GAME_TYPES

class ConfigTestCase(TestCase):
    """Tests pour la configuration"""
    
    def test_game_types_defined(self):
        """Vérifie que les types de jeux sont bien définis"""
        self.assertEqual(len(GAME_TYPES), 6)
        self.assertIn('quiz', GAME_TYPES)
        self.assertIn('wordgame', GAME_TYPES)
        self.assertIn('puzzle', GAME_TYPES)
        self.assertIn('story', GAME_TYPES)
        self.assertIn('treasure', GAME_TYPES)
        self.assertIn('memory', GAME_TYPES)
    
    @patch('django.conf.settings.OPENROUTER_API_KEY', 'test-key')
    @patch('django.conf.settings.GEMINI_API_KEY', 'test-key')
    def test_llm_configs_with_keys(self):
        """Vérifie que les configs LLM sont générées avec les clés"""
        configs = get_llm_configs()
        self.assertEqual(len(configs), 2)
        self.assertEqual(configs[0]['name'], 'openrouter')
        self.assertEqual(configs[1]['name'], 'gemini')
    
    @patch('django.conf.settings.OPENROUTER_API_KEY', '')
    @patch('django.conf.settings.GEMINI_API_KEY', '')
    def test_llm_configs_without_keys(self):
        """Vérifie le comportement sans clés API"""
        configs = get_llm_configs()
        self.assertEqual(len(configs), 0)

class APIEndpointsTestCase(APITestCase):
    """Tests pour les endpoints API"""
    
    def test_bulk_generate_invalid_params(self):
        """Test validation des paramètres invalides"""
        url = reverse('bulk_generate')
        
        # Test avec levels invalide
        response = self.client.get(url, {'levels': 'invalid', 'age': 8})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test avec age invalide
        response = self.client.get(url, {'levels': 5, 'age': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test avec levels trop élevé
        response = self.client.get(url, {'levels': 25, 'age': 8})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_generate_level_content_invalid_params(self):
        """Test validation pour generate_level_content"""
        url = reverse('generate_level_content')
        
        # Test sans level
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test avec level invalide
        response = self.client.get(url, {'level': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('api.views.get_llm_configs')
    def test_endpoints_without_llm_config(self, mock_get_configs):
        """Test comportement sans configuration LLM"""
        mock_get_configs.return_value = []
        
        url = reverse('bulk_generate')
        response = self.client.get(url, {'levels': 3, 'age': 8})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
    
    def test_bulk_generate_valid_params(self):
        """Test avec paramètres valides"""
        url = reverse('bulk_generate')
        response = self.client.get(url, {'levels': 3, 'age': 8})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # La réponse peut être vide si pas de clés API configurées
        self.assertIsInstance(response.json(), list)
    
    def test_generate_level_content_valid_params(self):
        """Test generate_level_content avec paramètres valides"""
        url = reverse('generate_level_content')
        response = self.client.get(url, {'level': 1, 'age': 8})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('level', data)
        self.assertIn('difficulty', data)
        self.assertIn('games', data)
        self.assertEqual(data['level'], 1)

class ThrottlingTestCase(APITestCase):
    """Tests pour le rate limiting"""
    
    def test_rate_limiting(self):
        """Test basique du rate limiting (nécessite configuration Redis en prod)"""
        url = reverse('bulk_generate')
        
        # Fait plusieurs requêtes rapidement
        for i in range(5):
            response = self.client.get(url, {'levels': 1, 'age': 8})
            # En développement, le throttling peut ne pas être actif
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS])