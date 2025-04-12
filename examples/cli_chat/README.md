# CLI Chat Example

A command-line chat application demonstrating the use of pubsubbud for real-time communication. This example implements a multi-room chat system with a server and client components.

## Features

- Real-time chat using WebSocket communication
- Multiple chat rooms support
- Command-line interface with curses for better UI
- Docker support for easy deployment
- Redis-based message broker

## Components

### CLI Chat Client (`cli_chat_client.py`)
A curses-based terminal client that provides:
- Room-based chat functionality
- Command system (e.g., `:join room_name` to switch rooms)
- Real-time message updates
- User identification
- Message history display

### CLI Chat Server (`cli_chat_server.py`)
A WebSocket server that:
- Handles client connections
- Manages message routing between clients
- Uses Redis as a message broker
- Supports multiple chat rooms

## Commands

The chat client supports the following commands:
- `:join room_name` - Join a different chat room

## Requirements

- Python 3.11 or higher
- Poetry for dependency management
- Redis server (if running without Docker)
- curses library (usually included with Python)

## Running the Example

### Using Kubernetes with Minikube

1. Start your Minikube cluster:
```bash
minikube start
```

2. Configure your terminal to use Minikube's Docker daemon:
```bash
eval $(minikube docker-env)
```

3. Build the chat server Docker image:
```bash
docker build -t cli-chat-server:latest .
```

4. Apply the Kubernetes configurations:
```bash
kubectl apply -f cli_chat_server.yaml
kubectl apply -f ingress-svc.yaml
```

5. Enable the Ingress addon in Minikube:
```bash
minikube addons enable ingress
```

6. Get the Minikube IP:
```bash
minikube ip
```

7. Run the client locally (use the Minikube IP from step 6):
```bash
poetry run python cli_chat_client.py --host <minikube-ip>
```

Note: When using Minikube's Docker daemon, make sure your cli_chat_server.yaml references the image as `imagePullPolicy: Never` to use the locally built image.

### Using Docker Compose (Recommended)

1. Start the server and Redis:
```bash
docker-compose up
```

2. Run the client locally:
```bash
poetry run python cli_chat_client.py
```

### Manual Setup

1. Start a Redis server locally on port 6379

2. Start the chat server:
```bash
poetry run python cli_chat_server.py
```

3. Run the client:
```bash
poetry run python cli_chat_client.py
```

## Usage

1. When starting the client, you'll be prompted to enter your name
2. You'll start in the "lobby" room
3. To send a message, simply type and press Enter
4. To switch rooms, use the command `:join room_name`
5. Messages are displayed in real-time as they arrive
6. Your own messages are marked with "(You)"

## Configuration

The example uses several configuration files in the `configs/` directory:
- `redis_broker.json` - Redis connection settings
- `pubsub.json` - PubSub manager configuration
- `websocket_handler.json` - WebSocket handler settings

## Architecture

- The server uses pubsubbud's WebSocket handler and Redis broker for message handling
- Clients connect via WebSocket and subscribe to room-specific channels
- Messages are broadcast to all clients subscribed to the same room
- The client UI is built using Python's curses library for a better terminal experience

## Environment Variables

- `BROKER`: Set to "redis" (currently the only supported broker for this example)

## Network Ports

- WebSocket Server: 8765
- Redis: 6379

## Client Command-Line Interface

The client supports the following command-line arguments:
- `--host`: Specify the chat server host (default: localhost)
- `--port`: Specify the WebSocket port (default: 8765)
- `--name`: Set your username (if not provided, you'll be prompted)

Example usage:
```bash
# Connect to a specific host
poetry run python cli_chat_client.py --host chat.example.com

# Connect with a specific port and username
poetry run python cli_chat_client.py --port 9000 --name Alice
``` 