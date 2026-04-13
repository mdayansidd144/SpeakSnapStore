import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
class LlamaClient:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    def _word_to_number(self, word: str) -> int:
        word_numbers = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
            'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
            'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
            'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
            'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
            'eighty': 80, 'ninety': 90
        }
        return word_numbers.get(word.lower(), 0)
    
    def _parse_multiple_items(self, text: str) -> list:
        """Parse multiple items from text like '10 toothpaste, 10 water bottles, 15 notebooks'"""
        text_lower = text.lower()
        
        # Remove common action words
        for word in ['add', 'stock', 'buy', 'purchase']:
            text_lower = text_lower.replace(word, '')
        
        items = []
        
        # Pattern 1: "10 toothpaste" (digit followed by item)
        pattern1 = r'(\d+)\s+([a-z\s]+?)(?=,|and|$|\.)'
        matches1 = re.findall(pattern1, text_lower)
        for quantity, item_name in matches1:
            item_name = item_name.strip().strip(',').strip()
            if item_name and len(item_name) > 1:
                items.append({
                    'item': item_name,
                    'quantity': int(quantity),
                    'action': 'add'
                })
        
        # Pattern 2: "ten toothpaste" (word number followed by item)
        if not items:
            words = text_lower.split()
            i = 0
            while i < len(words):
                num = self._word_to_number(words[i])
                if num > 0 and i + 1 < len(words):
                    item_parts = []
                    j = i + 1
                    while j < len(words) and not self._word_to_number(words[j]) > 0 and not re.match(r'\d+', words[j]):
                        if words[j] not in ['and', 'then', 'also']:
                            item_parts.append(words[j])
                        j += 1
                    
                    item_name = ' '.join(item_parts).strip().strip(',')
                    if item_name and len(item_name) > 1:
                        items.append({
                            'item': item_name,
                            'quantity': num,
                            'action': 'add'
                        })
                    i = j
                else:
                    i += 1
        
        return items
    
    def extract_inventory(self, text: str) -> dict:
        """Extract item and quantity - handles single or multiple items"""
        text_lower = text.lower().strip()
        
        # Check if this is a multiple items command (has commas or multiple numbers)
        has_comma = ',' in text_lower
        has_and = ' and ' in text_lower
        multiple_numbers = len(re.findall(r'\d+', text_lower)) > 1
        
        if has_comma or has_and or multiple_numbers:
            multiple_items = self._parse_multiple_items(text_lower)
            if len(multiple_items) > 1:
                return {
                    'type': 'multiple',
                    'items': multiple_items
                }
        
        # Single item parsing
        action = "add"
        if any(word in text_lower for word in ['remove', 'delete', 'take away']):
            action = "remove"
        
        # Extract quantity
        numbers = re.findall(r'\d+', text_lower)
        if numbers:
            quantity = sum(int(n) for n in numbers)
        else:
            # Try word numbers
            words = text_lower.split()
            quantity = 1
            for word in words:
                num = self._word_to_number(word)
                if num > 0:
                    quantity = num
                    break
        
        # Extract item name (remove numbers and action words)
        temp_text = text_lower
        for word in ['add', 'remove', 'delete', 'stock', 'more', 'less', 'buy', 'purchase']:
            temp_text = temp_text.replace(word, '')
        
        # Remove digits
        temp_text = re.sub(r'\d+', '', temp_text)
        
        # Remove number words
        number_words = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                       'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen',
                       'eighteen', 'nineteen', 'twenty']
        for word in number_words:
            temp_text = temp_text.replace(word, '')
        
        # Remove punctuation and extra spaces
        temp_text = re.sub(r'[^\w\s]', '', temp_text)
        temp_text = re.sub(r'\s+', ' ', temp_text).strip()
        
        # Convert plural to singular
        if temp_text.endswith('s') and len(temp_text) > 1 and not temp_text.endswith('ss'):
            temp_text = temp_text[:-1]
        
        return {
            'type': 'single',
            'item': temp_text if temp_text else 'item',
            'quantity': quantity if quantity > 0 else 1,
            'action': action
        }

llama = LlamaClient()