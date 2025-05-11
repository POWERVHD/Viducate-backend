# 🚀 Viducate Backend

![FastAPI](https://img.shields.io/badge/FastAPI-0.115.1-green?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-Custom-lightgrey)

A modern, high-performance backend for the **Viducate** application, built with FastAPI.

---

## 📚 Table of Contents
- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [License](#license)

---

## 📝 Overview
This project provides the backend API services for Viducate, built using FastAPI and Python. It is designed for speed, scalability, and ease of use.

---

## 🛠️ Technology Stack

- ⚡ **FastAPI** — Modern, fast web framework for building APIs
- 🐍 **Python** — Programming language
- 🔒 **Pydantic** — Data validation and settings management
- 🚦 **Uvicorn** — ASGI server for running the application

---

## 📁 Project Structure

```text
backend/
├── app/                    # Main application package
│   ├── main.py             # FastAPI application instance and endpoints
│   ├── config.py           # Configuration settings
│   ├── i18n.py             # Internationalization settings
│   ├── models/             # Database models
│   ├── routers/            # API route definitions
│   ├── schemas/            # Pydantic models for request/response validation
│   └── services/           # Business logic
├── tests/                  # Test modules
├── .env                    # Environment variables (not tracked by git)
├── .gitignore              # Git ignore file
├── requirements.txt        # Python dependencies
└── run.py                  # Entry point for running the application
```

---

## ⚙️ Setup & Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/viducate-backend.git
   cd viducate-backend
   ```
2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```
3. **Activate the virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Unix/MacOS:
     ```bash
     source .venv/bin/activate
     ```
4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
5. **Set up environment variables**
   - Create a `.env` file with the required configuration.

---

## ▶️ Running the Application

- **Using Python**
  ```bash
  python run.py
  ```
- **Or using Uvicorn directly**
  ```bash
  uvicorn app.main:app --reload
  ```

The API will be available at [http://localhost:8000](http://localhost:8000)

---

## 📖 API Documentation

- Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Testing

Run the tests using [pytest](https://docs.pytest.org/):

```bash
pytest
```

---

## 🚀 Deployment

The application can be deployed using Docker or directly to a hosting platform that supports Python applications.

---

## 📄 License

This project is proprietary. All rights reserved. 
