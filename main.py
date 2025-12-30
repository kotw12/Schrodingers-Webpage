# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
import openai
import uvicorn
import re
from datetime import datetime

# ==========================================
# [설정] API 키 및 비밀번호
# ==========================================
client = openai.OpenAI(api_key="YOUR_API_KEY_HERE")  # OpenAI API 키 설정
ADMIN_SECRET = "1q2w3e4r!"  # 관제실 접속용 비밀키

app = FastAPI()

# ==========================================
# [메모리] 로그 저장소 (DB 대용)
# ==========================================
# 서버가 켜져 있는 동안 공격 로그를 여기에 저장합니다.
ATTACK_LOGS = []

# ==========================================
# [보안 필터]
# ==========================================
def is_attack_pattern(input_str: str) -> bool:
    danger_chars = ["'", '"', "--", "#", ";", "/*", "union", "select", "sleep(", "benchmark("]
    input_lower = input_str.lower()
    for char in danger_chars:
        if char in input_lower:
            return True
    return False

# ==========================================
# [일관된 세계관]
# ==========================================
FAKE_DB_SCHEMA = """
[가짜 데이터베이스 명세]
- DB Type: MySQL 5.7
- Table: users
- Columns: id (int), username (varchar), password_hash (MD5), email (varchar), last_login (datetime)
- Fixed Data:
  1 | admin   | 5f4dcc3b5aa765d61d8327deb882cf99 | admin@stone-security.com
  2 | guest   | 084e0343a0486ff05530df6c705c8bb4 | guest@stone-security.com
  3 | tester  | 098f6bcd4621d373cade4e832627b4f6 | test@dev-team.net
"""

# ==========================================
# [템플릿]
# ==========================================
MARKDOWN_BLOCK = "`" * 3  
MARKDOWN_HTML = MARKDOWN_BLOCK + "html"

LOGIN_PAGE = """
<html>
<head>
    <style>
        body { background:#f0f2f5; display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif; }
        .login-box { padding:40px; background:white; border-radius:8px; box-shadow:0 4px 15px rgba(0,0,0,0.1); width:300px; }
        .input-group { position: relative; margin: 10px 0; }
        input { width:100%; padding:10px; box-sizing:border-box; border:1px solid #ccc; border-radius:4px; }
        .toggle-btn { 
            position: absolute; 
            right: 10px; 
            top: 50%; 
            transform: translateY(-50%); 
            cursor: pointer; 
            border: none; 
            background: none; 
            font-size: 1.2em;
        }
        button[type="submit"] { width:100%; padding:10px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <form action="/login" method="post">
            <h2 style="text-align:center; color:#333;">Secure Login</h2>
            
            <div class="input-group">
                <input type="text" name="username" placeholder="Username" required>
            </div>
            
            <div class="input-group">
                <input type="password" name="password" id="pwd" placeholder="Password" required>
                <span class="toggle-btn" onclick="togglePassword()">👁️</span>
            </div>
            
            <button type="submit">Sign In</button>
        </form>
    </div>

    <script>
        function togglePassword() {
            var pwdInput = document.getElementById("pwd");
            if (pwdInput.type === "password") {
                pwdInput.type = "text";
            } else {
                pwdInput.type = "password";
            }
        }
    </script>
</body>
</html>
"""


NORMAL_FAIL_PAGE = """
<html>
<body style="text-align:center; padding-top:100px; font-family:sans-serif;">
    <h2 style="color:red;">Login Failed</h2>
    <p>Invalid username or password.</p>
    <a href="/">Try Again</a>
</body>
</html>
"""

ERROR_TEMPLATE = """
<br />
<b>Warning</b>:  mysql_fetch_array() expects parameter 1 to be resource, boolean given in <b>/var/www/html/auth/auth_check.php</b> on line <b>38</b><br />
<br />
<b>Fatal error</b>:  Uncaught mysqli_sql_exception: __AI_ERROR__ in /var/www/html/includes/db.php:15
Stack trace:
#0 /var/www/html/auth/auth_check.php(38): mysqli_query(Object(mysqli), "__USER_QUERY__")
#1 {main}
  thrown in <b>/var/www/html/includes/db.php</b> on line <b>15</b><br />
"""

DUMP_TEMPLATE = """
<html>
<head><title>Debug View</title></head>
<body>
    <h2>[DEBUG] User Table Dump</h2>
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse; font-family:monospace; width:80%;">
        <thead style="background:#eee;">
            __TABLE_HEADER__
        </thead>
        <tbody>
            __TABLE_BODY__
        </tbody>
    </table>
    <p style="color:gray; font-size:0.8em;">Query executed in 0.04s</p>
</body>
</html>
"""

# 관제 대시보드
DASHBOARD_PAGE = """
<html>
<head>
    <title>Honeypot Control Center</title>
    <!-- 5초마다 자동 새로고침 -->
    <meta http-equiv="refresh" content="5">
    <style>
        body { background-color: #0d1117; color: #00ff41; font-family: 'Courier New', monospace; padding: 20px; }
        h1 { border-bottom: 2px solid #00ff41; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #30363d; padding: 10px; text-align: left; }
        th { background-color: #161b22; color: #fff; }
        tr:nth-child(even) { background-color: #0d1117; }
        tr:nth-child(odd) { background-color: #161b22; }
        .danger { color: #ff4444; font-weight: bold; }
        .badge { background: #238636; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    </style>
</head>
<body>
    <h1>👁️ HONEYPOT LIVE MONITOR</h1>
    <p>System Status: <span class="badge">ACTIVE</span> | Logs Collected: __LOG_COUNT__</p>
    
    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>Attacker IP</th>
                <th>Attack Type</th>
                <th>Input Payload</th>
                <th>AI Response</th>
            </tr>
        </thead>
        <tbody>
            __LOG_ROWS__
        </tbody>
    </table>
</body>
</html>
"""

# ==========================================
# [프롬프트]
# ==========================================
SYSTEM_PROMPT_ERROR = f"""
너는 MySQL 5.7 데이터베이스다. 
사용자의 쿼리에서 문법 오류가 발생하면, 아래 가짜 스키마를 참고하여 문맥에 맞는 에러 메시지 내용만 영어로 출력해라.
설명, 마크다운, 코드블록 없이 오직 텍스트만 뱉어라.
{FAKE_DB_SCHEMA}
"""

SYSTEM_PROMPT_DUMP = f"""
너는 해킹당한 데이터베이스다. 
사용자가 UNION SELECT 공격을 성공시켰다.
아래 [가짜 데이터베이스 명세]에 정의된 'Fixed Data' 3건을 사용하여 HTML <tr> 태그들을 생성해라.
오직 <tbody> 안에 들어갈 HTML 태그만 출력해.
{FAKE_DB_SCHEMA}
"""

# ==========================================
# [메인 로직]
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTMLResponse(content=LOGIN_PAGE)

# [New] 대시보드 접속용 엔드포인트
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(key: str = ""):
    # 간단한 보안 체크 (?key=1q2w3e4r!)
    if key != ADMIN_SECRET:
        return HTMLResponse(content="<h1 style='color:red;'>ACCESS DENIED</h1><p>Missing or wrong admin key.</p>", status_code=403)
    
    # 로그를 HTML 테이블 행으로 변환 (최신순 정렬)
    rows_html = ""
    for log in reversed(ATTACK_LOGS):
        rows_html += f"""
        <tr>
            <td>{log['time']}</td>
            <td>{log['ip']}</td>
            <td class="danger">{log['type']}</td>
            <td>{log['input']}</td>
            <td>{log['response']}</td>
        </tr>
        """
    
    if not rows_html:
        rows_html = "<tr><td colspan='5' style='text-align:center; color:gray;'>No attacks detected yet...</td></tr>"

    final_html = DASHBOARD_PAGE.replace("__LOG_ROWS__", rows_html)
    final_html = final_html.replace("__LOG_COUNT__", str(len(ATTACK_LOGS)))
    
    return HTMLResponse(content=final_html)


@app.post("/login")
async def fake_login(request: Request):
    try:
        # 클라이언트 IP 확보 (로컬에선 127.0.0.1로 뜸)
        client_ip = request.client.host
        
        form_data = await request.form()
        username = str(form_data.get("username", ""))
        password = str(form_data.get("password", ""))
        full_input = f"{username} {password}"
        
        # 1. 정상 유저
        if not is_attack_pattern(full_input):
            return HTMLResponse(content=NORMAL_FAIL_PAGE)

        # 2. 공격자 감지 -> AI 허니팟 & 로깅
        print(f"[!] Attack from {client_ip}: {full_input}")
        
        attack_type = "Unknown"
        ai_response_summary = ""
        final_html = ""

        # Case A: Dump
        if "union" in full_input.lower() and "select" in full_input.lower():
            attack_type = "UNION Injection (Dump)"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_DUMP},
                    {"role": "user", "content": f"Query: {full_input}"}
                ],
                temperature=0
            )
            fake_rows = response.choices[0].message.content or ""
            fake_rows = fake_rows.replace(MARKDOWN_HTML, "").replace(MARKDOWN_BLOCK, "").strip()
            
            fake_header = "<tr><th>id</th><th>username</th><th>password_hash</th><th>email</th><th>last_login</th></tr>"
            final_html = DUMP_TEMPLATE.replace("__TABLE_HEADER__", fake_header)
            final_html = final_html.replace("__TABLE_BODY__", fake_rows)
            
            ai_response_summary = "Fake Table Dump (3 rows)"

        # Case B: Error
        else:
            attack_type = "SQL Error Probing"
            query_snippet = full_input[:40]
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ERROR},
                    {"role": "user", "content": f"Query: {full_input}"}
                ],
                temperature=0.3
            )
            
            ai_error_msg = response.choices[0].message.content or "Error"
            ai_error_msg = ai_error_msg.replace(MARKDOWN_BLOCK, "").strip()
            
            final_html = ERROR_TEMPLATE.replace("__AI_ERROR__", ai_error_msg)
            final_html = final_html.replace("__USER_QUERY__", query_snippet)
            
            ai_response_summary = f"Error: {ai_error_msg[:30]}..."

        # [로그 기록]
        ATTACK_LOGS.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": client_ip,
            "type": attack_type,
            "input": full_input[:50] + "..." if len(full_input) > 50 else full_input,
            "response": ai_response_summary
        })

        return HTMLResponse(content=final_html)

    except Exception as e:
        print(f"[!] Server Error: {e}")
        return HTMLResponse(content=f"Server Error: {e}", status_code=200)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
