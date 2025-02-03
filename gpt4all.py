from flask import Flask, request, jsonify
import uuid
import redis
from datetime import datetime
from gpt4all import GPT4All

app = Flask(__name__)

# Default system message
system_message_default = "Congress shall make no law respecting an establishment of religion, or prohibiting the free exercise thereof; or abridging the freedom of speech, or of the press; or the right of the people peaceably to assemble, and to petition the Government for a redress of grievances."

# Redis connection
redis_url = "redis://user:password@localhost:6379/0"
r = redis.StrictRedis.from_url(redis_url)

model = GPT4All("Meta-Llama-3-8B-Instruct.Q4_0.gguf")

@app.route('/api/v1/systemMessage', methods=['GET'])
def get_system_message():
    return jsonify({"system_message": system_message_default})

@app.route('/api/v1/systemMessage', methods=['PUT'])
def update_system_message():
    data = request.json
    system_message_default = data.get('system_message', system_message)
    return jsonify({"system_message": system_message_default})

@app.route('/api/v1/chat/prompt', methods=['POST'])
def chat_prompt():
    data = request.json
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"error": "Prompt is mandatory"}), 400

    local_system_message = data.get('system_message', system_message)
    temperature = data.get('temperature', 0.1)
    chat_session = data.get('chatSession', str(uuid.uuid4()))
    timestamp = datetime.now().isoformat()

    response = generate_response(prompt, local_system_message, temperature)

    chat_data = {
        "system_message": local_system_message,
        "prompt": prompt,
        "response": response,
        "temperature": temperature,
        "timestamp": timestamp
    }

    r.hset(chat_session, mapping=chat_data)

    return jsonify({"chatSession": chat_session, "response": response})

def generate_response(prompt, system_message, temperature):
    """
    Generate a response using GPT4All model based on REST request parameters.
    """
    data = request.json
    prompt = data.get('prompt')
    if not prompt:
        return {"error": "Prompt is mandatory"}, 400
    
    system_message = data.get('system_message', "")
    temperature = data.get('temperature', 0.1)
    chat_session = data.get('chatSession', str(uuid.uuid4()))
    timestamp = datetime.now().isoformat()
    
    with model.chat_session(system_message=system_message):
        full_prompt = f"{system_message}\n{prompt}" if system_message else prompt
        response = model.generate(full_prompt, temp=temperature)
    
    chat_data = {
        "system_message": system_message,
        "prompt": prompt,
        "response": response,
        "temperature": temperature,
        "timestamp": timestamp
    }
    
    return {"response": response}


@app.route('/api/v1/chat/session', methods=['GET'])
def get_chat_sessions():
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    sessions = []
    for key in r.scan_iter():
        session_data = r.hgetall(key)
        session_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in session_data.items()}
        session_date = datetime.fromisoformat(session_data['timestamp'])

        if start_date and end_date:
            start_date = datetime.fromisoformat(start_date)
            end_date = datetime.fromisoformat(end_date)
            if start_date <= session_date <= end_date:
                sessions.append({key.decode('utf-8'): session_data})
        else:
            sessions.append({key.decode('utf-8'): session_data})

    return jsonify(sessions)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)