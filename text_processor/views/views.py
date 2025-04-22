
from text_processor.forms.universalcorpus.UniversalCorpusForm import UniversalCorpusForm
import datetime
import os
import datetime
from django.utils.text import get_valid_filename
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from text_easy_processor import settings
from django.core.files.storage import FileSystemStorage
from text_processor.Services.Corpus.BookCorpusProcessor import BookCorpusProcessor
from text_processor.Services.Corpus.WebCorpusProcessor import WebCorpusProcessor

# Глобальная переменная для хранения экземпляра процессора
processor_instance = None
import logging

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'home.html')

def universal_corpus(request):
    corpus_path = None  # Единая переменная для пути к корпусу
    rootPath = settings.MEDIA_ROOT
    
    if request.method == 'POST':
        form = UniversalCorpusForm(request.POST, request.FILES)
        if form.is_valid():
            process_type = form.cleaned_data['process_type']
            output_format = form.cleaned_data['type_outputcorpus']
            server_path = form.cleaned_data['server_path']     
            language = form.cleaned_data['language']
            
            try:
                if process_type == 'folder':
                    processor = BookCorpusProcessor(
                        books_folder=server_path, 
                        output_base='text_corpus', 
                        output_format=output_format,
                        skip_pages=(0, 0),
                        ignore_footnotes=True,
                        ignore_links=True,
                        language=language
                    )
                    corpus_path = processor.process_all_books()
                    form.instance.outputcorpus_path = corpus_path  # Сохраняем путь в форму
                    # form.save()  # Если нужно записать в БД

                elif process_type == 'web':
                    web_urls = form.cleaned_data['web_urls']
                    urls = [url.strip() for url in web_urls.split("\n") if url.strip()]
                    
                    if not urls:
                        message = "Не указаны URL-адреса."
                        form.add_error('web_urls', message)
                    else:
                        sources = [{"type": "web", "url": url} for url in urls]
                        processor = WebCorpusProcessor(
                            output_base="my_corpus",
                            output_format=output_format,
                            language=language,
                            encoding="utf-8",
                            rootPath=rootPath
                        )
                        corpus_path = processor.process_all_sources(sources)
                        form.instance.outputcorpus_path = corpus_path  # Сохраняем путь в форму
                        # form.save()  # Если нужно записать в БД

                form = UniversalCorpusForm(initial={
                'outputcorpus_path ': corpus_path
                })
                
            except Exception as e:
                message = f"Произошла ошибка: {e}"
                form.add_error(None, message)  # Добавляем ошибку в форму

        else:
            message = "Неверные данные формы. Ошибки: " + str(form.errors)

    else:
        form = UniversalCorpusForm()

    return render(
        request,
        'universalcorpus/universal_corpus.html',
        {
            'form': form,
            'corpus_path': corpus_path,       # Новый вариант
        }
    )

@csrf_exempt
def upload_folder_corpus(request):
    if request.method == 'POST':
        try:
            # Проверка наличия файлов
            if not request.FILES.getlist('files'):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Не выбраны файлы для загрузки'
                }, status=400)
         
            # Создаем папку с timestamp для уникальности
            timestamp = int(datetime.datetime.now().timestamp())  # Используем datetime.datetime.now().timestamp()
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploaded_corpus', f'corpus_{timestamp}')
            os.makedirs(upload_dir, exist_ok=True)

            # Сохраняем файлы
            fs = FileSystemStorage(location=upload_dir)
            saved_files = []
            
            for file in request.FILES.getlist('files'):
                filename = get_valid_filename(file.name)
                saved_path = fs.save(filename, file)
                saved_files.append({
                    'name': filename,
                    'path': saved_path,
                    'size': file.size
                })
            
            return JsonResponse({
                'status': 'success',
                'server_path': upload_dir,
                'relative_path': os.path.join('uploaded_corpus', f'corpus_{timestamp}'),
                'saved_files': saved_files,
                'message': f'Успешно загружено {len(saved_files)} файлов',
                'timestamp': timestamp
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка загрузки: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Недопустимый метод запроса'
    }, status=400)