import { marked } from 'marked'
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
    // Find $ not followed by $ (to avoid matching $$)
    const idx = src.search(/(?<!\$)\$(?!\$)/)
    return idx === -1 ? undefined : idx
  },
  tokenizer(src) {
    // Match $...$ (single $, not $$)
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

marked.use({ extensions: [blockMathExtension, mathExtension] })

marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true,
})

export function renderMarkdown(text) {
  return marked.parse(text)
}
