<template>
  <div ref="container" class="code-editor-wrap"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { EditorView, keymap } from '@codemirror/view'
import { EditorState, Compartment } from '@codemirror/state'
import { basicSetup } from 'codemirror'
import { indentWithTab } from '@codemirror/commands'
import { oneDarkHighlightStyle } from '@codemirror/theme-one-dark'
import { syntaxHighlighting } from '@codemirror/language'
import { markdown } from '@codemirror/lang-markdown'
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { html } from '@codemirror/lang-html'
import { css } from '@codemirror/lang-css'
import { json } from '@codemirror/lang-json'
import { yaml } from '@codemirror/lang-yaml'
import { java } from '@codemirror/lang-java'
import { cpp } from '@codemirror/lang-cpp'
import { rust } from '@codemirror/lang-rust'
import { go } from '@codemirror/lang-go'
import { sql } from '@codemirror/lang-sql'
import { xml } from '@codemirror/lang-xml'

const EXT_MAP = {
  md: markdown, markdown: markdown, mdx: markdown,
  js: () => javascript(), jsx: () => javascript({ jsx: true }),
  ts: () => javascript({ typescript: true }),
  tsx: () => javascript({ jsx: true, typescript: true }),
  py: python, pyw: python,
  html: html, htm: html, vue: html, svelte: html,
  css: css, scss: css, less: css,
  json: json, jsonc: json,
  yaml: yaml, yml: yaml,
  java: java,
  c: cpp, h: cpp, cpp: cpp, cc: cpp, cxx: cpp, hpp: cpp,
  rs: rust,
  go: go,
  sql: sql,
  xml: xml, svg: xml, xsl: xml,
}

function langForFile(filename) {
  if (!filename) return []
  const ext = filename.split('.').pop().toLowerCase()
  const fn = EXT_MAP[ext]
  if (!fn) return []
  const result = typeof fn === 'function' ? fn() : fn
  return Array.isArray(result) ? result : [result]
}

const props = defineProps({
  modelValue: { type: String, default: '' },
  filename: { type: String, default: '' },
  dark: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'save'])

const container = ref(null)
let view = null
let skipEmit = false

const themeComp = new Compartment()
const langComp = new Compartment()

// Custom dark theme matching app's --bg-primary / --bg-secondary
const appDarkTheme = EditorView.theme({
  '&': { backgroundColor: '#1a1a1a', color: '#f0f0f0' },
  '.cm-gutters': {
    backgroundColor: '#141414',
    color: '#606060',
    border: 'none',
    borderRight: '1px solid rgba(255,255,255,0.06)',
  },
  '.cm-activeLineGutter': { backgroundColor: 'rgba(255,255,255,0.04)', color: '#a0a0a0' },
  '.cm-activeLine': { backgroundColor: 'rgba(255,255,255,0.03)' },
  '&.cm-focused .cm-cursor': { borderLeftColor: '#3b82f6', borderLeftWidth: '2px' },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, &.cm-focused .cm-content ::selection': {
    backgroundColor: 'rgba(59,130,246,0.25) !important',
  },
  '.cm-searchMatch': { backgroundColor: 'rgba(250,204,21,0.3)' },
  '&.cm-focused .cm-searchMatch': { backgroundColor: 'rgba(250,204,21,0.45)' },
  '.cm-panels': { backgroundColor: '#1a1a1a', borderColor: 'rgba(255,255,255,0.08)' },
  '.cm-panels input, .cm-panels button, .cm-panels select': {
    backgroundColor: '#141414',
    color: '#f0f0f0',
    border: '1px solid rgba(255,255,255,0.1)',
  },
  '.cm-tooltip': {
    backgroundColor: '#141414',
    border: '1px solid rgba(255,255,255,0.1)',
    color: '#f0f0f0',
  },
  '.cm-tooltip-autocomplete > ul > li': { padding: '4px 8px' },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': {
    backgroundColor: 'rgba(59,130,246,0.2)',
    color: '#f0f0f0',
  },
}, { dark: true })

const editorTheme = EditorView.theme({
  '&': { height: '100%' },
  '.cm-scroller': { overflow: 'auto', height: '100%' },
  '.cm-gutters': { minWidth: '40px' },
  '.cm-content': {
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    fontSize: '14px',
    lineHeight: '1.7',
  },
})

onMounted(() => {
  view = new EditorView({
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        basicSetup,
        editorTheme,
        keymap.of([
          indentWithTab,
          { key: 'Mod-s', run: () => { emit('save'); return true } },
        ]),
        EditorView.updateListener.of(update => {
          if (update.docChanged && !skipEmit) {
            emit('update:modelValue', update.state.doc.toString())
          }
        }),
        EditorView.lineWrapping,
        themeComp.of(props.dark ? [appDarkTheme, syntaxHighlighting(oneDarkHighlightStyle)] : []),
        langComp.of(langForFile(props.filename)),
      ],
    }),
    parent: container.value,
  })
})

watch(() => props.modelValue, val => {
  if (!view || val === view.state.doc.toString()) return
  skipEmit = true
  view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: val } })
  skipEmit = false
})

watch(() => props.dark, isDark => {
  view?.dispatch({
    effects: themeComp.reconfigure(
      isDark ? [appDarkTheme, syntaxHighlighting(oneDarkHighlightStyle)] : []
    ),
  })
})

watch(() => props.filename, () => {
  view?.dispatch({ effects: langComp.reconfigure(langForFile(props.filename)) })
})

onUnmounted(() => view?.destroy())
</script>

<style scoped>
.code-editor-wrap {
  height: 100%;
  width: 100%;
  overflow: hidden;
}
</style>
