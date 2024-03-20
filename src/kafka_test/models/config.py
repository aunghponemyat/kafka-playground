from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_topic: str = "infra3-topic"
    kafka_group_id: str = "infra3"
    kafka_bootstrap_servers: str = "localhost:9092"

    binder_api: str = "binder-api"

    sasl_mechanism: str = ""
    sasl_protocol: str = ""
    sasl_username: str = ""
    sasl_password: str = ""

    properties_file: str = "config"
    default_worker: str = "default_dhcp_worker"
    app: str = "lts"
    log_directory: str = "log"

    tidb_dsn: str = "mysql+pymysql://root@127.0.0.1:4000/ltsdb"
    tidb_dsn_async: str = "mysql+aiomysql://root@127.0.0.1:4000/ltsdb"
    tidb_read_timeout: int = 60
    tidb_write_timeout: int = 60
    tidb_pool_recycle: int = 3600

@lru_cache
def get_settings() -> Settings:
    settings = Settings(_env_file=".env")
    return settings
