from flask import Flask, render_template, jsonify, request, session, url_for
import data
import json
import math
import copy
import numpy_financial as npf
import time
import random
import os
import re
import uuid
import requests
from datetime import datetime, timedelta
import calendar
from dotenv import load_dotenv
load_dotenv()

import qrcode
import base64
from io import BytesIO

def generate_qr_code(text):
    """生成 QR Code 圖片並返回 base64 字串"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    # 注意：這裡回傳的是帶有 Data URI 前綴的完整字串
    return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

# 引入處理真實音訊與語音識別的庫
import speech_recognition as sr
from pydub import AudioSegment
from groq import Groq

# ========== 設定區 ==========
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
VERIFIER_API_BASE = 'https://verifier-sandbox.wallet.gov.tw'
VERIFIER_ACCESS_TOKEN = os.getenv('VERIFIER_ACCESS_TOKEN', '')

# ========== 強制指定 FFmpeg 路徑 (解決 Windows 環境問題) ==========
base_dir = os.path.dirname(os.path.abspath(__file__))
# 如果是在雲端 (PythonAnywhere)，請將下面這兩行註解掉
AudioSegment.converter = os.path.join(base_dir, "ffmpeg.exe")
AudioSegment.ffprobe = os.path.join(base_dir, "ffprobe.exe")
# =============================================================

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'hcap-demo-secret-key-2023')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'static', 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.after_request
def inject_translate_script(response):
    if response.mimetype != 'text/html':
        return response

    if 'voice_ai' in request.path:
        return response

    translate_html = '''
    <div id="google_translate_element" style="display:none;"></div>
    
    <div id="hcap-translate-portal" class="notranslate">
        <div id="drag-handle" title="按住拖拽"><i class="fas fa-grip-vertical"></i></div>
        <div class="lang-items-container">
            <div class="lang-item"><button class="lang-node" data-lang="zh-TW">CH</button><span class="lang-desc">繁體中文</span></div>
            <div class="lang-item"><button class="lang-node" data-lang="en">EN</button><span class="lang-desc">English</span></div>
            <div class="lang-item"><button class="lang-node" data-lang="vi">VN</button><span class="lang-desc">Tiếng Việt</span></div>
            <div class="lang-item"><button class="lang-node" data-lang="id">ID</button><span class="lang-desc">Indonesia</span></div>
            <div class="lang-item"><button class="lang-node" data-lang="th">TH</button><span class="lang-desc">ภาษาไทย</span></div>
        </div>
    </div>

    <style>
        /* --- 終極暴力消滅 Google 橫條 (Banner) --- */
        html { 
            top: 0px !important; 
        }
        body { 
            top: 0px !important; 
            position: static !important; 
        }
        .goog-te-banner-frame {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }
        .skiptranslate {
            display: none !important;
        }
        #goog-gt-tt, .goog-te-balloon-frame, .goog-tooltip {
            display: none !important;
        }
        font {
            background-color: transparent !important;
            box-shadow: none !important;
        }

        /* --- 翻譯控制面板樣式 --- */
        #hcap-translate-portal {
            position: fixed;
            top: 30px;
            right: 30px;
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px 20px;
            background: rgba(255, 255, 255, 0.4);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 25px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.15);
            border: 1px solid rgba(255,255,255,0.5);
            z-index: 2147483647; /* 確保在最最最上層 */
            transform-origin: top right;
            transition: transform 0.1s ease-out;
            animation: floatIn 1s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        #drag-handle { cursor: move; color: #4a5568; padding: 10px 5px; font-size: 20px; }
        .lang-items-container { display: flex; gap: 15px; }
        .lang-item { display: flex; flex-direction: column; align-items: center; gap: 6px; }
        .lang-node {
            width: 55px; height: 55px; border-radius: 15px; border: none;
            background: #ffffff; color: #2d3748; font-size: 16px; font-weight: 800;
            cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: 0.3s;
        }
        .lang-node:hover { transform: translateY(-8px); background: #667eea; color: white; }
        .lang-node.active { background: #4a5568; color: white; }
        .lang-desc { font-size: 11px; font-weight: 600; color: #2d3748; }

        @keyframes floatIn {
            from { opacity: 0; transform: translateY(-40px) scale(0.9); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .language-selector { display: none !important; }
    </style>

    <script type="text/javascript">
        function googleTranslateElementInit() {
            new google.translate.TranslateElement({
                pageLanguage: 'zh-TW', 
                includedLanguages: 'zh-TW,en,vi,id,th', 
                autoDisplay: false
            }, 'google_translate_element');
        }

        // 定時監控並刪除可能殘留的橫條
        setInterval(function() {
            const banner = document.querySelector(".goog-te-banner-frame");
            if (banner) {
                banner.style.display = 'none';
                banner.remove();
            }
            document.documentElement.style.top = '0px';
            document.body.style.top = '0px';
        }, 100);

        function syncTranslate(lang) {
            const combo = document.querySelector('.goog-te-combo');
            if (combo) {
                combo.value = lang;
                combo.dispatchEvent(new Event('change'));
                document.querySelectorAll('.lang-node').forEach(b => {
                    b.classList.toggle('active', b.dataset.lang === lang);
                });
            } else {
                setTimeout(() => syncTranslate(lang), 500);
            }
        }

        const portal = document.getElementById('hcap-translate-portal');
        const handle = document.getElementById('drag-handle');
        let isDragging = false;
        let offset = [0, 0];

        handle.addEventListener('mousedown', (e) => {
            isDragging = true;
            offset = [portal.offsetLeft - e.clientX, portal.offsetTop - e.clientY];
            portal.style.transition = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                portal.style.left = (e.clientX + offset[0]) + 'px';
                portal.style.top = (e.clientY + offset[1]) + 'px';
                portal.style.right = 'auto';
                portal.style.bottom = 'auto';
            }
        });

        document.addEventListener('mouseup', () => { isDragging = false; portal.style.transition = 'transform 0.1s ease-out'; });

        let scale = 1;
        portal.addEventListener('wheel', (e) => {
            e.preventDefault();
            scale += e.deltaY * -0.0008;
            scale = Math.min(Math.max(.5, scale), 1.8); 
            portal.style.transform = `scale(${scale})`;
        });

        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.lang-node');
            if (btn) {
                const lang = btn.dataset.lang;
                localStorage.setItem('hcap_language', lang);
                syncTranslate(lang);
            }
        });

        window.addEventListener('load', () => {
            const savedLang = localStorage.getItem('hcap_language');
            if (savedLang && savedLang !== 'zh-TW') syncTranslate(savedLang);
        });
    </script>
    <script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
    '''
    
    content = response.get_data(as_text=True)
    response.set_data(content.replace('</body>', translate_html + '</body>'))
    return response
    
# ========== [核心資料庫] Bank Data Lake (每位客戶各一份) ==========
def _create_bank_db(applicant_id, name, remit_status, regularity, avg_amt, last_sync,
                    voice_status, risk_score, vp_match, voice_ts, voice_details):
    return {
        "applicant_info": { "id": applicant_id, "name": name, "status": "Under Review", "login_verified": False },
        "remittance_data": { "status": remit_status, "regularity_rate": regularity, "avg_amount": avg_amt, "last_sync_time": last_sync },
        "voice_analysis": {
            "status": voice_status,
            "risk_score": risk_score,
            "voiceprint_match": vp_match,
            "stress_level": "--",
            "timestamp": voice_ts,
            "details": voice_details,
            "full_video_url": ""
        },
        "risk_logs": []
    }

BANK_DATABASES = {
    "low_risk": _create_bank_db(
        "9823451", "Nguyen Van A",
        "Synced", 95, 12000, "2026-02-10 09:32:15",
        "Verified", 88, 97, "2026-02-10 10:15:42",
        [
            {"question": "Q1", "video_url": "", "transcript": "我保證所提供的資料真實無誤。", "score": 92, "reason": "宣誓朗讀完整，語氣堅定", "timestamp": "10:02"},
            {"question": "Q2", "video_url": "", "transcript": "我在鴻海精密工業擔任組裝技術員，負責電子零件組裝。", "score": 90, "reason": "職業描述明確，與申報一致", "timestamp": "10:05"},
            {"question": "Q3", "video_url": "", "transcript": "主要是每月匯款給越南家人，也想存一些緊急備用金。", "score": 85, "reason": "借款目的合理，家庭匯款為主", "timestamp": "10:08"},
            {"question": "Q4", "video_url": "", "transcript": "工廠每週大概加班兩到三次，每次三到四個小時。", "score": 88, "reason": "加班頻率描述具體，收入穩定", "timestamp": "10:11"},
            {"question": "Q5", "video_url": "", "transcript": "我有固定存款習慣，每月薪水扣掉生活費和匯款後還能存五千元。", "score": 85, "reason": "還款計劃清晰，有儲蓄習慣", "timestamp": "10:14"},
        ]
    ),
    "medium_risk": _create_bank_db(
        "9823452", "Maria Santos",
        "Synced", 80, 9500, "2026-02-08 14:20:33",
        "Verified", 68, 91, "2026-02-08 15:05:18",
        [
            {"question": "Q1", "video_url": "", "transcript": "I guarantee the data is true and genuine.", "score": 75, "reason": "宣誓完整但語氣略顯猶豫", "timestamp": "14:32"},
            {"question": "Q2", "video_url": "", "transcript": "I work as a packaging operator at Wistron factory.", "score": 70, "reason": "職業描述簡短但與申報吻合", "timestamp": "14:35"},
            {"question": "Q3", "video_url": "", "transcript": "I need money for my children education back in Philippines.", "score": 65, "reason": "借款目的合理但缺乏具體規劃", "timestamp": "14:38"},
            {"question": "Q4", "video_url": "", "transcript": "Sometimes I get overtime, maybe one or two times a week.", "score": 68, "reason": "加班頻率不固定，收入穩定度中等", "timestamp": "14:41"},
            {"question": "Q5", "video_url": "", "transcript": "I will use my monthly salary to pay back.", "score": 62, "reason": "還款計劃模糊，未提及具體金額", "timestamp": "14:44"},
        ]
    ),
    "high_risk": _create_bank_db(
        "9823453", "Budi Santoso",
        "Synced", 65, 6000, "2026-01-25 11:45:10",
        "Failed", 42, 72, "2026-01-25 13:20:55",
        [
            {"question": "Q1", "video_url": "", "transcript": "嗯...我保證資料是真的。", "score": 55, "reason": "宣誓不完整，有明顯停頓", "timestamp": "12:50"},
            {"question": "Q2", "video_url": "", "transcript": "清潔。", "score": 40, "reason": "回答過於簡短，缺乏職業細節", "timestamp": "12:53"},
            {"question": "Q3", "video_url": "", "transcript": "需要錢...生活費。", "score": 35, "reason": "借款目的模糊，無法判斷合理性", "timestamp": "12:56"},
            {"question": "Q4", "video_url": "", "transcript": "最近沒有加班了。", "score": 38, "reason": "無加班收入，收入來源不穩定", "timestamp": "12:59"},
            {"question": "Q5", "video_url": "", "transcript": "之後再說吧。", "score": 42, "reason": "迴避還款問題，缺乏還款意願", "timestamp": "13:02"},
        ]
    ),
}

# 向下相容：保留 BANK_DATABASE 作為預設 (low_risk)
BANK_DATABASE = BANK_DATABASES["low_risk"]

def get_client_db(client_id=None):
    """取得指定客戶的銀行資料庫"""
    if client_id:
        _ensure_client_infra(client_id)
        return BANK_DATABASES[client_id]
    return BANK_DATABASES["low_risk"]

# ========== [App Simulator 專用] 即時數位心跳資料 (每位客戶各一份) ==========
def _make_event(day, event, risk_level, trust_score, time_str, gps_ctx='工廠宿舍區', gps_status='safe',
                device_status=None, l2=True, l3=False):
    if device_status is None:
        device_status = {'math': 'good', 'wifi': 'good', 'batt': 'good'}
    return {
        'day': day, 'event': event, 'risk_level': risk_level, 'trust_score': trust_score,
        'time': time_str, 'timestamp': 0, 'is_demo': True,
        'l2_enabled': l2, 'l3_enabled': l3,
        'gps_context': gps_ctx, 'gps_status': gps_status,
        'device_status': device_status
    }

# --- Nguyen Van A (low_risk): 信任高、穩定運行 30 天 ---
_LOW_RISK_EVENTS = [
    _make_event(0, 'System: 裝置綁定成功 (FIDO)', 1, 100, '09:00:01'),
    _make_event(1, 'Auto L1: Wi-Fi SSID 一致 (Foxconn-Dorm-5F)', 1, 98, '09:15:22'),
    _make_event(2, 'L2 Math: 數學挑戰通過 (3.2秒)', 1, 97, '09:30:10'),
    _make_event(4, 'Auto L1: 電量模式正常 (72%→68%, -0.5%/hr)', 1, 96, '12:05:33'),
    _make_event(7, '📦 週結算: 平均 97分, 獎勵 500 H-Coins', 1, 97, '23:59:59'),
    _make_event(8, 'Auto L1: Wi-Fi SSID 一致 (Foxconn-Factory-B2)', 1, 96, '08:12:45'),
    _make_event(10, 'L2 Math: 數學挑戰通過 (2.8秒)', 1, 98, '10:20:18'),
    _make_event(14, '📦 週結算: 平均 96分, 獎勵 500 H-Coins', 1, 96, '23:59:59'),
    _make_event(15, 'Auto L1: 電量模式正常 (85%→80%, -0.4%/hr)', 1, 95, '14:30:22'),
    _make_event(18, 'L2 Math: 數學挑戰通過 (2.5秒)', 1, 97, '09:45:33'),
    _make_event(21, '📦 週結算: 平均 96分, 獎勵 500 H-Coins', 1, 96, '23:59:59'),
    _make_event(22, 'Auto L1: Wi-Fi SSID 一致 (Foxconn-Dorm-5F)', 1, 95, '22:10:05'),
    _make_event(25, 'L2 Math: 數學挑戰通過 (3.0秒)', 1, 96, '10:05:12'),
    _make_event(27, 'Auto L1: 電量模式正常 (90%→85%, -0.3%/hr)', 1, 95, '16:20:44'),
    _make_event(28, '📦 週結算: 平均 95分, 獎勵 500 H-Coins', 1, 95, '23:59:59'),
    _make_event(30, 'Auto L1: Wi-Fi SSID 一致 (Foxconn-Dorm-5F)', 1, 95, '21:30:18'),
]

# --- Maria Santos (medium_risk): 偶有異常、中等風險 ---
_MED_RISK_EVENTS = [
    _make_event(0, 'System: 裝置綁定成功 (FIDO)', 1, 100, '10:00:01'),
    _make_event(1, 'Auto L1: Wi-Fi SSID 一致 (Wistron-Dorm-3F)', 1, 95, '10:20:15'),
    _make_event(3, 'L2 Math: 數學挑戰通過 (4.8秒)', 1, 90, '11:05:22'),
    _make_event(5, 'Auto L1: 電量模式正常 (60%→55%, -0.6%/hr)', 1, 88, '14:15:30'),
    _make_event(7, '📦 週結算: 平均 90分, 獎勵 500 H-Coins', 1, 90, '23:59:59'),
    _make_event(9, '⚠️ L1 Alert: Wi-Fi SSID 變更 (Unknown-Cafe-WiFi)', 2, 75, '19:30:44',
                device_status={'math': 'good', 'wifi': 'warn', 'batt': 'good'}),
    _make_event(10, 'Auto L1: Wi-Fi SSID 恢復 (Wistron-Dorm-3F)', 1, 80, '08:05:12'),
    _make_event(12, 'L2 Math: 數學挑戰通過 (5.2秒)', 1, 82, '09:50:33'),
    _make_event(14, '📦 週結算: 平均 80分, 獎勵 300 H-Coins', 1, 80, '23:59:59'),
    _make_event(16, '⚠️ L1 Alert: 電量異常消耗 (45%→20%, -2.1%/hr)', 2, 72, '16:40:55',
                device_status={'math': 'good', 'wifi': 'good', 'batt': 'warn'}),
    _make_event(17, 'Auto L1: 電量模式恢復正常', 1, 76, '09:10:22'),
    _make_event(19, 'L2 Math: 數學挑戰通過 (4.5秒)', 1, 78, '10:30:18'),
    _make_event(20, 'Auto L1: Wi-Fi SSID 一致 (Wistron-Factory-A1)', 1, 78, '08:20:45'),
    _make_event(21, '📦 週結算: 平均 76分, 獎勵 300 H-Coins', 1, 76, '23:59:59'),
    _make_event(22, 'Auto L1: Wi-Fi SSID 一致 (Wistron-Dorm-3F)', 1, 75, '21:50:33'),
]

# --- Budi Santoso (high_risk): 多次異常、收入中斷 ---
_HIGH_RISK_EVENTS = [
    _make_event(0, 'System: 裝置綁定成功 (FIDO)', 1, 100, '11:00:01'),
    _make_event(1, 'Auto L1: Wi-Fi SSID 一致 (SmallFactory-Office)', 1, 90, '11:20:10'),
    _make_event(2, 'L2 Math: 數學挑戰通過 (6.5秒)', 1, 85, '12:05:22'),
    _make_event(4, '⚠️ L1 Alert: Wi-Fi SSID 變更 (FreeWiFi-TaipeiStation)', 2, 70, '20:15:44',
                device_status={'math': 'good', 'wifi': 'warn', 'batt': 'good'}),
    _make_event(5, '❌ L2 Math: 數學挑戰失敗 (超時 15秒)', 3, 55, '09:30:12',
                device_status={'math': 'danger', 'wifi': 'warn', 'batt': 'good'}),
    _make_event(7, '📦 週結算: 平均 65分, 獎勵 100 H-Coins', 1, 65, '23:59:59'),
    _make_event(8, '⚠️ L1 Alert: 電量異常消耗 (80%→30%, -4.2%/hr)', 2, 55, '15:40:33',
                device_status={'math': 'danger', 'wifi': 'good', 'batt': 'warn'}),
    _make_event(9, '❌ L2 Math: 數學挑戰失敗 (答案錯誤)', 3, 42, '10:20:55',
                device_status={'math': 'danger', 'wifi': 'good', 'batt': 'warn'}),
    _make_event(10, '⚠️ L1 Alert: Wi-Fi SSID 變更 (Unknown-Mobile-Hotspot)', 2, 38, '18:50:12',
                device_status={'math': 'danger', 'wifi': 'warn', 'batt': 'warn'}),
    _make_event(12, 'CRITICAL: 連續異常事件觸發風控預警', 3, 30, '09:00:00',
                device_status={'math': 'danger', 'wifi': 'warn', 'batt': 'warn'}),
    _make_event(14, '📦 週結算: 平均 45分, 無獎勵', 2, 35, '23:59:59',
                device_status={'math': 'danger', 'wifi': 'warn', 'batt': 'warn'}),
    _make_event(15, 'Auto L1: Wi-Fi SSID 恢復 (SmallFactory-Office)', 1, 40, '08:10:22'),
    _make_event(16, '⚠️ 雇主通報: 該移工已無薪假 (收入中斷)', 3, 32, '14:00:00',
                device_status={'math': 'danger', 'wifi': 'good', 'batt': 'warn'}),
    _make_event(18, '❌ L2 Math: 數學挑戰失敗 (未回應)', 3, 28, '10:15:45',
                device_status={'math': 'danger', 'wifi': 'good', 'batt': 'warn'}),
]

REALTIME_RISK_DATAS = {
    "low_risk": list(_LOW_RISK_EVENTS),
    "medium_risk": list(_MED_RISK_EVENTS),
    "high_risk": list(_HIGH_RISK_EVENTS),
}
# 向下相容
REALTIME_RISK_DATA = REALTIME_RISK_DATAS["low_risk"]

LAST_HEARTBEAT_TIMES = { "low_risk": time.time(), "medium_risk": time.time(), "high_risk": time.time() }
LAST_HEARTBEAT_TIME = LAST_HEARTBEAT_TIMES["low_risk"]

CURRENT_DAY_COUNTERS = { "low_risk": 30, "medium_risk": 22, "high_risk": 18 }
CURRENT_DAY_COUNTER = CURRENT_DAY_COUNTERS["low_risk"]

# [新增] 全域狀態暫存 (每位客戶各一份)
CLIENT_STATES = {
    "low_risk": {
        'l2_enabled': True, 'l3_enabled': False,
        'gps_context': '工廠宿舍區', 'gps_status': 'safe',
        'trust_score': 95, 'coins': 2000,
        'device_status': {'math': 'good', 'wifi': 'good', 'batt': 'good'},
        'weekly_scores': []
    },
    "medium_risk": {
        'l2_enabled': True, 'l3_enabled': False,
        'gps_context': '宿舍區域', 'gps_status': 'safe',
        'trust_score': 75, 'coins': 1100,
        'device_status': {'math': 'good', 'wifi': 'good', 'batt': 'good'},
        'weekly_scores': []
    },
    "high_risk": {
        'l2_enabled': True, 'l3_enabled': False,
        'gps_context': '未知區域', 'gps_status': 'warn',
        'trust_score': 28, 'coins': 100,
        'device_status': {'math': 'danger', 'wifi': 'good', 'batt': 'warn'},
        'weekly_scores': []
    },
}
CLIENT_STATE = CLIENT_STATES["low_risk"]

def _ensure_client_infra(client_id):
    """確保指定 client_id 有完整的狀態/風險/銀行資料基礎設施"""
    if client_id and client_id not in CLIENT_STATES:
        CLIENT_STATES[client_id] = {
            'l2_enabled': False, 'l3_enabled': False,
            'gps_context': '未啟用', 'gps_status': 'safe',
            'trust_score': 50, 'coins': 0,
            'device_status': {'math': 'good', 'wifi': 'good', 'batt': 'good'},
            'weekly_scores': []
        }
    if client_id and client_id not in REALTIME_RISK_DATAS:
        REALTIME_RISK_DATAS[client_id] = []
    if client_id and client_id not in BANK_DATABASES:
        BANK_DATABASES[client_id] = _create_bank_db(
            client_id.upper(), "Guest", "Not Synced", 0, 0, "--",
            "Not Verified", 0, 0, "--", []
        )

def get_client_risk_data(client_id=None):
    """取得指定客戶的即時風險資料"""
    if client_id:
        _ensure_client_infra(client_id)
    cid = client_id if client_id and client_id in REALTIME_RISK_DATAS else "low_risk"
    return REALTIME_RISK_DATAS[cid]

def get_client_state(client_id=None):
    """取得指定客戶的狀態"""
    if client_id:
        _ensure_client_infra(client_id)
    cid = client_id if client_id and client_id in CLIENT_STATES else "low_risk"
    return CLIENT_STATES[cid]

# ========== [雇主資料庫] ==========
EMPLOYERS = {
    "confirmed": [
        {"id": "EMP-001", "name": "鴻海精密工業", "type": "large_tech", "rating": "AA", "industry": "電子製造", "employees": 128, "outlook": "穩定"},
        {"id": "EMP-002", "name": "緯創資通", "type": "medium_tech", "rating": "A", "industry": "電子製造", "employees": 85, "outlook": "穩定"},
        {"id": "EMP-003", "name": "台積電供應鏈", "type": "large_tech", "rating": "AA", "industry": "半導體", "employees": 200, "outlook": "穩定"},
        {"id": "EMP-004", "name": "廣達電腦", "type": "medium_tech", "rating": "A", "industry": "電子製造", "employees": 95, "outlook": "穩定"},
        {"id": "EMP-005", "name": "中小型電子廠", "type": "small_factory", "rating": "B", "industry": "電子製造", "employees": 30, "outlook": "保守"},
        {"id": "EMP-006", "name": "傳統金屬加工廠", "type": "small_factory", "rating": "C", "industry": "傳統製造", "employees": 15, "outlook": "保守"},
    ],
    "pending": []
}

def lookup_employer_type(company_name):
    """根據公司名稱查找已確認雇主的 type，找不到則預設 medium_tech"""
    if not company_name:
        return 'medium_tech'
    for emp in EMPLOYERS['confirmed']:
        if emp['name'] == company_name or company_name in emp['name'] or emp['name'] in company_name:
            return emp['type']
    return 'medium_tech'

def add_pending_employer(company_name):
    """將新公司名稱加入待確認雇主（若不重複）"""
    if not company_name:
        return
    for emp in EMPLOYERS['confirmed']:
        if emp['name'] == company_name:
            return
    for emp in EMPLOYERS['pending']:
        if emp['name'] == company_name:
            return
    new_id = f"EMP-P{len(EMPLOYERS['pending']) + 1:03d}"
    EMPLOYERS['pending'].append({
        "id": new_id, "name": company_name, "type": "medium_tech",
        "rating": "A", "industry": "傳統製造", "employees": 100, "outlook": "保守",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

def lookup_employer_info(company_name):
    """根據公司名稱查找雇主完整資訊（confirmed + pending），回傳 dict 或 None"""
    if not company_name:
        return None
    for emp in EMPLOYERS['confirmed'] + EMPLOYERS['pending']:
        if emp['name'] == company_name or company_name in emp['name'] or emp['name'] in company_name:
            return emp
    return None

# --- 雇主評級 → 算法 type 對應表 ---
RATING_TO_TYPE = {
    'AA': 'large_tech', 'A': 'medium_tech', 'BBB': 'medium_tech',
    'BB': 'small_factory', 'B': 'small_factory', 'B+': 'caregiver',
    'C': 'unstable', '--': 'medium_tech'
}
RATING_TO_SCORE = {
    'AA': 95, 'A': 80, 'BBB': 75, 'BB': 65, 'B': 60, 'B+': 75, 'C': 55, '--': 80
}
RATING_TO_GRADE = {
    'AA': 'AA', 'A': 'A', 'BBB': 'BBB', 'BB': 'BB', 'B': 'B', 'B+': 'B+', 'C': 'C', '--': '--'
}

def recalculate_clients_for_employer(employer_name, new_employer_data):
    """當雇主資料變動時，重新計算所有關聯客戶的 H-CAP 分數"""
    rating = new_employer_data.get('rating', 'A')
    new_type = RATING_TO_TYPE.get(rating, 'medium_tech')
    new_score = RATING_TO_SCORE.get(rating, 80)
    new_grade = RATING_TO_GRADE.get(rating, rating)
    new_industry = new_employer_data.get('industry', '傳統製造')
    new_outlook = new_employer_data.get('outlook', '保守')

    for _cid, client in data.DEMO_CLIENTS.items():
        client_employer = client.get('company_name', '') or client.get('employer', '')
        if not client_employer:
            continue
        if client_employer != employer_name and employer_name not in client_employer and client_employer not in employer_name:
            continue

        # 更新雇主評級資訊
        client['employer_rating'] = {
            "score": new_score, "grade": new_grade,
            "industry": new_industry, "outlook": new_outlook
        }

        form_data = client.get('_form_data')
        if not form_data:
            continue

        form_data['employerType'] = new_type

        # --- 信貸模型重算 ---
        loan_result = calculate_client_score(form_data, product_type='loan')
        new_loan_score = loan_result['total_score']
        client['hcap_score'] = new_loan_score
        client['score_breakdown'] = {
            "repayment_capacity": {"score": loan_result['repayment_capacity_score'], "weight": 40},
            "income_stability": {"score": loan_result['income_stability_score'], "weight": 30},
            "repayment_willingness": {"score": loan_result['repayment_willingness_score'], "weight": 20},
            "external_risk": {"score": loan_result['external_risk_score'], "weight": 10}
        }

        # --- 信用卡模型重算（若有 card_hcap_score） ---
        if 'card_hcap_score' in client:
            card_result = calculate_client_score(form_data, product_type='card')
            client['card_hcap_score'] = card_result['total_score']
            client['card_score_breakdown'] = {
                "repayment_capacity": {"score": card_result['repayment_capacity_score'], "weight": 20},
                "income_stability": {"score": card_result['income_stability_score'], "weight": 30},
                "repayment_willingness": {"score": card_result['repayment_willingness_score'], "weight": 30},
                "external_risk": {"score": card_result['external_risk_score'], "weight": 20}
            }

        # --- 重新判定貸款建議 ---
        loan_approved = new_loan_score >= 650
        max_amount = 0; interest_rate = 0
        if loan_approved:
            if new_loan_score >= 750: max_amount = 50000; interest_rate = 9.5
            elif new_loan_score >= 700: max_amount = 40000; interest_rate = 10.5
            elif new_loan_score >= 650: max_amount = 30000; interest_rate = 12.5
        client['loan_recommendation']['survival_loan']['approved'] = loan_approved
        client['loan_recommendation']['survival_loan']['max_amount'] = max_amount
        client['loan_recommendation']['survival_loan']['interest_rate'] = interest_rate
        client['loan_recommendation']['survival_loan']['reason'] = "" if loan_approved else f"綜合評分不足 ({new_loan_score}分)"

        # ISA 資格
        client['loan_recommendation']['isa']['qualified'] = new_loan_score >= 680
        client['loan_recommendation']['isa']['training_field'] = "CNC精密加工" if new_loan_score >= 680 else ""
        client['loan_recommendation']['isa']['expected_salary_increase'] = 12000 if new_loan_score >= 700 else (8000 if new_loan_score >= 680 else 0)
        client['loan_recommendation']['isa']['reason'] = "" if new_loan_score >= 680 else "收入穩定度不足"

# 驗證服務代碼 (ref)
VC_VERIFIER_CONFIG = {
    'arc': {
        'ref': '00000000_alien_resident_certificate_vertification',
        'name': '外僑居留證'
    },
    'contract': {
        'ref': '00000000_employee_contract_vertification',
        'name': '移工勞動契約'
    }
}

# ========== [自定義模板過濾器] ==========
@app.template_filter('average')
def average_filter(lst):
    if not lst or not isinstance(lst, list): return 0
    return int(sum(lst) / len(lst))

@app.template_filter('intcomma')
def intcomma_filter(value):
    try:
        if isinstance(value, list): value = sum(value) / len(value)
        value = int(float(value))
        return f"{value:,}"
    except: return str(value)

# ========== [看門狗邏輯] ==========
def check_watchdog(client_id='low_risk'):
    global LAST_HEARTBEAT_TIME, REALTIME_RISK_DATA, CURRENT_DAY_COUNTER

    risk_data = get_client_risk_data(client_id)
    last_hb = LAST_HEARTBEAT_TIMES.get(client_id, time.time())
    day_counter = CURRENT_DAY_COUNTERS.get(client_id, 0)

    current_time = time.time()
    time_diff = current_time - last_hb

    # 超過 15 秒沒訊號 -> 判定失聯 (僅對有 App Simulator 運行中的客戶觸發)
    # 對於有預填 demo 事件的客戶，若最後事件不是心跳產生的，則不觸發看門狗
    if time_diff > 15:
        if len(risk_data) > 0 and ("失聯" in risk_data[-1]['event'] or "Watchdog" in risk_data[-1].get('event', '')):
            return
        # 如果最後事件是預填的 demo 事件，不觸發看門狗
        if len(risk_data) > 0 and risk_data[-1].get('is_demo', False):
            return

        alert_event = {
            'day': day_counter,
            'event': 'CRITICAL: 裝置失聯 > 48hr (Watchdog Triggered)',
            'risk_level': 3,
            'trust_score': 30,
            'time': datetime.now().strftime("%H:%M:%S"),
            'timestamp': current_time,
            'l2_enabled': False,
            'l3_enabled': False,
            'gps_context': '訊號遺失',
            'gps_status': 'danger',
            'device_status': {'math': 'danger', 'wifi': 'danger', 'batt': 'danger'}
        }
        risk_data.append(alert_event)

        get_client_db(client_id)['risk_logs'].append({
            "type": "WATCHDOG_ALERT",
            "level": "CRITICAL",
            "message": "裝置失聯超過安全閾值，啟動保護程序",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if len(risk_data) > 50: risk_data.pop(0)

# ========== [商業邏輯區] ==========

def generate_transactions(company_name, base_salary):
    """生成 6 個月的模擬電子存摺交易明細"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)

    transactions = []
    balance = 100000

    current_date = start_date
    while current_date <= end_date:
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
        salary_day = random.randint(25, min(28, last_day))
        salary_date = datetime(current_date.year, current_date.month, salary_day)

        num_transactions = random.randint(2, 4)

        transaction_dates = []
        for _ in range(num_transactions - 1):
            day = random.randint(1, salary_day - 1)
            transaction_dates.append(datetime(current_date.year, current_date.month, day))
        transaction_dates.sort()
        transaction_dates.append(salary_date)

        memo_choices_withdrawal = ['街口支付', '全聯', '家樂福', '麥當勞', '加油站', '7-11', '全家', 'NETFLIX', 'SPOTIFY']
        memo_choices_deposit = ['轉帳收入', '利息收入', '退款', '獎金']

        for i, trans_date in enumerate(transaction_dates[:-1]):
            is_withdrawal = random.choice([True, False])
            if is_withdrawal:
                memo = random.choice(memo_choices_withdrawal)
                amount = round(random.uniform(100, 5000), 2)
                balance -= amount
                transactions.append({
                    'date': trans_date.strftime('%Y%m%d'),
                    'memo': memo,
                    'withdrawal': f'${amount:,.2f}',
                    'deposit': '',
                    'balance': f'${balance:,.2f}'
                })
            else:
                memo = random.choice(memo_choices_deposit)
                amount = round(random.uniform(1000, 10000), 2)
                balance += amount
                transactions.append({
                    'date': trans_date.strftime('%Y%m%d'),
                    'memo': memo,
                    'withdrawal': '',
                    'deposit': f'${amount:,.2f}',
                    'balance': f'${balance:,.2f}'
                })

        overtime_pay = round(random.uniform(5000, 15000), 2)
        total_salary = base_salary + overtime_pay
        salary_memo = f'{company_name}_{salary_date.strftime("%Y%m%d")}薪資'
        balance += total_salary
        transactions.append({
            'date': salary_date.strftime('%Y%m%d'),
            'memo': salary_memo,
            'withdrawal': '',
            'deposit': f'${total_salary:,.2f}',
            'balance': f'${balance:,.2f}'
        })

        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1)

    return transactions

def calculate_repayment_capacity_score(monthly_salary, loan_amount=None, term_months=12):
    if loan_amount is None: loan_amount = 30000
    if loan_amount <= 30000: annual_rate = 0.105
    elif loan_amount <= 40000: annual_rate = 0.125
    else: annual_rate = 0.150
    monthly_rate = annual_rate / 12
    if monthly_rate == 0: monthly_payment = loan_amount / term_months
    else: monthly_payment = loan_amount * monthly_rate * math.pow(1 + monthly_rate, term_months) / (math.pow(1 + monthly_rate, term_months) - 1)
    
    if monthly_salary > 0: dbr = (monthly_payment / monthly_salary) * 100
    else: dbr = 100 

    if dbr <= 25: score = 100 - ((dbr / 25) * 10) 
    elif dbr <= 30: score = 90 - ((dbr - 25) / 5 * 10)
    elif dbr <= 40: score = 80 - ((dbr - 30) / 10 * 20)
    else: score = max(40, 60 - ((dbr - 40) * 2))
    
    return { 'score': int(score), 'dbr': round(dbr, 1), 'monthly_payment': int(monthly_payment), 'loan_amount': loan_amount, 'interest_rate': annual_rate * 100 }

def calculate_client_score(form_data, product_type='loan'):
    # 1. 雇主基本盤
    employer_multiplier = { 
        'large_tech': 1.10, 'medium_tech': 1.0, 'small_factory': 0.85, 'unstable': 0.75, 'caregiver': 0.90 
    }
    employer_base_score = { 
        'large_tech': 95, 'medium_tech': 80, 'small_factory': 65, 'unstable': 55, 'caregiver': 75 
    }
    employer_grade_map = { 'large_tech': 'AA', 'medium_tech': 'A', 'small_factory': 'BBB', 'unstable': 'BB', 'caregiver': 'B+' }
    employer_name_map = { "large_tech": "鴻海精密工業", "medium_tech": "緯創資通", "small_factory": "中小型電子廠", "unstable": "不穩定雇主", "caregiver": "家庭看護" }

    # 2. 國籍宏觀風險矩陣
    country_risk_map = {
        'Vietnam': {'penalty': 15, 'outlook': '波動'},   
        'Indonesia': {'penalty': 10, 'outlook': '中立'}, 
        'Philippines': {'penalty': 5, 'outlook': '穩定'}, 
        'Thailand': {'penalty': 5, 'outlook': '穩定'}    
    }

    # 獲取數據
    employer_type = form_data.get('employerType', 'medium_tech')
    if employer_type not in employer_base_score: employer_type = 'medium_tech'
    
    user_country = form_data.get('country', 'Vietnam')
    if user_country not in country_risk_map: user_country = 'Vietnam'

    raw_monthly_salary = int(form_data.get('monthlySalary', 42000))
    remittance = int(form_data.get('remittanceRegularity', 95))
    contract_months = int(form_data.get('contractRemaining', 24))
    
    try: loan_amount = int(form_data.get('loanAmount', 30000)); loan_term = int(form_data.get('loanTerm', 12))
    except: loan_amount = 30000; loan_term = 12
    
    # 風險調整
    risk_adjustment = 0; adjusted_salary = raw_monthly_salary 
    def is_true(key): return form_data.get(key) == 'true' or form_data.get(key) is True

    has_unpaid_leave = is_true('riskUnpaidLeave')
    if has_unpaid_leave:
        risk_adjustment -= 20; base_salary_part = raw_monthly_salary * 0.75
        adjusted_salary = (raw_monthly_salary * 3 + base_salary_part * 3) / 6
    if is_true('riskIrregularOvertime'): risk_adjustment -= 10; adjusted_salary = adjusted_salary * 0.95
    if is_true('riskVoiceAlert'): risk_adjustment -= 20
    
    # ===== [分流計算邏輯] =====
    # DBR 計算 (Dimension 1)
    if product_type == 'card':
        # [信用卡模式]：模擬最低應繳 (10% 額度) 作為月付金壓力
        simulated_monthly_payment = loan_amount * 0.1
        monthly_income = adjusted_salary if adjusted_salary > 0 else 1
        card_dbr = (simulated_monthly_payment / monthly_income) * 100
        
        # 信用卡 DBR 評分標準 (較寬鬆，因為額度低)
        if card_dbr <= 20: repayment_capacity_score = 95
        elif card_dbr <= 40: repayment_capacity_score = 80
        elif card_dbr <= 60: repayment_capacity_score = 60
        else: repayment_capacity_score = 40
        
        # 借用函式結構回傳，但覆蓋 score
        dbr_result = calculate_repayment_capacity_score(adjusted_salary, loan_amount, 12)
        dbr_result['score'] = repayment_capacity_score
        dbr_result['dbr'] = round(card_dbr, 1)
    
    else:
        # [信貸模式]：標準 DBR 計算 (維持原樣)
        dbr_result = calculate_repayment_capacity_score(adjusted_salary, loan_amount, loan_term)
        repayment_capacity_score = dbr_result['score']

    if has_unpaid_leave and repayment_capacity_score > 95: repayment_capacity_score = 95
    
    # 中間維度計算
    contract_score = min(100, contract_months * 3)
    income_stability_score = min(100, max(30, contract_score * 0.4 + employer_base_score[employer_type] * 0.6))
    repayment_willingness_score = min(100, max(50, remittance * 0.9 + risk_adjustment * 0.5))
    
    # 外部風險 (Dimension 4)
    external_risk_base = 80
    industry_adj = 10 if employer_type == 'large_tech' else (-10 if employer_type == 'unstable' else 0)
    country_penalty = country_risk_map[user_country]['penalty']
    fx_risk_adj = -(country_penalty * 1.5) if is_true('riskCountry') else -country_penalty
    
    external_risk_score = external_risk_base + industry_adj + fx_risk_adj
    if has_unpaid_leave: external_risk_score = min(70, external_risk_score)
    external_risk_score = min(100, max(40, external_risk_score))
    
    # ===== [權重分配] =====
    if product_type == 'card':
        # 信用卡：看重「意願」與「外部風險」 (行為評分)
        w_capacity = 0.20
        w_stability = 0.30
        w_willingness = 0.30
        w_external = 0.20
    else:
        # 信貸：看重「還款能力」 (申請評分，原始設定)
        w_capacity = 0.40
        w_stability = 0.30
        w_willingness = 0.20
        w_external = 0.10

    # 總分計算
    base_score = (repayment_capacity_score * w_capacity + 
                  income_stability_score * w_stability + 
                  repayment_willingness_score * w_willingness + 
                  external_risk_score * w_external)
                  
    total_score = max(400, min(850, int(base_score * employer_multiplier[employer_type] * 8.5)))
    
    return {
        'total_score': total_score, 'base_score': base_score, 
        'repayment_capacity_score': repayment_capacity_score, 'income_stability_score': income_stability_score, 
        'repayment_willingness_score': repayment_willingness_score, 'external_risk_score': external_risk_score, 
        'employer_type': employer_type, 'employer_grade': employer_grade_map[employer_type],
        'employer_name': employer_name_map[employer_type], 'employer_base_score': employer_base_score[employer_type],
        'monthly_salary': int(raw_monthly_salary), 'adjusted_salary': int(adjusted_salary), 
        'remittance': remittance, 'contract_months': contract_months, 'risk_adjustment': risk_adjustment, 
        'dbr_result': dbr_result,
        'country': user_country, 
        'loan_details': { 'amount': loan_amount, 'term': loan_term, 'monthly_payment': dbr_result['monthly_payment'], 'interest_rate': dbr_result['interest_rate'] },
        'product_type': product_type
    }

def generate_custom_client(form_data, salary_data_override=None):
    # 同時計算信貸 & 信用卡兩種模型
    score_data = calculate_client_score(form_data, product_type='loan')
    card_score_data = calculate_client_score(form_data, product_type='card')

    risk_factors = []
    if form_data.get('riskUnpaidLeave') == 'true' or form_data.get('riskUnpaidLeave') is True: risk_factors.append("曾有無薪假記錄")
    if form_data.get('riskIrregularOvertime') == 'true' or form_data.get('riskIrregularOvertime') is True: risk_factors.append("加班時數不穩定")
    if form_data.get('riskVoiceAlert') == 'true' or form_data.get('riskVoiceAlert') is True: risk_factors.append("AI語音測謊異常")
    if form_data.get('riskCountry') == 'true' or form_data.get('riskCountry') is True: risk_factors.append("母國匯率波動大")

    monthly_salary = score_data['monthly_salary']

    if salary_data_override:
        salary_data = salary_data_override
        base_salary = salary_data['base_salary'][0] if salary_data['base_salary'] else int(monthly_salary * 0.75)
    else:
        base_salary = int(monthly_salary * 0.75)
        salary_data = { "labels": ["1月", "2月", "3月", "4月", "5月", "6月"], "base_salary": [base_salary] * 6, "overtime": [], "total": [] }
        for i in range(6):
            if "曾有無薪假記錄" in risk_factors and i >= 3: overtime = 0
            else:
                variation = (i % 3 - 1) * 500
                overtime = max(0, int(monthly_salary * 0.25 + variation))
            salary_data["overtime"].append(overtime)
            salary_data["total"].append(base_salary + overtime)

    total_score = score_data['total_score']; loan_approved = total_score >= 650
    max_amount = 0; interest_rate = 0
    if loan_approved:
        if total_score >= 750: max_amount = 50000; interest_rate = 9.5
        elif total_score >= 700: max_amount = 40000; interest_rate = 10.5
        elif total_score >= 650: max_amount = 30000; interest_rate = 12.5
    
    country = "印尼" if "母國匯率波動大" in risk_factors else "越南"
    return {
        "id": f"CUSTOM-{int(total_score)}", "name": f"自定義客戶 - {country}籍", "country": country,
        "employer": score_data['employer_name'], "job_title": "技術員", "contract_remaining": score_data['contract_months'],
        "age": 30, "salary_data": salary_data, "hcap_score": total_score,
        "card_hcap_score": card_score_data['total_score'],
        "score_breakdown": {
            "repayment_capacity": {"score": score_data['repayment_capacity_score'], "weight": 40},
            "income_stability": {"score": score_data['income_stability_score'], "weight": 30},
            "repayment_willingness": {"score": score_data['repayment_willingness_score'], "weight": 20},
            "external_risk": {"score": score_data['external_risk_score'], "weight": 10}
        },
        "card_score_breakdown": {
            "repayment_capacity": {"score": card_score_data['repayment_capacity_score'], "weight": 20},
            "income_stability": {"score": card_score_data['income_stability_score'], "weight": 30},
            "repayment_willingness": {"score": card_score_data['repayment_willingness_score'], "weight": 30},
            "external_risk": {"score": card_score_data['external_risk_score'], "weight": 20}
        },
        "employer_rating": (lambda ei: {
            "score": RATING_TO_SCORE.get(ei['rating'], 80), "grade": ei['rating'],
            "industry": ei['industry'], "outlook": ei['outlook']
        } if ei else {
            "score": score_data['employer_base_score'], "grade": score_data['employer_grade'],
            "industry": "電子製造", "outlook": "穩定" if score_data['employer_grade'] in ['AA', 'A'] else "保守"
        })(lookup_employer_info(score_data['employer_name'])),
        "behavior_data": { "remittance_regularity": score_data['remittance'], "voice_ai_risk": "高風險" if score_data['repayment_willingness_score'] < 60 else "低風險", "digital_footprint": "活躍" if score_data['remittance'] >= 80 else "正常" },
        "loan_recommendation": {
            "survival_loan": { "approved": loan_approved, "max_amount": max_amount, "term": 12, "interest_rate": interest_rate, "reason": "" if loan_approved else "綜合評分不足" },
            "isa": { "qualified": total_score >= 680 and "曾有無薪假記錄" not in risk_factors, "training_field": "CNC精密加工" if total_score >= 680 else "", "expected_salary_increase": 12000 if total_score >= 700 else 8000, "reason": "" if total_score >= 680 else "收入穩定度不足" }
        },
        "risk_factors": risk_factors, "is_custom": True, "adjusted_salary": score_data['adjusted_salary'],
        "company_name": score_data['employer_name'],
        "_form_data": {**form_data, "_product_type": "loan"}
    }

# ========== [API 1] 接收 App Simulator 心跳 ==========
@app.route('/api/send_heartbeat', methods=['POST'])
def send_heartbeat():
    data = request.get_json()
    client_id = data.get('client_id', 'low_risk')

    c_state = get_client_state(client_id)
    risk_data = get_client_risk_data(client_id)

    if 'l2_enabled' in data: c_state['l2_enabled'] = data['l2_enabled']
    if 'l3_enabled' in data: c_state['l3_enabled'] = data['l3_enabled']
    if 'gps_context' in data: c_state['gps_context'] = data['gps_context']
    if 'gps_status' in data: c_state['gps_status'] = data['gps_status']
    if 'trust_score' in data: c_state['trust_score'] = data['trust_score']
    if 'coins' in data: c_state['coins'] = data['coins']
    if 'device_status' in data: c_state['device_status'] = data['device_status']

    msg_type = data.get('type', 'normal')
    custom_text = data.get('text', '')
    sim_day = data.get('simulation_day', CURRENT_DAY_COUNTERS.get(client_id, 0))
    trust_score = c_state['trust_score']

    LAST_HEARTBEAT_TIMES[client_id] = time.time()
    CURRENT_DAY_COUNTERS[client_id] = sim_day

    risk_level = 1
    if msg_type == 'danger': risk_level = 3
    elif msg_type == 'warning': risk_level = 2

    if 'weekly_scores' not in c_state:
        c_state['weekly_scores'] = []

    c_state['weekly_scores'].append(trust_score)
    settlement_result = None

    if sim_day > 0 and sim_day % 7 == 0 and len(c_state['weekly_scores']) > 0:
        scores = c_state['weekly_scores']
        avg_score = int(sum(scores) / len(scores))
        reward = 0

        if avg_score >= 90: reward = 500
        elif avg_score >= 80: reward = 300
        elif avg_score >= 60: reward = 100

        if reward > 0:
            c_state['coins'] += reward

            settlement_result = {
                'week': int(sim_day / 7),
                'avg': avg_score,
                'reward': reward,
                'total_coins': c_state['coins']
            }

        c_state['weekly_scores'] = []

    new_event = {
        'day': CURRENT_DAY_COUNTERS[client_id],
        'time': datetime.now().strftime("%H:%M:%S"),
        'risk_level': risk_level,
        'trust_score': c_state['trust_score'],
        'event': custom_text,
        'timestamp': LAST_HEARTBEAT_TIMES[client_id],
        'l3_enabled': c_state['l3_enabled'],
        'gps_context': c_state['gps_context'],
        'gps_status': c_state['gps_status'],
        'device_status': c_state.get('device_status')
    }

    if msg_type == 'gps_pulse':
        if len(risk_data) > 0 and 'L3 GPS' in risk_data[-1]['event']:
            risk_data[-1] = new_event
        else:
            risk_data.append(new_event)
    else:
        risk_data.append(new_event)

        if risk_level >= 2:
            db = get_client_db(client_id)
            db['risk_logs'].append({
                "type": "APP_ALERT",
                "level": "CRITICAL" if risk_level == 3 else "WARNING",
                "message": f"Device Alert: {custom_text}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            if len(db['risk_logs']) > 20: db['risk_logs'].pop(0)

    if len(risk_data) > 50: risk_data.pop(0)

    # --- Custom 客戶：App 數位足跡回饋 H-CAP ---
    if client_id == 'custom' and 'custom' in data.DEMO_CLIENTS:
        custom = data.DEMO_CLIENTS['custom']
        # 即時更新數位足跡狀態
        if trust_score >= 80:
            custom['behavior_data']['digital_footprint'] = '活躍'
        elif trust_score >= 60:
            custom['behavior_data']['digital_footprint'] = '正常'
        else:
            custom['behavior_data']['digital_footprint'] = '不活躍'
        custom['behavior_data']['app_trust_score'] = trust_score

        # 週結算時，根據 trust_score 調整 H-CAP 分數（同時更新信貸 & 信用卡兩種模型）
        form_d = custom.get('_form_data')
        if form_d and settlement_result:
            app_bonus = min(15, max(-20, int((trust_score - 60) * 0.5)))
            orig_remit = int(form_d.get('remittanceRegularity', 50))
            form_d['remittanceRegularity'] = min(100, max(0, orig_remit + app_bonus))

            # 信貸模型重算
            loan_res = calculate_client_score(form_d, product_type='loan')
            custom['hcap_score'] = loan_res['total_score']
            custom['score_breakdown'] = {
                "repayment_capacity": {"score": loan_res['repayment_capacity_score'], "weight": 40},
                "income_stability": {"score": loan_res['income_stability_score'], "weight": 30},
                "repayment_willingness": {"score": loan_res['repayment_willingness_score'], "weight": 20},
                "external_risk": {"score": loan_res['external_risk_score'], "weight": 10}
            }

            # 信用卡模型重算
            card_res = calculate_client_score(form_d, product_type='card')
            custom['card_hcap_score'] = card_res['total_score']
            custom['card_score_breakdown'] = {
                "repayment_capacity": {"score": card_res['repayment_capacity_score'], "weight": 20},
                "income_stability": {"score": card_res['income_stability_score'], "weight": 30},
                "repayment_willingness": {"score": card_res['repayment_willingness_score'], "weight": 30},
                "external_risk": {"score": card_res['external_risk_score'], "weight": 20}
            }

            # 更新貸款建議
            ns = loan_res['total_score']
            loan_ok = ns >= 650
            mx = 0; ir = 0
            if loan_ok:
                if ns >= 750: mx = 50000; ir = 9.5
                elif ns >= 700: mx = 40000; ir = 10.5
                elif ns >= 650: mx = 30000; ir = 12.5
            custom['loan_recommendation']['survival_loan']['approved'] = loan_ok
            custom['loan_recommendation']['survival_loan']['max_amount'] = mx
            custom['loan_recommendation']['survival_loan']['interest_rate'] = ir
            custom['loan_recommendation']['survival_loan']['reason'] = "" if loan_ok else f"綜合評分不足 ({ns}分)"

    return jsonify({'success': True, 'risk_level': risk_level, 'settlement': settlement_result})

# ========== [API 2] 接收 Remittance 資料 ==========
@app.route('/api/upload_remittance', methods=['POST'])
def upload_remittance():
    try:
        data = request.get_json()
        client_id = data.get('client_id', 'low_risk')
        db = get_client_db(client_id)
        db['remittance_data'] = {
            "status": "Synced",
            "regularity_rate": data.get('regularity_rate', 95),
            "avg_amount": data.get('avg_amount', 12000),
            "last_sync_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return jsonify({"success": True, "message": "Synced", "saved_data": db['remittance_data']})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========== [API 3] 提供 Bank Database 資料 ==========
@app.route('/api/get_bank_database')
def get_bank_database():
    client_id = request.args.get('client_id', 'low_risk')
    return jsonify(get_client_db(client_id))

# ========== [API 4] 提供 Lifecycle 資料 ==========
@app.route('/api/get_lifecycle_data')
def get_lifecycle_data():
    client_id = request.args.get('client_id', 'low_risk')
    check_watchdog(client_id)
    limit = int(request.args.get('limit', 20))
    risk_data = get_client_risk_data(client_id)
    return jsonify(risk_data[-limit:])

# ========== [API 6] 接收完整監控錄影 ==========
@app.route('/api/upload_full_session', methods=['POST'])
def upload_full_session():
    try:
        if 'video_file' not in request.files: 
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['video_file']
        filename = f"full_session_{int(time.time())}.webm"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        
        client_id = request.form.get('client_id', 'low_risk')
        db = get_client_db(client_id)
        db['voice_analysis']['full_video_url'] = f"/static/uploads/{filename}"

        return jsonify({"success": True, "url": db['voice_analysis']['full_video_url']})
    except Exception as e:
        print(f"Full Session Upload Error: {e}")
        return jsonify({'error': str(e)}), 500

# ========== [AI 語音邏輯] ==========
INTERVIEW_QUESTIONS = [
    "請朗讀：我保證資料真實，絕無虛假。",
    "第一題：請問您在台灣從事什麼工作？",
    "第二題：這筆貸款的主要用途是什麼？",
    "第三題：您目前在工廠的加班頻率高嗎？",
    "第四題：如果沒有加班費，您如何還款？"
]

def transcribe_with_groq(filepath):
    if not GROQ_API_KEY: return None
    try:
        client = Groq(api_key=GROQ_API_KEY)
        with open(filepath, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(filepath, file.read()), model="whisper-large-v3", response_format="json", language="zh", temperature=0.0,
                prompt="這是一段關於銀行貸款申請的語音回答。請逐字稿轉錄。"
            )
        return transcription.text.strip()
    except Exception as e:
        print(f"Groq STT Error: {e}")
        return None

def analyze_with_groq(question, answer):
    if not GROQ_API_KEY: return fallback_analysis(question, answer)
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        prompt = f"""
        角色：你是一位針對東南亞移工的普惠金融風控官。
        任務：分析申請人的回答是否真實且合理。請考慮移工的語言能力與職業特性。

        題目：{question}
        回答：{answer}

        請依據以下標準評分 (Real Analysis)：

        1. 【職業與身分】(針對工作題)：
           - 若回答「看護」、「家庭幫傭」、「照顧老人」、「工廠作業員」等，皆視為具體且合理的職業，給 85-95 分。
           - 若只說「工作」、「上班」，則視為模糊，給 50 分。

        2. 【還款能力與來源】(針對還款題)：
           - 若回答「積蓄」、「存款」、「省吃儉用」、「薪水扣」、「借錢」等，視為有還款計畫，給 85-95 分。
           - 若回答「不知道」、「沒錢」，給 20 分。

        3. 【頻率與數字】(針對加班題)：
           - 只要出現數字(如 "1-2次") 或頻率詞(如 "每週"、"很少"、"旺季")，即視為具體回答，給 80 分以上。
           - 移工中文可能不流利，不要因為文法錯誤扣分。

        4. 【躲閃偵測】：
           - 只有在回答極短(少於3字)且無意義時(如 "哼"、"那個")才判定為躲閃。

        回傳 JSON 格式：
        {{
            "score": <0-100 的整數>,
            "reason": "<繁體中文簡評>"
        }}
        """
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model="llama3-8b-8192", response_format={"type": "json_object"}, temperature=0.0
        )
        result = json.loads(chat_completion.choices[0].message.content)
        return result['score'], result['reason']
    except Exception as e:
        print(f"Groq NLP Error: {e}")
        return fallback_analysis(question, answer)

def fallback_analysis(question, answer):
    clean = answer.replace(" ", "")
    if "工作" in question or "職位" in question:
        valid_jobs = ["電子","工廠","製造","作業員","技術","操作","組裝", "看護", "照顧", "幫傭", "家庭"]
        if any(k in clean for k in valid_jobs): return 90, "職業明確"
        return 50, "需補充工作細節"
    elif "用途" in question:
        if any(k in clean for k in ["家","父母","學費","生活","寄回","買","醫療","看病"]): return 90, "用途合理"
        return 40, "用途不明"
    elif "加班" in question and "頻率" in question:
        if any(k in clean for k in ["有","多","穩定","正常","旺季","次","週","天","少","沒"]): return 85, "已說明加班頻率"
        return 45, "回答含糊"
    elif "還款" in question:
        if any(k in clean for k in ["存款","底薪","省","借","薪水","積蓄","存錢"]): return 90, "具備還款觀念"
        if "不知道" in clean or "沒錢" in clean: return 20, "高風險"
        return 40, "還款來源不明"
    if len(clean) < 2: return 20, "回答過短"
    return 60, "待人工審核"

# ========== [API 5] 接收 Voice AI 分析結果 ==========
@app.route('/api/analyze_video_step', methods=['POST'])
def analyze_video_step():
    try:
        if 'video_file' not in request.files: return jsonify({'error': 'No file'}), 400
        file = request.files['video_file']
        q_idx = int(request.form.get('question_index', 0))
        current_q = INTERVIEW_QUESTIONS[q_idx] if q_idx < len(INTERVIEW_QUESTIONS) else "未知題目"
        
        filename = f"video_q{q_idx}_{int(time.time())}.webm"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        wav_path = save_path.replace('.webm', '.wav')
        try:
            import subprocess
            ffmpeg_path = os.path.join(base_dir, "ffmpeg.exe") if os.name == 'nt' else "ffmpeg"
            subprocess.run([ffmpeg_path, '-i', save_path, '-y', wav_path],
                           capture_output=True, timeout=30, check=True)
        except Exception as conv_err:
            import traceback; traceback.print_exc()
            print(f"[轉檔失敗] save_path={save_path}, size={os.path.getsize(save_path) if os.path.exists(save_path) else 'NOT FOUND'}, error={conv_err}")
            return jsonify({'text': "(轉檔失敗)", 'score': 0, 'reason': f"系統錯誤: {str(conv_err)}"}), 500

        text = transcribe_with_groq(wav_path)
        if not text:
            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                try: text = r.recognize_google(r.record(source), language="zh-TW")
                except: text = "(無法辨識)"

        score, reason = 0, ""
        if q_idx == 0: 
             target = "我保證資料真實絕無虛假"
             def clean(t): return re.sub(r'[^\w]', '', t)
             sim = len(set(clean(text)) & set(clean(target))) / len(set(clean(target))) * 100
             if sim > 40: score = 98; reason = "誓詞吻合"
             else: score = 40; reason = "內容不符"
        else:
            score, reason = analyze_with_groq(current_q, text)

        video_record = { 
            "question": f"Q{q_idx+1}", 
            "video_url": f"/static/uploads/{filename}", 
            "transcript": text, 
            "score": score, 
            "reason": reason, 
            "timestamp": datetime.now().strftime("%H:%M") 
        }
        
        client_id = request.form.get('client_id', 'low_risk')
        db = get_client_db(client_id)

        if q_idx == 0:
            db['voice_analysis']['details'] = []

        db['voice_analysis']['details'].append(video_record)

        details = db['voice_analysis']['details']
        if len(details) > 0:
            avg = int(sum(d['score'] for d in details) / len(details))
            db['voice_analysis']['risk_score'] = avg
            db['voice_analysis']['status'] = "Verified" if avg >= 60 else "Failed"
            db['voice_analysis']['voiceprint_match'] = random.randint(95, 99)
            db['voice_analysis']['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({ "success": True, "text": text, "score": score, "reason": reason })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

# ========== 頁面路由 ==========
@app.route('/')
def index(): return render_template('index.html')

# Portal 入口頁面
@app.route('/portal/customer')
def portal_customer():
    custom_exists = 'custom' in data.DEMO_CLIENTS
    custom_name = data.DEMO_CLIENTS['custom']['name'] if custom_exists else ''
    return render_template('portal_customer.html', custom_exists=custom_exists, custom_name=custom_name)

@app.route('/portal/bank')
def portal_bank():
    custom_client = data.DEMO_CLIENTS.get('custom')
    return render_template('portal_bank.html',
                           custom_client=custom_client,
                           clients=data.DEMO_CLIENTS,
                           employers=EMPLOYERS)

# 客戶詳細頁面（整合風控儀表板）
@app.route('/client/<client_id>')
def client_detail(client_id):
    # 獲取客戶資料（優先使用 DEMO_CLIENTS 中的最新資料，因雇主變動可能已更新分數）
    if client_id == 'custom' and 'custom' in data.DEMO_CLIENTS:
        client = data.DEMO_CLIENTS['custom']
    elif client_id == 'custom' and 'custom_client' in session:
        client = session['custom_client']
    else:
        client = data.DEMO_CLIENTS.get(client_id, data.DEMO_CLIENTS.get('low_risk'))

    # 獲取當前查看的視圖（默認為 dashboard）
    current_view = request.args.get('view', 'dashboard')
    # 獲取模型類型（loan 或 card）
    model = request.args.get('model', 'loan')

    # 根據模型類型選擇對應分數
    if model == 'card' and 'card_hcap_score' in client:
        active_score = client['card_hcap_score']
        active_breakdown = client.get('card_score_breakdown', client['score_breakdown'])
        model_label = '信用卡'
    else:
        active_score = client['hcap_score']
        active_breakdown = client['score_breakdown']
        model_label = '信貸'
        model = 'loan'

    return render_template('client_detail.html',
                         client=client,
                         client_id=client_id,
                         current_view=current_view,
                         model=model,
                         model_label=model_label,
                         active_score=active_score,
                         active_breakdown=active_breakdown)

@app.route('/voice_ai')
def voice_ai():
    cid = request.args.get('client_id', 'custom')
    return render_template('voice_ai.html', client_id=cid)
@app.route('/remittance')
def remittance(): return render_template('remittance.html')
@app.route('/apply')
def apply_page():
    return render_template('apply.html')
@app.route('/loan')
def loan_page():
    return render_template('loan.html')

@app.route('/credential_verify')
def credential_verify_page():
    next_page = request.args.get('next', 'apply')
    
    # 先渲染模板成 HTML 字串
    html_content = render_template('credential_verify.html', next_page=next_page)
    
    # 定義要注入的 CSS 樣式
    button_styles = '''
<style>
    /* --- [專屬注入] OID4VP Demo 一鍵帶入按鈕樣式 --- */
    #fill-arc-demo-data, #fill-contract-demo-data {
        padding: 12px 24px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        color: white !important;
        border-radius: 8px !important;
        cursor: pointer;
        transition: all 0.2s ease;
        border: none !important;
        line-height: 1.3 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    #fill-arc-demo-data {
        background-color: #3B82F6 !important; /* 實心藍色背景 */
    }
    #fill-arc-demo-data:hover {
        background-color: #2563EB !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-1px);
    }
    #fill-contract-demo-data {
        background-color: #22C55E !important; /* 實心綠色背景 */
    }
    #fill-contract-demo-data:hover {
        background-color: #16A34A !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-1px);
    }
</style>
'''
    # 將樣式注入到 </head> 標籤之前，確保能被優先載入
    if '</head>' in html_content:
        injected_content = html_content.replace('</head>', button_styles + '</head>')
    else:
        injected_content = html_content.replace('</body>', button_styles + '</body>')
        
    return injected_content

@app.route('/dashboard')
def dashboard():
    client_id = request.args.get('client', 'low_risk')
    embedded = request.args.get('embedded', 'false') == 'true'
    model = request.args.get('model', 'loan')
    if client_id == 'custom' and 'custom_client' in session: client = session['custom_client']
    else: client = data.DEMO_CLIENTS.get(client_id, data.DEMO_CLIENT)
    if model == 'card' and 'card_hcap_score' in client:
        active_score = client['card_hcap_score']
        active_breakdown = client.get('card_score_breakdown', client['score_breakdown'])
    else:
        active_score = client['hcap_score']
        active_breakdown = client['score_breakdown']
    return render_template('dashboard.html', client=client, client_id=client_id, embedded=embedded,
                         active_score=active_score, active_breakdown=active_breakdown)
@app.route('/products')
def products():
    client_id = request.args.get('client', 'low_risk')
    embedded = request.args.get('embedded', 'false') == 'true'
    if client_id == 'custom' and 'custom_client' in session: client = session['custom_client']
    else: client = data.DEMO_CLIENTS.get(client_id, data.DEMO_CLIENT)
    return render_template('products.html', client=client, client_id=client_id, embedded=embedded)
@app.route('/lifecycle')
def lifecycle():
    embedded = request.args.get('embedded', 'false') == 'true'
    return render_template('lifecycle.html', embedded=embedded)
@app.route('/algorithms')
def algorithms(): return render_template('algorithms.html')
@app.route('/stress_test')
def stress_test():
    custom_client = session.get('custom_client', None)
    return render_template('stress_test.html', custom_client=custom_client)
@app.route('/portfolio')
def portfolio():
    portfolio_data = { "total_aum": 425000000, "total_clients": 12850, "avg_hcap": 685, "npl_ratio": 0.82, "avg_yield": 12.5, "risk_dist": [65, 25, 8, 2], "product_mix": [70, 30], "geo_dist": { "labels": ["桃園龜山", "新竹科學園區", "台中精機", "台南科工", "高雄路竹"], "data": [35, 25, 20, 15, 5] }, "monthly_trend": [1200, 1500, 1800, 2200, 2100, 2500] }
    return render_template('portfolio.html', data=portfolio_data)
@app.route('/app_simulator')
def app_simulator():
    cid = request.args.get('client_id', 'low_risk')
    client = data.DEMO_CLIENTS.get(cid)
    client_name = client['name'] if client else 'Guest'
    return render_template('app_simulator.html', client_id=cid, client_name=client_name)
@app.route('/employer_app')
def employer_app(): return render_template('employer_app.html')
@app.route('/employer_manage')
def employer_manage(): return render_template('employer_manage.html')

# ========== [雇主管理 API] ==========
@app.route('/api/employers')
def get_employers():
    return jsonify(EMPLOYERS)

@app.route('/api/employers/add', methods=['POST'])
def add_employer():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"success": False, "error": "名稱不可為空"}), 400
    for emp in EMPLOYERS['confirmed']:
        if emp['name'] == name:
            return jsonify({"success": False, "error": "該雇主已存在"}), 400
    new_id = f"EMP-{len(EMPLOYERS['confirmed']) + len(EMPLOYERS['pending']) + 1:03d}"
    new_emp = {
        "id": new_id, "name": name,
        "type": data.get('type', 'medium_tech'),
        "rating": data.get('rating', 'B'),
        "industry": data.get('industry', '待分類'),
        "employees": int(data.get('employees', 0)),
        "outlook": data.get('outlook', '待評估')
    }
    EMPLOYERS['confirmed'].append(new_emp)
    return jsonify({"success": True, "employer": new_emp})

@app.route('/api/employers/confirm', methods=['POST'])
def confirm_employer():
    req = request.get_json()
    emp_id = req.get('id')
    target = None
    for i, emp in enumerate(EMPLOYERS['pending']):
        if emp['id'] == emp_id:
            target = EMPLOYERS['pending'].pop(i)
            break
    if not target:
        return jsonify({"success": False, "error": "找不到該待確認雇主"}), 404
    if req.get('name', '').strip():
        target['name'] = req['name'].strip()
    target['rating'] = req.get('rating', 'B')
    target['industry'] = req.get('industry', target.get('industry', '待分類'))
    target['type'] = req.get('type', 'medium_tech')
    target['outlook'] = req.get('outlook', '待評估')
    target.pop('submitted_at', None)
    overwrite = req.get('overwrite', False)
    if overwrite:
        # 覆寫：找到同名正式雇主並取代（保留原 ID）
        existing_idx = next(
            (i for i, e in enumerate(EMPLOYERS['confirmed'])
             if e['name'].strip().lower() == target['name'].strip().lower()),
            None
        )
        if existing_idx is not None:
            target['id'] = EMPLOYERS['confirmed'][existing_idx]['id']
            EMPLOYERS['confirmed'][existing_idx] = target
        else:
            target['id'] = f"EMP-{len(EMPLOYERS['confirmed']) + 1:03d}"
            EMPLOYERS['confirmed'].append(target)
    else:
        target['id'] = f"EMP-{len(EMPLOYERS['confirmed']) + 1:03d}"
        EMPLOYERS['confirmed'].append(target)
    # 確認後重新計算關聯客戶的 H-CAP 分數
    recalculate_clients_for_employer(target['name'], target)
    affected = []
    for cid, c in data.DEMO_CLIENTS.items():
        cn = c.get('company_name', '') or c.get('employer', '')
        if cn == target['name'] or target['name'] in cn or cn in target['name']:
            affected.append({"id": cid, "hcap_score": c.get('hcap_score'), "employer_rating": c.get('employer_rating')})
    return jsonify({"success": True, "employer": target, "affected_clients": affected})

@app.route('/api/employers/edit', methods=['POST'])
def edit_employer():
    req = request.get_json()
    emp_id = req.get('id')
    for emp in EMPLOYERS['confirmed']:
        if emp['id'] == emp_id:
            old_name = emp['name']
            if req.get('name'): emp['name'] = req['name'].strip()
            if req.get('rating'): emp['rating'] = req['rating']
            if req.get('industry'): emp['industry'] = req['industry']
            if 'employees' in req: emp['employees'] = int(req['employees'])
            if req.get('type'): emp['type'] = req['type']
            if req.get('outlook'): emp['outlook'] = req['outlook']
            # 重新計算所有關聯客戶的 H-CAP 分數
            recalculate_clients_for_employer(old_name, emp)
            # 回傳受影響的客戶清單
            affected = []
            for cid, c in data.DEMO_CLIENTS.items():
                cn = c.get('company_name', '') or c.get('employer', '')
                if cn == emp['name'] or emp['name'] in cn or cn in emp['name']:
                    affected.append({"id": cid, "hcap_score": c.get('hcap_score'), "employer_rating": c.get('employer_rating')})
            return jsonify({"success": True, "employer": emp, "affected_clients": affected})
    return jsonify({"success": False, "error": "找不到該雇主"}), 404

@app.route('/api/employers/delete', methods=['POST'])
def delete_employer():
    req = request.get_json()
    emp_id = req.get('id')
    # 先找到該雇主名稱
    target_name = None
    for lst in [EMPLOYERS['confirmed'], EMPLOYERS['pending']]:
        for emp in lst:
            if emp['id'] == emp_id:
                target_name = emp['name']
                break
        if target_name:
            break
    if not target_name:
        return jsonify({"success": False, "error": "找不到該雇主"}), 404
    # 防呆：檢查是否有客戶關聯此雇主
    linked_clients = []
    for cid, c in data.DEMO_CLIENTS.items():
        cn = c.get('company_name', '') or c.get('employer', '')
        if cn == target_name or target_name in cn or cn in target_name:
            linked_clients.append(c.get('name', cid))
    if linked_clients:
        return jsonify({"success": False, "error": f"無法刪除：尚有 {len(linked_clients)} 位客戶（{', '.join(linked_clients)}）隸屬此雇主，刪除將影響其 H-CAP 評分"}), 400
    # 安全刪除
    for lst in [EMPLOYERS['confirmed'], EMPLOYERS['pending']]:
        for i, emp in enumerate(lst):
            if emp['id'] == emp_id:
                lst.pop(i)
                return jsonify({"success": True})
    return jsonify({"success": False, "error": "找不到該雇主"}), 404

# ========== 其他 API ==========
@app.route('/api/login_check', methods=['POST'])
def login_check():
    data = request.get_json()
    if data.get('username') == "ABC" and data.get('password') == "1234":
        client_id = data.get('client_id', 'low_risk')
        get_client_db(client_id)['applicant_info']['login_verified'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "帳號或密碼錯誤"})

@app.route('/api/generate_bank_statement', methods=['POST'])
def api_generate_bank_statement():
    """根據公司名稱和底薪生成 6 個月模擬交易明細"""
    try:
        req = request.get_json()
        company_name = req.get('company_name', '公司')
        base_salary = int(req.get('base_salary', 27470))
        transactions = generate_transactions(company_name, base_salary)
        return jsonify({"success": True, "transactions": transactions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate_client', methods=['POST'])
def api_generate_client():
    try:
        form_data = request.get_json()
        custom_client = generate_custom_client(form_data)
        session['custom_client'] = custom_client
        session.modified = True
        return jsonify({"success": True, "client": custom_client, "redirect": "/dashboard?client=custom"})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/calculate_loan', methods=['POST'])
def calculate_loan():
    request_data = request.get_json() if request.is_json else {}
    amount = request_data.get('amount', 40000); term = request_data.get('term', 12)
    monthly_salary = 36500
    if amount <= 30000: interest_rate = 10.5
    elif amount <= 40000: interest_rate = 12.5
    else: interest_rate = 15.0
    monthly_rate = interest_rate / 100 / 12
    monthly_payment = amount * monthly_rate * math.pow(1 + monthly_rate, term) / (math.pow(1 + monthly_rate, term) - 1)
    dbr = (monthly_payment / monthly_salary * 100)
    result = { "approved_amount": amount, "monthly_payment": round(monthly_payment), "total_repayment": round(monthly_payment * term), "interest_rate": interest_rate, "dbr": round(dbr, 1), "message": "符合核貸條件" if dbr < 30 else "DBR過高" }
    return jsonify(result)

# ========== [API 7 - 修改版] 信用卡申請處理 (明確指定 product_type='card') ==========
@app.route('/api/apply_credit_card', methods=['POST'])
def apply_credit_card():
    try:
        form = request.form
        
        # 檢查憑證驗證狀態（從 localStorage 傳來的資料）
        arc_verified = form.get('arc_verified') == 'true'
        contract_verified = form.get('contract_verified') == 'true'
        
        if not (arc_verified and contract_verified):
            return jsonify({
                "status": "rejected",
                "score": 0,
                "reason": "請先完成數位憑證驗證（居留證 + 勞動契約）",
                "details": {}
            }), 400

        # 1. 居留證效期硬指標
        arc_expiry = form.get('arc_expiry')
        if not arc_expiry:
            expiry_date = datetime.now().replace(year=datetime.now().year + 1)
        else:
            try:
                expiry_date = datetime.strptime(arc_expiry, '%Y-%m-%d')
            except:
                expiry_date = datetime.now().replace(year=datetime.now().year + 1)
        
        days_remaining = (expiry_date - datetime.now()).days
        contract_months = max(1, int(days_remaining / 30))

        # 2. 資料清洗與預設值
        try:
            base_salary = int(form.get('base_salary', 27470))
        except:
            base_salary = 27470

        # [關鍵修改] 優先讀取精確分數
        exact_score = form.get('exact_remittance_score')
        
        if exact_score and exact_score.strip() != "":
            remit_score = int(exact_score)
        else:
            remit_status = form.get('remittance_habit', 'none')
            remit_score = 95 if remit_status == 'regular' else (50 if remit_status == 'irregular' else 0)

        # 3. 建構算法輸入
        company_name = form.get('company_name', '')
        employer_type = form.get('employer_type', '') or lookup_employer_type(company_name)
        if company_name:
            add_pending_employer(company_name)
        algo_input_data = {
            'employerType': employer_type,
            'country': form.get('country', 'Vietnam'),
            'monthlySalary': base_salary,
            'remittanceRegularity': remit_score,
            'contractRemaining': contract_months,
            'loanAmount': 20000,
            'loanTerm': 12,
            'riskUnpaidLeave': False,
            'riskIrregularOvertime': False,
            'riskVoiceAlert': False,
            'riskCountry': False
        }
        
        # 現金懲罰
        if form.get('pay_method') == 'cash':
            algo_input_data['monthlySalary'] = int(base_salary * 0.9)

        # 4. 調用算法 — 同時計算信用卡 & 信貸兩種模型
        result = calculate_client_score(algo_input_data, product_type='card')
        card_hcap_score = result['total_score']
        loan_result = calculate_client_score(algo_input_data, product_type='loan')
        loan_hcap_score = loan_result['total_score']

        # 4.5 語音驗證加分（若已完成）
        voice_done = session.get('voice_verification_done', False)
        voice_avg = session.get('voice_avg_score', 0)
        voice_bonus = 0
        voice_label = "尚未檢測"
        if voice_done and voice_avg > 0:
            voice_bonus = min(50, int(voice_avg * 0.5))
            card_hcap_score = min(850, card_hcap_score + voice_bonus)
            loan_hcap_score = min(850, loan_hcap_score + voice_bonus)
            voice_label = f"低風險 (已驗證 {voice_avg}分)" if voice_avg >= 70 else f"中風險 (已驗證 {voice_avg}分)"

        hcap_score = card_hcap_score  # 信用卡申請以 card 分數為主

        # 5. 結果判定
        status = "review"
        reason = ""
        
        if days_remaining < 180:
            status = "rejected"
            reason = f"居留證效期不足 (剩 {days_remaining} 天)"
        elif hcap_score >= 700:
            status = "approved"
        elif hcap_score >= 650:
            status = "review"
            reason = "信用評分位於邊緣，建議開啟 App 數位足跡加分。"
        else:
            status = "rejected"
            reason = f"綜合評分不足 ({hcap_score}分)，風險過高。"

        # 6. 解析電子存摺交易明細 → 拆分底薪/加班費
        bank_statement_json = form.get('bank_statement_data', '')
        if bank_statement_json:
            try:
                bs_transactions = json.loads(bank_statement_json)
                salary_records = [t for t in bs_transactions if '薪資' in t.get('memo', '')]
                monthly_totals = []
                monthly_overtimes = []
                labels = []
                for rec in salary_records:
                    deposit = float(rec['deposit'].replace('$', '').replace(',', ''))
                    overtime = max(0, deposit - base_salary)
                    monthly_totals.append(int(deposit))
                    monthly_overtimes.append(int(overtime))
                    date_str = rec['memo'].split('_')[1][:6]
                    labels.append(f"{int(date_str[4:6])}月")
                salary_data = {
                    "labels": labels,
                    "base_salary": [base_salary] * len(labels),
                    "overtime": monthly_overtimes,
                    "total": monthly_totals
                }
            except:
                salary_data = {
                    "labels": ["M-5", "M-4", "M-3", "M-2", "M-1", "Current"],
                    "base_salary": [base_salary] * 6,
                    "overtime": [0] * 6,
                    "total": [base_salary] * 6
                }
        else:
            salary_data = {
                "labels": ["M-5", "M-4", "M-3", "M-2", "M-1", "Current"],
                "base_salary": [base_salary] * 6,
                "overtime": [0] * 6,
                "total": [base_salary] * 6
            }

        session['custom_client'] = {
            "id": "CREDIT-APP-001",
            "name": form.get('english_name', 'Guest'),
            "country": form.get('country', 'Vietnam'),
            "employer": algo_input_data['employerType'],
            "company_name": company_name,
            "job_title": "作業員",
            "contract_remaining": contract_months,
            "age": 28,
            "salary_data": salary_data,
            "hcap_score": loan_hcap_score,
            "card_hcap_score": card_hcap_score,
            "adjusted_salary": base_salary,
            "score_breakdown": {
                "repayment_capacity": {"score": loan_result['repayment_capacity_score'], "weight": 40},
                "income_stability": {"score": loan_result['income_stability_score'], "weight": 30},
                "repayment_willingness": {"score": loan_result['repayment_willingness_score'], "weight": 20},
                "external_risk": {"score": loan_result['external_risk_score'], "weight": 10}
            },
            "card_score_breakdown": {
                "repayment_capacity": {"score": result['repayment_capacity_score'], "weight": 20},
                "income_stability": {"score": result['income_stability_score'], "weight": 30},
                "repayment_willingness": {"score": result['repayment_willingness_score'], "weight": 30},
                "external_risk": {"score": result['external_risk_score'], "weight": 20}
            },
            "employer_rating": (lambda ei: {
                "score": RATING_TO_SCORE.get(ei['rating'], 80), "grade": ei['rating'],
                "industry": ei['industry'], "outlook": ei['outlook']
            } if ei else {
                "score": result['employer_base_score'], "grade": result['employer_grade'],
                "industry": "電子製造", "outlook": "穩定"
            })(lookup_employer_info(company_name)),
            "behavior_data": { "remittance_regularity": remit_score, "voice_ai_risk": voice_label, "digital_footprint": "尚未啟用" },
            "loan_recommendation": {
                "survival_loan": { "approved": False, "max_amount": 0, "term": 0, "interest_rate": 0, "reason": "需持卡滿 6 個月解鎖" },
                "isa": { "qualified": False, "training_field": "", "expected_salary_increase": 0, "reason": "信用歷史不足" }
            },
            "risk_factors": ["新戶申請"],
            "is_custom": True,
            "_form_data": {**algo_input_data, "_product_type": "card"}
        }

        # 同步寫入 DEMO_CLIENTS['custom']，供銀行端客戶資料庫存取
        data.DEMO_CLIENTS['custom'] = session['custom_client']

        # 初始化 custom 客戶的即時監控基礎設施
        CLIENT_STATES['custom'] = {
            'l2_enabled': False, 'l3_enabled': False,
            'gps_context': '未啟用', 'gps_status': 'safe',
            'trust_score': 50, 'coins': 0,
            'device_status': {'math': 'good', 'wifi': 'good', 'batt': 'good'},
            'weekly_scores': []
        }
        REALTIME_RISK_DATAS['custom'] = []
        remit_synced = remit_score > 0

        # [新增] 備份既有的語音數據
        existing_voice_data = None
        if 'custom' in BANK_DATABASES:
            existing_voice_data = BANK_DATABASES['custom'].get('voice_analysis')

        BANK_DATABASES['custom'] = _create_bank_db(
            "CUSTOM-001", form.get('english_name', 'Guest'),
            "Synced" if remit_synced else "Not Synced",
            remit_score, int(base_salary * 0.3) if remit_synced else 0,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') if remit_synced else "--",
            "Not Verified", 0, 0, "--", []
        )

        # [新增] 還原語音數據
        if existing_voice_data and existing_voice_data.get('status') != 'Not Verified':
            BANK_DATABASES['custom']['voice_analysis'] = existing_voice_data

        return jsonify({
            "status": status,
            "score": hcap_score,
            "credit_limit": 20000 if status == 'approved' else 0,
            "reason": reason,
            "details": {
                "base_score": round(result['base_score'], 1),
                "breakdown": {
                    "repayment": result['repayment_capacity_score'],
                    "stability": result['income_stability_score']
                }
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc() # 在後台印出錯誤詳細訊息
        return jsonify({"status": "error", "message": str(e)}), 500

# ========== [API] 貸款申請 ==========
@app.route('/api/apply_loan', methods=['POST'])
def apply_loan():
    try:
        form = request.form
        
        # 1. 居留證效期硬指標
        arc_expiry = form.get('arc_expiry')
        if not arc_expiry:
            expiry_date = datetime.now().replace(year=datetime.now().year + 1)
        else:
            try:
                expiry_date = datetime.strptime(arc_expiry, '%Y-%m-%d')
            except:
                expiry_date = datetime.now().replace(year=datetime.now().year + 1)
        
        days_remaining = (expiry_date - datetime.now()).days
        contract_months = min(int(form.get('contract_months', 24)), max(1, int(days_remaining / 30)))

        # 2. 資料清洗
        try:
            base_salary = int(form.get('base_salary', 27470))
            loan_amount = int(form.get('loan_amount', 50000))
            loan_term = int(form.get('loan_term', 12))
        except:
            base_salary = 27470
            loan_amount = 50000
            loan_term = 12

        # 優先讀取匯款頁精確分數，與信用卡申請邏輯一致
        exact_score = form.get('exact_remittance_score')
        if exact_score and exact_score.strip() != "":
            remit_regularity = int(exact_score)
        else:
            remit_status = form.get('remittance_habit', 'none')
            remit_regularity = 95 if remit_status == 'regular' else (50 if remit_status == 'irregular' else 0)

        # 3. 建構算法輸入
        company_name = form.get('company_name', '')
        employer_type = form.get('employer_type', '') or lookup_employer_type(company_name)
        if company_name:
            add_pending_employer(company_name)
        algo_input_data = {
            'employerType': employer_type,
            'country': form.get('country', 'Vietnam'),
            'monthlySalary': base_salary,
            'remittanceRegularity': remit_regularity,
            'contractRemaining': contract_months,
            'loanAmount': loan_amount,
            'loanTerm': loan_term,
            'riskUnpaidLeave': form.get('risk_unpaid_leave') == 'on',
            'riskIrregularOvertime': form.get('risk_irregular_overtime') == 'on',
            'riskVoiceAlert': form.get('risk_voice_alert') == 'on',
            'riskCountry': form.get('risk_currency_volatility') == 'on'
        }
        
        # 現金懲罰
        if form.get('pay_method') == 'cash':
            algo_input_data['monthlySalary'] = int(base_salary * 0.9)

        # 4. 調用算法 — 同時計算信貸 & 信用卡兩種模型
        result = calculate_client_score(algo_input_data, product_type='loan')
        hcap_score = result['total_score']
        card_result = calculate_client_score(algo_input_data, product_type='card')
        card_hcap_score = card_result['total_score']

        # 4.5 語音驗證加分（若已完成）
        voice_done = session.get('voice_verification_done', False)
        voice_avg = session.get('voice_avg_score', 0)
        voice_bonus = 0
        voice_label = "尚未檢測"
        if voice_done and voice_avg > 0:
            voice_bonus = min(50, int(voice_avg * 0.5))
            hcap_score = min(850, hcap_score + voice_bonus)
            card_hcap_score = min(850, card_hcap_score + voice_bonus)
            voice_label = f"低風險 (已驗證 {voice_avg}分)" if voice_avg >= 70 else f"中風險 (已驗證 {voice_avg}分)"

        # 計算 DBR (仲裁: 月薪 * 0.4 / 月付金 * 100)
        monthly_payment = npf.pmt(rate=0.06/12, nper=loan_term, pv=-loan_amount)
        dbr_ratio = (base_salary * 0.4) / abs(monthly_payment) * 100 if monthly_payment != 0 else 0
        dbr_score = min(100, dbr_ratio * 2)

        # 5. 結果判定
        status = "review"
        reason = ""
        
        if days_remaining < 180:
            status = "rejected"
            reason = f"居留證效期不足 (剩 {days_remaining} 天)"
        elif loan_amount > base_salary * 6:
            status = "rejected"
            reason = f"貸款金額超過限額 (最高 {int(base_salary * 6)})"
        elif hcap_score >= 700 and dbr_score >= 70:
            status = "approved"
        elif hcap_score >= 650 and dbr_score >= 60:
            status = "review"
            reason = "評分合理，可進行下一步驗證以增加通過率。"
        else:
            status = "rejected"
            reason = f"綜合評分 ({hcap_score}分) 或 DBR ({dbr_score:.0f}%) 不足。"

        # 6. 解析電子存摺交易明細 → 拆分底薪/加班費
        bank_statement_json = form.get('bank_statement_data', '')
        if bank_statement_json:
            try:
                bs_transactions = json.loads(bank_statement_json)
                salary_records = [t for t in bs_transactions if '薪資' in t.get('memo', '')]
                monthly_totals = []
                monthly_overtimes = []
                labels = []
                for rec in salary_records:
                    deposit = float(rec['deposit'].replace('$', '').replace(',', ''))
                    overtime = max(0, deposit - base_salary)
                    monthly_totals.append(int(deposit))
                    monthly_overtimes.append(int(overtime))
                    date_str = rec['memo'].split('_')[1][:6]
                    labels.append(f"{int(date_str[4:6])}月")
                salary_data = {
                    "labels": labels,
                    "base_salary": [base_salary] * len(labels),
                    "overtime": monthly_overtimes,
                    "total": monthly_totals
                }
            except:
                salary_data = {
                    "labels": ["M-5", "M-4", "M-3", "M-2", "M-1", "Current"],
                    "base_salary": [base_salary] * 6,
                    "overtime": [0] * 6,
                    "total": [base_salary] * 6
                }
        else:
            salary_data = {
                "labels": ["M-5", "M-4", "M-3", "M-2", "M-1", "Current"],
                "base_salary": [base_salary] * 6,
                "overtime": [0] * 6,
                "total": [base_salary] * 6
            }

        session['custom_client'] = {
            "id": "LOAN-APP-001",
            "name": form.get('english_name', 'Guest'),
            "country": form.get('country', 'Vietnam'),
            "employer": algo_input_data['employerType'],
            "company_name": company_name,
            "job_title": "作業員",
            "contract_remaining": contract_months,
            "age": 28,
            "salary_data": salary_data,
            "hcap_score": hcap_score,
            "card_hcap_score": card_hcap_score,
            "adjusted_salary": base_salary,
            "score_breakdown": {
                "repayment_capacity": {"score": result['repayment_capacity_score'], "weight": 40},
                "income_stability": {"score": result['income_stability_score'], "weight": 30},
                "repayment_willingness": {"score": result['repayment_willingness_score'], "weight": 20},
                "external_risk": {"score": result['external_risk_score'], "weight": 10}
            },
            "card_score_breakdown": {
                "repayment_capacity": {"score": card_result['repayment_capacity_score'], "weight": 20},
                "income_stability": {"score": card_result['income_stability_score'], "weight": 30},
                "repayment_willingness": {"score": card_result['repayment_willingness_score'], "weight": 30},
                "external_risk": {"score": card_result['external_risk_score'], "weight": 20}
            },
            "employer_rating": (lambda ei: {
                "score": RATING_TO_SCORE.get(ei['rating'], 80), "grade": ei['rating'],
                "industry": ei['industry'], "outlook": ei['outlook']
            } if ei else {
                "score": result['employer_base_score'], "grade": result['employer_grade'],
                "industry": "電子製造", "outlook": "穩定"
            })(lookup_employer_info(company_name)),
            "behavior_data": { "remittance_regularity": remit_regularity, "voice_ai_risk": voice_label, "digital_footprint": "尚未啟用" },
            "loan_recommendation": {
                "survival_loan": {
                    "approved": status == 'approved',
                    "max_amount": loan_amount if status == 'approved' else 0,
                    "term": loan_term,
                    "interest_rate": round(result['dbr_result']['interest_rate'], 1),
                    "reason": "" if status == 'approved' else reason
                },
                "isa": {
                    "qualified": hcap_score >= 680,
                    "training_field": "CNC精密加工" if hcap_score >= 680 else "",
                    "expected_salary_increase": 12000 if hcap_score >= 700 else 8000,
                    "reason": "" if hcap_score >= 680 else "收入穩定度不足"
                }
            },
            "risk_factors": ["新戶申請"],
            "is_custom": True,
            "_form_data": {**algo_input_data, "_product_type": "loan"}
        }

        # 同步寫入 DEMO_CLIENTS['custom']，供銀行端客戶資料庫存取
        data.DEMO_CLIENTS['custom'] = session['custom_client']

        # 初始化 custom 客戶的即時監控基礎設施
        CLIENT_STATES['custom'] = {
            'l2_enabled': False, 'l3_enabled': False,
            'gps_context': '未啟用', 'gps_status': 'safe',
            'trust_score': 50, 'coins': 0,
            'device_status': {'math': 'good', 'wifi': 'good', 'batt': 'good'},
            'weekly_scores': []
        }
        REALTIME_RISK_DATAS['custom'] = []
        remit_synced = remit_regularity > 0

        # [新增] 備份既有的語音數據
        existing_voice_data = None
        if 'custom' in BANK_DATABASES:
            existing_voice_data = BANK_DATABASES['custom'].get('voice_analysis')

        BANK_DATABASES['custom'] = _create_bank_db(
            "CUSTOM-001", form.get('english_name', 'Guest'),
            "Synced" if remit_synced else "Not Synced",
            remit_regularity, int(base_salary * 0.3) if remit_synced else 0,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') if remit_synced else "--",
            "Not Verified", 0, 0, "--", []
        )

        # [新增] 還原語音數據
        if existing_voice_data and existing_voice_data.get('status') != 'Not Verified':
            BANK_DATABASES['custom']['voice_analysis'] = existing_voice_data

        return jsonify({
            "status": status,
            "score": hcap_score,
            "approved_amount": loan_amount if status == 'approved' else 0,
            "monthly_payment": round(abs(monthly_payment), 2),
            "dbr_ratio": round(dbr_score, 2),
            "reason": reason,
            "details": {
                "base_score": round(result['base_score'], 1),
                "dbr_score": round(dbr_score, 2),
                "breakdown": {
                    "repayment": result['repayment_capacity_score'],
                    "stability": result['income_stability_score']
                }
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/generate_credential_qr', methods=['POST'])
def generate_credential_qr():
    """
    [H-CAP 核心流程]
    1. 清空舊紀錄 (避免狀態汙染)
    2. 向政府 API 申請新的 OID4VP 交易 (Transaction)
    3. 初始化 Session 狀態記憶 (為 Latch Logic 做準備)
    """
    try:
        # 1. 【關鍵】徹底清空舊的 Session 狀態
        # 這一步保證每次點進來都是「未驗證」的乾淨狀態
        session.pop('credential_verification', None)
        session.pop('verified_user_info', None) 
        
        # 準備 API Header
        headers = {
            'Access-Token': VERIFIER_ACCESS_TOKEN,
            'Content-Type': 'application/json'
        }

        # 準備用來存入 Session 的結構
        # 先預設 verified = False，讓 verify_credential 有位置可以改成 True
        session_data = {
            'arc_verified': False,
            'contract_verified': False,
            'arc_transaction_id': None,
            'contract_transaction_id': None,
            'verified_real_name': None # 用來存將來驗證到的真名
        }
        
        # 準備回傳給前端的 QR Code 圖片資料
        qr_response = {}

        # 2. 迴圈產生 ARC 與 Contract 的 QR Code
        for key in ['arc', 'contract']:
            # 產生唯一的交易序號 (UUID v4)
            transaction_id = str(uuid.uuid4())
            
            # 呼叫政府 API (/api/oidvp/qrcode)
            # 注意：VC_VERIFIER_CONFIG[key]['ref'] 對應你在 config 裡的設定
            response = requests.get(
                f"{VERIFIER_API_BASE}/api/oidvp/qrcode",
                params={
                    'ref': VC_VERIFIER_CONFIG[key]['ref'],
                    'transactionId': transaction_id
                },
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                api_data = response.json()
                
                # 儲存圖片給前端顯示
                qr_response[f'{key}_qrcode'] = api_data.get('qrcodeImage')
                
                # 儲存 ID 到 session_data 結構中
                session_data[f'{key}_transaction_id'] = transaction_id
                
                print(f"✅ QR 生成成功 [{key}] ID: {transaction_id}")
            else:
                print(f"❌ QR 生成失敗 [{key}]: {response.text}")
                return jsonify({"success": False, "error": f"API Error: {response.status_code}"}), 500

        # 3. 【關鍵】將初始化好的結構寫入 Session
        session['credential_verification'] = session_data
        session.modified = True # 強制 Flask 更新 Session Cookie

        return jsonify({
            "success": True, 
            "qr_codes": qr_response
        })
        
    except Exception as e:
        print(f"🔥 QR 生成發生例外: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/verify_credential', methods=['POST'])
def verify_credential():
    try:
        # 1. 抓取前端傳來的 13 欄位資料
        user_input = request.get_json(silent=True) or {}
        # 前端用 'name'，VC 用 'worker_name'，統一映射
        if 'name' in user_input and 'worker_name' not in user_input:
            user_input['worker_name'] = user_input['name']
        v_data = session.get('credential_verification')
        if not v_data: return jsonify({"success": True, "error": "No Session"})

        headers = {'Access-Token': VERIFIER_ACCESS_TOKEN, 'Content-Type': 'application/json'}
        arc_done = v_data.get('arc_verified', False)
        contract_done = v_data.get('contract_verified', False)
        real_name = v_data.get('verified_real_name', None)

        for key in ['arc', 'contract']:
            if key == 'arc' and arc_done: continue
            if key == 'contract' and contract_done: continue

            tx_id = v_data.get(f'{key}_transaction_id')
            if not tx_id: continue

            # 呼叫結果查詢
            response = requests.post(
                f"{VERIFIER_API_BASE}/api/oidvp/result",
                headers=headers, json={"transactionId": tx_id}, timeout=5
            )

            if response.status_code == 200:
                api_res = response.json()
                if api_res.get('verifyResult') in [True, 'SUCCESS']:
                    # 💡 解析政府端回傳的憑證內容
                    vc_data = {c.get('ename'): str(c.get('value', '')) for c in api_res['data'][0].get('claims', [])}
                    
                    # 💡 定義比對欄位清單 (與發行端模板 ename 完全一致)
                    if key == 'arc':
                        check_fields = ['worker_name', 'ui_num', 'issue_date', 'expiry_date', 'card_num']
                    else:
                        check_fields = [
                            'worker_name', 'company_name', 'company_telephone', 'company_address', 
                            'job_title', 'monthly_wages', 'contract_expiry', 'agency_name', 'agency_telephone'
                        ]

                    is_match = True
                    for f in check_fields:
                        # 姓名與文字類：去除底線/空格後比對
                        if f in ['worker_name', 'company_name', 'agency_name']:
                            vc_val = vc_data.get(f, '').replace('_', '').replace(' ', '').upper()
                            user_val = str(user_input.get(f, '')).replace('_', '').replace(' ', '').upper()
                        else:
                            vc_val = vc_data.get(f, '').strip()
                            user_val = str(user_input.get(f, '')).strip()
                        
                        if vc_val != user_val:
                            print(f"❌ [{key}] 欄位不符: {f} (VC: {vc_val} vs Input: {user_val})")
                            is_match = False
                            break

                    if is_match:
                        print(f"✅ [{key}] 100% 資料吻合，核實通過！")
                        if key == 'arc': 
                            arc_done = True
                            real_name = vc_data.get('worker_name', '').replace('_', ' ')
                            get_client_db('low_risk')['applicant_info']['worker_name'] = real_name # 同步真名到銀行後台
                        if key == 'contract':
                            contract_done = True
                            # 將契約薪資同步到銀行資料庫，作為風控依據
                            get_client_db('low_risk')['remittance_data']['avg_amount'] = vc_data.get('monthly_wages', 0)
                        
                        v_data[f'{key}_verified'] = True
                        v_data['verified_real_name'] = real_name
                        session.modified = True

        return jsonify({
            "success": True,
            "arc_verified": arc_done,
            "contract_verified": contract_done,
            "all_verified": (arc_done and contract_done),
            "real_name": real_name
        })

    except Exception as e:
        print(f"🔥 驗證後端發生錯誤: {e}")
        return jsonify({"success": False, "error": str(e)}), 200
    
# ========== [API 8] 語音面試完成（僅記錄，不判斷門檻） ==========
@app.route('/api/finalize_voice_verification', methods=['POST'])
def finalize_voice_verification():
    try:
        req_data = request.get_json() or {}
        client_id = req_data.get('client_id', 'low_risk')
        db = get_client_db(client_id)
        details = db['voice_analysis'].get('details', [])

        if not details:
            return jsonify({"success": False, "message": "尚未進行任何面試"}), 400

        # 計算平均分
        avg_voice_score = int(sum(d['score'] for d in details) / len(details))

        # 更新 BANK_DATABASES 狀態
        db['voice_analysis']['status'] = "Verified"
        db['voice_analysis']['risk_score'] = avg_voice_score
        db['voice_analysis']['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # [新增的區塊] 開始動態更新 H-CAP 分數
        client_to_update = data.DEMO_CLIENTS.get(client_id)

        if client_to_update and '_form_data' in client_to_update:
            form_d = client_to_update['_form_data']

            # 1. 將語音分數轉換為模型看得懂的風險因子
            form_d['riskVoiceAlert'] = avg_voice_score < 60

            # 2. 重新計算信貸模型分數
            loan_res = calculate_client_score(form_d, product_type='loan')
            client_to_update['hcap_score'] = loan_res['total_score']
            client_to_update['score_breakdown']['repayment_willingness']['score'] = loan_res['repayment_willingness_score']

            # 3. 重新計算信用卡模型分數
            if 'card_hcap_score' in client_to_update:
                card_res = calculate_client_score(form_d, product_type='card')
                client_to_update['card_hcap_score'] = card_res['total_score']
                if 'card_score_breakdown' in client_to_update:
                    client_to_update['card_score_breakdown']['repayment_willingness']['score'] = card_res['repayment_willingness_score']

            # 4. 更新行為數據的文字描述
            if 'behavior_data' in client_to_update:
                if avg_voice_score >= 80:
                    client_to_update['behavior_data']['voice_ai_risk'] = "低風險"
                elif avg_voice_score >= 60:
                    client_to_update['behavior_data']['voice_ai_risk'] = "中風險"
                else:
                    client_to_update['behavior_data']['voice_ai_risk'] = "高風險"

        # 將語音驗證分數存入 session，供提交申請時使用
        session['voice_verification_done'] = True
        session['voice_avg_score'] = avg_voice_score
        session.modified = True

        return jsonify({
            "success": True,
            "passed": True,
            "avg_score": avg_voice_score,
            "message": f"語音驗證已完成！平均分數 {avg_voice_score} 分，將在提交申請時納入 H-CAP 評分。"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========== [API 9 - NEW] ISA 職涯投資產品試算 ==========
@app.route('/api/calculate_isa_scenario/<scenario>')
def calculate_isa_scenario(scenario):
    try:
        increase_val = request.args.get('increase', 30000)
        increase = int(increase_val)
        
        # 初始化變數
        bank_cashflow = [] # 負值代表銀行撥款，正值代表銀行回收
        total_return = 0
        irr = 0
        description = ""
        details = {}

        if scenario == 'success':
            # 情境 A: 成功考取並就業 (高回報)
            # T0-T2: 銀行分期撥款學費 (共 10萬)
            bank_cashflow = [-30000, -30000, -40000] 
            
            # M1-M12: 移工就業後，銀行分潤 (薪資漲幅的 60%)
            # 例如漲薪 3萬 * 60% = 1.8萬/月
            monthly_share = int(increase * 0.6)
            
            # 假設合約期 12 個月
            for _ in range(12):
                bank_cashflow.append(monthly_share)
            
            total_return = monthly_share * 12
            # 簡單模擬 IRR (內部報酬率)
            net_profit = total_return - 100000
            irr = round((net_profit / 100000) * 100, 1) # 粗略估算
            if irr < 0: irr = 2.5 # 保底
            
            description = "考取證照並進入大廠 (高分潤)"
            details = {"monthly_pay": monthly_share, "status": "分潤中"}

        elif scenario == 'fail_with_job':
            # 情境 B: 培訓結束但未考上 (保本)
            bank_cashflow = [-30000, -30000, -40000]
            
            # 轉為一般無息分期，每月還 5000
            monthly_pay = 5000
            installments = 100000 // monthly_pay
            for _ in range(installments): 
                bank_cashflow.append(monthly_pay)
            
            # 取前 15 個數據點做圖表就好，不然太長
            bank_cashflow = bank_cashflow[:15]
            
            total_return = 100000
            irr = 0.0 # 無息回本
            description = "未考取證照 (轉為無息分期)"
            details = {"monthly_pay": monthly_pay, "status": "分期償還"}

        elif scenario == 'fail_dropout':
            # 情境 C: 中途放棄 (止損)
            # 銀行只撥了第一期款項，學員就跑了
            bank_cashflow = [-30000] 
            
            # 沒收保證金 (假設 5000)
            bank_cashflow.append(5000)
            
            # 後面幾期都是 0 (呆帳)
            for _ in range(4): bank_cashflow.append(0)
            
            total_return = 5000
            irr = -83.3 # 虧損
            description = "中途放棄培訓 (啟動止損機制)"
            details = {"monthly_pay": 0, "status": "壞帳核銷"}

        return jsonify({
            "bank_cashflow": bank_cashflow,
            "total_return": total_return,
            "irr": irr,
            "description": description,
            "details": details
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True, host='0.0.0.0')