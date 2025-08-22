"""
📝 Text Processing Utilities - Reusable text processing functions
Text cleaning, chunking, and formatting utilities
"""
import re
from typing import List, Optional


def chunk_text(text: str, max_tokens: int = 100000) -> List[str]:
    """
    Split text into chunks for GPT-4o's 128k context window
    Optimized for much larger chunks to preserve context
    
    🚀 GPT-4o OPTIMIZED: 
    - Default 100k tokens per chunk (vs old 500 words)
    - Estimates ~1.3 tokens per word (more accurate)
    - With 128k context, we have room for 25k prompt + 100k text + 3k response
    - Fewer chunks = better context preservation = better extraction
    """
    if not text or not text.strip():
        return []
    
    # Clean the text first
    cleaned_text = clean_text(text)
    
    # 🚀 GPT-4o: Estimate tokens more accurately (1.3 tokens per word)
    estimated_tokens = int(len(cleaned_text.split()) * 1.3)
    
    # If the entire text fits in one chunk (common with 128k context), return as-is
    if estimated_tokens <= max_tokens:
        return [cleaned_text]
    
    # Calculate target words per chunk based on token limit
    target_words_per_chunk = int(max_tokens / 1.3)  # Convert tokens back to words
    
    # Split into sentences first (try to keep sentences together)
    sentences = re.split(r'[.!?]+\s+', cleaned_text)
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Count words in this sentence
        sentence_words = len(sentence.split())
        
        # If adding this sentence would exceed the limit, start a new chunk
        if current_word_count + sentence_words > target_words_per_chunk and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_word_count = sentence_words
        else:
            current_chunk.append(sentence)
            current_word_count += sentence_words
    
    # Add the last chunk if it has content
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # If no sentences were found, fall back to word-based chunking
    if not chunks:
        return chunk_by_words(cleaned_text, target_words_per_chunk)
    
    return chunks


def chunk_by_words(text: str, max_words: int) -> List[str]:
    """Fallback chunking method that splits by words (optimized for GPT-4o)"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), max_words):
        chunk = ' '.join(words[i:i + max_words])
        chunks.append(chunk)
    
    return chunks


def clean_text(text: str) -> str:
    """
    Clean text for processing
    - Remove extra whitespace
    - Normalize line breaks
    - Remove special characters that might interfere with AI processing
    """
    if not text:
        return ""
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters (except tabs and newlines)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Remove excessive punctuation
    text = re.sub(r'[.]{3,}', '...', text)
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)
    
    return text.strip()


def clean_json_string(json_str: str) -> str:
    """
    Clean a JSON string to make it more likely to parse correctly
    Removes common issues that cause JSON parsing to fail
    """
    if not json_str:
        return json_str
    
    # Remove control characters
    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
    
    # Remove trailing commas before } or ]
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    # Remove comments (// or /* */)
    json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # Fix common quote issues
    # Replace smart quotes with regular quotes
    json_str = json_str.replace('"', '"').replace('"', '"')
    json_str = json_str.replace(''', "'").replace(''', "'")
    
    # Ensure proper quote escaping in string values
    # This is a simple fix - for more complex cases, a proper JSON parser would be needed
    json_str = re.sub(r'(?<!\\)"(?![,}\]\s])', r'\\"', json_str)
    
    return json_str.strip()


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extract keywords from text
    Returns list of unique words longer than min_length
    """
    if not text:
        return []
    
    # Convert to lowercase and extract words
    words = re.findall(r'\b[a-záéíóúñü]+\b', text.lower())
    
    # Filter by length and common stop words
    stop_words = {
        'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 
        'le', 'da', 'su', 'por', 'son', 'con', 'del', 'las', 'al', 'una', 'para',
        'son', 'los', 'me', 'si', 'ya', 'tu', 'muy', 'más', 'todo', 'esta', 'este'
    }
    
    keywords = []
    for word in words:
        if len(word) >= min_length and word not in stop_words:
            keywords.append(word)
    
    # Return unique keywords maintaining order
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)
    
    return unique_keywords


def format_currency(amount: float, currency: str = "MXN") -> str:
    """Format amount as currency"""
    if currency.upper() == "MXN":
        return f"${amount:,.2f} MXN"
    else:
        return f"{amount:,.2f} {currency}"


def format_product_list(products: List[dict]) -> str:
    """
    Format a list of products for display
    Returns a formatted string representation
    """
    if not products:
        return "No products"
    
    formatted_products = []
    for product in products:
        nombre = product.get('nombre', 'Producto')
        cantidad = product.get('cantidad', 1)
        unidad = product.get('unidad', 'unidades')
        
        formatted_products.append(f"• {nombre}: {cantidad} {unidad}")
    
    return '\n'.join(formatted_products)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max_length characters, adding suffix if truncated
    Tries to break at word boundaries
    """
    if not text or len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix
    
    # Find the last space before max_length - len(suffix)
    truncate_at = max_length - len(suffix)
    last_space = text.rfind(' ', 0, truncate_at)
    
    if last_space > 0:
        return text[:last_space] + suffix
    else:
        return text[:truncate_at] + suffix


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text"""
    if not text:
        return ""
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    return text.strip()
