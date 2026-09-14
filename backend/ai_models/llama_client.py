import os
import re
import json
import time
import asyncio
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from groq import Groq
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

CACHE_SIZE = 100
CACHE_TTL = 3600          # 1 hour
MAX_RETRIES = 3
RETRY_DELAY = 1           # seconds
TIMEOUT = 30              # seconds


# ============================================================
# CACHE
# ============================================================

class TimeoutCache:
    """Simple TTL-based cache for inventory parse results."""

    def __init__(
        self,
        maxsize: int = CACHE_SIZE,
        ttl: int = CACHE_TTL
    ):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl

    def get(self, key: str) -> Optional[Dict[str, Any]]:

        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]

        # Expired entry
        if time.time() - timestamp >= self.ttl:
            del self.cache[key]
            return None

        self.cache.move_to_end(key)

        return value

    def set(
        self,
        key: str,
        value: Dict[str, Any]
    ):

        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = (
            value,
            time.time()
        )

        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()

    def size(self) -> int:
        return len(self.cache)


# Global cache
parse_cache = TimeoutCache()


# ============================================================
# LLAMA / GROQ CLIENT
# ============================================================

class LlamaClient:

    def __init__(self):

        self.api_key = os.getenv("GROQ_API_KEY")

        # Do not expose the API key in logs.
        if not self.api_key:
            logger.warning(
                "[LLAMA] GROQ_API_KEY is not configured. "
                "Local fallback parsing will be used."
            )

            self.client = None

        else:
            try:
                self.client = Groq(
                    api_key=self.api_key,
                    timeout=TIMEOUT
                )

                logger.info(
                    "[LLAMA] Groq client initialized successfully"
                )

            except Exception as e:

                self.client = None

                logger.exception(
                    "[LLAMA] Failed to initialize Groq client: %s",
                    e
                )

        # Keep your existing model for now.
        self.model = "llama3-8b-8192"

        self.temperature = 0.1

        self.max_tokens = 100

        # ----------------------------------------------------
        # Word -> number mapping
        # ----------------------------------------------------

        self.word_numbers = {

            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
            "twenty": 20,
            "thirty": 30,
            "forty": 40,
            "fifty": 50,
            "sixty": 60,
            "seventy": 70,
            "eighty": 80,
            "ninety": 90,
            "hundred": 100,
            "thousand": 1000,
            "dozen": 12,
            "score": 20,
            "gross": 144,
        }

        # ----------------------------------------------------
        # Stop words
        # ----------------------------------------------------

        self.stop_words = {
            "add",
            "remove",
            "delete",
            "stock",
            "buy",
            "purchase",
            "get",
            "want",
            "please",
            "kindly",
            "help",
            "need",
            "order",
            "place",
            "put",
            "take",
            "and",
            "or",
            "then",
            "also",
            "with",
            "for",
            "from",
            "to",
            "of",
            "the",
            "a",
            "an",
            "some",
            "more",
            "less",
            "extra",
            "additional",
        }

        # ----------------------------------------------------
        # Common item mappings
        # ----------------------------------------------------

        self.item_mappings = {

            "apple": "apple",
            "banana": "banana",
            "orange": "orange",
            "mango": "mango",
            "grape": "grape",
            "strawberry": "strawberry",

            "biscuit": "biscuit",
            "cookie": "cookie",
            "chocolate": "chocolate",

            "water": "water",
            "bottle": "bottle",
            "packet": "packet",

            "notebook": "notebook",
            "pen": "pen",
            "pencil": "pencil",
            "eraser": "eraser",
            "sharpener": "sharpener",
            "ruler": "ruler",
        }

        logger.info("[LLAMA] LlamaClient initialized")


    # ========================================================
    # CACHE KEY
    # ========================================================

    def _get_cache_key(self, text: str) -> str:
        """Generate deterministic cache key."""

        normalized = text.lower().strip()

        return hashlib.md5(
            normalized.encode("utf-8")
        ).hexdigest()


    # ========================================================
    # WORD TO NUMBER
    # ========================================================

    def _word_to_number(self, word: str) -> int:
        """Convert a number word to an integer."""

        return self.word_numbers.get(
            word.lower(),
            0
        )


    # ========================================================
    # COMPOUND NUMBER
    # ========================================================

    def _parse_compound_number(
        self,
        words: List[str],
        start_idx: int
    ) -> Tuple[int, int]:
        """Parse compound numbers such as 'twenty five'."""

        total = 0
        idx = start_idx

        while idx < len(words):

            word = words[idx]

            num = self.word_numbers.get(
                word,
                0
            )

            if num == 0:
                break

            # Example: twenty five
            if idx + 1 < len(words):

                next_word = words[idx + 1]

                next_num = self.word_numbers.get(
                    next_word,
                    0
                )

                if (
                    1 <= next_num <= 9
                    and num >= 20
                ):
                    total += num + next_num
                    idx += 2
                    continue

            total += num

            idx += 1

        return total, idx - start_idx


    # ========================================================
    # EXTRACT QUANTITY
    # ========================================================

    def _extract_quantity(self, text: str) -> int:
        """Extract quantity from text."""

        text_lower = text.lower()

        # ----------------------------------------------------
        # Digits first
        # ----------------------------------------------------

        digits = re.findall(
            r"\d+",
            text_lower
        )

        if digits:
            return max(
                1,
                sum(int(d) for d in digits)
            )

        # ----------------------------------------------------
        # Word numbers
        # ----------------------------------------------------

        words = re.findall(
            r"[a-z]+",
            text_lower
        )

        total = 0
        idx = 0

        while idx < len(words):

            # -----------------------------------------------
            # Compound number: twenty five
            # -----------------------------------------------

            if idx + 1 < len(words):

                first = self.word_numbers.get(
                    words[idx],
                    0
                )

                second = self.word_numbers.get(
                    words[idx + 1],
                    0
                )

                if (
                    first >= 20
                    and 1 <= second <= 9
                ):
                    total += first + second
                    idx += 2
                    continue

                # -------------------------------------------
                # five hundred
                # -------------------------------------------

                if second == 100 and first > 0:
                    total += first * 100
                    idx += 2
                    continue

                # -------------------------------------------
                # five thousand
                # -------------------------------------------

                if second == 1000 and first > 0:
                    total += first * 1000
                    idx += 2
                    continue

            num = self.word_numbers.get(
                words[idx],
                0
            )

            if num > 0:
                total += num

            idx += 1

        return total if total > 0 else 1


    # ========================================================
    # EXTRACT ITEM
    # ========================================================

    def _extract_item(self, text: str) -> str:
        """Extract and clean inventory item name."""

        text_lower = text.lower()

        # Remove punctuation
        text_lower = re.sub(
            r"[^\w\s]",
            "",
            text_lower
        )

        # Remove action/stop words
        for word in self.stop_words:

            text_lower = re.sub(
                rf"\b{re.escape(word)}\b",
                "",
                text_lower
            )

        # Remove digits
        text_lower = re.sub(
            r"\d+",
            "",
            text_lower
        )

        # Remove number words
        for word in self.word_numbers.keys():

            text_lower = re.sub(
                rf"\b{re.escape(word)}\b",
                "",
                text_lower
            )

        # Normalize whitespace
        text_lower = re.sub(
            r"\s+",
            " ",
            text_lower
        ).strip()

        if not text_lower:
            return "item"

        # Known mappings
        for key, value in self.item_mappings.items():

            if key in text_lower:
                return value

        # Plural -> singular
        if (
            text_lower.endswith("s")
            and len(text_lower) > 1
            and not text_lower.endswith("ss")
        ):

            if text_lower.endswith("ies"):

                text_lower = (
                    text_lower[:-3] + "y"
                )

            elif text_lower.endswith("ves"):

                text_lower = (
                    text_lower[:-3] + "f"
                )

            else:

                text_lower = text_lower[:-1]

        return (
            text_lower
            if len(text_lower) > 1
            else "item"
        )


    # ========================================================
    # MULTIPLE ITEMS
    # ========================================================

    def _parse_multiple_items(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """
        Parse multiple inventory items.
        """

        text_lower = text.lower()

        # Remove action words
        for word in self.stop_words:

            text_lower = re.sub(
                rf"\b{re.escape(word)}\b",
                "",
                text_lower
            )

        # Split on commas, ampersands or 'and'
        parts = re.split(
            r"\s+and\s+|[,&]+",
            text_lower
        )

        items = []

        for part in parts:

            part = part.strip()

            if not part:
                continue

            quantity = self._extract_quantity(
                part
            )

            item_name = self._extract_item(
                part
            )

            if item_name and item_name != "item":

                items.append({
                    "item": item_name,
                    "quantity": quantity,
                    "action": "add",
                })

        return items


    # ========================================================
    # MAIN INVENTORY EXTRACTION
    # ========================================================

    def extract_inventory(
        self,
        text: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Extract inventory information.

        Uses Groq when available and falls back to
        local parsing when the API is unavailable.
        """

        if not text or not text.strip():

            return {
                "item": "item",
                "quantity": 1,
                "action": "add",
            }

        text = text.strip()

        # ----------------------------------------------------
        # Cache
        # ----------------------------------------------------

        cache_key = self._get_cache_key(text)

        if use_cache:

            cached = parse_cache.get(
                cache_key
            )

            if cached is not None:

                logger.debug(
                    "[LLAMA] Cache hit: %s",
                    text[:50]
                )

                return cached

        # ----------------------------------------------------
        # Detect multiple items
        # ----------------------------------------------------

        has_comma = "," in text

        has_and = bool(
            re.search(
                r"\band\b",
                text.lower()
            )
        )

        multiple_numbers = (
            len(
                re.findall(
                    r"\d+",
                    text
                )
            ) > 1
        )

        if (
            has_comma
            or has_and
            or multiple_numbers
        ):

            items = self._parse_multiple_items(
                text
            )

            if len(items) > 1:

                result = {
                    "type": "multiple",
                    "items": items,
                }

                parse_cache.set(
                    cache_key,
                    result
                )

                return result

        # ----------------------------------------------------
        # Groq single-item extraction
        # ----------------------------------------------------

        if self.client is not None:

            for attempt in range(
                MAX_RETRIES
            ):

                try:

                    result = self._extract_single_item(
                        text
                    )

                    parse_cache.set(
                        cache_key,
                        result
                    )

                    return result

                except Exception as e:

                    logger.warning(
                        "[LLAMA] Attempt %d/%d failed: %s",
                        attempt + 1,
                        MAX_RETRIES,
                        e
                    )

                    if attempt < MAX_RETRIES - 1:

                        time.sleep(
                            RETRY_DELAY * (attempt + 1)
                        )

        # ----------------------------------------------------
        # Local fallback
        # ----------------------------------------------------

        logger.info(
            "[LLAMA] Using local fallback parser"
        )

        result = self._fallback_extract(
            text
        )

        parse_cache.set(
            cache_key,
            result
        )

        return result


    # ========================================================
    # GROQ SINGLE ITEM
    # ========================================================

    def _extract_single_item(
        self,
        text: str
    ) -> Dict[str, Any]:
        """Extract one inventory item using Groq."""

        if self.client is None:

            raise RuntimeError(
                "Groq client is not initialized"
            )

        prompt = f"""
Extract inventory information from:
"{text}"

Rules:
- Return ONLY valid JSON.
- Format:
  {{"item": "item_name", "quantity": number, "action": "add" or "remove"}}
- Item name should be singular.
- Default quantity is 1 if not specified.
- Default action is "add" unless remove/delete is mentioned.

Examples:
"add 5 apples"
-> {{"item": "apple", "quantity": 5, "action": "add"}}

"remove 2 oranges"
-> {{"item": "orange", "quantity": 2, "action": "remove"}}

"stock bananas"
-> {{"item": "banana", "quantity": 1, "action": "add"}}
"""

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=self.temperature,

            max_tokens=self.max_tokens,
        )

        # ----------------------------------------------------
        # Validate response
        # ----------------------------------------------------

        if (
            not response
            or not response.choices
        ):
            raise ValueError(
                "Groq returned an empty response"
            )

        result_text = (
            response
            .choices[0]
            .message
            .content
        )

        if not result_text:
            raise ValueError(
                "Groq returned empty content"
            )

        result_text = result_text.strip()

        # Remove Markdown code fences
        result_text = re.sub(
            r"^```json\s*",
            "",
            result_text,
            flags=re.IGNORECASE
        )

        result_text = re.sub(
            r"^```\s*",
            "",
            result_text
        )

        result_text = re.sub(
            r"\s*```$",
            "",
            result_text
        )

        result_text = result_text.strip()

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        result = json.loads(
            result_text
        )

        # ----------------------------------------------------
        # Normalize result
        # ----------------------------------------------------

        item = self._extract_item(
            str(
                result.get(
                    "item",
                    "item"
                )
            )
        )

        try:

            quantity = int(
                result.get(
                    "quantity",
                    1
                )
            )

        except (
            TypeError,
            ValueError
        ):

            quantity = 1

        quantity = max(
            1,
            quantity
        )

        action = str(
            result.get(
                "action",
                "add"
            )
        ).lower().strip()

        if action not in {
            "add",
            "remove"
        }:

            action = "add"

        return {
            "item": item,
            "quantity": quantity,
            "action": action,
        }


    # ========================================================
    # LOCAL FALLBACK
    # ========================================================

    def _fallback_extract(
        self,
        text: str
    ) -> Dict[str, Any]:
        """Extract inventory information without Groq."""

        text_lower = text.lower()

        # Determine action
        remove_words = {
            "remove",
            "delete",
            "take",
        }

        action = (
            "remove"
            if any(
                word in text_lower
                for word in remove_words
            )
            else "add"
        )

        quantity = self._extract_quantity(
            text_lower
        )

        item = self._extract_item(
            text_lower
        )

        return {
            "item": item,
            "quantity": quantity,
            "action": action,
        }


    # ========================================================
    # CACHE CONTROL
    # ========================================================

    def clear_cache(self):
        """Clear inventory parsing cache."""

        parse_cache.clear()

        logger.info(
            "[LLAMA] Parse cache cleared"
        )


    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""

        return {
            "size": parse_cache.size(),
            "max_size": CACHE_SIZE,
            "ttl_seconds": CACHE_TTL,
        }


# ============================================================
# SINGLETON
# ============================================================

llama = LlamaClient()


# ============================================================
# ASYNC WRAPPER
# ============================================================

async def extract_inventory_async(
    text: str
) -> Dict[str, Any]:
    """
    Async wrapper around inventory extraction.
    """

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        None,
        llama.extract_inventory,
        text
    )