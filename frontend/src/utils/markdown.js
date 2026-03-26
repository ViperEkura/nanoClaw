import { marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import katex from 'katex'
import hljs from 'highlight.js'

function renderMath(text, displayMode) {
  try {
    return katex.renderToString(text, {
      displayMode,
      throwOnError: false,
      strict: false,
    })
  } catch {
    return text
  }
}

// marked extension for inline math $...$
const mathExtension = {
  name: 'math',
  level: 'inline',
  start(src) {
    const idx = src.search(/(?<!\$)\$(?!\$)/)
    return idx === -1 ? undefined : idx
  },
  tokenizer(src) {
    const match = src.match(/^(?<!\$)\$(?!\$)([^\$\n]+?)\$(?!\$)/)
    if (match) {
      return { type: 'math', raw: match[0], text: match[1].trim(), displayMode: false }
    }
  },
  renderer(token) {
    return renderMath(token.text, token.displayMode)
  },
}

// marked extension for block math $$...$$
const blockMathExtension = {
  name: 'blockMath',
  level: 'block',
  start(src) {
    const idx = src.indexOf('$$')
    return idx === -1 ? undefined : idx
  },
  tokenizer(src) {
    const match = src.match(/^\$\$([\s\S]+?)\$\$\n?/)
    if (match) {
      return { type: 'blockMath', raw: match[0], text: match[1].trim() }
    }
  },
  renderer(token) {
    return `<div class="math-block">${renderMath(token.text, true)}</div>`
  },
}

marked.use({
  extensions: [blockMathExtension, mathExtension],
  ...markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value
      }
      return hljs.highlightAuto(code).value
    },
  }),
})

marked.setOptions({
  breaks: true,
  gfm: true,
})

export function renderMarkdown(text) {
  return marked.parse(text)
}

/**
 * 后处理 HTML：为所有代码块包裹 .code-block 容器，
 * 添加语言标签和复制按钮。在组件 onMounted / updated 中调用。
 */
export function enhanceCodeBlocks(container) {
  if (!container) return

  const pres = container.querySelectorAll('pre')
  for (const pre of pres) {
    // 跳过已处理过的
    if (pre.parentElement.classList.contains('code-block')) continue

    const code = pre.querySelector('code')
    const langClass = code?.className || ''
    const lang = langClass.replace(/hljs\s+language-/, '').trim() || 'code'

    const wrapper = document.createElement('div')
    wrapper.className = 'code-block'

    const header = document.createElement('div')
    header.className = 'code-header'

    const langSpan = document.createElement('span')
    langSpan.className = 'code-lang'
    langSpan.textContent = lang

    const copyBtn = document.createElement('button')
    copyBtn.className = 'code-copy-btn'
    copyBtn.title = '复制'
    copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'

    const checkSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>'

    copyBtn.addEventListener('click', () => {
      const raw = code?.textContent || ''
      navigator.clipboard.writeText(raw).then(() => {
        copyBtn.innerHTML = checkSvg
        setTimeout(() => { copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>' }, 1500)
      }).catch(() => {
        const ta = document.createElement('textarea')
        ta.value = raw
        ta.style.position = 'fixed'
        ta.style.opacity = '0'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
        copyBtn.innerHTML = checkSvg
        setTimeout(() => { copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>' }, 1500)
      })
    })

    header.appendChild(langSpan)
    header.appendChild(copyBtn)
    pre.parentNode.insertBefore(wrapper, pre)
    wrapper.appendChild(header)
    wrapper.appendChild(pre)

    // 重置 pre 的内联样式，确保由 .code-block 系列样式控制
    pre.style.cssText = 'margin:0;padding:0;border:none;border-radius:0;background:transparent;'
    if (code) {
      code.style.cssText = 'display:block;padding:12px 12px 12px 16px;overflow-x:auto;font-family:JetBrains Mono,Fira Code,monospace;font-size:13px;line-height:1.5;'
    }
  }
}
