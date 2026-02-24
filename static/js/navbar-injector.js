// static/js/navbar-injector.js

document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    
    // 1. 注入 Google Translate 初始化設定
    window.googleTranslateElementInit = function() {
        new google.translate.TranslateElement({
            pageLanguage: 'zh-TW',
            includedLanguages: 'en,id,vi,zh-TW',
            layout: google.translate.TranslateElement.InlineLayout.SIMPLE,
            autoDisplay: false
        }, 'google_translate_element');
    };

    // 2. 載入 Google 官方翻譯腳本
    if (!document.querySelector('script[src*="translate.google.com"]')) {
        const script = document.createElement('script');
        script.src = '//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
        script.async = true;
        document.head.appendChild(script);
    }

    // 3. 生成導航列 HTML (包含所有連結 + 核心資料庫)
    const navbarHTML = `
    <nav class="navbar navbar-expand-lg navbar-dark navbar-hcap" style="position: relative; z-index: 1000;">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-shield-alt"></i> <span class="notranslate">H-CAP</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto align-items-center">
                    <li class="nav-item"><a class="nav-link ${currentPath === '/' || currentPath === '/index' ? 'active' : ''}" href="/">首頁</a></li>
                    <li class="nav-item"><a class="nav-link ${currentPath === '/dashboard' ? 'active' : ''}" href="/dashboard">客戶畫像</a></li>
                    <li class="nav-item"><a class="nav-link ${currentPath === '/products' ? 'active' : ''}" href="/products">產品模擬</a></li>
                    <li class="nav-item"><a class="nav-link ${currentPath === '/lifecycle' ? 'active' : ''}" href="/lifecycle">風控監控</a></li>
                    

                    <li class="nav-item"><a class="nav-link ${currentPath === '/clients' ? 'active' : ''}" href="/clients">客戶列表</a></li>
                    <li class="nav-item"><a class="nav-link ${currentPath === '/algorithms' ? 'active' : ''}" href="/algorithms">算法說明</a></li>
                    <li class="nav-item"><a class="nav-link ${currentPath === '/stress_test' ? 'active' : ''}" href="/stress_test">壓力測試</a></li>
                    
                    <li class="nav-item ms-lg-3">
                        <div id="google_translate_element"></div>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    `;
    
    // 4. 插入導航列
    const existingNavbar = document.querySelector('.navbar-hcap');
    if (existingNavbar) {
        existingNavbar.outerHTML = navbarHTML;
    } else {
        document.body.insertAdjacentHTML('afterbegin', navbarHTML);
        if (window.getComputedStyle(document.body).paddingTop === '0px') {
             document.body.style.paddingTop = '70px';
        }
    }
    
    // 5. 初始化 Bootstrap Mobile Menu
    if (typeof bootstrap !== 'undefined') {
        const navEl = document.getElementById('navbarNav');
        if (navEl) new bootstrap.Collapse(navEl, { toggle: false });
    }
    
    // 6. CSS 強制修正
    const style = document.createElement('style');
    style.innerHTML = `
        .goog-te-banner-frame.skiptranslate { display: none !important; }
        iframe.goog-te-banner-frame { display: none !important; visibility: hidden !important; height: 0 !important; }
        body { top: 0px !important; position: static !important; margin-top: 0px !important; }
        html { margin-top: 0px !important; height: 100% !important; }
        .goog-te-gadget-icon { display: none !important; }
        .goog-te-menu-value span:nth-child(3), .goog-te-menu-value span:nth-child(5) { display: none !important; }
        
        .goog-te-gadget-simple {
            background-color: rgba(255,255,255,0.1) !important;
            border: 1px solid rgba(255,255,255,0.3) !important;
            padding: 6px 12px !important;
            border-radius: 20px !important;
            cursor: pointer;
            transition: all 0.3s;
            font-family: inherit !important;
        }
        .goog-te-gadget-simple:hover { background-color: rgba(255,255,255,0.2) !important; }
        .goog-te-gadget-simple span { color: white !important; font-weight: 500 !important; vertical-align: middle !important; }
    `;
    document.head.appendChild(style);
});