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
2. **Manage Web Data:** There is a table with *DDG* search results. In that table, there are buttons to add comments, add tags, and automatically navigate to the web page to save that page (in 2 files: code file, and PDF document) and store in SQL database converted readable text to Markdown. Additionally, there is a button to view a table with the web page versions for each URL. In each row of that URL versions table, there is a button to split the readable text of that version, store it in a SQL database, create embeddings, and store those embeddings in a FAISS database. There is also a button to view a table with the text chunks.
3. **Chat with a LLM:** Uses a context with semantically selected text chunks (from those web searches). It's possible to use an LLM from *Ollama* or *Groq* (to use *Groq*, the user needs to export the environment variable `GROQ_API_KEY` with their *Groq* key before starting this web application).

## Installation

```sh
git clone https://github.com/ChatScraping/ChatScraping
cd ChatScraping
pip install -r requirements.txt
cd web_app
python app.py
```

## Chat voice

*ChatScraping* can speak out the output text in the chat. For this, [Piper](https://github.com/rhasspy/piper) is used, because it is entirely local, the quality is good enough, and the speed is very good. You need to download [the desired voice](https://github.com/rhasspy/piper/blob/master/VOICES.md) and place the files (.onnx and .json) in the directory/folder 'web_app/static/voices'. If there are several voices in that directory, they will be listed in the 'Voices' dropdown in the chat web page (to the right and under the LLMs dropdowns).

## Implementation

To use the chat functionality of this web application, it's needed to either have [Ollama](https://ollama.com) installed (which allows you to use [a lot of LLMs](https://ollama.com/library?sort=newest) locally; this is better for privacy but requires more computational resources), or have a Groq key (it is free but [it have limits](https://console.groq.com/settings/limits)). [Groq](https://console.groq.com/playground) is a remote service, but it uses only free LLMs, is very fast, and the free limits are sufficient for a single human user.

The main libraries of this aplications are the following.

 - [LangChain](https://github.com/langchain-ai/langchain). It supports both [Ollama](https://python.langchain.com/v0.2/docs/integrations/llms/ollama/) (including [ollama_functions](https://python.langchain.com/v0.2/docs/integrations/chat/ollama_functions/)) and [Groq](https://python.langchain.com/v0.1/docs/integrations/chat/groq/). Additionally, it has many classes for scraping,  which inspired the idea for *ChatScraping*. However, those clases are very simple and, so, *ChatScraping* does not use *LangChain* for this purpose (we have our own implementations, and now the main idea of *ChatScraping* is to be a tool for developers who want to improve the workflows of information retrieval, including web scraping and parsing of different types of documents). *LangChain* also has many classes for vector stores (for embeddings), and in *ChatScraping* it is used for *FAISS*; this is tricky, because *FAISS* only stores embeddings and not the texts, so, in *ChatScraping*, *FAISS* is used together with a SQL database (for the texts and for indexes to the embeddings in the *FAISS* database).
 - [HuggingFace's transformers](https://github.com/huggingface/transformers). It is used for text embeddings.
 - [FAISS](https://github.com/facebookresearch/faiss)
 - *Flask*
 - *jQuery*
 - *DataTables*
 - *SQLAlchemy*. The current implementation of *ChatScraping* uses this with *SQLite*, but using *SQLAlchemy* it is very easy change that to another SQL engine/platform, like *PostgreSQL*.

## Future work

This is a baby project, so there is a lot of work to do. :-) Here there are some examples.

- Create tools to help users develop the scraping workflows.
- Create some specific scraping tools. For now, there is a simple scraping technique, where all readible text is extracted. However, better scraping requires a specific tool for each use case (often, one for each website). Additionally, it would be awesome to use LLMs to improve the parsing of web pages.
- Tools for automatic navigation: A scheduler, link parsers, etc.
- More document loaders (*LangChain* has many of them, so this will be easy).
- Better conversion from HTML to Markdown.
- Better text splitters. Again, using LLMs for this would be awesome.
- Better techniques for sematic search, like Graph-RAG.
- Improvements in the chat functionality.
- Vision. I have been considering (and also testing) vision both for information retrieval (*MoonDream* works very good, and fast, in some use cases, and I also like *CLIP* and *YOLO*), and for the chat part (like *OpenAI* and *Google* demos).
- Audio. Dreamming is free, so I also think it would be awesome to recognize types of sounds and their 3D positions. :-)
- Bug fixes.

## Author

Eduardo Gutiérrez

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
