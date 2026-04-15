# Mini ChatGPT Agent

A tool-augmented conversational AI powered by TinyLlama 1.1B with web search, weather, calculator, memory and GitHub tools.

## Features

- 🔍 **Web Search** — DuckDuckGo search with summarized top results
- 🌤 **Weather** — Current conditions via wttr.in
- 🧮 **Calculator** — Safe math evaluation from natural language
- 🧠 **Memory** — Session facts about you for personalized replies
- 🐙 **GitHub** — Profile and repository info with a personal access token

## How to Run

1. Clone the repo
2. `pip install -r requirements.txt`
3. `streamlit run app.py`

## How it Works

Your message is matched to optional tools using keyword routing (`router.py`). When a tool applies, its output is combined with any saved memory and wrapped in a structured prompt (`prompt_builder.py`). TinyLlama then generates a reply using that context instead of guessing.

## Tech Stack

TinyLlama 1.1B, Streamlit, DuckDuckGo Search, wttr.in, PyGithub
