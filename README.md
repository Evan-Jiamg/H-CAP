# H-CAP — Holistic Credit Assessment Platform

> 台灣移工普惠金融系統 · 永豐金控商業競賽提案

<p>
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" height="40"/> Python &nbsp;&nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/flask/flask-original.svg" height="40"/> Flask &nbsp;&nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg" height="40"/> HTML5 &nbsp;&nbsp;
  <img src="https://huggingface.co/front/assets/huggingface_logo.svg" height="40"/> Hugging Face &nbsp;&nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vercel/vercel-original.svg" height="40"/> Vercel
</p>

## Overview

台灣約有 70 萬名移工，因缺乏本地信用紀錄，難以取得銀行金融服務。H-CAP 是一套針對此問題設計的 FinTech Demo 系統，透過多維度信用評分模型，整合數位憑證驗證、AI 語音面談與區塊鏈匯款追蹤，分別提供移工端與銀行端兩大入口。

## Core features

| Feature | Description |
|---|---|
| H-CAP 信用評分 | 多維度評分模型，突破傳統徵信限制 |
| OID4VCI 數位憑證 | 串接數發部沙盒 API，QR Code + DeepLink 回傳 |
| Groq AI 語音面談 | AI 輔助面談，補充非結構化信用資訊 |
| 區塊鏈匯款追蹤 | 移工匯款行為作為信用評估依據 |
| 雙入口設計 | 移工端申請流程 / 銀行端審核介面分流 |
| Vercel Serverless Proxy | 解決數發部數位憑證沙盒 API 的 CORS 限制 |

## Tech stack

- **Backend：** Python Flask
- **Frontend：** HTML / CSS / JavaScript（Bootstrap）
- **Deployment：** Hugging Face Spaces（主站）、Vercel Serverless Proxy（CORS bypass）
- **AI：** Groq AI 語音面談
- **Identity：** OID4VCI / OID4VP — 數發部數位憑證沙盒 API

## Project structure

```
H-CAP/
├── app.py              # Flask 主程式，路由與邏輯
├── data.py             # 資料處理
├── requirements.txt    # 相依套件
├── .env.example        # 環境變數範本
├── templates/          # Jinja2 HTML 模板
│   ├── worker/         # 移工端頁面
│   └── bank/           # 銀行端頁面
├── static/             # CSS / JS / 圖片資源
└── ARCHITECTURE.md     # 系統架構說明
```
