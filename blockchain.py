# Module 1: Creating a blockchain

import datetime
import hashlib
import json
from flask import Flask, jsonify


# Part 1 - Building the blockchain

class Blockchain:
    def __init__(self):
        self.chain = []  # Chain that holds the mined blocks
        # Create the genesis block
        self.create_block(proof = 1, previous_hash = '0')

    # create_block adds a new block into the chain
    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': str(datetime.datetime.now()),
            'proof': proof,
            'previous_hash': previous_hash
        }
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
    def is_chain_valid(self):
        previous_block = self.chain[0]
        block_index = 1

        while block_index < len(self.chain):
            block = self.chain[block_index]
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


# Part 2 - Mining the blockchain
# Creating a web app
app = Flask(__name__)

# Creating the blockchain
blockchain = Blockchain()


@app.route('/mine-block', methods = ['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    new_block_proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)

    mined_block = blockchain.create_block(new_block_proof, previous_hash)

    response = {
        'message': 'Congratulations, you just mined a block',
        'index': mined_block['index'],
        'timestamp': mined_block['timestamp'],
        'proof': mined_block['proof'],
        'previous_hash': mined_block['previous_hash']
    }

    return jsonify(response), 200


@app.route('/get-chain', methods = ['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/is-valid', methods = ['GET'])
def is_chain_valid():
    is_valid = blockchain.is_chain_valid()
    if is_valid:
        response = {'message': 'Blockchain is valid'}
        return jsonify(response), 200
    else:
        response = {'message': 'Blockchain is not valid'}
        return jsonify(response), 500


# Start the webapp
app.run(host = 'localhost', port = 5000)
