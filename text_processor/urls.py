from django.urls import path
from text_processor.views import views

urlpatterns = [
    path('', views.home, name='home'),    
    path('universal-corpus/', views.universal_corpus, name='universal_corpus'),  
    path('upload-folder-corpus/', views.upload_folder_corpus, name='upload_folder_corpus'),
]