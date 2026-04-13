import os
import re
import json
import time
import asyncio
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
from collections import OrderedDict
import logging
from groq import Groq
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

CACHE_SIZE = 100
CACHE_TTL = 3600  # 1 hour
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
TIMEOUT = 30  # seconds

# ==================== CACHE IMPLEMENTATION ====================

class TimeoutCache:
    """Simple TTL-based cache for parse results"""
    def __init__(self, maxsize: int = CACHE_SIZE, ttl: int = CACHE_TTL):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Dict]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Dict):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time())
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)
    
    def clear(self):
        self.cache.clear()
    
    def size(self) -> int:
        return len(self.cache)

# Global cache instance
parse_cache = TimeoutCache()

# ==================== LLAMA CLIENT ====================

class LlamaClient:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama3-8b-8192"
        self.temperature = 0.1
        self.max_tokens = 100
        
        # Extended word to number mapping
        self.word_numbers = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
            'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
            'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
            'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
            'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
            'eighty': 80, 'ninety': 90, 'hundred': 100, 'thousand': 1000,
            'dozen': 12, 'score': 20, 'gross': 144
        }
        
        # Common stop words to filter
        self.stop_words = {
            'add', 'remove', 'delete', 'stock', 'buy', 'purchase', 'get', 'want',
            'please', 'kindly', 'help', 'need', 'order', 'place', 'put', 'take',
            'and', 'or', 'then', 'also', 'with', 'for', 'from', 'to', 'of', 'the',
            'a', 'an', 'some', 'more', 'less', 'extra', 'additional'
        }
        
        # Common item name mappings
        self.item_mappings = {
            'apple': 'apple', 'banana': 'banana', 'orange': 'orange',
            'mango': 'mango', 'grape': 'grape', 'strawberry': 'strawberry',
            'biscuit': 'biscuit', 'cookie': 'cookie', 'chocolate': 'chocolate',
            'water': 'water', 'bottle': 'bottle', 'packet': 'packet',
            'notebook': 'notebook', 'pen': 'pen', 'pencil': 'pencil',
            'eraser': 'eraser', 'sharpener': 'sharpener', 'ruler': 'ruler'
        }
        
        logger.info("LlamaClient initialized")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        return hashlib.md5(text.lower().strip().encode()).hexdigest()
    
    def _word_to_number(self, word: str) -> int:
        """Convert word to number with support for compound numbers"""
        word = word.lower()
        
        # Direct mapping
        if word in self.word_numbers:
            return self.word_numbers[word]
        
        # Handle "twenty five" pattern (handled in parse method)
        return 0
    
    def _parse_compound_number(self, words: List[str], start_idx: int) -> Tuple[int, int]:
        """Parse compound numbers like 'twenty five'"""
        total = 0
        idx = start_idx
        
        while idx < len(words):
            word = words[idx]
            num = self.word_numbers.get(word, 0)
            
            if num == 0:
                break
            
            # Handle "twenty five" pattern
            if idx + 1 < len(words):
                next_word = words[idx + 1]
                next_num = self.word_numbers.get(next_word, 0)
                if 1 <= next_num <= 9 and num >= 20:
                    total += num + next_num
                    idx += 2
                    continue
            
            total += num
            idx += 1
        
        return total, idx - start_idx
    
    def _extract_quantity(self, text: str) -> int:
        """Extract quantity with support for compound numbers"""
        text_lower = text.lower()
        
        # Find digits first
        digits = re.findall(r'\d+', text_lower)
        if digits:
            return sum(int(d) for d in digits)
        
        # Parse word numbers
        words = text_lower.split()
        total = 0
        idx = 0
        
        while idx < len(words):
            # Check for compound numbers
            if idx + 1 < len(words):
                # Check for "twenty five" pattern
                first = self.word_numbers.get(words[idx], 0)
                second = self.word_numbers.get(words[idx + 1], 0)
                
                if first >= 20 and 1 <= second <= 9:
                    total += first + second
                    idx += 2
                    continue
                
                # Check for "hundred", "thousand"
                if second == 100 and first > 0:
                    total += first * 100
                    idx += 2
                    continue
                if second == 1000 and first > 0:
                    total += first * 1000
                    idx += 2
                    continue
            
            num = self.word_numbers.get(words[idx], 0)
            if num > 0:
                total += num
            idx += 1
        
        return total if total > 0 else 1
    
    def _extract_item(self, text: str) -> str:
        """Extract item name with better cleaning"""
        text_lower = text.lower()
        
        # Remove punctuation
        text_lower = re.sub(r'[^\w\s]', '', text_lower)
        
        # Remove action words
        for word in self.stop_words:
            text_lower = re.sub(rf'\b{word}\b', '', text_lower)
        
        # Remove digits
        text_lower = re.sub(r'\d+', '', text_lower)
        
        # Remove number words
        for word in self.word_numbers.keys():
            text_lower = re.sub(rf'\b{word}\b', '', text_lower)
        
        # Clean up spaces
        text_lower = re.sub(r'\s+', ' ', text_lower).strip()
        
        if not text_lower:
            return "item"
        
        # Check for known mappings
        for key, value in self.item_mappings.items():
            if key in text_lower:
                return value
        
        # Convert plural to singular
        if text_lower.endswith('s') and len(text_lower) > 1 and not text_lower.endswith('ss'):
            if text_lower.endswith('ies'):
                text_lower = text_lower[:-3] + 'y'
            elif text_lower.endswith('ves'):
                text_lower = text_lower[:-3] + 'f'
            else:
                text_lower = text_lower[:-1]
        
        return text_lower if len(text_lower) > 1 else "item"
    
    def _parse_multiple_items(self, text: str) -> List[Dict[str, Any]]:
        """Parse multiple items from text (comma or 'and' separated)"""
        text_lower = text.lower()
        
        # Remove common action words
        for word in self.stop_words:
            text_lower = re.sub(rf'\b{word}\b', '', text_lower)
        
        # Split by commas or 'and'
        separators = r'[ ,&]+|\s+and\s+'
        parts = re.split(separators, text_lower)
        
        items = []
        current_quantity = 1
        current_item_parts = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check if part contains a number
            if re.search(r'\d+', part) or any(w in part for w in self.word_numbers.keys()):
                # This part has a number - save previous item
                if current_item_parts:
                    item_name = ' '.join(current_item_parts).strip()
                    if item_name and len(item_name) > 1:
                        items.append({
                            'item': self._extract_item(item_name),
                            'quantity': current_quantity,
                            'action': 'add'
                        })
                    current_item_parts = []
                
                # Extract quantity from this part
                current_quantity = self._extract_quantity(part)
                
                # Extract item name from remaining text
                remaining = re.sub(r'\d+', '', part)
                for word in self.word_numbers.keys():
                    remaining = re.sub(rf'\b{word}\b', '', remaining)
                remaining = remaining.strip()
                if remaining:
                    current_item_parts.append(remaining)
            else:
                # This is part of an item name
                current_item_parts.append(part)
        
        # Save last item
        if current_item_parts:
            item_name = ' '.join(current_item_parts).strip()
            if item_name and len(item_name) > 1:
                items.append({
                    'item': self._extract_item(item_name),
                    'quantity': current_quantity,
                    'action': 'add'
                })
        
        return items
    
    def extract_inventory(self, text: str, use_cache: bool = True) -> Dict[str, Any]:
        """Extract inventory information with caching and retry logic"""
        text = text.strip()
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        if use_cache:
            cached = parse_cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for: {text[:50]}...")
                return cached
        
        # Check for multiple items
        has_comma = ',' in text
        has_and = ' and ' in text
        multiple_numbers = len(re.findall(r'\d+', text)) > 1
        
        if has_comma or has_and or multiple_numbers:
            items = self._parse_multiple_items(text)
            if len(items) > 1:
                result = {
                    'type': 'multiple',
                    'items': items
                }
                parse_cache.set(cache_key, result)
                return result
        
        # Single item parsing with retries
        for attempt in range(MAX_RETRIES):
            try:
                result = self._extract_single_item(text)
                parse_cache.set(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    # Fallback to local parsing
                    result = self._fallback_extract(text)
                    parse_cache.set(cache_key, result)
                    return result
        
        return self._fallback_extract(text)
    
    def _extract_single_item(self, text: str) -> Dict[str, Any]:
        """Extract single item using Groq API"""
        prompt = f"""Extract inventory information from: "{text}"

Rules:
- Return ONLY valid JSON
- Format: {{"item": "item_name", "quantity": number, "action": "add" or "remove"}}
- Item name should be singular
- Default quantity is 1 if not specified
- Default action is "add" unless remove/delete is mentioned

Examples:
"add 5 apples" -> {{"item": "apple", "quantity": 5, "action": "add"}}
"remove 2 oranges" -> {{"item": "orange", "quantity": 2, "action": "remove"}}
"stock bananas" -> {{"item": "banana", "quantity": 1, "action": "add"}}
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        result_text = response.choices[0].message.content
        result_text = re.sub(r'```json\n?', '', result_text)
        result_text = re.sub(r'```', '', result_text)
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        # Validate and clean result
        return {
            "item": self._extract_item(result.get("item", "item")),
            "quantity": max(1, result.get("quantity", 1)),
            "action": "add" if result.get("action", "add") != "remove" else "remove"
        }
    
    def _fallback_extract(self, text: str) -> Dict[str, Any]:
        """Fallback extraction using regex"""
        text_lower = text.lower()
        
        # Determine action
        action = "remove" if any(w in text_lower for w in ['remove', 'delete', 'take']) else "add"
        
        # Extract quantity
        quantity = self._extract_quantity(text_lower)
        
        # Extract item
        item = self._extract_item(text_lower)
        
        return {
            "item": item,
            "quantity": quantity,
            "action": action
        }
    
    def clear_cache(self):
        """Clear the parse cache"""
        parse_cache.clear()
        logger.info("Parse cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": parse_cache.size(),
            "max_size": CACHE_SIZE,
            "ttl_seconds": CACHE_TTL
        }

# Create singleton instance
llama = LlamaClient()

# Async wrapper
async def extract_inventory_async(text: str) -> Dict[str, Any]:
    """Async wrapper for extract_inventory"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, llama.extract_inventory, text)