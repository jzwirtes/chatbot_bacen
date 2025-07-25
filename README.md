# BCBot

This repository contains a small Streamlit application that works as a chatbot for consulting Brazilian Central Bank (BCB) regulations.

## Requirements

- Python 3.11+
- Packages listed in `requirements.txt`
- A Google Generative AI API key in the environment variable `KEY`

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Running

Set the `KEY` environment variable and then start the application with Streamlit:

```bash
export KEY=<your-gemini-api-key>
streamlit run app_v2.py
```

The application will open in your browser, allowing you to add regulations and interact with them via chat.
