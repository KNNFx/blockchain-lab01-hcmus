gitfrom io import StringIO
import json

# import đúng theo cấu trúc project:
# C:\blockchain-lab01-hcmus\src\network\...
from network.messages import Message, MessageType
from network.logging_utils import JsonLinesLogger
from network.network import Network


class DummyNode:
    """
    Node giả để kiểm tra network.deliver gọi đúng node.receive().
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.received = []  # lưu msg_id đã nhận

    def receive(self, message: Message) -> None:
        self.received.append(message.msg_id)


def test_network_basic_send_and_deliver():
    """
    Test cơ bản:
    - Gửi 1 message từ A -> B
    - Network schedule và deliver đúng
    - Node B nhận message
    - Log JSON hợp lệ
    """

    buf = StringIO()
    logger = JsonLinesLogger(buf)

    # random seed cố định để deterministic
    import random
    rng = random.Random(1234)

    # delay = 0 để đơn giản hóa kiểm tra
    net = Network(
        logger=logger,
        rng=rng,
        min_delay=0.0,
        max_delay=0.0,
        drop_prob=0.0,
        dup_prob=0.0,
    )

    # tạo 2 node giả
    a = DummyNode("A")
    b = DummyNode("B")
    net.add_node(a)
    net.add_node(b)

    # tạo message
    msg = Message(
        msg_id=1,
        from_id="A",
        to_id="B",
        msg_type=MessageType.TX,
        payload={"v": 1},
        height=5,
    )

    # gửi message vào mạng (t=0)
    net.send(msg, now=0.0)

    # phải có event pending
    assert net.has_pending_events()

    # deliver event kế tiếp
    t = net.deliver_next()

    # simulated time phải là 0.0
    assert t == 0.0

    # node B phải nhận message id 1
    assert b.received == [1]

    # Kiểm tra log JSON hợp lệ
    lines = buf.getvalue().strip().split("\n")

    assert len(lines) >= 2   # phải có SEND + DELIVER

    for line in lines:
        obj = json.loads(line)       # parse JSON
        assert "time" in obj
        assert "node" in obj
        assert "event" in obj

        # nếu có msg_id thì phải là 1
        if "msg_id" in obj:
            assert obj["msg_id"] == 1
