# ChatScraping

## Introduction

***ChatScraping* is not a clone of *ChatGPT***, and it's not the target of this project. *ChatScraping* is a tool (a web application) to help with the development of techniques of scraping to add context in questions to LLMs (in prompts of LLMs).

It's a baby project, so for now only help to show the proccess of:
 1. Extract readible text from web pages.
 2. Convert that text to MarkDown for more easy proccess from LLMs.
 3. Split that text in chunks for embeddings creation (one embedding for chunk).
 4. Storage and semantic search.
 5. Prompt generation with the correct context.

The are 3 pages/views:
 1. To web search. Use *DuckDuckGo* and automatically stores the results in a SQL database. Also, it's possible to introduce texts directly in the database a través de a textarea.
 2. To manage the we data. There is a table with DDG search results. In that table, there are buttons for add comments, add tags and automatically navegate to the web page and save that page (code, in PDF format, and convert readible text in MarkDown). Also, there is a button to view a table with the web page versions for each URL. In each row of that URL versions table, there is a button to split the readible text of that version, storage in SQL database, create embeddings and storage those embeddings in a FAISS database. Also, in that URL versions table, there is a button to view a table with the text chunks.
 3. To chat with a LLM using a context with semantically selected text chunks (from those web searchs). It's possible to use a LLM from *Ollama* or from *Groq* (to use *Groq*, the user needs to export environment variable *GROQ_API_KEY* with his Groq key, before to start this web application). 

## Instalation

pip install -r requerements.txt

