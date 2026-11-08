import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
import paho.mqtt.client as mqtt
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_BROKER = "localhost"  
MQTT_PORT = 1883
MQTT_TOPIC = "fastapi/device/control"

# Global client holder or state container
mqtt_client: mqtt.Client | None = None


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Connected successfully to MQTT Broker!")
        client.subscribe("home/device/#")
    else:
        logger.error(f"Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    """Callback function to handle incoming MQTT messages."""
    topic = msg.topic
    try:
        payload = msg.payload.decode("utf-8")
    except UnicodeDecodeError:
        logger.error(f"Received non-UTF-8 payload on topic {topic}")
        return
    logger.info(f"incomming message ===> on topic {topic}")
    
    # Here you can add logic to process the incoming message, e.g., store it, trigger actions, etc.
    if topic == "home/device/watch":
        logger.info(f"Processing watch device message: {payload}")
        # Add your processing logic here
    
    if topic == "home/device/fridge":
        logger.info(f"Processing fridge device message: {payload}")
        # Add your processing logic here
    


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_client
    # Initialize Paho MQTT client (CallbackAPIVersion.VERSION2 is standard for modern paho-mqtt)
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fastapi_backend")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        # Start the background network loop thread to handle incoming/outgoing packets non-blocking
        mqtt_client.loop_start()
    except Exception as e:
        logger.warning(f"Could not connect to MQTT broker on startup: {e}")

    yield

    # Shutdown: Stop loop and disconnect cleanly
    if mqtt_client:
        logger.info("Disconnecting from MQTT broker...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


app = FastAPI(title="FastAPI MQTT Gateway", lifespan=lifespan)


class MessagePayload(BaseModel):
    message: str
    target_device: str


@app.post("/publish", status_code=status.HTTP_202_ACCEPTED)
async def publish_mqtt_message(payload: MessagePayload):
    """Publish a command or message to an MQTT topic."""
    global mqtt_client
    if not mqtt_client or not mqtt_client.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT broker is not connected.",
        )

    topic = f"home/device/{payload.target_device}/command"
    result = mqtt_client.publish(topic, payload.message, qos=1, retain=True)

    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish message. Error code: {result.rc}",
        )

    return {
        "status": "success",
        "topic": topic,
        "message": payload.message,
        "mid": result.mid,
    }


@app.get("/health/mqtt")
async def mqtt_health_check():
    """Check connection status to the MQTT broker."""
    global mqtt_client
    connected = mqtt_client.is_connected() if mqtt_client else False
    return {"mqtt_connected": connected, "broker": MQTT_BROKER, "port": MQTT_PORT}