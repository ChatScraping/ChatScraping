import os
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_transformers import Html2TextTransformer
from playwright.async_api import async_playwright
import asyncio
import nest_asyncio
from urllib.parse import urlparse, unquote
from pathlib import Path
from datetime import datetime

from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.chains import LLMChain
from langchain_community.llms import Ollama
from langchain_groq import ChatGroq
from langchain.schema.document import Document

from chatscraping_utils import db, URL, URL_version, Text
from sqlalchemy.exc import IntegrityError

class DocumentManager:
    def __init__(self, vectordb_name='faiss_local', embeddings_model_name='sentence-transformers/LaBSE', llm='solar', instruction='You are a useful assistant. Answer the questions the better way you can do.'):
        self.llm = llm
        self.instruction = instruction
        self.embeddings_model_name = embeddings_model_name # other: 'sentence-transformers/all-mpnet-base-v2' (only english)
        self.load_vector_db(vectordb_name)

    def load_vector_db(self, vectordb_name):
        self.vectordb_name = vectordb_name
        self.db = None
        vectordb_exist = os.path.exists(self.vectordb_name+".faiss")
        if vectordb_exist:
            self.db = FAISS.load_local(".", HuggingFaceEmbeddings(model_name=self.embeddings_model_name), self.vectordb_name, allow_dangerous_deserialization=True)
        else:
            print(f"{self.vectordb_name} NOT FOUND.")

    def add_texts(self, texts, texts_origin="ChatScraping - Texts panel - Textarea"):
        if texts is None or len(texts) < 1:
            print("DocumentManager:add_texts have finished without texts.", flush=True)
            return 1
        for text in texts:
            try:
                new_text = Text(text=text, origin=texts_origin)
                db.session.add(new_text)
                db.session.commit()
            except IntegrityError:
                print(f"DocumentManager:add_texts: {text} already exists in DB.")
                db.session.rollback()
                texts.remove(text)
        if self.db is None:
            self.db = FAISS.from_texts(texts, HuggingFaceEmbeddings(model_name=self.embeddings_model_name))
        else:
            self.db.add_texts(texts)
        self.db.save_local(".", self.vectordb_name)

    def add_texts_from_file(self, text_file):
        if not os.path.exists(text_file):
            raise FileNotFoundError(f"Text file {text_file} not found.")

        with open(text_file, 'r') as f:
            texts = f.read().splitlines()

        self.add_texts(texts=texts, texts_origin="ChatScraping - Texts panel - From file")
        
    async def scrape_webpage(self, url: str, save_html=True, save_pdf=True, base_dir='saved_pages'):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url)
                html_content = await page.content()
                
                if save_html or save_pdf:
                    # Parse the URL to extract the path
                    parsed_url = urlparse(url)
                    path = unquote(parsed_url.path)
                    
                    # Get the current time for the suffix
                    timestamp = datetime.utcnow().strftime('%F_%H-%M-%S_UTC')
                    # and for the directory
                    date = datetime.now().strftime('%F')
                    
                    # Construct the full path for saving the file
                    if not path or path == '/':
                        html_path = f'index_{timestamp}.html'
                        pdf_path = f'index_{timestamp}.pdf'
                    else:
                        if path.endswith('/'):
                            html_path = path + f'index_{timestamp}.html'
                            pdf_path = path + f'index_{timestamp}.pdf'
                        else:
                            # Split the path into name and extension
                            base, ext = os.path.splitext(path)
                            html_path = f'{base}_{timestamp}.html'
                            pdf_path = f'{base}_{timestamp}.pdf'
                    
                    # Join the base directory with the parsed path
                    full_html_path = os.path.join(base_dir, date, parsed_url.netloc, html_path.lstrip('/'))
                    full_pdf_path = os.path.join(base_dir, date, parsed_url.netloc, pdf_path.lstrip('/'))
                    
                    # Ensure the directory exists
                    os.makedirs(os.path.dirname(full_html_path), exist_ok=True)
                    
                    if save_html:
                        # Save the HTML content to the file
                        with open(full_html_path, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                    
                    if save_pdf:
                        # Save the page as PDF
                        await page.pdf(path=full_pdf_path)
            
            except Exception as e:
                print(f"DocumentManager:scrape_webpage: Error: {e}")
            
            await browser.close()
        
        return html_content, full_html_path, full_pdf_path

    def add_documents_from_urls(self, urls, urls_origin="ChatScraping - URLs panel - Textarea", new_urls=True):
        if urls is None or len(urls) < 1:
            print(f"DocumentManager:add_documents_from_urls: ERROR: No URLs.", flush=True)
            return 1
        urls_number = len(urls)
        
        for url in urls:
            if new_urls:
                new_url = URL(url=url, origin=urls_origin)
                db.session.add(new_url)
                db.session.commit()
                url_id = new_url.id
            else:
                url_id = URL.query.filter_by(url=url).first().id
            
            html_content, html_file_path, pdf_file_path = asyncio.run(self.scrape_webpage(url=url))
            metadata = {"source": url}
            doc = Document(page_content=html_content, metadata=metadata)
            html2text = Html2TextTransformer()
            docs_transformed = html2text.transform_documents([doc])
            new_url_version = URL_version(url_id=url_id, all_readable_text=docs_transformed[0].page_content, html_file_path=html_file_path, pdf_file_path=pdf_file_path)
            db.session.add(new_url_version)
            db.session.commit()
        
        return 0
        
    def add_documents_from_urls_in_file(self, url_file):
        if not os.path.exists(url_file):
            raise FileNotFoundError(f"URL file {url_file} not found.")

        with open(url_file, 'r') as f:
            urls = f.read().splitlines()
            
        self.add_documents_from_urls(urls=urls, urls_origin="ChatScraping - URLs panel - From file")
    
    def split_text(self, url_version_id, texts_origin="ChatScraping - DocumentManager:split_text", chunk_size=100, chunk_overlap=0):
        if not isinstance(url_version_id, int):
            raise ValueError("url_version_id must be an integer.")
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer.")
        if not isinstance(chunk_overlap, int) or chunk_overlap < 0:
            raise ValueError("chunk_overlap must be a not negative integer.")

        url_version = URL_version.query.get(url_version_id)
        if url_version is None:
            raise ValueError(f"URL_version with id {url_version_id} not found.")
            
        text = url_version.all_readable_text
        doc = Document(page_content=text)
        text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunked_documents = text_splitter.split_documents([doc])
        
        for document_chunk in chunked_documents:
            try:
                new_text = Text(text=document_chunk.page_content, url_version_id=url_version_id, origin=texts_origin)
                db.session.add(new_text)
                db.session.commit()
            except IntegrityError:
                print(f"DocumentManager:split_text: '{document_chunk.page_content}' already exists in DB.")
                db.session.rollback()
                chunked_documents.remove(document_chunk)
        
        if self.db is None:
            self.db = FAISS.from_documents(chunked_documents, HuggingFaceEmbeddings(model_name=self.embeddings_model_name))
        else:
            self.db.add_documents(chunked_documents)
        
        self.db.save_local(".", self.vectordb_name)
        return 0

    def answer_question(self, question, faiss_only=False, llm_only=False, num_docs=4, text_only=False, use_groq=False):
        answer = {}
        print("lalala")
        if faiss_only:
            answer['faiss'] = self.db.similarity_search(question, k=num_docs)
        else:
            if use_groq:
                chat = ChatGroq(temperature=0, model_name=self.llm)
                system = "You are a helpful assistant."
                retrieval_texts = self.db.similarity_search(question, k=num_docs)
                context = "\n".join([text.page_content for text in retrieval_texts])
                human = "{question}\n\nHere is context to help:\n\n{context}"
                prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
                chain = prompt | chat
                answer['Groq'] = chain.invoke({"question": question, "context": context})
            else:
                prompt_template = f"""
                ### [INST] Instruction: {self.instruction} Here is context to help:

                {{context}}

                ### QUESTION:
                {{question}} [/INST]
                """
                prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)
                llm_ollama = Ollama(model=self.llm)
                llm_chain = LLMChain(llm=llm_ollama, prompt=prompt)
                rag_chain = ({"context": self.db.as_retriever(), "question": RunnablePassthrough()} | llm_chain)
                answer['Ollama'] = rag_chain.invoke(question)
        
        if text_only:
            if 'Ollama' in answer:
                return answer['Ollama']['text']
            elif 'Groq' in answer:
                return answer['Groq'].content
            elif 'faiss' in answer:
                return "Textos seleccionados:\n" + "\n".join([ans.page_content for ans in answer['faiss']])
        else:
            return answer
