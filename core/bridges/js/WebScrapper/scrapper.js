const puppeteer = require('puppeteer');

class SafeScraper {
    constructor() {
        this.browser = null;
    }

    async scrape(url, selector) {
        try {
            this.browser = await puppeteer.launch({
                headless: true,
                args: ['--no-sandbox', '--disable-setuid-sandbox']
            });
            
            const page = await this.browser.newPage();
            await page.goto(url, {waitUntil: 'networkidle2'});
            
            return await page.evaluate((sel) => {
                return Array.from(document.querySelectorAll(sel))
                    .map(el => el.textContent);
            }, selector);
            
        } finally {
            if(this.browser) await this.browser.close();
        }
    }
}