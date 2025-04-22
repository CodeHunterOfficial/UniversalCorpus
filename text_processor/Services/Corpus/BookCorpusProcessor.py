import os
import re
from docx import Document
import logging
from typing import List, Dict, Optional, Tuple
import nltk
from langdetect import detect
import json
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from ebooklib import epub
from concurrent.futures import ThreadPoolExecutor
import zipfile

# Настройка логирования с UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

class BookCorpusProcessor:
    def __init__(self,
                 books_folder: str,
                 output_base: str = "Corpus_Books",
                 output_format: str = "txt",
                 language: str = "ru",
                 skip_pages: Tuple[int, int] = (3, 3),
                 ignore_footnotes: bool = True,
                 ignore_links: bool = True):
        """
        Инициализация класса.

        :param books_folder: Путь к папке с книгами
        :param output_base: Базовое имя выходных файлов
        :param output_format: Формат вывода ('txt', 'json', 'xml' или 'zip')
        :param language: Язык книг ('tg' для таджикского, 'ru', 'en' и др.)
        :param skip_pages: Сколько страниц пропустить в начале и конце (start, end)
        :param ignore_footnotes: Игнорировать сноски
        :param ignore_links: Игнорировать ссылки
        """
        self.books_folder = books_folder
        self.output_base = output_base
        self.output_format = output_format.lower()
        self.language = language.lower()
        self.skip_pages = skip_pages
        self.ignore_footnotes = ignore_footnotes
        self.ignore_links = ignore_links
        self.processed_books = []
        self.progress = 0
        self.language = self._map_language_code(language)

    def _map_language_code(self, language_code: str) -> str:
        """Сопоставляет код языка с форматом nltk."""
        language_mapping = {
            "ru": "russian",
            "en": "english",
            "tg": "tajik",  # Для таджикского языка
            "tj": "tajik",  # Альтернативный код
        }
        return language_mapping.get(language_code, "english")

    def clean_text(self, text: str, custom_patterns: Optional[List[str]] = None) -> str:
        """
        Очищает текст с учетом настроек для сносок, ссылок и цифр.
        Также выполняет замену символов љ, ї, њ, Ќ, ў, ѓ на ҷ, ӣ, ҳ, қ, ӯ, ғ соответственно.
        """
        patterns = [
            r"^\s*\d+\s*$",  # Номера страниц
            r"[^\w\s\.,!?;:()«»“”'\"\\/-]",  # Спецсимволы (сохраняем таджикские буквы)
            r"\s+",  # Множественные пробелы
            r"^\s*$",  # Пустые строки
            r"\t+",  # Табуляции
            r"\.{2,}",  # Многоточия
            r"<.*?>",  # HTML-теги
        ]
        # Добавляем паттерны для сносок и ссылок если нужно
        if self.ignore_footnotes:
            patterns.extend([
                r"\[\d+\]",  # Сноски типа [1], [2]
                r"\^[a-zA-Z0-9]+",  # Сноски типа ^1, ^footnote
                r"^\d+\.\s*([А-ЯЁA-Za-z\-]+\.)?.*",  # Сноски вида "1. И-Зи кирдори бад бо љањон."
                r"^\d+\.\s*[А-ЯЁA-Za-z\-]+\.\s*\d+\s+.*",  # Сноски вида "6. И-б. 1331 нест."
                r"^\d+\..*",  # Удаляет любые строки, начинающиеся с цифры и точки
            ])
        if self.ignore_links:
            patterns.extend([
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",  # URL
                r"www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}",  # URL без http
            ])
        if custom_patterns:
            patterns.extend(custom_patterns)
        
        # Удаляем все цифры
        patterns.append(r"\d+")  # Находит все цифры
        
        for pattern in patterns:
            text = re.sub(pattern, " ", text, flags=re.MULTILINE)

        # Замена символов (строчные и заглавные)
        replacements = {
            "љ": "ҷ",
            "ї": "ӣ",
            "њ": "ҳ",
            "ќ": "қ",
            "ў": "ӯ",
            "ѓ": "ғ",
            "Љ": "Ҷ",
            "Ї": "Ӣ",
            "Њ": "Ҳ",
            "Ќ": "Қ",
            "Ў": "Ӯ",
            "Ѓ": "Ғ"
        }
        for old_char, new_char in replacements.items():
            text = text.replace(old_char, new_char)

        return text.strip()

        
        
    def extract_metadata(self, filename: str) -> Dict[str, str]:
        """Извлекает метаданные из имени файла."""
        base_name = os.path.splitext(filename)[0]
        parts = base_name.split("_", 1)

        if len(parts) == 2:
            title, author = parts
            return {"title": title.strip(), "author": author.strip()}
        return {"title": base_name.strip(), "author": "Unknown"}

    def process_docx_file(self, file_path: str) -> str:
        """Обрабатывает DOCX файл с учетом пропуска страниц."""
        try:
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]

            # Пропускаем первые N "страниц" (здесь - абзацы)
            if self.skip_pages[0] > 0:
                paragraphs = paragraphs[self.skip_pages[0]:]

            # Пропускаем последние M "страниц"
            if self.skip_pages[1] > 0:
                paragraphs = paragraphs[:-self.skip_pages[1]] if self.skip_pages[1] > 0 else paragraphs

            raw_text = "\n".join(paragraphs)
            cleaned_text = self.clean_text(raw_text)
            metadata = self.extract_metadata(os.path.basename(file_path))
            metadata_str = f"# Title: {metadata['title']}\n# Author: {metadata['author']}\n# Language: {self.language}\n# -----\n"
            return metadata_str + cleaned_text + "\n\n"
        except Exception as e:
            logging.error(f"Error processing DOCX {file_path}: {e}")
            return ""

    def process_txt_file(self, file_path: str) -> str:
        """Обрабатывает TXT файл с учетом пропуска страниц."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()

            # Пропускаем первые N строк как "страницы"
            if self.skip_pages[0] > 0:
                lines = lines[self.skip_pages[0]:]

            # Пропускаем последние M строк
            if self.skip_pages[1] > 0:
                lines = lines[:-self.skip_pages[1]] if self.skip_pages[1] > 0 else lines

            raw_text = "".join(lines)
            cleaned_text = self.clean_text(raw_text)
            metadata = self.extract_metadata(os.path.basename(file_path))
            metadata_str = f"# Title: {metadata['title']}\n# Author: {metadata['author']}\n# Language: {self.language}\n# -----\n"
            return metadata_str + cleaned_text + "\n\n"
        except Exception as e:
            logging.error(f"Error processing TXT {file_path}: {e}")
            return ""

    def process_pdf_file(self, file_path: str) -> str:
        """Обрабатывает PDF файл с пропуском страниц."""
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)

            # Определяем диапазон страниц для обработки
            start_page = min(self.skip_pages[0], total_pages - 1)
            end_page = max(total_pages - self.skip_pages[1], start_page + 1)

            raw_text = "\n".join(
                reader.pages[i].extract_text()
                for i in range(start_page, end_page))

            cleaned_text = self.clean_text(raw_text)
            metadata = self.extract_metadata(os.path.basename(file_path))
            metadata_str = f"# Title: {metadata['title']}\n# Author: {metadata['author']}\n# Language: {self.language}\n# -----\n"
            return metadata_str + cleaned_text + "\n\n"
        except Exception as e:
            logging.error(f"Error processing PDF {file_path}: {e}")
            return ""

    def process_html_file(self, file_path: str) -> str:
        """Обрабатывает HTML файл."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                soup = BeautifulSoup(file.read(), 'html.parser')

            # Удаляем скрипты, стили, сноски и ссылки если нужно
            for element in soup(["script", "style"] +
                              (["sup"] if self.ignore_footnotes else []) +
                              (["a"] if self.ignore_links else [])):
                element.decompose()

            raw_text = soup.get_text(separator="\n")
            cleaned_text = self.clean_text(raw_text)
            metadata = self.extract_metadata(os.path.basename(file_path))
            metadata_str = f"# Title: {metadata['title']}\n# Author: {metadata['author']}\n# Language: {self.language}\n# -----\n"
            return metadata_str + cleaned_text + "\n\n"
        except Exception as e:
            logging.error(f"Error processing HTML {file_path}: {e}")
            return ""

    def process_epub_file(self, file_path: str) -> str:
        """Обрабатывает EPUB файл."""
        try:
            book = epub.read_epub(file_path)
            raw_text = ""
            for item in book.get_items_of_type(epub.ITEM_DOCUMENT):
                text = item.content.decode("utf-8")

                # Удаляем сноски и ссылки если нужно
                if self.ignore_footnotes:
                    text = re.sub(r"<epub:footnote.*?</epub:footnote>", "", text, flags=re.DOTALL)
                if self.ignore_links:
                    text = re.sub(r"<a href=.*?</a>", "", text, flags=re.DOTALL)

                raw_text += text

            cleaned_text = self.clean_text(raw_text)
            metadata = self.extract_metadata(os.path.basename(file_path))
            metadata_str = f"# Title: {metadata['title']}\n# Author: {metadata['author']}\n# Language: {self.language}\n# -----\n"
            return metadata_str + cleaned_text + "\n\n"
        except Exception as e:
            logging.error(f"Error processing EPUB {file_path}: {e}")
            return ""

    def validate_filename(self, filename: str) -> bool:
        """Проверяет имя файла."""
        return "_" in filename and len(filename.split("_")) >= 2

    def split_into_sentences(self, text: str) -> str:
        """Разделяет текст на предложения."""
        try:
            nltk.download('punkt', quiet=True)
            sentences = nltk.sent_tokenize(text, language=self.language)
            return "\n".join(sentences)
        except Exception as e:
            logging.warning(f"Sentence splitting error: {e}")
            return text

    def process_all_books(self):
        """Обрабатывает все книги в папке."""
        if not os.path.exists(self.books_folder):
            logging.error("Directory does not exist.")
            return None

        all_books = []
        supported_formats = (".docx", ".txt", ".pdf", ".html", ".epub")
        files = [f for f in os.listdir(self.books_folder)
                if any(f.endswith(fmt) for fmt in supported_formats)]
        total_files = len(files)

        for i, filename in enumerate(files, 1):
            file_path = os.path.join(self.books_folder, filename)

            if not self.validate_filename(filename):
                logging.warning(f"Skipping invalid filename: {filename}")
                continue

            processor = {
                ".docx": self.process_docx_file,
                ".txt": self.process_txt_file,
                ".pdf": self.process_pdf_file,
                ".html": self.process_html_file,
                ".epub": self.process_epub_file,
            }.get(os.path.splitext(filename)[1].lower())

            if processor:
                processed_text = processor(file_path)
                if processed_text:
                    all_books.append(processed_text)
                    self.processed_books.append(filename)
                    logging.info(f"Processed: {filename}")

            self.progress = int((i / total_files) * 100)

        if not all_books:
            logging.error("No books were processed.")
            return None

        # Сохранение результатов
        output_path = None
        try:
            if self.output_format == 'txt':
                output_path = os.path.join(self.books_folder, f"{self.output_base}.txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(all_books))

            elif self.output_format == 'json':
                output_path = os.path.join(self.books_folder, f"{self.output_base}.json")
                json_data = []
                for book in all_books:
                    lines = book.split("\n")
                    title = lines[0].split(":")[1].strip()
                    author = lines[1].split(":")[1].strip()
                    text = "\n".join(lines[4:]).strip()
                    json_data.append({
                        "title": title,
                        "author": author,
                        "language": self.language,
                        "text": text
                    })
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

            elif self.output_format == 'xml':
                output_path = os.path.join(self.books_folder, f"{self.output_base}.xml")
                root = ET.Element("books")
                for book in all_books:
                    lines = book.split("\n")
                    book_elem = ET.SubElement(root, "book")
                    ET.SubElement(book_elem, "title").text = lines[0].split(":")[1].strip()
                    ET.SubElement(book_elem, "author").text = lines[1].split(":")[1].strip()
                    ET.SubElement(book_elem, "language").text = self.language
                    ET.SubElement(book_elem, "text").text = "\n".join(lines[4:]).strip()
                ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)

            elif self.output_format == 'zip':
                # Создаем временные файлы
                temp_files = []
                for fmt in ['txt', 'json', 'xml']:
                    temp_path = os.path.join(self.books_folder, f"{self.output_base}.{fmt}")
                    temp_files.append(temp_path)

                    if fmt == 'txt':
                        with open(temp_path, "w", encoding="utf-8") as f:
                            f.write("\n".join(all_books))
                    elif fmt == 'json':
                        json_data = []
                        for book in all_books:
                            lines = book.split("\n")
                            json_data.append({
                                "title": lines[0].split(":")[1].strip(),
                                "author": lines[1].split(":")[1].strip(),
                                "language": self.language,
                                "text": "\n".join(lines[4:]).strip()
                            })
                        with open(temp_path, "w", encoding="utf-8") as f:
                            json.dump(json_data, f, ensure_ascii=False, indent=2)
                    elif fmt == 'xml':
                        root = ET.Element("books")
                        for book in all_books:
                            lines = book.split("\n")
                            book_elem = ET.SubElement(root, "book")
                            ET.SubElement(book_elem, "title").text = lines[0].split(":")[1].strip()
                            ET.SubElement(book_elem, "author").text = lines[1].split(":")[1].strip()
                            ET.SubElement(book_elem, "language").text = self.language
                            ET.SubElement(book_elem, "text").text = "\n".join(lines[4:]).strip()
                        ET.ElementTree(root).write(temp_path, encoding="utf-8", xml_declaration=True)

                # Архивируем
                output_path = os.path.join(self.books_folder, f"{self.output_base}.zip")
                with zipfile.ZipFile(output_path, 'w') as zipf:
                    for file in temp_files:
                        zipf.write(file, arcname=os.path.basename(file))

                # Удаляем временные файлы
                for file in temp_files:
                    os.remove(file)

            logging.info(f"Processing complete. Saved to: {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"Error saving results: {e}")
            return None    