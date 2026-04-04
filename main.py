import requests
from curl_cffi import requests as cffi_requests
import datetime
import random
import time
import os

# 从 GitHub Secrets 读取配置
PUSH_WEBHOOK_URL = os.getenv("PUSH_WEBHOOK_URL", "")
ACCOUNTS_JSON = os.getenv("ACCOUNTS_JSON", "[]")

# 代理（GitHub 服务器在国外，无需代理）
PROXY_CONFIG = None

# 解析账号
import json
ACCOUNTS = json.loads(ACCOUNTS_JSON)

def translate_message(raw_message):
    if raw_message == "Please Try Tomorrow":
        return "签到失败，请明天再试 🤖"
    elif "Checkin! Got" in raw_message:
        points = raw_message.split("Got ")[1].split(" Points")[0]
        return f"签到成功，获得{points}积分 🎉"
    elif raw_message == "Checkin Repeats! Please Try Tomorrow":
        return "重复签到，请明天再试 🔁"
    elif "please checkin via" in raw_message:
        return "签到失败，请更新Cookie ⚠️"
    else:
        return f"未知结果: {raw_message} ❓"

def sanitize_header_value(value):
    if isinstance(value, str):
        try:
            value.encode('latin-1')
            return value
        except UnicodeEncodeError:
            return value.encode('latin-1', 'replace').decode('latin-1')
    return value

def generate_headers(cookie):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
    ]
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": cookie,
        "Origin": "https://glados.cloud",
        "User-Agent": random.choice(user_agents)
    }
    return {k: sanitize_header_value(v) for k, v in headers.items()}

def format_days(days_str):
    days = float(days_str)
    return str(int(days)) if days.is_integer() else f"{days:.2f}"

def send_webhook(content):
    if not PUSH_WEBHOOK_URL:
        print("未配置 Webhook，跳过推送")
        return
    try:
        data = {"msgtype": "text", "text": {"content": content}}
        requests.post(PUSH_WEBHOOK_URL, json=data, timeout=10)
        print("Webhook 发送成功")
    except Exception as e:
        print(f"发送失败: {e}")

def create_retry_session():
    return cffi_requests.Session(impersonate="chrome124")

def check_account_status(email, cookie):
    url = "https://glados.cloud/api/user/status"
    headers = generate_headers(cookie)
    try:
        r = create_retry_session().get(url, headers=headers, timeout=15)
        data = r.json()
        days = format_days(data['data']['leftDays'])
        return f"{email} | 剩余 {days} 天"
    except:
        return f"{email} | 状态查询失败"

def fetch_points(cookie):
    url = "https://glados.cloud/api/user/points"
    headers = generate_headers(cookie)
    try:
        data = create_retry_session().get(url, headers=headers, timeout=15).json()
        return f"积分 {data.get('points', 0)}"
    except:
        return "积分查询失败"

def sign(email, cookie):
    url = "https://glados.cloud/api/user/checkin"
    headers = generate_headers(cookie)
    data = {"token": "glados.cloud"}
    try:
        r = create_retry_session().post(url, headers=headers, json=data, timeout=15)
        msg = r.json().get("message", "")
        return translate_message(msg)
    except Exception as e:
        return f"请求异常: {str(e)[:30]}"

def run():
    if not ACCOUNTS:
        print("未配置任何账号")
        return

    msg_list = []
    beijing_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    now = beijing_time.strftime("%m-%d %H:%M")
    msg_list.append(f"【GLaDOS 自动签到】{now}\n")

    for idx, acc in enumerate(ACCOUNTS, 1):
        email = acc.get("email", f"账号{idx}")
        cookie = acc.get("cookie", "")
        if not cookie:
            msg_list.append(f"{email} | 无Cookie")
            continue

        print(f"签到: {email}")
        sign_msg = sign(email, cookie)
        status_msg = check_account_status(email, cookie)
        point_msg = fetch_points(cookie)
        msg_list.append(f"{email}\n结果：{sign_msg}\n状态：{status_msg} | {point_msg}\n")
        time.sleep(random.randint(2, 5))

    final_msg = "\n".join(msg_list)
    print(final_msg)
    send_webhook(final_msg)

if __name__ == "__main__":
    print("===== 开始签到 =====")
    run()
    print("===== 执行完成 =====")
