from mock.mock_network import MockNetwork
from node_sim.node import Node
from node_sim.simulator import Simulator

def main():
    # Khởi tạo network mock
    network = MockNetwork()

    # Tạo các node (ví dụ 4 node)
    nodes = [Node(node_id=i, network=network) for i in range(4)]

    # Khởi tạo simulator chạy mock
    sim = Simulator(network=network, nodes=nodes)

    # Chạy mô phỏng 10 tick
    for _ in range(10):
        sim.tick()

if __name__ == "__main__":
    main()
