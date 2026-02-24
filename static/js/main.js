// 通用工具函數
function formatCurrency(amount) {
    return 'NT$ ' + amount.toLocaleString();
}

function calculateDBR(monthlyPayment, monthlyIncome) {
    return ((monthlyPayment / monthlyIncome) * 100).toFixed(1);
}

// 貸款計算器
class LoanCalculator {
    constructor(principal, termMonths, annualRate) {
        this.principal = principal;
        this.termMonths = termMonths;
        this.annualRate = annualRate;
    }
    
    calculateMonthlyPayment() {
        const monthlyRate = this.annualRate / 100 / 12;
        const numerator = monthlyRate * Math.pow(1 + monthlyRate, this.termMonths);
        const denominator = Math.pow(1 + monthlyRate, this.termMonths) - 1;
        return this.principal * numerator / denominator;
    }
    
    calculateTotalInterest() {
        return (this.calculateMonthlyPayment() * this.termMonths) - this.principal;
    }
}

// ISA情境計算器
class ISAScenario {
    static scenarios = {
        success: {
            bank_cashflow: [-50000, 18000, 18000, 18000, 18000, 18000],
            total_return: 40000,
            irr: 18.5,
            description: "學員成功考取證照並轉任中階技術人力"
        },
        fail_with_job: {
            bank_cashflow: [-25000, 4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167],
            total_return: 25000,
            irr: 0,
            description: "學員未考取證照，合約轉為零利率分期還本"
        },
        fail_dropout: {
            bank_cashflow: [-5000, 0, 0, 0, 0, 0],
            total_return: 0,
            irr: -100,
            description: "學員中途放棄培訓，銀行損失第一階段撥款"
        }
    };
    
    static getScenario(name) {
        return this.scenarios[name] || this.scenarios.success;
    }
}

// 風險等級計算
function calculateRiskLevel(score) {
    if (score >= 750) return { level: '低風險', color: 'primary' };
    if (score >= 700) return { level: '中低風險', color: 'success' };
    if (score >= 650) return { level: '中高風險', color: 'warning' };
    return { level: '高風險', color: 'danger' };
}

// 頁面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 如果有貸款計算器，初始化它
    const loanCalculator = document.getElementById('loanAmount');
    if (loanCalculator) {
        initLoanCalculator();
    }
    
    // 如果有時間軸，添加懸停效果
    const timelineItems = document.querySelectorAll('.timeline-item');
    timelineItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(5px)';
        });
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
    
    // 更新版權年份
    const yearElement = document.getElementById('currentYear');
    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }
});

// 初始化貸款計算器
function initLoanCalculator() {
    const amountSlider = document.getElementById('loanAmount');
    const termSlider = document.getElementById('loanTerm');
    
    if (amountSlider && termSlider) {
        const updateCalculator = () => {
            const amount = parseInt(amountSlider.value);
            const term = parseInt(termSlider.value);
            const calculator = new LoanCalculator(amount, term, 10.5);
            const monthlyPayment = calculator.calculateMonthlyPayment();
            
            document.getElementById('monthlyPayment').textContent = 
                formatCurrency(Math.round(monthlyPayment));
            
            // 計算DBR（假設月薪36,500）
            const dbr = calculateDBR(monthlyPayment, 36500);
            const dbrElement = document.getElementById('dbrValue');
            dbrElement.textContent = dbr + '%';
            
            // 根據DBR調整顏色
            if (dbr > 30) {
                dbrElement.className = 'text-danger';
            } else if (dbr > 25) {
                dbrElement.className = 'text-warning';
            } else {
                dbrElement.className = 'text-success';
            }
        };
        
        amountSlider.addEventListener('input', updateCalculator);
        termSlider.addEventListener('input', updateCalculator);
        updateCalculator(); // 初始計算
    }
}