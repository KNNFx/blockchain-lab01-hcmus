# src/network/network.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple, Protocol
from enum import Enum, auto
import heapq
import random

from .messages import Message
from .logging_utils import JsonLinesLogger


class NetworkEventType(Enum):
    DELIVER = auto()


@dataclass(order=True)
class ScheduledDelivery:
    """
    Một lần delivery được xếp lịch trong event queue.
    Priority queue sắp theo (deliver_time, seq) để deterministic.
    """
    sort_key: Tuple[float, int] = field(init=False, repr=False)

    deliver_time: float
    seq: int
    message: Message

    def __post_init__(self):
        self.sort_key = (self.deliver_time, self.seq)


class Node(Protocol):
    """
    Interface đơn giản cho Node:
    chỉ cần có .node_id và .receive(message)
    """
    node_id: str

    def receive(self, message: Message) -> None:
        ...


class Network:
    """
    Network layer đơn giản:
    - Event queue (priority queue) cho các lần deliver.
    - Simulate delay / drop / duplicate / reorder.
    - Throttle outbound rate (min interval giữa 2 lần gửi của 1 node).
    - Block / unblock peer: chặn tạm thời 1 hướng gửi (src -> dst).
    - Ghi log toàn bộ event bằng JSON lines (deterministic).
    """

    def __init__(
        self,
        *,
        logger: JsonLinesLogger,
        rng: Optional[random.Random] = None,
        min_delay: float = 0.1,
        max_delay: float = 1.0,
        drop_prob: float = 0.0,
        dup_prob: float = 0.0,
        min_send_interval: float = 0.0,
    ):
        """
        :param logger: JsonLinesLogger để ghi log.
        :param rng: random.Random với seed cố định để deterministic.
        :param min_delay: delay tối thiểu trước khi deliver.
        :param max_delay: delay tối đa trước khi deliver.
        :param drop_prob: xác suất drop 1 message.
        :param dup_prob: xác suất tạo 1 bản duplicate (2 lần deliver).
        :param min_send_interval: khoảng thời gian tối thiểu giữa 2 lần gửi từ 1 node.
        """
        assert min_delay >= 0 and max_delay >= min_delay

        self._logger = logger
        self._rng = rng or random.Random(0)
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._drop_prob = drop_prob
        self._dup_prob = dup_prob
        self._min_send_interval = min_send_interval

        self._nodes: Dict[str, Node] = {}
        self._queue: List[ScheduledDelivery] = []
        self._next_seq: int = 0
        self._last_send_time: Dict[str, float] = {}  # node_id -> last send time

        # tập các cặp (src, dst) đang bị block
        self._blocked_pairs: set[tuple[str, str]] = set()

    # ---------- quản lý node ----------

    def add_node(self, node: Node) -> None:
        self._nodes[node.node_id] = node

    # ---------- helper internal ----------

    def _alloc_seq(self) -> int:
        seq = self._next_seq
        self._next_seq += 1
        return seq

    def _schedule_delivery(self, deliver_time: float, msg: Message) -> None:
        sd = ScheduledDelivery(
            deliver_time=deliver_time,
            seq=self._alloc_seq(),
            message=msg,
        )
        heapq.heappush(self._queue, sd)

        # log SCHEDULE_DELIVER
        self._logger.log_event(
            sim_time=deliver_time,
            node_id=msg.to_id,
            event="SCHEDULE_DELIVER",
            height=msg.height,
            msg_id=msg.msg_id,
            extra={
                "from": msg.from_id,
                "to": msg.to_id,
                "msg_type": msg.msg_type.name,
            },
        )

    # ---------- block / unblock peer ----------

    def block_peer(self, src: str, dst: str, now: float) -> None:
        """
        Block hướng gửi src -> dst.
        Mọi message từ src gửi tới dst sau thời điểm này sẽ bị chặn.
        """
        pair = (src, dst)
        if pair not in self._blocked_pairs:
            self._blocked_pairs.add(pair)

        self._logger.log_event(
            sim_time=now,
            node_id=dst,
            event="BLOCK_PEER",
            height=None,
            msg_id=None,
            extra={"from": src, "to": dst},
        )

    def unblock_peer(self, src: str, dst: str, now: float) -> None:
        """
        Unblock hướng src -> dst.
        """
        pair = (src, dst)
        if pair in self._blocked_pairs:
            self._blocked_pairs.remove(pair)

        self._logger.log_event(
            sim_time=now,
            node_id=dst,
            event="UNBLOCK_PEER",
            height=None,
            msg_id=None,
            extra={"from": src, "to": dst},
        )

    def is_blocked(self, src: str, dst: str) -> bool:
        return (src, dst) in self._blocked_pairs

    # ---------- API chính ----------

    def send(self, msg: Message, now: float) -> None:
        """
        Gửi message từ msg.from_id tới msg.to_id tại thời điểm 'now' (simulated).
        Thực tế nó sẽ:
        - áp dụng throttle
        - nếu cặp (from, to) đang bị block → log & bỏ
        - random drop/duplicate
        - random delay → xếp lịch deliver vào priority queue
        """

        sender = msg.from_id
        receiver = msg.to_id

        # throttle outbound rate
        last_t = self._last_send_time.get(sender, -1e18)
        earliest = last_t + self._min_send_interval
        send_time = max(now, earliest)
        self._last_send_time[sender] = send_time

        # log SEND event
        self._logger.log_event(
            sim_time=send_time,
            node_id=sender,
            event="SEND",
            height=msg.height,
            msg_id=msg.msg_id,
            extra={
                "from": sender,
                "to": receiver,
                "msg_type": msg.msg_type.name,
            },
        )

        # nếu đang bị block → log và dừng
        if self.is_blocked(sender, receiver):
            self._logger.log_event(
                sim_time=send_time,
                node_id=sender,
                event="SEND_BLOCKED",
                height=msg.height,
                msg_id=msg.msg_id,
                extra={
                    "from": sender,
                    "to": receiver,
                    "reason": "blocked_peer",
                },
            )
            return

        # random drop
        if self._rng.random() < self._drop_prob:
            self._logger.log_event(
                sim_time=send_time,
                node_id=sender,
                event="DROP",
                height=msg.height,
                msg_id=msg.msg_id,
                extra={
                    "from": sender,
                    "to": receiver,
                    "reason": "random_drop",
                },
            )
            return

        # tính delay & schedule deliver
        delay = self._rng.uniform(self._min_delay, self._max_delay)
        deliver_time = send_time + delay
        self._schedule_delivery(deliver_time, msg)

        # duplicate ?
        if self._rng.random() < self._dup_prob:
            # thêm một bản duplicate với delay hơi khác để tạo reorder
            extra_delay = self._rng.uniform(0.0, self._min_delay)
            dup_time = deliver_time + extra_delay
            self._schedule_delivery(dup_time, msg)

            self._logger.log_event(
                sim_time=send_time,
                node_id=sender,
                event="DUPLICATE_SCHEDULED",
                height=msg.height,
                msg_id=msg.msg_id,
                extra={
                    "from": sender,
                    "to": receiver,
                },
            )

    def has_pending_events(self) -> bool:
        """Kiểm tra còn event trong queue không."""
        return bool(self._queue)

    def deliver_next(self) -> Optional[float]:
        """
        Lấy event sớm nhất trong queue và deliver message cho node nhận.
        - nếu cặp (from, to) bị block tại thời điểm deliver → log & drop
        - ngược lại: log DELIVER rồi gọi Node.receive(message)
        Trả về simulated_time của lần deliver này, hoặc None nếu queue rỗng.
        """
        if not self._queue:
            return None

        sd = heapq.heappop(self._queue)
        msg = sd.message
        t = sd.deliver_time
        sender = msg.from_id
        receiver = msg.to_id

        # nếu cặp đang bị block tại thời điểm deliver → drop
        if self.is_blocked(sender, receiver):
            self._logger.log_event(
                sim_time=t,
                node_id=receiver,
                event="DELIVER_BLOCKED",
                height=msg.height,
                msg_id=msg.msg_id,
                extra={
                    "from": sender,
                    "to": receiver,
                    "reason": "blocked_peer",
                },
            )
            return t

        node = self._nodes.get(receiver)
        if node is None:
            # node không tồn tại → log rồi bỏ qua
            self._logger.log_event(
                sim_time=t,
                node_id=receiver,
                event="DELIVER_DROPPED_NO_NODE",
                height=msg.height,
                msg_id=msg.msg_id,
                extra={
                    "from": sender,
                    "to": receiver,
                },
            )
            return t

        # log DELIVER trước khi gọi node.receive (deterministic)
        self._logger.log_event(
            sim_time=t,
            node_id=receiver,
            event="DELIVER",
            height=msg.height,
            msg_id=msg.msg_id,
            extra={
                "from": sender,
                "to": receiver,
                "msg_type": msg.msg_type.name,
            },
        )

        node.receive(msg)
        return t
