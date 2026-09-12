import puppeteer from 'puppeteer-core';

const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage'],
  protocolTimeout: 60000,
});
const page = await browser.newPage();
await page.setViewport({width:1792,height:1100});

await page.goto('http://localhost:5174/?redirect=/links', {waitUntil:'networkidle2',timeout:30000});
await new Promise(r=>setTimeout(r,1000));
await page.evaluate(()=>{
  document.querySelector('#login-username').value='demo';
  document.querySelector('#login-password').value='demo123';
});
await page.click('button.submit-btn');
await new Promise(r=>setTimeout(r,3000));

await page.screenshot({path:'/tmp/links_before.png',fullPage:false});
console.log('saved /tmp/links_before.png, URL:', page.url());

await browser.close();
