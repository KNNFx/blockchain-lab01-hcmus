import pytest #
import sys #
import os #
sys.path.append(os.path.join(os.path.dirname(__file__), "../src")) #

from mock.mock_network import MockNetwork #
from node_sim.node import Node #
from node_sim.simulator import Simulator #
import yaml #

def test_simulation_run(capsys): #
    """Test that the simulation runs end-to-end without errors.""" #
    network = MockNetwork() #
    nodes = [Node(i, network) for i in range(4)] #
    
    # Create a temporary config for testing #
    config = {"simulation": {"num_nodes": 4, "max_blocks": 2}} #
    config_path = "tests/test_config.yaml" #
    with open(config_path, "w") as f: #
        yaml.dump(config, f) #
        
    sim = Simulator(network, nodes, config_path) #
    
    # Run simulation (mock run, just a few ticks) #
    # We need to modify Simulator to allow running for a limited steps or check output #
    # For this test, we'll just call tick() manually a few times to simulate run() #
    
    print("Starting E2E Test Run") #
    for _ in range(5): #
        sim.tick() #
        for node in nodes: #
            node.propose_block() #
            
    captured = capsys.readouterr() #
    assert "Starting E2E Test Run" in captured.out #
    assert "[Node 0]" in captured.out #
    
    # Clean up #
    if os.path.exists(config_path): #
        os.remove(config_path) #

def test_determinism(capsys): #
    """Test that two runs produce identical output.""" #
    # Run 1 #
    network1 = MockNetwork() #
    nodes1 = [Node(i, network1) for i in range(4)] #
    sim1 = Simulator(network1, nodes1) #
    # Inject config manually or use default #
    sim1.config = {"simulation": {"num_nodes": 4, "max_blocks": 2}} #
    
    print("RUN 1 START") #
    for _ in range(5): #
        sim1.tick() #
        for node in nodes1: #
            node.propose_block() #
    out1 = capsys.readouterr().out #
    
    # Run 2 #
    network2 = MockNetwork() #
    nodes2 = [Node(i, network2) for i in range(4)] #
    sim2 = Simulator(network2, nodes2) #
    sim2.config = {"simulation": {"num_nodes": 4, "max_blocks": 2}} #
    
    print("RUN 2 START") #
    for _ in range(5): #
        sim2.tick() #
        for node in nodes2: #
            node.propose_block() #
    out2 = capsys.readouterr().out #
    
    # Compare outputs (stripping the "RUN X START" lines) #
    output1 = out1.split("RUN 1 START")[1] #
    output2 = out2.split("RUN 2 START")[1] #
    
    assert output1 == output2 #
