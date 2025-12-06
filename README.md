# Math Solver Tool

Math Solver Tool is a Flask-based web application that provides a clean interface for solving mathematical problems, chatting with an AI assistant powered by the Gemini API, and managing user accounts. It includes a responsive UI, persistent chat history, built-in dark mode, and structured math handling.

---

## Features

### Math Solver

* Supports arithmetic expressions.
* Evaluates expressions on the backend with error handling.
* Returns results through `/solve` in JSON format.

### AI Chat (Gemini API)

* Chat interface uses Google Gemini for responses.
* Messages are stored locally in `chats.json`.
* Full chat UI with editing, deleting, renaming, and archiving.

### User Accounts

* Login and signup system using JSON storage (`people.json`).
* Password and username validation included.
* Session management through Flask.

### UI & Frontend

* Fully custom CSS theme using `style.css`.
* Built-in dark and light modes (switchable).
* Responsive layout for desktop and mobile.
* Sidebar with chat management and settings dialogs.

### FAQ System

* Frequently asked questions generated from `faq_data.py`.
* Includes structured answers for math usage and system behavior.

---

## Project Structure

```
Math-solver-tool/
├── app.py                 # Flask backend (routes, auth, Gemini responses, solving)
├── faq_data.py            # FAQ entries
├── chats.json             # Local chat storage
├── people.json            # User account data
│
├── static/
│   ├── style.css          # UI design and theming
│   └── script.js          # Chat handling, sidebar logic, requests
│
└── templates/
    ├── index.html         # Main UI (chat + solver)
    ├── login.html         # Login page
    └── signup.html        # Signup page
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ghazanfar-Abbas550/Math-solver-tool.git
cd Math-solver-tool
```

### 2. Install dependencies

```bash
pip install flask google-generativeai
```

### 3. Add your Gemini API key

Inside `app.py`, set:

```python
genai.configure(api_key="YOUR_API_KEY")
```

### 4. Run the app

```bash
python app.py
```

### 5. Open in browser

```
http://127.0.0.1:5000
```

---

## How It Works

### Math Solving

`/solve` receives a math expression, validates it, safely evaluates it, and returns a simple JSON response.

### AI Chat

Messages are sent to Gemini using the Generative AI Python SDK.
Responses and conversation history are saved in `chats.json`.

### Frontend Logic

`script.js` handles:

* Sending messages
* Updating chat history
* Editing and deleting messages
* Dialog and sidebar behavior
* Auto-scrolling
* Switching between dark and light modes

---

## Ideas for Future Improvements

* Add **camera-based equation scanning**.
* Add multi-user chat separation on backend.
* Add user profiles.
