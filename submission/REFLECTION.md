# Reflection — Lab 19

**Tên:** Trần Văn Thắng

**Cohort:** 4

**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

Trên golden set 50 queries, hybrid đạt Precision@10 trung bình cao nhất
(78,6%), nhỉnh hơn BM25 (77,8%) và vector (73,2%). Với `exact`, BM25 và hybrid
cùng đạt 96,7% vì các thuật ngữ xuất hiện nguyên văn, còn vector đạt 88,7%.
Với `mixed`, hybrid thắng rõ nhất (100%) nhờ RRF kết hợp tín hiệu lexical của
BM25 và quan hệ ngữ nghĩa của vector. Kết quả `paraphrase` lại khác kỳ vọng:
BM25 đạt 33,3%, hybrid 32,0% và vector chỉ 24,0%. Nguyên nhân là
`BAAI/bge-small-en-v1.5` được huấn luyện chủ yếu cho tiếng Anh nên biểu diễn
paraphrase tiếng Việt chưa tốt; đây là giới hạn của model, không phải bằng
chứng rằng BM25 hiểu ngữ nghĩa tốt hơn.

Tôi không dùng hybrid khi truy vấn cần khớp chính xác mã lỗi, SKU, tên riêng
hoặc thuật ngữ pháp lý—pure BM25 đơn giản, nhanh và dễ giải thích hơn. Pure
vector phù hợp khi người dùng diễn đạt tự nhiên, từ vựng khác tài liệu và đã
có embedding đa ngôn ngữ đủ tốt. Hybrid là lựa chọn mặc định cho lưu lượng
thực tế pha trộn, nhưng không nên trả thêm chi phí nếu một tín hiệu đã đủ mạnh.

---

## Điều ngạc nhiên nhất khi làm lab này

Hybrid thắng trung bình nhưng không thắng mọi lát cắt. Chất lượng và ngôn ngữ
của embedding model có thể đảo ngược kết luận tưởng như hiển nhiên về semantic search.

---

## Bonus challenge

- [ ] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: không
