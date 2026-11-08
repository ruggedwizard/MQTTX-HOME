# MQTTX-HOME - FastAPI MQTT Gateway

A lightweight, asynchronous gateway service built with **FastAPI** and **Paho-MQTT** to bridge HTTP REST APIs with MQTT-enabled smart home/IoT devices.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
  - [Architecture Diagram](#architecture-diagram)
  - [Message Flow](#message-flow)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation Procedure](#installation-procedure)
  - [Option A: Using `uv` (Recommended)](#option-a-using-uv-recommended)
  - [Option B: Using Standard Python & `pip`](#option-b-using-standard-python--pip)
- [Running the Application](#running-the-application)
  - [1. Start an MQTT Broker](#1-start-an-mqtt-broker)
  - [2. Start the FastAPI Server](#2-start-the-fastapi-server)
- [API Reference & Usage](#api-reference--usage)
  - [Health Check](#1-mqtt-health-check)
  - [Publish Command to Device](#2-publish-command-to-device)
  - [Interactive API Docs](#3-interactive-api-docs)
- [Testing with MQTT Clients (e.g., MQTTX / Mosquitto)](#testing-with-mqtt-clients-eg-mqttx--mosquitto)
- [Configuration](#configuration)
- [Project Structure](#project-structure)

---

## Overview

`MQTTX-HOME` is designed to act as a bridge between web clients (mobile apps, web dashboards, microservices) and local IoT/home automation devices communicating over MQTT. 

With this service, you can:
- Send HTTP `POST` requests to trigger device commands via MQTT.
- Listen for inbound telemetry/status messages published by IoT devices and process them within the application.
- Check the connectivity health of the MQTT broker connection.

---

## How It Works

### Architecture Diagram

```mermaid
flowchart LR
    Client[HTTP Client / Frontend] -->|POST /publish| FastAPI[FastAPI Gateway\nmain.py]
    FastAPI -->|GET /health/mqtt| Client
    FastAPI <-->|MQTT Pub/Sub\nPort 1883| Broker[(MQTT Broker\nMosquitto / EMQX)]
    Broker <-->|Sub: home/device/{id}/command| Devices[Smart Devices\nWatch, Fridge, etc.]
    Devices <-->|Pub: home/device/{id}| Broker
```

### Message Flow

1. **Lifespan Initialization (`lifespan`)**:
   - When FastAPI starts, it instantiates a Paho MQTT Client (v2 callback API).
   - Establishes a TCP connection to the MQTT broker (`MQTT_BROKER:MQTT_PORT`).
   - Spawns a background thread loop (`loop_start()`) to process incoming and outgoing MQTT packets without blocking FastAPI's async event loop.
   - Subscribes to the wildcard topic: `home/device/#`.

2. **Publishing Commands (`POST /publish`)**:
   - Clients send an HTTP request with a `target_device` and a `message`.
   - The gateway constructs an MQTT topic: `home/device/{target_device}/command`.
   - Publishes the message with **QoS 1** and **Retain = True**, ensuring the broker stores the message for the target device even if it is momentarily offline.

3. **Handling Incoming Device Messages (`on_message`)**:
   - When devices publish status updates to `home/device/{device_name}` (e.g. `home/device/watch` or `home/device/fridge`), the `on_message` callback receives the payload.
   - The payload is decoded as UTF-8, logged, and routed to specific handling logic based on the topic.

4. **Graceful Shutdown**:
   - Upon FastAPI server shutdown, the lifespan context manager stops the background MQTT network loop (`loop_stop()`) and disconnects cleanly from the broker.

---

## Features

- **FastAPI Framework**: High performance, type safety with Pydantic validation, and auto-generated Swagger UI docs.
- **Paho-MQTT v2**: Modern client API with non-blocking threaded network loop.
- **Bi-directional Communication**: REST-to-MQTT publishing and MQTT subscription ingestion.
- **Health Monitoring**: Dedicated `/health/mqtt` endpoint for readiness and liveness probes.

---

## Prerequisites

1. **Python**: Python `>= 3.14` (or `>= 3.10` compatible).
2. **MQTT Broker**: A running MQTT broker such as [Eclipse Mosquitto](https://mosquitto.org/), [EMQX](https://www.emqx.io/), or a Docker container.
3. **Package Manager**: [uv](https://docs.astral.sh/uv/) (recommended) or standard `pip`.

---

## Installation Procedure

### Option A: Using `uv` (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd MQTTX-HOME
   ```

2. **Sync dependencies**:
   ```bash
   uv sync
   ```
   This will automatically create a virtual environment (`.venv`) and install all pinned dependencies from `uv.lock`.

---

### Option B: Using Standard Python & `pip`

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd MQTTX-HOME
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -e .
   ```
   *Alternatively, install directly:*
   ```bash
   pip install "fastapi[standard]>=0.162.2" "paho-mqtt>=2.2.0" "pydantic-settings>=2.16.2" "uvicorn>=0.54.0"
   ```

---

## Running the Application

### 1. Start an MQTT Broker

If you do not have an MQTT broker running locally, you can start one using Docker:

```bash
docker run -d --name mosquitto -p 1883:1883 eclipse-mosquitto
```

Or start a local Mosquitto service:
- **Windows**: `net start mosquitto` or run `mosquitto -v`
- **Linux / macOS**: `brew services start mosquitto` or `sudo systemctl start mosquitto`

### 2. Start the FastAPI Server

- **Using `uv`**:
  ```bash
  uv run uvicorn main:app --reload --port 8000
  ```

- **Using activated virtual environment (`pip`)**:
  ```bash
  uvicorn main:app --reload --port 8000
  ```

The server will be accessible at `http://127.0.0.1:8000`.

---

## API Reference & Usage

### 1. MQTT Health Check

Check whether the gateway is successfully connected to the MQTT broker.

- **Endpoint**: `GET /health/mqtt`
- **Example Request**:
  ```bash
  curl -X GET http://127.0.0.1:8000/health/mqtt
  ```
- **Example Response**:
  ```json
  {
    "mqtt_connected": true,
    "broker": "localhost",
    "port": 1883
  }
  ```

---

### 2. Publish Command to Device

Publish a command or message to an MQTT-connected device.

- **Endpoint**: `POST /publish`
- **Status Code**: `202 Accepted`
- **Request Body**:
  ```json
  {
    "target_device": "watch",
    "message": "power_off"
  }
  ```
- **Example Request**:
  ```bash
  curl -X POST http://127.0.0.1:8000/publish \
    -H "Content-Type: application/json" \
    -d "{\"target_device\": \"watch\", \"message\": \"power_off\"}"
  ```
- **Example Response**:
  ```json
  {
    "status": "success",
    "topic": "home/device/watch/command",
    "message": "power_off",
    "mid": 1
  }
  ```

---

### 3. Interactive API Docs

Once the server is running, you can explore and test the endpoints directly via your browser:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Testing with MQTT Clients (e.g., MQTTX / Mosquitto)

You can verify the bridge using desktop tools like [MQTTX](https://mqttx.app/) or Mosquitto CLI tools:

1. **Listen for Device Commands**:
   Subscribe to `home/device/+/command`:
   ```bash
   mosquitto_sub -h localhost -p 1883 -t "home/device/+/command"
   ```
   When you send a `POST /publish` request to `/publish` with `target_device="watch"`, the command will appear here.

2. **Simulate a Device Sending Data**:
   Publish a status message from a simulated device:
   ```bash
   mosquitto_pub -h localhost -p 1883 -t "home/device/watch" -m '{"battery": 85, "heart_rate": 72}'
   ```
   Check the FastAPI application terminal logs to observe the inbound message:
   ```text
   INFO:main:incomming message ===> on topic home/device/watch
   INFO:main:Processing watch device message: {"battery": 85, "heart_rate": 72}
   ```

---

## Configuration

Default connection values are defined in `main.py`:

```python
MQTT_BROKER = "localhost"  # Hostname or IP of the MQTT broker
MQTT_PORT = 1883           # Broker port (standard MQTT default: 1883)
MQTT_TOPIC = "fastapi/device/control"
```

> **Tip**: You can extend these settings using environment variables or a `.env` file with `pydantic-settings`.

---

## Project Structure

```text
MQTTX-HOME/
├── .gitignore
├── .python-version    # Specified Python version (e.g., 3.14)
├── pyproject.toml     # Project configuration and dependency specifications
├── uv.lock            # Lockfile for reproducible dependencies
├── main.py            # FastAPI app and MQTT client logic
└── README.md          # Project documentation
```
