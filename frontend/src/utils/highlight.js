import hljs from 'highlight.js'

/**
 * Syntax-highlight code and return HTML string.
 * @param {string} code - raw source code
 * @param {string} lang - language hint (e.g. 'python', 'js')
 * @returns {string} highlighted HTML
 */
export function highlightCode(code, lang = '') {
  if (lang && hljs.getLanguage(lang)) {
    return hljs.highlight(code, { language: lang }).value
  }
  return hljs.highlightAuto(code).value
}
