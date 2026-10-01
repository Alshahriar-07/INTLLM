import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { CodeBlock } from './CodeBlock';

/**
 * Renders assistant/user message content as rich markdown.
 *
 * - GFM: tables, task lists, strikethrough, autolinks
 * - Fenced code blocks -> CodeBlock (language label + copy button + hljs tokens)
 * - Inline code stays inline; backticks are never shown literally
 *
 * Note on ordering: rehype-highlight tokenizes block code into React spans
 * before our renderers run. We therefore override `pre` (not `code`) for
 * blocks and pass the highlighted children straight into CodeBlock, keeping
 * the tokens intact. The `code` override only restyles inline code.
 */
export const Markdown: React.FC<{ content: string }> = ({ content }) => {
  const components: Components = {
    pre: ({ children }) => {
      const child = React.Children.toArray(children)[0] as React.ReactElement<{
        className?: string;
        children?: React.ReactNode;
      }> | undefined;

      // Rare malformed input: render as-is inside the default pre.
      if (!child || child.type !== 'code') {
        return <pre className="code-plain">{children}</pre>;
      }

      const className: string = child.props?.className ?? '';
      const langMatch = /language-([\w+-]+)/.exec(className);
      const language = langMatch?.[1] ?? 'text';

      return (
        <CodeBlock language={language}>
          {child.props.children}
        </CodeBlock>
      );
    },
    code: ({ className, children, ...props }) => {
      const isBlock = typeof className === 'string' && className.includes('hljs');
      if (isBlock || /language-/.test(className ?? '')) {
        // Block code: pass through so `pre` can wrap it in a CodeBlock while
        // keeping the rehype-highlight token spans.
        return (
          <code className={className} {...props}>
            {children}
          </code>
        );
      }
      // Inline code.
      return (
        <code className="inline-code" {...props}>
          {children}
        </code>
      );
    }
  };

  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
