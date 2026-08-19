"""Five-query demonstration required by BONUS-CHALLENGE.md."""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bonus.agent import HybridMemoryAgent  # noqa: E402


def main() -> int:
    agent = HybridMemoryAgent()
    memories = [
        "Tôi đã đọc hướng dẫn Kubernetes Horizontal Pod Autoscaler. HPA tăng hoặc giảm số pod dựa trên CPU và custom metrics.",
        "Ghi chú cloud security: áp dụng Zero Trust, IAM least privilege, mã hóa dữ liệu và xoay vòng secrets định kỳ.",
        "Terraform và autoscaling group giúp tự động mở rộng hạ tầng theo lưu lượng người dùng mà không cấu hình máy chủ thủ công.",
        "Bài viết về FinOps khuyên đặt budget alert, theo dõi cost theo team và tắt tài nguyên cloud nhàn rỗi.",
        "Tôi thích tài liệu kỹ thuật tiếng Việt ngắn gọn, có ví dụ thực hành trước phần lý thuyết dài.",
    ]
    for memory in memories:
        agent.remember(memory, user_id="u_001")

    queries = [
        "Tôi đã đọc gì về Kubernetes?",
        "Recommend đọc gì tiếp",
        "Tôi đang quan tâm gì gần đây?",
        "Tài liệu về tự động mở rộng hạ tầng?",
        "Cho tôi summary cloud security",
    ]
    for number, query in enumerate(queries, start=1):
        print(f"\n{'=' * 18} QUERY {number} {'=' * 18}")
        print(agent.recall(query, user_id="u_001"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
