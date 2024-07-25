from flask import render_template, request, redirect, url_for, jsonify, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from chatscraping_utils import app, db, Text, URL, URL_version, Tag, Comment
import os, glob
from DocumentManager import DocumentManager
from datetime import datetime
import subprocess, shlex
import time
from groq import Groq
from duckduckgo_search import DDGS
import json
from sqlalchemy.exc import IntegrityError

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
import secrets
clave_secreta = secrets.token_hex(16)
app.secret_key = clave_secreta

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

doc_manager = DocumentManager()
# All models: https://console.groq.com/settings/limits
GROQ_MODELS = ['mixtral-8x7b-32768', 'llama3-70b-8192', 'llama3-8b-8192', 'gemma-7b-it', 'gemma2-9b-it',
               'llama3-groq-8b-8192-tool-use-preview', 'llama3-groq-70b-8192-tool-use-preview',
              'llama-3.1-8b-instant', 'llama-3.1-70b-versatile', 'llama-3.1-405b-reasoning']
OLLAMA_MODELS = ['tinyllama', 'dolphin-phi', 'solar', 'nous-hermes2', 'llava', 'bakllava']

def get_databases():
    databases = [ db[:-6] for db in glob.glob('*.faiss') ]
    return databases


@app.route('/add_new_db', methods=['POST'])
def add_new_db():
    new_db = request.form['new_db']
    return jsonify({'new_db': new_db})

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'text_file' in request.files or 'urls_file' in request.files:
            database_name = request.form.get('database')
            if database_name == "":
                print(f"app.py:upload: ERROR: User must select a DB.")
            else:
                doc_manager.vectordb_name = database_name
        
                texts_from_textarea = request.form.get('text_content')
                if texts_from_textarea is not None and texts_from_textarea != "":
                    texts = texts_from_textarea.split("\n")
                    doc_manager.add_texts(texts)
                if 'text_file' in request.files:
                    text_file = request.files['text_file']
                    if text_file and allowed_file(text_file.filename):
                        text_filename = secure_filename(text_file.filename)
                        text_file_path = os.path.join(app.config['UPLOAD_FOLDER'], text_filename)
                        text_file.save(text_file_path)
                        doc_manager.add_texts_from_file(text_file_path)
                
                urls_from_textarea = request.form.get('urls_content')
                if urls_from_textarea is not None and urls_from_textarea != "":
                    urls = urls_from_textarea.split("\n")
                    doc_manager.add_documents_from_urls(urls)
                if 'urls_file' in request.files:
                    urls_file = request.files['urls_file']
                    if urls_file and allowed_file(urls_file.filename):
                        urls_filename = secure_filename(urls_file.filename)
                        urls_file_path = os.path.join(app.config['UPLOAD_FOLDER'], urls_filename)
                        urls_file.save(urls_file_path)
                        doc_manager.add_documents_from_urls_in_file(urls_file_path)
    
    databases = get_databases()
    return render_template('upload.html', databases=databases)

@app.route('/search_with_DDG', methods=['POST'])
def search_with_DDG():
    text_to_search = request.form['text_to_search']
    max_results_number = request.form['max_results_number']
    results = "No results in search with DDG."
    with DDGS() as ddgs:
        ddgs_gen = ddgs.text(
            text_to_search,
            #region="wt-wt",
            #safesearch="moderate",
            #timelimit=self.time,
            max_results = int(max_results_number),
            #backend=self.backend, # which backend to use in DDGS.text() (api, html, lite)
        )
        if ddgs_gen:
            results = [r for r in ddgs_gen]
            for result in results:
                try:
                    url = result["href"]
                    new_url = URL(url=url, page_title=result["title"], body=result["body"], origin=f"ChatScraping - URLs panel - Search with DuckDuckGo and text '{text_to_search}'")
                    db.session.add(new_url)
                    db.session.commit()
                except IntegrityError:
                    print(f"app.py:search_with_DDG: '{url}' already exists in DB.")
                    db.session.rollback()
        else:
            print(f"app.py:search_with_DDG: No results.")
    return jsonify({'search_results': results})

@app.route('/chat', methods=['GET', 'POST'])
def render_chat():
    conversation_id = session.get('conversation_id')
    if request.method == 'POST':
        question_time = datetime.now()
        question = request.form.get('question')
        retrieval_only = 'true' in request.form.get('retrieval_only')
        llm_only = 'true' in request.form.get('llm_only')
        text_only = 'true' in request.form.get('text_only')
        use_groq = 'true' in request.form.get('use_groq')
        vectordb_name = request.form.get('db')
        num_docs = int(request.form.get('num_docs', 4))
        llm = request.form.get('llm')
        instruction = request.form.get('instruction')
        voice = request.form.get('voice')

        if question:
            doc_manager.llm = llm
            if instruction != "":
                doc_manager.instruction = instruction
            doc_manager.load_vector_db(vectordb_name)
            answer = doc_manager.answer_question(question, retrieval_only, llm_only, num_docs, text_only, use_groq)
            answer_time = datetime.now()
            
            if conversation_id:
                conversation = Conversation.query.get(conversation_id)
            else:
                conversation = Conversation(name=f'conversation_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}')
                db.session.add(conversation)
                db.session.flush()
                conversation_id = conversation.id
            
            if retrieval_only:
                answer = str(answer)

            new_message = Message(
                conversation_id=conversation.id,
                question=question,
                answer=answer,
                retrieval_only=retrieval_only,
                llm_only=llm_only,
                text_only=text_only,
                use_groq=use_groq,
                num_docs=num_docs,
                llm=llm,
                instruction=instruction,
                question_time=question_time,
                answer_time=answer_time
            )
            db.session.add(new_message)
            db.session.commit()
        
            if text_only:
                escaped_answer = shlex.quote(answer)
                escaped_answer = escaped_answer.replace('\n', ' ')
                audio_file_name = 'answer.webm'
                subprocess.run(f"cd static/voices; echo {escaped_answer} | piper --model {voice} --output_file ../{audio_file_name}", shell=True)
                return jsonify({'question': question, 'answer': answer, 'text_only': text_only, 'conversation_id': conversation_id})
            else:
                if retrieval_only:
                    return jsonify({'question': question, 'answer': answer, 'text_only': text_only, 'conversation_id': conversation_id})
                else:
                    return jsonify({'question': question, 'answer': str(answer), 'text_only': text_only, 'conversation_id': conversation_id})
        
    databases = get_databases()
    voice_models = [ voice[:-5].split("/")[-1] for voice in glob.glob('static/voices/*.onnx') ]
    return render_template('chat.html', databases=databases, ollama_llms=OLLAMA_MODELS, groq_llms=GROQ_MODELS, voices=voice_models, conversation_id=conversation_id)

@app.route('/upload_and_process_question_audio', methods=['POST'])
def upload_and_process_question_audio():
    file = request.files['audio']
    filename = 'uploaded_question_audio.webm'
    file_path = os.path.join('uploads', filename)
    file.save(file_path)
    
    # Speech to text with 'Whisper large v3' using 'Groq'
    question = "";
    client = Groq()
    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
          file=(filename, file.read()),
          model="whisper-large-v3",
          # prompt="Specify context or spelling",  # Optional
          response_format="json",  # Optional
          # language="en",  # Optional
          temperature=0.0  # Optional
        )
        question = transcription.text;
    
    return question

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        pass

    return render_template('upload.html')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    messages = db.relationship('Message', backref='conversation', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    question = db.Column(db.String(1024), nullable=False)
    answer = db.Column(db.String(1024), nullable=False)
    retrieval_only = db.Column(db.Boolean)
    llm_only = db.Column(db.Boolean)
    text_only = db.Column(db.Boolean)
    use_groq = db.Column(db.Boolean)
    num_docs = db.Column(db.Integer)
    llm = db.Column(db.String(255))
    instruction = db.Column(db.String(1024))
    question_time = db.Column(db.DateTime, default=db.func.current_timestamp())
    answer_time = db.Column(db.DateTime, default=db.func.current_timestamp())
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route('/start_conversation', methods=['GET', 'POST'])
def start_conversation():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            name = f'conversation_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        new_conversation = Conversation(name=name)
        db.session.add(new_conversation)
        db.session.commit()
        session['conversation_id'] = new_conversation.id
        return redirect(url_for('query'))
    return render_template('start_conversation.html')

@app.route('/conversations')
def conversations():
    all_conversations = Conversation.query.all()
    return render_template('conversations.html', conversations=all_conversations)

@app.route('/conversations/<int:conversation_id>')
def view_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = Message.query.filter_by(conversation_id=conversation.id).all()
    return render_template('view_conversation.html', conversation=conversation, messages=messages)

@app.route('/saved_pages/<path:filename>')
def saved_files(filename):
    try:
        return send_from_directory('saved_pages', filename)
    except FileNotFoundError:
        abort(404)

@app.route('/URLs')
def render_URLs():
    return render_template('URLs.html', texts=Text.query.all())

@app.route('/api/texts', methods=['GET'])
def get_texts():
    start_id = request.args.get('start_id', type=int, default=0)
    end_id = request.args.get('end_id', type=int, default=None)
    if start_id is not None:
        query = Text.query.filter(Text.id >= start_id)
    if end_id is not None:
        query = query.filter(Text.id <= end_id)
    texts = query.all()

    texts_list = []
    for text in texts:
        texts_list.append({
            'id': text.id,
            'text': text.text,
            'url_version_id': text.url_version_id,
            'YouTube_video_id': text.YouTube_video_id,
            'origin': text.origin,
            'rating': text.rating,
            'created_at': text.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': text.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return jsonify(texts_list)

@app.route('/api/urls', methods=['POST'])
def add_urls():
    urls = request.get_json()
    if urls is not None and urls != "":
        urls = urls.split("\n")
        doc_manager.add_documents_from_urls(urls=urls, urls_origin="ChatScraping - upload_urls")
        
        for url in urls:
            url_to_update = URL.query.filter_by(url=url).first()
            if url_to_update:
                url_to_update.is_saved = True
                db.session.commit()
        return jsonify({'message': 'URLs added successfully'})
    return jsonify({'error': 'URL not send'}), 404

@app.route('/api/urls', methods=['GET'])
def get_urls():
    start_id = request.args.get('start_id', type=int, default=0)
    end_id = request.args.get('end_id', type=int, default=None)
    if start_id is not None:
        query = URL.query.filter(URL.id >= start_id)
    if end_id is not None:
        query = query.filter(URL.id <= end_id)
    urls = query.all()
    
    urls_list = []
    for url in urls:
        urls_list.append({
            'id': url.id,
            'url': url.url,
            'page_title': url.page_title,
            'body': url.body,
            'origin': url.origin,
            'rating': url.rating,
            'is_saved': url.is_saved,
            'created_at': url.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': url.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'tags': [{'id': tag.id, 'name': tag.name, 'path': tag.path} for tag in url.tags],
            'comments': [{'id': comment.id, 'text': comment.text} for comment in url.comments],
            'versions': [{'id': version.id, 'created_at': version.created_at, 'html_file_path': version.html_file_path, 'pdf_file_path': version.pdf_file_path} 
                         for version in url.versions],
        })
    return jsonify(urls_list)

@app.route('/api/url_versions', methods=['POST'])
def add_url_version():
    data = request.get_json()
    url_id = data['id']
    url_url = data['url']
    
    url_to_update = URL.query.get(url_id)
    
    doc_manager.add_documents_from_urls(urls=[url_to_update.url], urls_origin="ChatScraping - /api/save_page_version", new_urls=False)
    
    if url_to_update:
        url_to_update.is_saved = True
        db.session.commit()
    
    return jsonify({'message': 'Page version saved successfully'})

@app.route('/api/url_versions', methods=['GET'])
def get_url_versions():
    start_id = request.args.get('start_id', type=int, default=0)
    end_id = request.args.get('end_id', type=int, default=None)
    if start_id is not None:
        query = URL_version.query.filter(URL.id >= start_id)
    if end_id is not None:
        query = query.filter(URL.id <= end_id)
    url_versions = query.all()

    versions_list = []
    for version in url_versions:
        versions_list.append({
            'id': version.id,
            'url_id': version.url_id,
            'all_readable_text': version.all_readable_text,
            'html_file_path': version.html_file_path,
            'pdf_file_path': version.pdf_file_path,
            'are_texts_saved': version.are_texts_saved,
            'created_at': version.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': version.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'texts': [text.text for text in version.texts],
            'url_title': version.url.page_title,
            'url': version.url.url,
        })
    return jsonify(versions_list)

@app.route('/api/save_text_chunks', methods=['POST'])
def save_text_chunks():
    data = request.get_json()
    url_version_id = data['id']
    
    doc_manager.split_text(url_version_id, "ChatScraping - /api/save_text_chunks")
    
    # actualiza el campo are_texts_saved
    url_version_to_update = URL_version.query.get(url_version_id)
    if url_version_to_update:
        url_version_to_update.are_texts_saved = True
        db.session.commit()
    
    return jsonify({'message': 'Text splited successfully'})

@app.route('/api/comments', methods=['POST'])
def add_comment():
    data = request.get_json()
    url_id = data['url_id']
    comment_text = data['comment']

    comment = Comment(text=comment_text)
    url = URL.query.get(url_id)
    if url is None:
        return jsonify({'error': 'URL not found'}), 404
    db.session.add(comment)
    url.comments.append(comment)
    db.session.commit()

    return jsonify({'message': 'Comment added successfully'})

@app.route('/api/tags', methods=['POST'])
def add_tags():
    data = request.get_json()
    url_id = data['url_id']
    tags_text = data['tags']
    tags_list = [tag.strip() for tag in tags_text.split(',') if tag.strip()]

    url = URL.query.get(url_id)
    if url is None:
        return jsonify({'error': 'URL not found'}), 404

    for tag_text in tags_list:
        tag = Tag.query.filter_by(name=tag_text).first()
        if not tag:
            tag = Tag(name=tag_text, path=tag_text)
            db.session.add(tag)
        if tag not in url.tags:
            url.tags.append(tag)

    db.session.commit()

    return jsonify({'message': 'Tags added successfully'})
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
