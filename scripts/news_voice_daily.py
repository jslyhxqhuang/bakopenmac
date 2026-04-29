#!/usr/bin/env python3
"""
每日新闻语音播报 v2
每天早上抓取中文新闻（财经/科技/体育），生成语音推送到 QQ
重点：全中文来源，去除英文噪音
"""

import fcntl, os, subprocess, re, sys, xml.etree.ElementTree, concurrent.futures
from datetime import datetime
import urllib.request

# ========== 配置 ==========
SCRIPT_DIR = "/Users/magichuang/.openclaw/workspace"
USER_ID = "E19D02C454BEE853199D3F98AB573C06"
AUDIO_PATH = f"{SCRIPT_DIR}/news_voice.mp3"
LOCK_FILE = "/tmp/news_voice_daily.lock"
LOG_DIR = f"{SCRIPT_DIR}/logs"
LOG_FILE = f"{LOG_DIR}/news_voice_daily.log"
PROXY = "http://127.0.0.1:7897"

# ========== MiniMax TTS HD ==========
MINIMAX_API_KEY = "sk-cp-bBvPXT4d8MrklAmqrYlA-_4TlbzfSpIdbfYfajC2onRid6zV_zD6vXbqIlS8b29kGFkv06ct674CuL7itzDfTvPAguL5k3MDnAQNY15-61dgNOUUkbWNMGg"
MINIMAX_TTS_URL = "https://api.minimaxi.com/v1/t2a_v2"
MINIMAX_MODEL = "speech-2.8-hd"
MINIMAX_VOICE_ID = "Cantonese_GentleLady"  # 粤语·温柔女声

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ========== 代理 Opener ==========
proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
proxy_opener = urllib.request.build_opener(proxy_handler)

# ========== 日志 ==========
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")

# ========== 通用工具 ==========
def fetch_page(url, timeout=12):
    """获取网页内容（走系统代理）"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with proxy_opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"请求失败 {url}: {e}")
        return ""

def extract_chinese_titles(html, max_items=10):
    """从HTML中提取中文新闻标题（去英文噪音）"""
    if not html:
        return []

    # 去除噪音标签
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # 提取所有 <a> 标签文本（新闻标题多在此）
    link_texts = re.findall(r'<a[^>]*>([^<]+)</a>', html)

    results = []
    seen = set()

    # 排除词（导航/广告/版权）
    skip_words = {
        '登录', '注册', '首页', '关于', '联系', '版权', '隐私', '用户',
        '菜单', '导航', '分享', '返回', '阅读', '评论', '收藏', '更多',
        'Previous', 'Next', 'Copyright', 'cookie', '关闭', '打开',
        '已有', '账号', '密码', '验证码', '发送', '获取', '同意',
    }

    for text in link_texts:
        text = text.strip()
        # 长度过滤
        if len(text) < 8 or len(text) > 70:
            continue
        # 必须有足够中文字符
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if chinese_count < 4:
            continue
        # 汉字占比 > 40%
        if chinese_count / len(text) < 0.4:
            continue
        # 排除导航开头
        if any(text.startswith(w) for w in skip_words):
            continue
        # 排除纯数字/符号
        if re.match(r'^[\d\s\.\,\:\-\+\%]+$', text):
            continue

        norm = re.sub(r'\s+', '', text)
        if norm and norm not in seen:
            seen.add(norm)
            results.append(text)

    return results[:max_items]

# ========== 新闻来源 ==========

def fetch_tmtpost():
    """钛媒体 RSS（科技+商业+财经，覆盖面广）"""
    url = "https://www.tmtpost.com/rss"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with proxy_opener.open(req, timeout=12) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        root = xml.etree.ElementTree.fromstring(data)
        items = root.findall('.//item')
        results = []
        for item in items[:10]:
            title_el = item.find('title')
            if title_el is not None and title_el.text:
                t = title_el.text.strip()
                chinese_count = sum(1 for c in t if '\u4e00' <= c <= '\u9fff')
                if chinese_count >= 4 and len(t) >= 8:
                    results.append(t)
        return results[:8]
    except Exception as e:
        log(f"钛媒体 RSS 失败: {e}")
        return []

def fetch_bbc_chinese():
    """BBC 中文（走代理）"""
    url = "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with proxy_opener.open(req, timeout=12) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        root = xml.etree.ElementTree.fromstring(data)
        items = root.findall('.//item')
        results = []
        for item in items[:8]:
            t = item.find('title')
            if t is not None and t.text and len(t.text.strip()) >= 6:
                results.append(t.text.strip())
        return results
    except Exception as e:
        log(f"BBC 中文失败: {e}")
        return []

def fetch_zaobao():
    """联合早报（走代理，提取主页中文标题）"""
    html = fetch_page("https://www.zaobao.com.sg/")
    titles = extract_chinese_titles(html, 10)
    # 过滤噪音标题
    skip = {'登录', '注册', '订阅', 'App', '关于', '联系', '版权'}
    return [t for t in titles if not any(t.startswith(w) for w in skip)]

def fetch_takungpao():
    """大公网（走代理，提取主页中文标题）"""
    html = fetch_page("https://www.takungpao.com.hk/")
    return extract_chinese_titles(html, 8)

def fetch_udn_money():
    """UDN 财经（走代理）"""
    html = fetch_page("https://money.udn.com/money/index")
    return extract_chinese_titles(html, 8)

def fetch_stnn():
    """星岛日报（走代理）"""
    html = fetch_page("https://www.stnn.cc/")
    return extract_chinese_titles(html, 8)

def fetch_sina_finance():
    """新浪财经"""
    html = fetch_page("https://finance.sina.com.cn/")
    return extract_chinese_titles(html, 10)

def fetch_163_sports():
    """网易体育"""
    html = fetch_page("https://sports.163.com/")
    return extract_chinese_titles(html, 10)

def fetch_guancha():
    """观察者网（政治军事）"""
    html = fetch_page("https://www.guancha.cn/")
    return extract_chinese_titles(html, 8)

# ========== 合成播报文本 ==========
def build_voice_text():
    date_str = datetime.now().strftime("%Y年%m月%d日")
    log("开始抓取新闻...")

    # 并行抓取各分类
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as executor:
        f_finance = executor.submit(fetch_sina_finance)
        f_sports = executor.submit(fetch_163_sports)
        f_tech = executor.submit(fetch_tmtpost)
        f_military = executor.submit(fetch_guancha)
        f_bbc = executor.submit(fetch_bbc_chinese)
        f_zaobao = executor.submit(fetch_zaobao)
        f_takungpao = executor.submit(fetch_takungpao)
        f_udn = executor.submit(fetch_udn_money)
        f_stnn = executor.submit(fetch_stnn)

        finance_news = f_finance.result()
        sports_news = f_sports.result()
        tech_news = f_tech.result()
        military_news = f_military.result()
        bbc_news = f_bbc.result()
        zaobao_news = f_zaobao.result()
        takungpao_news = f_takungpao.result()
        udn_news = f_udn.result()
        stnn_news = f_stnn.result()

    log(f"科技{len(tech_news)} | 财经{len(finance_news)} | 体育{len(sports_news)} | 军事{len(military_news)} | BBC{len(bbc_news)} | 早报{len(zaobao_news)} | 大公{len(takungpao_news)} | UDN{len(udn_news)} | 星岛{len(stnn_news)}")

    # 公众号样式排版（emoji 分类标题 + 简短条目，QQ 直接发文本）
    sections = []

    if tech_news:
        items = "\n  ".join([f"● {t}" for t in tech_news[:5]])
        sections.append(f"📱 科技商业\n  {items}")

    if finance_news:
        items = "\n  ".join([f"● {t}" for t in finance_news[:6]])
        sections.append(f"💰 财经股市\n  {items}")

    # 体育（过滤广告词）
    clean_sports = [t for t in sports_news if len(t) > 8 and not re.search(r'(购彩|专家|方案|哈利|魔法|奇迹|王者|联盟)', t)]
    if clean_sports:
        items = "\n  ".join([f"● {t}" for t in clean_sports[:5]])
        sections.append(f"⚽ 体育竞技\n  {items}")

    if military_news:
        items = "\n  ".join([f"● {t}" for t in military_news[:4]])
        sections.append(f"🎯 军事政治\n  {items}")

    if bbc_news:
        items = "\n  ".join([f"● {t}" for t in bbc_news[:4]])
        sections.append(f"🌍 国际要闻\n  {items}")

    # 海外华文（去重）
    overseas = zaobao_news + takungpao_news
    if overseas:
        seen = set()
        unique = []
        for t in overseas:
            norm = re.sub(r'\s+', '', t)
            if norm not in seen:
                seen.add(norm)
                unique.append(t)
        items = "\n  ".join([f"● {t}" for t in unique[:5]])
        sections.append(f"🌏 海外华文\n  {items}")

    if udn_news:
        items = "\n  ".join([f"● {t}" for t in udn_news[:4]])
        sections.append(f"📊 台港财经\n  {items}")
    if stnn_news:
        items = "\n  ".join([f"● {t}" for t in stnn_news[:4]])
        sections.append(f"📰 香港动态\n  {items}")

    if not sections:
        log("所有来源均失败，使用备用内容")
        return get_backup_text()

    # 组装公众号样式文本（粤语播报风格）
    header = f"📬 今日新聞播報 | {date_str}\n{'='*20}\n"
    body = "\n\n".join(sections)
    footer = f"\n{'='*20}\n✅ 以上就係今日新聞，祝你今日順利，生活愉快！"
    voice_text = header + body + footer

    # 截断（MiniMax TTS HD，约 1500 字上限，约 150 秒音频）
    if len(voice_text) > 1500:
        voice_text = voice_text[:1500] + f"\n{'='*20}\n✅ 以上就係今日新聞，祝你今日順利，生活愉快！"

    log(f"播报文本：{len(voice_text)} 字")
    return voice_text

def get_backup_text():
    """备用播报内容（粤语风格）"""
    return (
        "早晨，今日嘅新聞播報如下。科技方面，中国人工智能应用持续出海，多家企业宣布海外市场突破。"
        "财经方面，国内金融市场保持平稳，创业板指数小幅上扬。黄金价格近期波动加大，投资者关注美元走势。"
        "体育方面，斯诺克世锦赛正在进行，中国选手赵心童成功晋级八强。英超联赛曼城队继续领跑积分榜。"
        "以上就係今日新聞，祝你今日順利，生活愉快！"
    )

# ========== 生成语音（MiniMax TTS HD） ==========
def generate_voice(text, output_path):
    """使用 MiniMax TTS HD 生成语音（男声/清雅）"""
    import json, binascii

    payload = {
        "model": MINIMAX_MODEL,
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": MINIMAX_VOICE_ID,
            "speed": 1.0,
            "vol": 1,
            "pitch": 0,
            "emotion": "happy"
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1
        }
    }

    req = urllib.request.Request(
        MINIMAX_TTS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            # audio 字段是 hex 编码的 MP3 数据
            audio_hex = result["data"]["audio"]
            audio_bytes = binascii.unhexlify(audio_hex)

            ei = result["extra_info"]
            log(f"MiniMax TTS 成功，{ei['audio_length']/1000:.1f}s，{len(audio_bytes)} bytes")

            # 直接写入 MP3（无需转码，MiniMax 已返回 MP3）
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 1000

    except Exception as e:
        log(f"MiniMax TTS 失败: {e}")
        return generate_voice_fallback(text, output_path)

def generate_voice_fallback(text, output_path):
    """macOS say fallback"""
    text_file = "/tmp/news_voice_input.txt"
    with open(text_file, "w") as f:
        f.write(text)
    aiff_path = "/tmp/news_voice_output.aiff"
    for voice in ["Tingting", "Sinji", "Meijia"]:
        r = subprocess.run(["/usr/bin/say", "-v", voice, "-o", aiff_path, "-f", text_file],
                          timeout=60, capture_output=True)
        if r.returncode == 0 and os.path.exists(aiff_path) and os.path.getsize(aiff_path) > 1000:
            log(f"say fallback 成功: {voice}")
            break
    if os.path.exists("/opt/homebrew/bin/ffmpeg"):
        subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-i", aiff_path,
                        "-f", "mp3", "-ab", "192000", output_path], capture_output=True)
    else:
        subprocess.run(["cp", aiff_path, output_path])
    os.remove(text_file)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000

# ========== 发送音频（Node.js + silk-wasm） ==========
def send_audio_via_node(audio_path, target_user):
    """通过 Node.js + silk-wasm 发送 SILK 格式语音到 QQ"""
    node_script = f"""
const fs = require('fs');
const https = require('https');
const {{ execSync }} = require('child_process');
const silk = require('/Users/magichuang/.openclaw/plugin-runtime-deps/openclaw-2026.4.24-da6bdffc3d96/node_modules/silk-wasm/lib/index.cjs');

const APP_ID = '1903672709';
const APP_SECRET = 'cCmNyZAlMyaCoQ2eHuXAnQ3gKycGuYCr';
const USER_ID = process.argv[2];
const MP3_PATH = process.argv[3];

function httpPost(hostname, path, headers, body) {{
    return new Promise((resolve, reject) => {{
        const req = https.request({{ hostname, path, method: 'POST', headers, rejectUnauthorized: false }}, res => {{
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve({{ status: res.statusCode, body: data }}));
        }});
        req.on('error', reject);
        req.write(body);
        req.end();
    }});
}}

async function getAccessToken() {{
    const body = JSON.stringify({{ appId: APP_ID, clientSecret: APP_SECRET }});
    const resp = await httpPost('bots.qq.com', '/app/getAppAccessToken',
        {{ 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }}, body);
    return JSON.parse(resp.body).access_token;
}}

async function uploadMedia(token, openid, fileData) {{
    const body = JSON.stringify({{ file_type: 3, srv_send_msg: false, file_data: fileData.toString('base64') }});
    const resp = await httpPost('api.sgroup.qq.com', `/v2/users/${{openid}}/files`, {{
        'Authorization': `QQBot ${{token}}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
    }}, body);
    return JSON.parse(resp.body);
}}

async function sendVoiceMsg(token, openid, fileInfo) {{
    const body = JSON.stringify({{ msg_type: 7, media: {{ file_info: fileInfo }} }});
    const resp = await httpPost('api.sgroup.qq.com', `/v2/users/${{openid}}/messages`, {{
        'Authorization': `QQBot ${{token}}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
    }}, body);
    return JSON.parse(resp.body);
}}

async function main() {{
    const token = await getAccessToken();
    const pcmPath = '/tmp/news_voice_send.pcm';
    execSync('/opt/homebrew/bin/ffmpeg -y -i ' + MP3_PATH + ' -ar 24000 -ac 1 -acodec pcm_s16le -f s16le ' + pcmPath + ' 2>/dev/null');
    const pcmData = fs.readFileSync(pcmPath);
    const result = await silk.encode(pcmData, 24000);
    const silkBuffer = Buffer.from(result.data.buffer, result.data.byteOffset, result.data.byteLength);
    const uploadData = await uploadMedia(token, USER_ID, silkBuffer);
    const fileInfo = uploadData.file_info || uploadData.uuid;
    const sendData = await sendVoiceMsg(token, USER_ID, fileInfo);
    if (sendData.id) {{
        console.log('SUCCESS:' + sendData.id);
    }} else {{
        console.log('FAIL:' + JSON.stringify(sendData));
        process.exit(1);
    }}
}}

main().catch(e => {{ console.error('ERROR:' + e.message); process.exit(1); }});
"""
    script_path = "/tmp/send_voice_node.js"
    with open(script_path, "w") as f:
        f.write(node_script)

    result = subprocess.run(
        ["node", script_path, target_user, audio_path],
        capture_output=True, text=True, timeout=120
    )
    log(f"Node stdout: {result.stdout.strip()}")
    if result.stderr:
        log(f"Node stderr: {result.stderr.strip()[:200]}")
    return result.returncode == 0 and "SUCCESS:" in result.stdout

# ========== 主流程 ==========
def main():
    log("========== 新闻语音播报开始 ==========")

    lock_fp = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log("已有实例运行，退出")
        sys.exit(0)

    text = build_voice_text()

    # 先发送文字版
    log("发送文字版...")
    try:
        # 调用 openclaw message send 发送文本
        r = subprocess.run(
            ["/opt/homebrew/bin/openclaw", "message", "send",
             "--channel", "qqbot",
             "--target", USER_ID,
             "--message", text],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            log("文字版发送成功")
        else:
            log(f"文字版发送失败: {r.stderr[:100]}")
    except Exception as e:
        log(f"文字版发送异常: {e}")

    # 再发送语音版
    if not generate_voice(text, AUDIO_PATH):
        log("语音生成失败，退出")
        sys.exit(1)

    log(f"音频文件：{os.path.getsize(AUDIO_PATH)} bytes")

    success = send_audio_via_node(AUDIO_PATH, USER_ID)
    if success:
        log("✅ 推送完成！")
    else:
        log("❌ 推送失败")
        sys.exit(1)

    log("========== 播报任务结束 ==========")

if __name__ == "__main__":
    main()
