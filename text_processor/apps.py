from django.apps import AppConfig
import nltk
import logging

logger = logging.getLogger(__name__)

class TextProcessorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'text_processor'
