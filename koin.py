# Module 1: Creating a Cryptocurrency

import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse


# Part 1 - Building the blockchain

class Blockchain:
    def __init__(self):
        self.chain = []  # Chain that holds the mined blocks
        self.transactions = []  # Transactions before they are added to a block
        # Create the genesis block
        self.create_block(proof = 1, previous_hash = '0')
        self.nodes = set()  # Distributed nodes receiving this blockchain

    # create_block adds a new block into the chain
    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': str(datetime.datetime.now()),
            'proof': proof,
            'previous_hash': previous_hash,
            'transactions': self.transactions
        }
        self.transactions = []  # Empty the transactions list after adding them into a block
        self.chain.append(block)
        return block

    # get_previous_block returns the last block on the chain
    def get_previous_block(self):
        return self.chain[-1]

    # proof_of_work is the problem miners have to put in.
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False

        while check_proof is False:
            # problem the miners will have to solve. Problem should not be symmetrical. i.e. new_proof +
            # previous_proof = previous_proof + new_proof. Hence, it's not a good challenge. Smaller the hash value,
            # harder to mine.
            hash_operation = hashlib.sha256(str(new_proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            # 0000 defines the target of all accepted hash values in our chain. Increasing number of
            # leading zeros increases the complexity
            if hash_operation[:4] == '0000':
                # miner has successfully found a hash satisfying the problem
                check_proof = True
            else:
                # retry mining until succeed
                new_proof += 1

        return new_proof

    # hash returns the cryptographic hash of the block
    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    # is_chain_valid determines if the chain is valid
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1

        while block_index < len(self.chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                # chain is not valid
                return False

            previous_proof = previous_block['proof']
            proof = block['proof']

            # Have to check if the proof satisfy the problem defined within the chain.
            # This has to be the same problem that is used by miners to mine blocks.
            hash_operation = hashlib.sha256(str(proof ** 2 - previous_proof ** 2).encode()).hexdigest()

            if hash_operation[:4] != '0000':
                return False

            previous_block = block
            block_index += 1

        return True

    # add_transaction adds transactions to the empty list so the mined blocks can include them within the blocks
    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount
        })

        previous_block = self.get_previous_block()
        # Index of the block containing the above transactions
        return previous_block['index'] + 1

    # add_node adds the node address to the set of nodes receiving this blockchain
    def add_node(self, node_address):
        parsed_url = urlparse(node_address)
        self.nodes.add(parsed_url.netloc)

    # replace_chain will replace the current chain with the longest chain within the nodes in the blockchain
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)

        for node in network:
            response = requests.get(f'http://{node}/get-chain')  # Query each node to get its local chain
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if local chain of any node is longer than the current chain of this node.
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain

        if longest_chain:
            # Longest chain becomes the accepted chain for all nodes.
            self.chain = longest_chain
            return True

        return False


# Part 2 - Mining the blockchain
# Creating a web app
app = Flask(__name__)

node_id = str(uuid4()).replace('-', '')

# Creating the blockchain
blockchain = Blockchain()


# Mining new blocks
@app.route('/mine-block', methods = ['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    new_block_proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)

    miner = request.headers['user']
    if not miner:
        return jsonify({'message': 'Mandatory header `user` not found'}), 400

    # This transaction is to indicate the reward a miner gets after mining a block
    blockchain.add_transaction(node_id, miner, 16)

    mined_block = blockchain.create_block(new_block_proof, previous_hash)

    response = {
        'message': 'Congratulations, you just mined a block',
        'index': mined_block['index'],
        'timestamp': mined_block['timestamp'],
        'proof': mined_block['proof'],
        'previous_hash': mined_block['previous_hash'],
        'transactions': mined_block['transactions']
    }

    return jsonify(response), 201


@app.route('/get-chain', methods = ['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/is-valid', methods = ['GET'])
def is_chain_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': 'Blockchain is valid'}
        return jsonify(response), 200
    else:
        response = {'message': 'Blockchain is not valid'}
        return jsonify(response), 500


@app.route('/add-transaction', methods = ['POST'])
def add_transaction():
    payload = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']

    if not all(key in payload for key in transaction_keys):
        return jsonify({'message': 'Mandatory attributes of a transaction are missing'}), 400

    index = blockchain.add_transaction(payload['sender'], payload['receiver'], payload['amount'])
    response = {'message': f'This transaction will be added to block {index}'}

    return jsonify(response), 200


# Part 3 - Decentralizing the blockchain

# Connecting new nodes
@app.route('/connect-node', methods = ['POST'])
def connect_node():
    payload = request.get_json()
    nodes = payload.get('nodes')
    if nodes is None:
        return jsonify({'message': 'no nodes address provided'}), 400

    for node in nodes:
        blockchain.add_node(node)

    return jsonify({'message': 'nodes added', 'total_nodes': len(blockchain.nodes)}), 201


# Replace the chain with the longest chain if needed
@app.route('/replace-chain', methods = ['GET'])
def replace_chain():
    is_replaced = blockchain.replace_chain()
    if is_replaced:
        response = {
            'message': 'Nodes had different chains. Chain was replaced by the longest chain',
            'chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Current chain is the largest chain',
            'chain': blockchain.chain
        }
    return jsonify(response), 200


# Start the webapp
app.run(host = 'localhost', port = 5000)
