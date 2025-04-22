from django import forms

PROCESS_TYPE_CHOICES = [
    ('folder', 'Обработать из папки'),
   # ('archive', 'Обработать из архива'),
    ('web', 'Обработать веб-страницы')
]

OUTPUT_FORMAT_CHOICES = [
    ('json', 'Json'),
    ('txt', 'txt'),
    ('xml', 'xml'),
    ('rtf', 'rtf'),
    ('zip', 'zip archive')
]

class UniversalCorpusForm(forms.Form):
    process_type = forms.ChoiceField(
        label="Тип обработки",
        choices=PROCESS_TYPE_CHOICES,
        initial='folder',
        widget=forms.Select(attrs={'class': 'form-control', 'onchange': 'toggleFields()'})
    )

    web_urls = forms.CharField(
        label="URL веб-страниц",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        required=False,
        initial=["https://en.wikipedia.org/wiki/Daniel_Noboa", "\n" "https://en.wikipedia.org/wiki/Kellogg_School_of_Management"]
    )

    type_outputcorpus = forms.ChoiceField(
        label="Формат выходного файла",
        choices=OUTPUT_FORMAT_CHOICES,
        initial='txt',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    language = forms.ChoiceField(choices=[('en', 'English'), ('ru', 'Russian'), ('tg', 'Tajik')], label="Выберите язык", required=False)

    folder_path = forms.CharField(
        label="Относительный путь к корпусу",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'placeholder': 'Будет заполнен автоматически после загрузки'
        }),
        required=False
    )
    
    server_path = forms.CharField(
        label="Полный серверный путь",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'placeholder': 'Будет заполнен автоматически после загрузки'
        }),
        required=False
    )

    outputcorpus_path = forms.CharField(
        label="Путь к созданному корпусу",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'readonly': 'readonly'}),
        initial='output_corpus',
        required=False
    )