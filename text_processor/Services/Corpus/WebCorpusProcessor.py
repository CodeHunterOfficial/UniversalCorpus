import io
import os
import re
import logging
from typing import List, Dict, Optional, Union
import json
import requests
from bs4 import BeautifulSoup
from trafilatura import extract
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class WebCorpusProcessor:
    def __init__(
        self,
        output_base: str = "news_corpus",
        output_format: str = 'txt',
        language: str = 'ru',
        encoding: str = 'utf-8',
        clean_html: bool = True,
        remove_extra_spaces: bool = True,
        normalize_punctuation: bool = True,
        rootPath:str=''
    ):
        self.output_base = output_base
        self.output_format = output_format.lower()
        self.language = language.lower()
        self.encoding = encoding
        self.clean_html = clean_html
        self.remove_extra_spaces = remove_extra_spaces
        self.normalize_punctuation = normalize_punctuation
        self.processed_items: List[Dict] = []
        self.rootPath=rootPath

        self.language_patterns = {
            'ru': {
                'quotes': ['«»', '""', "''"],
                'special_chars': r"[^\w\s\.,!?;:()«»“”'\"\\/-]"
            },
            'en': {
                'quotes': ['""', "''", '“”'],
                'special_chars': r"[^\w\s\.,!?;:()\"'\\/-]"
            }
        }

    def clean_text(self, text: str, custom_patterns: Optional[List[str]] = None) -> str:
        if self.clean_html:
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text(separator=" ")

        lang_patterns = self.language_patterns.get(self.language, self.language_patterns['en'])

        patterns = [
            r"^\s*\d+\s*$",
            lang_patterns['special_chars'],
            r"\s+",
            r"^\s*$",
            r"\t+",
            r"\.{2,}",
        ]

        if self.remove_extra_spaces:
            patterns.append(r"\s+")

        if self.normalize_punctuation:
            patterns.extend([
                r"\.{2,}",
                r",{2,}",
                r"!{2,}",
                r"\?{2,}",
            ])

        if custom_patterns:
            patterns.extend(custom_patterns)

        for pattern in patterns:
            text = re.sub(pattern, " ", text, flags=re.MULTILINE)

        return text.strip()

    def clean_content(self, data: Dict) -> Dict:
        cleaned_data = {
            "title": self.clean_text(data.get("title", "")),
            "author": self.clean_text(data.get("author", "")),
            "content": self.clean_text(data.get("content", ""))
        }
        return cleaned_data

    def extract_web_content(self, url: str) -> Dict:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Используем trafilatura для извлечения основного текста
            main_content = extract(response.text) or ""

            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else "No Title"

            author = "Unknown Author"
            for meta_name in ['author', 'dc.creator', 'dcterms.creator']:
                author_tag = soup.find("meta", attrs={"name": meta_name})
                if author_tag and "content" in author_tag.attrs:
                    author = author_tag["content"].strip()
                    break

            raw_data = {
                "title": title,
                "author": author,
                "content": main_content,
                "url": url,
                "language": self.language
            }

            return self.clean_content(raw_data)
        except Exception as e:
            logging.error(f"Ошибка при извлечении контента из {url}: {e}")
            return {
                "title": "Error",
                "author": "Unknown",
                "content": "",
                "url": url,
                "language": self.language
            }

    # Остальные методы класса остаются без изменений...
    def process_all_sources(self, sources: List[Dict]):
        all_data = []
        filename=None
        for source in sources:
            if source["type"] == "web":
                content = self.extract_web_content(source["url"])
                if content:
                    all_data.append({
                        "source": "web",
                        "url": source["url"],
                        "content": content,
                        "language": self.language
                    })

        if self.output_format == 'json':
            filename= self.save_to_json(all_data)
        elif self.output_format == 'xml':
            filename= self.save_to_xml(all_data)
        elif self.output_format == 'zip':
            filename= self.save_to_zip(all_data)
        else:
            filename= self.save_to_txt(all_data)

        logging.info(f"Обработано источников: {len(all_data)}.")
        full_path = Path(self.rootPath) / filename
        print('full_path',full_path)
        return full_path

    def save_to_json(self, data: List[Dict]):
        filename = f"{self.output_base}.json"
        with open(filename, "w", encoding=self.encoding) as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        logging.info(f"Данные сохранены в {filename}")
        return filename

    def save_to_txt(self, data: List[Dict]):
        filename = f"{self.output_base}.txt"
        with open(filename, "w", encoding=self.encoding) as txt_file:
            for item in data:
                content = item.get('content', {})
                txt_file.write(f"Title: {content.get('title', 'N/A')}\n")
                txt_file.write(f"Author: {content.get('author', 'N/A')}\n")
                txt_file.write(f"URL: {item.get('url', 'N/A')}\n")
                txt_file.write(f"Language: {item.get('language', 'N/A')}\n")
                txt_file.write(f"Content:\n{content.get('content', '')}\n\n")
        logging.info(f"Данные сохранены в {filename}")
        return filename

    def save_to_xml(self, data: List[Dict]):
        filename = f"{self.output_base}.xml"
        root = ET.Element("news_corpus")

        for item in data:
            entry = ET.SubElement(root, "entry")
            ET.SubElement(entry, "source").text = item.get("source", "web")
            ET.SubElement(entry, "url").text = item.get("url", "")
            ET.SubElement(entry, "language").text = item.get("language", self.language)

            content = item.get("content", {})
            content_elem = ET.SubElement(entry, "content")
            ET.SubElement(content_elem, "title").text = content.get("title", "N/A")
            ET.SubElement(content_elem, "author").text = content.get("author", "N/A")
            ET.SubElement(content_elem, "text").text = content.get("content", "")

        tree = ET.ElementTree(root)
        tree.write(filename, encoding=self.encoding, xml_declaration=True)
        logging.info(f"Данные сохранены в {filename}")
        return filename

    def save_to_zip(self, data: List[Dict]):
        zip_filename = f"{self.output_base}.zip"
        temp_files = []
        formats = ['json', 'xml', 'txt']

        try:
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for fmt in formats:
                    filename = f"{self.output_base}.{fmt}"
                    if fmt == 'json':
                        self.save_to_json(data)
                    elif fmt == 'xml':
                        self.save_to_xml(data)
                    else:
                        self.save_to_txt(data)
                    zipf.write(filename)
                    temp_files.append(filename)

            logging.info(f"Все данные сохранены в ZIP-архив {zip_filename}")
            return filename
        finally:
            for filename in temp_files:
                try:
                    os.remove(filename)
                except OSError as e:
                    logging.warning(f"Не удалось удалить временный файл {filename}: {e}")