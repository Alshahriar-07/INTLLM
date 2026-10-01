import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { cn } from '../../lib/utils';

/** Canonical display names for the languages we explicitly support. */
const LANGUAGE_LABELS: Record<string, string> = {
  bash: 'bash',
  sh: 'shell',
  shell: 'shell',
  zsh: 'shell',
  powershell: 'powershell',
  ps1: 'powershell',
  python: 'python',
  py: 'python',
  javascript: 'javascript',
  js: 'javascript',
  jsx: 'jsx',
  mjs: 'javascript',
  cjs: 'javascript',
  typescript: 'typescript',
  ts: 'typescript',
  tsx: 'tsx',
  html: 'html',
  xml: 'xml',
  css: 'css',
  scss: 'scss',
  json: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'toml',
  markdown: 'markdown',
  md: 'markdown',
  sql: 'sql',
  c: 'c',
  cpp: 'cpp',
  'c++': 'cpp',
  java: 'java',
  rust: 'rust',
  rs: 'rust',
  go: 'go',
  golang: 'go',
  text: 'text',
  plaintext: 'text',
  txt: 'text'
};

export interface CodeBlockProps {
  language?: string;
  className?: string;
  /** Pre-rendered children; keeps rehype-highlight token spans intact. */
  children: React.ReactNode;
}

/**
 * Developer-grade code block: language label, copy button, horizontal
 * scrolling, token styling inherited from the .hljs theme in index.css.
 */
export const CodeBlock: React.FC<CodeBlockProps> = ({ language, className, children }) => {
  const [copied, setCopied] = useState(false);
  const preRef = useRef<HTMLPreElement>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, []);

  const handleCopy = useCallback(async () => {
    // Prefer the DOM text (works for highlighted spans); fall back to a
    // clipboard write of nothing when the ref is unavailable.
    const text = preRef.current?.innerText ?? '';
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard unavailable (permissions / non-secure context): fail silently.
    }
  }, []);

  const langKey = (language ?? '').toLowerCase();
  const label = LANGUAGE_LABELS[langKey] ?? (langKey ? langKey : 'text');

  return (
    <div className={cn('code-block group/code my-3', className)}>
      <div className="code-block-header">
        <span className="code-block-lang">{label}</span>
        <button type="button" onClick={handleCopy} className="code-block-copy" aria-label={copied ? 'Copied' : 'Copy code'}>
          {copied ? (
            <>
              <Check className="w-3 h-3" aria-hidden />
              Copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" aria-hidden />
              Copy
            </>
          )}
        </button>
      </div>
      <pre ref={preRef} className="code-block-pre" tabIndex={0}>
        <code className="hljs">{children}</code>
      </pre>
    </div>
  );
};
