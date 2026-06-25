# 🚀 FWG Autonomous Intelligence Operating System (AI-OS)

## 1. Executive Summary

This document serves as the official blueprint and technical guide for the **FWG Autonomous Intelligence Operating System (AI-OS)**, a production-grade, fully autonomous AI ecosystem. The system was designed and built over a series of 30+ architectural phases, evolving from a basic recommendation engine into a sophisticated, self-learning, and self-operating intelligence platform.

The core mission of the AI-OS is to autonomously achieve high-level goals by planning, executing tasks with intelligent agents, learning from feedback, and persisting its knowledge. It is built on a modern, scalable microservices architecture using Python, FastAPI, Docker, and a suite of production-ready databases (PostgreSQL, Redis, Qdrant).

---

## 2. Final System Architecture

The AI-OS is built upon a layered, modular architecture. Each layer represents a distinct set of capabilities, built upon the foundation of the layer below it.

![AI-OS Architecture Diagram](https'://i.imgur.com/your-diagram-image.png') <!-- Placeholder for a real diagram -->

#### Architectural Layers:

1.  **Data & Infrastructure Layer (`Phases 1, 8, 17, 28`):**
    *   **Core Services:** PostgreSQL (Persistence), Redis (State/Cache), Qdrant (Vector Memory).
    *   **Containerization:** Docker & Docker Compose for consistent, reproducible environments.
    *   **Deployment:** Designed for Kubernetes with a distributed architecture in mind (`Distributed Inference Engine`).

2.  **Core Recommendation Engine (`Phases 2, 3, 4, 7`):**
    *   **`DiscoveryEngine`:** A concurrent, multi-source engine (YouTube, Reddit) to find content candidates.
    *   **`RankingEngine`:** A multi-factor system that scores content based on popularity, engagement, freshness, etc.
    *   **`PersonalizationEngine`:** Applies a personalization bonus based on user interest profiles stored in Redis.
    *   **`MultimodalEngine`:** Understands and processes text, image, and audio inputs into a unified semantic space.

3.  **Real-Time Learning System (`Phases 5, 15, 26`):**
    *   **Event-Driven:** An API endpoint (`/v1/feedback`) accepts user interaction events (likes, skips, watch time).
    *   **`RewardEngine`:** Translates user events into positive or negative numerical rewards.
    *   **`OnlineLearning`:** Updates user interest profiles in real-time based on rewards.
    *   **Asynchronous Processing:** A Celery-based worker system processes feedback events in the background, ensuring the API remains fast.

4.  **LLM Orchestration Brain (`Phases 9, 21`):**
    *   **`LLMOrchestrator`:** The central reasoning core of the system.
    *   **RAG (Retrieval-Augmented Generation):** Before answering, the brain retrieves relevant context from the Qdrant vector database to provide accurate, fact-based responses.
    *   **`ToolPlanner` & `LLMRouter`:** Intelligently decides whether to use an external tool or which LLM (e.g., GPT-4o, Claude 3.5) is best suited for a given task.

5.  **Autonomous Operating System (`Phases 10, 22-24, 30`):**
    *   **`AutonomousLoop`:** The main control loop that orchestrates the entire goal-achievement process.
    *   **Plan-Execute-Reflect:**
        1.  **`TaskPlanner`:** Decomposes high-level user goals into a series of smaller, actionable tasks.
        2.  **`Executor`:** Dispatches these tasks to the Celery worker system for intelligent execution by the LLM brain.
        3.  **`ReflectionEngine`:** Evaluates the outcome of the entire process to enable self-improvement.

---

## 3. Getting Started & Launching the System

### Prerequisites
*   Docker & Docker Compose installed.
*   A clean environment (e.g., a new GitHub Codespace).

### The One-Shot Launch Command
This single command block will configure the environment, install dependencies, and launch the entire AI-OS. Run this in the root directory of the project in a **clean Codespace**.

```bash
# This script is the definitive way to launch the system in a Codespace environment.

# STEP 1: Stop the default Docker service.
echo "--> STEP 1/5: Stopping default Docker service..."
sudo systemctl stop docker
sudo pkill dockerd
sleep 2

# STEP 2: Manually start a new Docker daemon on the /tmp partition.
echo "--> STEP 2/5: Starting new Docker daemon on the 40GB /tmp partition..."
nohup sudo dockerd --data-root /tmp/docker-data &
sleep 5

# STEP 3: Verify the new daemon is operational.
echo "--> STEP 3/5: Verifying new daemon..."
if ! sudo docker info | grep "Docker Root Dir: /tmp/docker-data"; then
    echo "--> FATAL ERROR: Docker daemon failed to start on /tmp. Aborting."
    exit 1
fi
echo "✅ Verification successful. Docker is running on /tmp."

# STEP 4: Install all project dependencies.
echo "--> STEP 4/5: Installing dependencies..."
pip install -r requirements.txt

# STEP 5: Launch the entire AI Operating System.
echo "--> STEP 5/5: Launching the AI-OS. This will take a while..."
docker compose up --build
