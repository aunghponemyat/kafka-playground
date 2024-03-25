from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    properties_file: str = "config"
    default_worker: str = "default_dhcp_worker"
    log_filename: str = "log"

    tidb_dsn: str = "mysql+pymysql://root@127.0.0.1:4000/ltsdb"
    tidb_dsn_async: str = "mysql+aiomysql://root@127.0.0.1:4000/ltsdb"
    tidb_read_timeout: int = 60
    tidb_write_timeout: int = 60
    tidb_pool_recycle: int = 3600

@lru_cache
def get_settings() -> Settings:
    settings = Settings(_env_file=".env")
    return settings
