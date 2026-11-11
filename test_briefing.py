from briefing import build

items = [("标题甲", "https://a"), ("标题乙", "https://b")]
out = build(items, [{"i": 1, "s": "摘要乙"}, {"i": 9, "s": "越界"}, {"i": "x", "s": "坏"}, {"s": "无编号"}])
assert [l for _, l in out] == ["https://b"], out  # 越界/非整数/缺失编号都被丢弃, 链接取自 RSS
assert all(len(t) <= 200 for t, _ in out)
print("ok")
