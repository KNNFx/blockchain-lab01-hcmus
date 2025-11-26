from mock.mock_network import MockNetwork
from node_sim.node import Node
from node_sim.simulator import Simulator

import sys

def main():
    # Default config path
    config_path = "config/config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    # Khởi tạo network mock
    network = MockNetwork()

    # Tạo các node (ví dụ 4 node)
    nodes = [Node(node_id=i, network=network) for i in range(4)]

    # Khởi tạo simulator chạy mock
    sim = Simulator(network=network, nodes=nodes, config_path=config_path)

    # Chạy mô phỏng
    sim.run()

if __name__ == "__main__":
    main()