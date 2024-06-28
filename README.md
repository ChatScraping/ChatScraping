# ChatScraping

## Introduction

***ChatScraping* is not a clone of *ChatGPT***, and it's not the target of this project. *ChatScraping* is a tool (a web application) to help with the development of scraping techniques to add context in questions to LLMs (in prompts of LLMs).

It's an early-stage project, so for now it only helps to demonstrate the process of:
1. Extracting readable text from web pages.
2. Converting that text to Markdown for easier processing by LLMs.
3. Splitting that text into chunks for embedding creation (one embedding per chunk).
4. Storage and semantic search.
5. Prompt generation with the correct context.

There are 3 pages/views:
1. **Web Search:** Uses *DuckDuckGo* and automatically stores the results in a SQL database. It's also possible to introduce texts directly into the database via a textarea.
2. **Manage Web Data:** There is a table with *DDG* search results. In that table, there are buttons to add comments, add tags, and automatically navigate to the web page to save that page (code in PDF format, and convert readable text to Markdown). Additionally, there is a button to view a table with the web page versions for each URL. In each row of that URL versions table, there is a button to split the readable text of that version, store it in a SQL database, create embeddings, and store those embeddings in a FAISS database. There is also a button to view a table with the text chunks.
3. **Chat with a LLM:** Uses a context with semantically selected text chunks (from those web searches). It's possible to use an LLM from *Ollama* or *Groq* (to use *Groq*, the user needs to export the environment variable `GROQ_API_KEY` with their *Groq* key before starting this web application).

## Installation

```sh
git clone https://github.com/ChatScraping/ChatScraping
cd ChatScraping/web_app
pip install -r requirements.txt
python app.py
