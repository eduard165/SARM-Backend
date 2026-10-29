from dataclasses import dataclass
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    publishable_key: str
    secret_key: str
    app_env: str

    def ensure_public(self) -> None:
        if not self.supabase_url.startswith('https://') or not self.publishable_key.startswith(('sb_publishable_', 'eyJ')) or 'REEMPLAZAR' in self.publishable_key:
            raise RuntimeError('Configura SUPABASE_URL y SUPABASE_PUBLISHABLE_KEY en .env')

    def ensure_admin(self) -> None:
        self.ensure_public()
        if not self.secret_key.startswith(('sb_secret_', 'eyJ')) or 'REEMPLAZAR' in self.secret_key:
            raise RuntimeError('Configura SUPABASE_SECRET_KEY en .env')


@lru_cache
def get_settings() -> Settings:
    return Settings(
        supabase_url=os.getenv('SUPABASE_URL', '').rstrip('/'),
        publishable_key=os.getenv('SUPABASE_PUBLISHABLE_KEY', ''),
        secret_key=os.getenv('SUPABASE_SECRET_KEY', ''),
        app_env=os.getenv('APP_ENV', 'development'),
    )
