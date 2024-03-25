import asyncio
import json

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from kafka_test.models.config import Settings, get_settings
from kafka_test.utils import parse_properties

settings: Settings = get_settings()

async def send_payload(data):
    try:
        kafka_config = parse_properties(settings.properties_file)
        producer = AIOKafkaProducer(
            bootstrap_servers=kafka_config['bootstrap_servers'],
            key_serializer=lambda x: x.encode('utf-8'),
            value_serializer=lambda m: json.dumps(m).encode('utf-8'),
        )
        await producer.start()

        key = data.get("hwaddr")
        try:
            await producer.send_and_wait(kafka_config['topic'], data, key=key)
            print("Data sent!")
        except KafkaError as e:
            # Decide what to do if produce request failed...
            print(f'Error: {e}')
        finally:
            await producer.stop()

        return {"message": "Data sent to Kafka!"}
    except KeyboardInterrupt:
        pass

async def main():
    try:
        with open('sample/payload.json', 'r') as file:
            data = json.load(file)
            for item in data:
                await send_payload(item)
                # time.sleep(5)
    except FileNotFoundError as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
