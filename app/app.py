from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import paramiko

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
socketio = SocketIO(app)

ssh_clients = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ssh', methods=['POST'])
def ssh_connect():
    ssh_key_path = request.form['ssh_key_path']
    username = request.form['username']
    hostname = request.form['hostname']
    port = request.form.get('port', 22)

    try:
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=hostname, username=username, key_filename=ssh_key_path, port=port)

        # Store SSH client in dictionary
        session_id = request.remote_addr  # Use client IP as session ID
        ssh_clients[session_id] = ssh

        return render_template('ssh.html', hostname=hostname, username=username, ssh_key_path=ssh_key_path, session_id=session_id)
    except paramiko.ssh_exception.AuthenticationException:
        output = "Authentication failed. Please check your credentials."
    except Exception as e:
        output = f"An error occurred: {str(e)}"
    
    return render_template('index.html', output=output)

@socketio.on('connect', namespace='/ssh')
def ssh_connect_socket():
    session_id = request.args.get('session_id')
    if session_id in ssh_clients:
        emit('ssh_response', {'data': 'Connected to SSH WebSocket'})
    else:
        emit('ssh_response', {'data': 'SSH session not found'})

@socketio.on('disconnect', namespace='/ssh')
def ssh_disconnect():
    session_id = request.args.get('session_id')
    if session_id in ssh_clients:
        ssh = ssh_clients.pop(session_id)
        ssh.close()

@socketio.on('ssh_command', namespace='/ssh')
def handle_ssh_command(command):
    session_id = request.args.get('session_id')
    if session_id in ssh_clients:
        ssh = ssh_clients[session_id]
        stdin, stdout, stderr = ssh.exec_command(command['data'])
        output = stdout.read().decode()
        emit('ssh_response', {'data': output})
    else:
        emit('ssh_response', {'data': 'SSH session not found'})

if __name__ == '__main__':
    socketio.run(app, debug=True)
