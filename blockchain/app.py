import os
import time
from flask import Flask, jsonify, request
from uuid import uuid4
from blockchain import Blockchain
import requests

app = Flask(__name__)

# Eindeutige Adresse für diesen Knoten
node_identifier = str(uuid4()).replace('-', '')

# Initialisiere Blockchain
blockchain = Blockchain()

# Hole Umgebungsvariable für andere Knoten im Netzwerk
known_nodes = os.getenv('KNOWN_NODES', '')

# Registrierung der Knoten (manuell über den API-Endpunkt)
def register_known_nodes():
    if known_nodes:
        nodes = known_nodes.split(',')
        for node in nodes:
            try:
                response = requests.post(f'http://{node}/nodes/register', json={"nodes": [f"http://{node_identifier}"]})
                if response.status_code == 201:
                    print(f"Node registered with {node}")
            except Exception as e:
                print(f"Failed to register with node {node}: {e}")

# Registrierung von Validatoren (manuell über den API-Endpunkt)
def register_validator():
    try:
        response = requests.post(f'http://localhost:5000/validators/register', json={"validator": node_identifier})
        if response.status_code == 201:
            print(f"Validator {node_identifier} registered.")
    except Exception as e:
        print(f"Failed to register validator: {e}")

@app.route('/mine', methods=['POST'])
def mine_block():
    values = request.get_json()
    validator = values.get('validator')

    if validator is None or not blockchain.valid_validator(validator):
        response = {'message': 'Unauthorized validator'}
        return jsonify(response), 403

    last_block = blockchain.last_block
    previous_hash = last_block['hash']
    block = blockchain.create_block(previous_hash, validator)

    response = {
        'message': 'New block mined',
        'block': block,
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    index = blockchain.add_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/validators/register', methods=['POST'])
def register_validator_endpoint():
    values = request.get_json()
    validator = values.get('validator')

    if validator is None:
        return 'Missing validator address', 400

    blockchain.register_validator(validator)

    response = {'message': f'Validator {validator} has been registered.'}
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

if __name__ == '__main__':
    # Kein automatisches Registrieren mehr, alles manuell
    # Knoten und Validatoren werden über die Endpunkte registriert

    # Flask App starten
    app.run(host='0.0.0.0', port=5000)
