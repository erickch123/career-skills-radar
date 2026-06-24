import { Component, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Error boundary — if ReactMarkdown throws for any reason, render plain text
class MarkdownBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { error: boolean }
> {
  state = { error: false }
  static getDerivedStateFromError() { return { error: true } }
  render() {
    return this.state.error ? this.props.fallback : this.props.children
  }
}

interface Props {
  content: string
  isStreaming?: boolean
}

function PlainFallback({ content, isStreaming }: Props) {
  return (
    <>
      {content.split('\n').map((line, j) =>
        line ? <p key={j}>{line}</p> : <br key={j} />
      )}
      {isStreaming && <span className="cursor" />}
    </>
  )
}

export default function MarkdownMessage({ content, isStreaming }: Props) {
  return (
    <MarkdownBoundary fallback={<PlainFallback content={content} isStreaming={isStreaming} />}>
      <div className="md">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
        {isStreaming && <span className="cursor" />}
      </div>
    </MarkdownBoundary>
  )
}
