# 示範數據
DEMO_CLIENTS = {
    "low_risk": {
        "id": "WORKER-2023-001",
        "name": "Nguyen Van A",
        "country": "越南",
        "employer": "鴻海精密工業",
        "company_name": "鴻海精密工業",
        "job_title": "組裝技術員",
        "contract_remaining": 18,
        "age": 28,
        "salary_data": {
            "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
            "base_salary": [28000, 28000, 28000, 28000, 28000, 28000],
            "overtime": [7000, 8000, 8500, 9000, 8000, 8500],
            "total": [35000, 36000, 36500, 37000, 36000, 36500]
        },
        "hcap_score": 765,  # 信貸模型分數
        "card_hcap_score": 777,  # 信用卡模型分數
        "score_breakdown": {
            "repayment_capacity": {"score": 85, "weight": 40},
            "income_stability": {"score": 82, "weight": 30},
            "repayment_willingness": {"score": 92, "weight": 20},
            "external_risk": {"score": 70, "weight": 10}
        },
        "card_score_breakdown": {
            "repayment_capacity": {"score": 85, "weight": 20},
            "income_stability": {"score": 82, "weight": 30},
            "repayment_willingness": {"score": 92, "weight": 30},
            "external_risk": {"score": 70, "weight": 20}
        },
        "employer_rating": {
            "score": 90,
            "grade": "AA",
            "industry": "電子製造",
            "outlook": "穩定"
        },
        "behavior_data": {
            "remittance_regularity": 95,
            "voice_ai_risk": "低風險",
            "digital_footprint": "活躍"
        },
        "loan_recommendation": {
            "survival_loan": {
                "approved": True,
                "max_amount": 40000,
                "term": 12,
                "interest_rate": 10.5
            },
            "isa": {
                "qualified": True,
                "training_field": "CNC精密加工",
                "expected_salary_increase": 12000,
                "reason": ""
            }
        },
        "_form_data": {
            "employerType": "large_tech", "country": "Vietnam",
            "monthlySalary": 36000, "remittanceRegularity": 95,
            "contractRemaining": 18, "loanAmount": 40000, "loanTerm": 12,
            "riskUnpaidLeave": False, "riskIrregularOvertime": False,
            "riskVoiceAlert": False, "riskCountry": False,
            "_product_type": "loan"
        }
    },
    "medium_risk": {
        "id": "WORKER-2023-002",
        "name": "Maria Santos",
        "country": "菲律賓",
        "employer": "緯創資通",
        "company_name": "緯創資通",
        "job_title": "包裝作業員",
        "contract_remaining": 12,
        "age": 32,
        "salary_data": {
            "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
            "base_salary": [26000, 26000, 26000, 26000, 26000, 26000],
            "overtime": [6000, 6500, 5800, 6200, 5500, 6000],
            "total": [32000, 32500, 31800, 32200, 31500, 32000]
        },
        "hcap_score": 680,  # 信貸模型分數
        "card_hcap_score": 620,  # 信用卡模型分數
        "score_breakdown": {
            "repayment_capacity": {"score": 75, "weight": 40},
            "income_stability": {"score": 70, "weight": 30},
            "repayment_willingness": {"score": 80, "weight": 20},
            "external_risk": {"score": 65, "weight": 10}
        },
        "card_score_breakdown": {
            "repayment_capacity": {"score": 75, "weight": 20},
            "income_stability": {"score": 70, "weight": 30},
            "repayment_willingness": {"score": 80, "weight": 30},
            "external_risk": {"score": 65, "weight": 20}
        },
        "employer_rating": {
            "score": 80,
            "grade": "A",
            "industry": "電子製造",
            "outlook": "穩定"
        },
        "behavior_data": {
            "remittance_regularity": 80,
            "voice_ai_risk": "中風險",
            "digital_footprint": "正常"
        },
        "loan_recommendation": {
            "survival_loan": {
                "approved": True,
                "max_amount": 30000,
                "term": 12,
                "interest_rate": 12.5
            },
            "isa": {
                "qualified": False,
                "training_field": "",
                "expected_salary_increase": 0,
                "reason": "收入穩定度不足，需進一步評估"
            }
        },
        "_form_data": {
            "employerType": "medium_tech", "country": "Philippines",
            "monthlySalary": 32000, "remittanceRegularity": 80,
            "contractRemaining": 12, "loanAmount": 30000, "loanTerm": 12,
            "riskUnpaidLeave": False, "riskIrregularOvertime": False,
            "riskVoiceAlert": False, "riskCountry": False,
            "_product_type": "loan"
        }
    },
    "high_risk": {
        "id": "WORKER-2023-003",
        "name": "Budi Santoso",
        "country": "印尼",
        "employer": "中小型電子廠",
        "company_name": "中小型電子廠",
        "job_title": "清潔員",
        "contract_remaining": 6,
        "age": 35,
        "salary_data": {
            "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
            "base_salary": [22000, 22000, 22000, 0, 0, 0],
            "overtime": [6000, 5500, 4500, 0, 0, 0],
            "total": [28000, 27500, 26500, 0, 0, 0]
        },
        "hcap_score": 585,  # 信貸模型分數 (與 portal_bank.html 一致)
        "card_hcap_score": 400,  # 信用卡模型分數
        "score_breakdown": {
            "repayment_capacity": {"score": 50, "weight": 40},
            "income_stability": {"score": 40, "weight": 30},
            "repayment_willingness": {"score": 65, "weight": 20},
            "external_risk": {"score": 55, "weight": 10}
        },
        "card_score_breakdown": {
            "repayment_capacity": {"score": 50, "weight": 20},
            "income_stability": {"score": 40, "weight": 30},
            "repayment_willingness": {"score": 65, "weight": 30},
            "external_risk": {"score": 55, "weight": 20}
        },
        "employer_rating": {
            "score": 70,
            "grade": "B",
            "industry": "電子製造",
            "outlook": "保守"
        },
        "behavior_data": {
            "remittance_regularity": 65,
            "voice_ai_risk": "高風險",
            "digital_footprint": "不活躍"
        },
        "loan_recommendation": {
            "survival_loan": {
                "approved": False,
                "max_amount": 0,
                "term": 0,
                "interest_rate": 0,
                "reason": "收入中斷，風險過高"
            },
            "isa": {
                "qualified": False,
                "training_field": "",
                "expected_salary_increase": 0,
                "reason": "不符合基本資格"
            }
        },
        "_form_data": {
            "employerType": "small_factory", "country": "Indonesia",
            "monthlySalary": 27000, "remittanceRegularity": 65,
            "contractRemaining": 6, "loanAmount": 20000, "loanTerm": 12,
            "riskUnpaidLeave": "true", "riskIrregularOvertime": False,
            "riskVoiceAlert": False, "riskCountry": "true",
            "_product_type": "loan"
        }
    }
}

# 保留原始 DEMO_CLIENT 作為預設
DEMO_CLIENT = DEMO_CLIENTS["low_risk"]

# 風控事件時間軸數據
RISK_TIMELINE = [
    {"day": 1, "event": "放款成功", "risk_level": 1},
    {"day": 30, "event": "第一次正常代扣還款", "risk_level": 1},
    {"day": 45, "event": "加班時數正常範圍", "risk_level": 1},
    {"day": 65, "event": "AI偵測加班時數下降30%", "risk_level": 3},
    {"day": 66, "event": "系統自動發送關懷通知", "risk_level": 2},
    {"day": 75, "event": "恢復正常加班", "risk_level": 1},
    {"day": 90, "event": "第三次還款完成", "risk_level": 1}
]