"""LLM client wrapper supporting Claude and OpenAI with caching and fallback."""

import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
from pathlib import Path


class LLMClient:
    """
    Wrapper for LLM APIs (Claude or OpenAI) with offline fallback.

    Supports:
    - ANTHROPIC_API_KEY for Claude
    - OPENAI_API_KEY for OpenAI
    - Automatic fallback between providers
    - Response caching
    - Offline fallback responses
    """

    def __init__(self, cache_path: Optional[Path] = None, prefer: str = "auto"):
        """
        Initialize LLM client.

        Args:
            cache_path: Path for response cache
            prefer: Preferred provider ("claude", "openai", "auto")
        """
        self._claude_client = None
        self._openai_client = None
        self._provider = None
        self._prefer = prefer

        if cache_path is None:
            cache_path = Path(__file__).parent.parent.parent / "data" / "coaching_cache.json"
        self.cache_path = cache_path
        self._cache: Optional[Dict] = None

    @property
    def available(self) -> bool:
        """Check if any LLM API is available."""
        return self.provider is not None

    @property
    def provider(self) -> Optional[str]:
        """Get the active provider name."""
        if self._provider is None:
            self._init_provider()
        return self._provider

    def _init_provider(self):
        """Initialize the best available provider."""
        # Check preferred provider first
        if self._prefer == "openai":
            if self._try_openai():
                return
            if self._try_claude():
                return
        elif self._prefer == "claude":
            if self._try_claude():
                return
            if self._try_openai():
                return
        else:  # auto - try OpenAI first (often already configured)
            if self._try_openai():
                return
            if self._try_claude():
                return

        self._provider = None

    def _try_claude(self) -> bool:
        """Try to initialize Claude client."""
        try:
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return False
            self._claude_client = anthropic.Anthropic(api_key=api_key)
            self._provider = "claude"
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _try_openai(self) -> bool:
        """Try to initialize OpenAI client."""
        try:
            from openai import OpenAI
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return False
            self._openai_client = OpenAI(api_key=api_key)
            self._provider = "openai"
            return True
        except ImportError:
            return False
        except Exception:
            return False

    @property
    def cache(self) -> Dict:
        """Lazy-load cache."""
        if self._cache is None:
            self._cache = self._load_cache()
        return self._cache

    def _load_cache(self) -> Dict:
        """Load response cache from file."""
        if not self.cache_path.exists():
            return {"responses": {}, "last_updated": None}

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"responses": {}, "last_updated": None}

    def _save_cache(self):
        """Save cache to file."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache["last_updated"] = datetime.now().isoformat()

        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def _get_cache_key(self, prompt: str, context: Dict) -> str:
        """Generate cache key from prompt and context."""
        import hashlib
        key_data = f"{prompt}:{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict] = None,
        max_tokens: int = 500,
        use_cache: bool = True,
        cache_ttl_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Generate a response using available LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User message
            context: Optional context for caching
            max_tokens: Maximum response tokens
            use_cache: Whether to use caching
            cache_ttl_hours: Cache validity in hours

        Returns:
            Response dictionary with 'text' and metadata
        """
        context = context or {}

        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(user_prompt, context)
            cached = self.cache.get("responses", {}).get(cache_key)

            if cached:
                cached_time = datetime.fromisoformat(cached.get("timestamp", "2000-01-01"))
                if datetime.now() - cached_time < timedelta(hours=cache_ttl_hours):
                    return {
                        "text": cached["text"],
                        "cached": True,
                        "model": cached.get("model", "unknown"),
                        "provider": cached.get("provider", "unknown"),
                    }

        # Try API call
        if not self.available:
            return self._get_fallback_response(user_prompt, context)

        try:
            if self._provider == "openai":
                return self._call_openai(system_prompt, user_prompt, max_tokens, use_cache)
            else:
                return self._call_claude(system_prompt, user_prompt, max_tokens, use_cache)

        except Exception as e:
            return {
                "text": self._get_fallback_response(user_prompt, context).get("text"),
                "cached": False,
                "error": str(e),
                "fallback": True,
            }

    def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        use_cache: bool,
    ) -> Dict[str, Any]:
        """Call Claude API."""
        response = self._claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text
        model = "claude-sonnet-4-20250514"

        # Cache the response
        if use_cache:
            cache_key = self._get_cache_key(user_prompt, {})
            self.cache.setdefault("responses", {})[cache_key] = {
                "text": text,
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "provider": "claude",
            }
            self._save_cache()

        return {
            "text": text,
            "cached": False,
            "model": model,
            "provider": "claude",
        }

    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        use_cache: bool,
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        response = self._openai_client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        text = response.choices[0].message.content
        model = "gpt-4o-mini"

        # Cache the response
        if use_cache:
            cache_key = self._get_cache_key(user_prompt, {})
            self.cache.setdefault("responses", {})[cache_key] = {
                "text": text,
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "provider": "openai",
            }
            self._save_cache()

        return {
            "text": text,
            "cached": False,
            "model": model,
            "provider": "openai",
        }

    def _get_fallback_response(
        self,
        prompt: str,
        context: Dict
    ) -> Dict[str, Any]:
        """
        Get a fallback response when API is unavailable.

        Uses pre-defined responses based on common patterns.
        """
        fallbacks = [
            "Cada momento de conversa com seu filho constroi conexoes importantes!",
            "Voce esta fazendo um otimo trabalho ao se conectar com seu filho.",
            "Lembre-se: nao precisa ser perfeito, so precisa estar presente.",
            "Continue conversando, narrando e respondendo - isso faz toda a diferenca!",
        ]

        import hashlib
        idx = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % len(fallbacks)

        return {
            "text": fallbacks[idx],
            "cached": False,
            "fallback": True,
            "provider": None,
        }


# Backwards compatibility alias
ClaudeClient = LLMClient
