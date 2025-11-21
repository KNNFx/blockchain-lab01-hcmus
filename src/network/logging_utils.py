# logging_utils.py
from __future__ import annotations

import json
from typing import Any, Dict, TextIO, Optional


class JsonLinesLogger:
    """
    Ghi log dạng JSON Lines:
    - Mỗi event 1 dòng JSON.
    - Không dùng thời gian hệ thống, chỉ dùng simulated_time do simulator cung cấp.
    - sort_keys=True để format deterministic.
    """

    def __init__(self, file: TextIO):
        self._file = file

    def log_event(
        self,
        *,
        sim_time: float,
        node_id: str,
        event: str,
        height: Optional[int] = None,
        msg_id: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        record: Dict[str, Any] = {
            "time": round(sim_time, 6),  # giới hạn 6 chữ số thập phân cho ổn định
            "node": node_id,
            "event": event,
        }
        if height is not None:
            record["height"] = height
        if msg_id is not None:
            record["msg_id"] = msg_id
        if extra:
            # merge thêm thông tin khác (loại msg, from/to,...)
            record.update(extra)

        line = json.dumps(record, sort_keys=True)
        self._file.write(line + "\n")
        self._file.flush()
