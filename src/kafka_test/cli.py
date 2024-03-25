import click
import asyncio

from kafka_test.consumer import initialize
from kafka_test.models.config import Settings, get_settings
from kafka_test.utils import get_process
from kafka_test.producer import main as produce

settings: Settings = get_settings()

@click.group(invoke_without_command=True, no_args_is_help=True)
@click.version_option()
def entrypoint():
    pass

@entrypoint.command()
@click.option("--worker", type=click.STRING, default=get_process('kafka-test'), show_default=True)
def start_consumer(worker: str):
    """Consume Messages from the topic"""
    try:
        initialize(worker)
    except KeyboardInterrupt:
        pass

@entrypoint.command()
def run_producer():
    """Run Producer script to send messages to Kafka"""
    try:
        asyncio.run(produce)
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        pass


