"""每日 AI 新闻简报: Google News RSS -> Gemini 挑 3 条并写中文摘要 -> KakaoTalk「我的聊天」。
环境变量: GEMINI_API_KEY, KAKAO_REST_KEY, KAKAO_REFRESH_TOKEN, KAKAO_CLIENT_SECRET(应用开了 Client Secret 时必填); 可选 FORCE=1(跳过时间/已发检查), DRY=1(只打印)。"""
import json, os, sys, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
SEND_AFTER = (8, 50)  # 目标 9:00, 提前 10 分钟放行; Actions 会延迟, 所以 cron 从凌晨起每 30 分钟触发
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
RSS = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
    {"q": "AI 인공지능 when:1d", "hl": "ko", "gl": "KR", "ceid": "KR:ko"})


def call(url, data=None, headers=None):
    req = urllib.request.Request(url, data, headers or {})
    try:
        return urllib.request.urlopen(req, timeout=30).read()
    except urllib.error.HTTPError as e:
        sys.exit(f"{url.split('?')[0]} -> {e.code} {e.read().decode()[:300]}")


def fetch():
    root = ET.fromstring(call(RSS))
    return [(i.findtext("title"), i.findtext("link")) for i in root.iter("item")]


def ask_gemini(items):
    lines = "\n".join(f"{n}. {t}" for n, (t, _) in enumerate(items))
    prompt = ("下面是带编号的韩国 AI 新闻标题。选出最重要的 3 条, 各写一句中文摘要(40 字内, "
              "只能用标题里已有的信息, 不要编造数字或日期)。"
              '只返回 JSON 数组: [{"i": 编号, "s": "摘要"}]\n' + lines)
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"responseMimeType": "application/json"}}).encode()
    r = call(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent", body,
             {"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    return json.loads(json.loads(r)["candidates"][0]["content"]["parts"][0]["text"])


def build(items, picks):
    """链接只从 RSS 取, 不信模型给的; 编号越界的丢掉, 防止幻觉。"""
    out = []
    for p in picks:
        i = p.get("i")
        if isinstance(i, int) and 0 <= i < len(items):
            out.append((f"📰 {p['s']}\n{items[i][0]}"[:200], items[i][1]))
    return out


def kakao_send(msgs):
    d = json.loads(call("https://kauth.kakao.com/oauth/token", urllib.parse.urlencode({
        "grant_type": "refresh_token", "client_id": os.environ["KAKAO_REST_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
        "client_secret": os.environ.get("KAKAO_CLIENT_SECRET", "")}).encode()))
    if "refresh_token" in d:  # shortcut: 不自动回写 secret, 刷新令牌约 2 个月到期, 到时重新授权一次
        print("⚠ Kakao 返回了新的 refresh_token, 请重新授权并更新 secret")
    for text, link in msgs:
        tpl = {"object_type": "text", "text": text, "link": {"web_url": link, "mobile_web_url": link},
               "button_title": "원문 보기"}  # 链接域名需先在 Kakao「제품 링크 관리」登记(news.google.com), 否则点不开
        call("https://kapi.kakao.com/v2/api/talk/memo/default/send",
             urllib.parse.urlencode({"template_object": json.dumps(tpl, ensure_ascii=False)}).encode(),
             {"Authorization": "Bearer " + d["access_token"]})


def main():
    now = datetime.now(KST)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"date": "", "links": []}
    if not os.environ.get("FORCE") and (state["date"] == now.date().isoformat() or (now.hour, now.minute) < SEND_AFTER):
        return print("skip:", now.strftime("%H:%M"), "已发或未到时间")
    items = [x for x in fetch() if x[1] not in state["links"]][:15]
    if not items:
        return print("没有新新闻")
    msgs = build(items, ask_gemini(items))
    if os.environ.get("DRY"):
        return print("\n\n".join(f"{t}\n-> {l}" for t, l in msgs))
    kakao_send(msgs)
    json.dump({"date": now.date().isoformat(), "links": (state["links"] + [l for _, l in msgs])[-200:]},
              open(STATE, "w"), ensure_ascii=False)
    print("已发送", len(msgs), "条")


if __name__ == "__main__":
    main()
