/**
 * SEO 预渲染脚本
 * 构建后运行，使用 Puppeteer 生成静态 HTML 快照
 * 用法: node scripts/prerender.mjs
 * 
 * 前置条件:
 * 1. 先执行 npm run build
 * 2. 安装 puppeteer: npm install puppeteer --save-dev
 * 3. 运行此脚本
 */

import puppeteer from 'puppeteer'
import { readFileSync, writeFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DIST_DIR = resolve(__dirname, '../dist')

async function prerender() {
  console.log('🚀 Starting prerender...')
  
  let browser
  try {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    })

    const page = await browser.newPage()
    
    // 从 dist 目录读取 index.html
    const indexPath = resolve(DIST_DIR, 'index.html')
    const originalHtml = readFileSync(indexPath, 'utf-8')
    
    // 启动本地服务器来提供 dist 文件
    // 使用 file:// 协议加载
    const fileUrl = `file://${indexPath}`
    
    await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 30000 })
    
    // 等待 Vue 应用渲染完成
    await page.waitForSelector('#app', { timeout: 10000 })
    
    // 等待额外时间确保所有内容渲染
    await new Promise(r => setTimeout(r, 2000))
    
    // 获取渲染后的 HTML
    const renderedHtml = await page.content()
    
    // 保存预渲染的 HTML
    writeFileSync(indexPath, renderedHtml, 'utf-8')
    console.log('✅ Prerendered index.html saved to dist/')
    
  } catch (error) {
    console.error('❌ Prerender failed:', error.message)
    console.log('💡 提示: 请确保已运行 npm run build 并安装 puppeteer')
    process.exit(1)
  } finally {
    if (browser) await browser.close()
  }
}

prerender()
