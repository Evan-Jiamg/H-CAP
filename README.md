# H-CAP — Holistic Credit Assessment Platform

> 台灣移工普惠金融系統 · 永豐金控商業競賽提案

![Python](https://img.shields.io/badge/Python-639922?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-888780?style=flat-square&logo=flask&logoColor=white)
![HTML](https://img.shields.io/badge/HTML-D85A30?style=flat-square&logo=html5&logoColor=white)
![Hugging Face](https://img.shields.io/badge/Hugging_Face-D4537E?style=flat-square&logo=huggingface&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-444441?style=flat-square&logo=vercel&logoColor=white)

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
