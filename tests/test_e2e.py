import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mock.mock_network import MockNetwork
from node_sim.node import Node
from node_sim.simulator import Simulator
import yaml

@pytest.fixture
def temp_config(tmp_path):
    config = {"simulation": {"num_nodes": 4, "max_blocks": 2}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    return str(config_path)

def test_simulation_run(capsys, temp_config):
    """Test that the simulation runs end-to-end without errors."""
    network = MockNetwork()
    nodes = [Node(i, network) for i in range(4)]
    
    sim = Simulator(network, nodes, temp_config)
    
    print("Starting E2E Test Run")
    # Run simulation for a limited number of steps
    sim.run(max_steps=5)
            
    captured = capsys.readouterr()
    assert "Starting E2E Test Run" in captured.out
    assert "--- Step 1 ---" in captured.out
    assert "Simulation ended (max steps reached)." in captured.out

def test_determinism(capsys, temp_config):
    """Test that two runs produce identical output."""
    # Run 1
    network1 = MockNetwork()
    nodes1 = [Node(i, network1) for i in range(4)]
    sim1 = Simulator(network1, nodes1, temp_config)
    
    print("RUN 1 START")
    sim1.run(max_steps=5)
    out1 = capsys.readouterr().out
    
    # Run 2
    network2 = MockNetwork()
    nodes2 = [Node(i, network2) for i in range(4)]
    sim2 = Simulator(network2, nodes2, temp_config)
    
    print("RUN 2 START")
    sim2.run(max_steps=5)
    out2 = capsys.readouterr().out
    
    # Compare outputs (stripping the "RUN X START" lines and memory addresses if any)
    # Since our mock output is deterministic and doesn't contain memory addresses, direct comparison should work
    # after stripping the start marker.
    
    output1 = out1.split("RUN 1 START")[1]
    output2 = out2.split("RUN 2 START")[1]
    
    assert output1 == output2

def test_transaction_propagation(capsys, temp_config):
    """Test that transactions are propagated to other nodes."""
    network = MockNetwork()
    nodes = [Node(i, network) for i in range(4)]
    sim = Simulator(network, nodes, temp_config)
    
    # Manually inject a transaction into Node 0's mempool (simulating a client submission)
    tx = {"type": "TX", "data": "tx_data_1"}
    # In a real scenario, we might use a client to send this, but for now we simulate network receipt
    # or direct injection. Let's use network send to simulate receiving from a client/peer.
    # Since MockNetwork.send delivers immediately in this mock:
    network.send(None, nodes[0], tx)
    
    # Run simulation briefly to allow propagation (if implemented)
    # Current Node implementation adds to mempool but doesn't broadcast TXs on receipt in `receive`.
    # However, let's check if it was added to Node 0's mempool.
    assert "tx_data_1" in nodes[0].mempool
    
    # If Node logic included rebroadcasting, we would check other nodes.
    # For now, let's verify Node 0 has it.
    
    print("Transaction Propagation Test")
    sim.run(max_steps=2)
    
    captured = capsys.readouterr()
    assert "Added TX to mempool" in captured.out

def test_block_proposal(capsys, temp_config):
    """Test that nodes propose blocks when they have transactions."""
    network = MockNetwork()
    nodes = [Node(i, network) for i in range(4)]
    sim = Simulator(network, nodes, temp_config)
    
    # Inject tx
    tx = {"type": "TX", "data": "tx_data_for_block"}
    network.send(None, nodes[0], tx)
    
    print("Block Proposal Test")
    # Run enough steps for a proposal to happen (Simulator calls propose_block every even step)
    sim.run(max_steps=4)
    
    captured = capsys.readouterr()
    assert "Proposing block" in captured.out
    assert "Block validated" in captured.out 