import { execSync, spawn } from 'node:child_process'
import WebSocket from 'ws'
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const chrome = spawn(CHROME, ['--headless', '--disable-gpu', '--remote-debugging-port=9223', '--window-size=390,844', 'about:blank'], { stdio: 'ignore' })
await new Promise(r => setTimeout(r, 2000))
const targets = JSON.parse(execSync('curl -s http://localhost:9223/json').toString())
const ws = new WebSocket(targets[0].webSocketDebuggerUrl)
let id = 0
const send = (method, params) => new Promise(res => {
  const mid = ++id
  ws.send(JSON.stringify({ id: mid, method, params }))
  const h = (d) => { const m = JSON.parse(d); if (m.id === mid) { ws.off('message', h); res(m.result) } }
  ws.on('message', h)
})
await new Promise(r => ws.on('open', r))
await send('Page.enable')
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })
await send('Page.navigate', { url: 'http://localhost:3001/products' })
await new Promise(r => setTimeout(r, 6000))
const { result } = await send('Runtime.evaluate', { expression: `JSON.stringify({scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth, bodyW: document.body.scrollWidth})`, returnByValue: true })
console.log('overflow check:', result.value)
const shot = await send('Page.captureScreenshot', { format: 'png' })
execSync(`base64 -d > /tmp/products-mobile-cdp.png`, { input: shot.data })
chrome.kill()
