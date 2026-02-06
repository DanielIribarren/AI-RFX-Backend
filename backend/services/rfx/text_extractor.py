"""
📄 Text Extractor - Extracción de texto de múltiples formatos
Soporta: PDF, Excel, Word, imágenes (OCR), archivos ZIP
"""
import io
import os
import logging
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TextExtractor:
    """
    Extractor de texto de múltiples formatos de archivo.
    
    Principio KISS: Una responsabilidad = extraer texto.
    El AI se encarga de interpretar el contenido.
    """
    
    def __init__(self, use_ocr: bool = True, use_zip: bool = True):
        """
        Args:
            use_ocr: Habilitar OCR para imágenes
            use_zip: Habilitar procesamiento de archivos ZIP
        """
        self.use_ocr = use_ocr
        self.use_zip = use_zip
        self._pdf_reader = None
        self._ocr_engine = None
    
    def extract_from_files(self, files: List[Dict[str, Any]]) -> str:
        """
        Extrae texto de múltiples archivos.
        
        Args:
            files: Lista de dicts con 'content' (bytes) y 'filename' (str)
            
        Returns:
            Texto consolidado de todos los archivos
        """
        if not files:
            logger.warning("⚠️ No files provided for extraction")
            return ""
        
        logger.info(f"📦 Extracting text from {len(files)} file(s)")
        
        texts = []
        for file_data in files:
            try:
                content = file_data['content']
                filename = file_data['filename']
                
                logger.info(f"📄 Processing: {filename} ({len(content)} bytes)")
                
                # Detectar tipo de archivo
                file_type = self._detect_file_type(content, filename)
                
                # Extraer según tipo
                if file_type == 'pdf':
                    text = self._extract_pdf(content)
                elif file_type == 'excel':
                    text = self._extract_excel(content)
                elif file_type == 'word':
                    text = self._extract_word(content)
                elif file_type == 'image':
                    text = self._extract_image_ocr(content)
                elif file_type == 'zip' and self.use_zip:
                    text = self._extract_zip(content)
                else:
                    logger.warning(f"⚠️ Unsupported file type: {file_type}")
                    text = ""
                
                if text:
                    texts.append(f"### SOURCE: {filename}\n{text}")
                    logger.info(f"✅ Extracted {len(text)} characters from {filename}")
                else:
                    logger.warning(f"⚠️ No text extracted from {filename}")
                    
            except Exception as e:
                logger.error(f"❌ Error extracting {file_data.get('filename', 'unknown')}: {e}")
                continue
        
        consolidated_text = "\n\n".join(texts)
        logger.info(f"✅ Total extracted: {len(consolidated_text)} characters from {len(texts)} files")
        
        return consolidated_text
    
    def _detect_file_type(self, content: bytes, filename: str) -> str:
        """
        Detecta el tipo de archivo por magic bytes y extensión.
        
        Args:
            content: Contenido del archivo
            filename: Nombre del archivo
            
        Returns:
            Tipo detectado: 'pdf', 'excel', 'word', 'image', 'zip', 'unknown'
        """
        # Magic bytes detection
        if content.startswith(b'%PDF'):
            return 'pdf'
        elif content[:2] == b'PK':  # ZIP-based formats
            if filename.lower().endswith(('.xlsx', '.xls')):
                return 'excel'
            elif filename.lower().endswith(('.docx', '.doc')):
                return 'word'
            elif filename.lower().endswith('.zip'):
                return 'zip'
        elif content[:2] in [b'\xff\xd8', b'\x89P', b'GIF']:  # JPEG, PNG, GIF
            return 'image'
        
        # Fallback to extension
        ext = filename.lower().split('.')[-1]
        if ext in ['pdf']:
            return 'pdf'
        elif ext in ['xlsx', 'xls', 'csv']:
            return 'excel'
        elif ext in ['docx', 'doc']:
            return 'word'
        elif ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']:
            return 'image'
        elif ext in ['zip']:
            return 'zip'
        
        return 'unknown'
    
    def _extract_pdf(self, content: bytes) -> str:
        """Extrae texto de PDF."""
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"❌ PDF extraction error: {e}")
            return ""
    
    def _extract_excel(self, content: bytes) -> str:
        """Extrae texto de Excel."""
        try:
            import pandas as pd
            
            # Leer todas las hojas
            excel_file = pd.ExcelFile(io.BytesIO(content))
            text_parts = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheet_text = f"--- Sheet: {sheet_name} ---\n{df.to_string(index=False)}"
                text_parts.append(sheet_text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"❌ Excel extraction error: {e}")
            return ""
    
    def _extract_word(self, content: bytes) -> str:
        """Extrae texto de Word."""
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"❌ Word extraction error: {e}")
            return ""
    
    def _extract_image_ocr(self, content: bytes) -> str:
        """Extrae texto de imagen usando OCR."""
        if not self.use_ocr:
            logger.warning("⚠️ OCR disabled, skipping image")
            return ""
        
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image, lang='spa+eng')
            
            return text
            
        except Exception as e:
            logger.error(f"❌ OCR extraction error: {e}")
            return ""
    
    def _extract_zip(self, content: bytes) -> str:
        """Extrae y procesa archivos dentro de ZIP."""
        try:
            zip_file = zipfile.ZipFile(io.BytesIO(content))
            
            text_parts = []
            for file_info in zip_file.filelist:
                if file_info.is_dir():
                    continue
                
                try:
                    file_content = zip_file.read(file_info.filename)
                    file_data = {
                        'content': file_content,
                        'filename': file_info.filename
                    }
                    
                    # Recursión para extraer contenido del archivo
                    file_text = self.extract_from_files([file_data])
                    if file_text:
                        text_parts.append(file_text)
                        
                except Exception as e:
                    logger.error(f"❌ Error extracting {file_info.filename} from ZIP: {e}")
                    continue
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"❌ ZIP extraction error: {e}")
            return ""


# Singleton para reutilización
text_extractor = TextExtractor(
    use_ocr=os.getenv("RFX_USE_OCR", "true").lower() in {"1", "true", "yes", "on"},
    use_zip=os.getenv("RFX_USE_ZIP", "true").lower() in {"1", "true", "yes", "on"}
)
