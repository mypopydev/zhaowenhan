#!/usr/bin/env node
/**
 * recitation/ 从「文件传输助手」网页版抽取公众号文章链接
 *
 * 为什么走这条路：
 *   mp.weixin.qq.com 的登录页是公众号**后台**（需该号管理员扫码），读者登录不了；
 *   公众号历史消息也没有公开接口。可行的半自动办法是——你在手机微信里把该号的
 *   历史文章发到「文件传输助手」，本脚本打开 filehelper.weixin.qq.com（**你自己的
 *   微信**扫码即可登录），把消息里所有 mp.weixin.qq.com/s/ 链接抽出来写入 urls.txt。
 *
 * 用法：
 *   1) 手机微信 → 公众号「发现之旅 速来记单词」→ 历史消息 → 逐篇「转发」到
 *      文件传输助手（或复制链接后粘贴到文件传输助手）
 *   2) 在本机执行：   node 工具/取链接.js
 *      → 弹出 Chrome，用手机微信扫码登录
 *      → 脚本自动滚动、抽取链接，写入 原文/urls.txt（去重、保序）
 *   3) 再跑：python3 工具/抓取解析.py 原文/urls.txt
 *
 * 依赖：playwright-core（npm i playwright-core）+ 本机 Google Chrome
 */

const fs = require('fs');
const path = require('path');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT = path.join(__dirname, '..', '原文', 'urls.txt');

(async () => {
  // playwright-core 可能装在系统或 /tmp/pw 下，逐个尝试
function loadPlaywright() {
  const cands = ['playwright-core', '/tmp/pw/node_modules/playwright-core'];
  if (process.env.PW) cands.unshift(process.env.PW);
  for (const c of cands) { try { return require(c); } catch (e) {} }
  throw new Error('找不到 playwright-core，请先执行：cd /tmp/pw && npm i playwright-core');
}
const { chromium } = loadPlaywright();
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: false,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
  await page.goto('https://filehelper.weixin.qq.com/', { waitUntil: 'domcontentloaded' });

  console.log('请用手机微信扫描页面上的二维码登录…');
  // 等待消息列表出现（登录成功）
  try {
    await page.waitForFunction(
      () => document.body && document.body.innerText.length > 0 &&
            !/扫码|二维码/.test(document.body.innerText.slice(0, 200)),
      { timeout: 180000 }
    );
  } catch (e) {
    console.log('× 等待扫码超时（3 分钟）。确认已登录后重跑本脚本即可。');
    await browser.close();
    process.exit(1);
  }
  console.log('登录成功，开始读取消息…');

  const links = new Set();
  const collect = async () => {
    const found = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('a').forEach(a => { if (a.href) out.push(a.href); });
      const re = /https?:\/\/mp\.weixin\.qq\.com\/s\/[A-Za-z0-9_\-]+/g;
      const m = document.body.innerText.match(re) || [];
      return out.concat(m);
    });
    found.forEach(u => {
      const m = u.match(/https?:\/\/mp\.weixin\.qq\.com\/s\/[A-Za-z0-9_\-]+/);
      if (m) links.add(m[0]);
    });
  };

  await collect();
  // 向上滚动加载更早的消息
  for (let i = 0; i < 30; i++) {
    await page.mouse.wheel(0, -3000);
    await page.waitForTimeout(600);
    const before = links.size;
    await collect();
    if (links.size === before && i > 5) break;
  }

  const list = [...links];
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, list.join('\n') + '\n', 'utf8');
  console.log(`✓ 共抽取 ${list.length} 条链接 → ${OUT}`);
  console.log('下一步：python3 工具/抓取解析.py 原文/urls.txt');
  await browser.close();
})().catch(e => { console.error('×', e.message); process.exit(1); });
