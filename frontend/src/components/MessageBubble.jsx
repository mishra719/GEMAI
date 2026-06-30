import { lazy, Suspense, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Copy, Check, Download, FileCode, Folder, ChevronDown, ChevronRight, Sparkles } from 'lucide-react';
import API from '../api/axios';

const CodeBlock = lazy(() => import('./CodeBlock'));

function decodeEscapedSource(text) {
  if (typeof text !== 'string' || !text.includes('\\')) return text;
  if (!['\\n', '\\r', '\\t', '\\"'].some((token) => text.includes(token))) return text;

  return text
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\r/g, '\r')
    .replace(/\\t/g, '\t')
    .replace(/\\"/g, '"');
}

function normalizeProjectFiles(project) {
  if (!project || typeof project !== 'object' || !project.files) return null;

  const files = Array.isArray(project.files)
    ? project.files.reduce((acc, entry) => {
        const filePath = entry?.name || entry?.path;
        if (!filePath || entry?.content === undefined) return acc;
        acc[filePath] = decodeEscapedSource(String(entry.content));
        return acc;
      }, {})
    : Object.fromEntries(
        Object.entries(project.files).map(([filePath, content]) => [
          filePath,
          decodeEscapedSource(String(content)),
        ])
      );

  return { ...project, files };
}

export default function MessageBubble({ message }) {
  const [copiedKey, setCopiedKey] = useState(null);
  const [expandedProject, setExpandedProject] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const isUser = message.role === 'user';
  const isCodeMode = message.mode === 'coding' && !isUser;
  const isImageMode = message.mode === 'image' && !isUser;

  // Parse JSON project structure from coding response
  const parsedProject = (() => {
    if (!isCodeMode) return null;

    const tryParse = (text) => {
      try {
        const parsed = JSON.parse(text);
        if (!parsed.files) return null;
        return normalizeProjectFiles(parsed);
      } catch { /* ignore */ }
      return null;
    };

    // Try direct parse
    let result = tryParse(message.content);
    if (result) return result;

    // Try extracting from markdown code blocks
    const match = message.content.match(/```(?:json)?\s*\n?([\s\S]*?)\n?\s*```/);
    if (match) {
      result = tryParse(match[1].trim());
      if (result) return result;
    }

    // Try finding any JSON object in the text
    const jsonMatch = message.content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      result = tryParse(jsonMatch[0]);
      if (result) return result;
    }

    return null;
  })();

  const copyToClipboard = async (text, key) => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.setAttribute('readonly', '');
        textArea.style.position = 'absolute';
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
      }
      setCopiedKey(key);
      window.setTimeout(() => setCopiedKey(null), 2000);
    } catch (error) {
      console.error('Failed to copy text:', error);
    }
  };

  const handleDownloadZip = async () => {
    setDownloading(true);
    try {
      const res = await API.post(
        '/generate-zip',
        { code_response: parsedProject ? JSON.stringify(parsedProject) : message.content },
        { responseType: 'blob' }
      );

      // Create blob with explicit ZIP MIME type
      const blob = new Blob([res.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);

      // Extract filename from Content-Disposition header (primary)
      let filename = 'project.zip';
      const disposition = res.headers['content-disposition'];
      if (disposition) {
        const match = disposition.match(/filename[^;=\n]*=["']?([^"';\n]+)/);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      // Fallback: try extracting project name from message content
      if (filename === 'project.zip') {
        try {
          const parsed = JSON.parse(message.content);
          if (parsed.project_name) filename = `${parsed.project_name}.zip`;
        } catch { /* ignore */ }
      }

      // Ensure .zip extension
      if (!filename.endsWith('.zip')) filename += '.zip';

      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();

      // Cleanup after a small delay to ensure download starts
      setTimeout(() => {
        link.remove();
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (err) {
      console.error('ZIP download failed:', err);
      alert('Failed to generate ZIP. The response may not contain a valid project structure.');
    } finally {
      setDownloading(false);
    }
  };

  const renderDownloadZipButton = (label = 'Download as ZIP') => (
    <button
      className="download-zip-btn"
      onClick={handleDownloadZip}
      disabled={downloading}
    >
      {downloading ? (
        <>
          <span className="btn-loading" />
          Generating ZIP...
        </>
      ) : (
        <>
          <Download size={16} />
          {label}
        </>
      )}
    </button>
  );

  const renderHighlightedCode = (language, code, customStyle) => (
    <Suspense
      fallback={
        <pre className="code-fallback" style={customStyle}>
          <code>{code}</code>
        </pre>
      }
    >
      <CodeBlock language={language} code={code} customStyle={customStyle} />
    </Suspense>
  );

  // Render a coding project structure nicely
  const renderProjectStructure = (project) => {
    const fileEntries = Object.entries(project.files);
    return (
      <div className="project-structure">
        <div className="project-header" onClick={() => setExpandedProject(!expandedProject)}>
          <div className="project-header-left">
            {expandedProject ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <Folder size={16} className="folder-icon" />
            <span className="project-name">{project.project_name || 'project'}</span>
          </div>
          <span className="project-file-count">{fileEntries.length} files</span>
        </div>

        {expandedProject && (
          <div className="project-files">
            {fileEntries.map(([filePath, content]) => (
              <details key={filePath} className="project-file">
                <summary className="file-summary">
                  <FileCode size={14} />
                  <span>{filePath}</span>
                </summary>
                <div className="file-content">
                  <div className="file-content-header">
                    <span>{filePath.split('/').pop()}</span>
                    <button
                      className="copy-btn"
                      onClick={() => copyToClipboard(String(content), filePath)}
                      title="Copy file content"
                    >
                      {copiedKey === filePath ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  </div>
                  {renderHighlightedCode(
                    getLanguageFromPath(filePath),
                    String(content),
                    { margin: 0, borderRadius: '0 0 8px 8px', fontSize: '0.8rem' }
                  )}
                </div>
              </details>
            ))}
          </div>
        )}

        {renderDownloadZipButton()}
      </div>
    );
  };

  // Determine the image URL to display (use proxy path)
  const imageUrl = message.image_url || null;

  return (
    <div className={`message ${isUser ? 'message-user' : 'message-ai'}`}>
      <div className="message-avatar">
        {isUser ? <User size={18} /> : <Sparkles size={18} />}
      </div>

      <div className="message-content">
        <div className="message-body">
          {/* Image mode: show generated image */}
          {isImageMode && imageUrl && (
            <div className="generated-image-container">
              <img
                src={imageUrl}
                alt="Generated by Gem-AI"
                className="generated-image"
                loading="lazy"
              />
            </div>
          )}

          {/* Coding mode: show project structure if JSON detected */}
          {parsedProject ? (
            renderProjectStructure(parsedProject)
          ) : (
            <>
              <ReactMarkdown
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    const codeString = String(children).replace(/\n$/, '');

                    if (!inline && match) {
                      return (
                        <div className="code-block">
                          <div className="code-header">
                            <span>{match[1]}</span>
                            <button
                              className="copy-btn"
                              onClick={() => copyToClipboard(codeString, `code-${codeString}`)}
                            >
                              {copiedKey === `code-${codeString}` ? <Check size={14} /> : <Copy size={14} />}
                            </button>
                          </div>
                          {renderHighlightedCode(match[1], codeString, props.customStyle)}
                        </div>
                      );
                    }
                    return (
                      <code className="inline-code" {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>

              {isCodeMode && (
                <div style={{ marginTop: '0.9rem' }}>
                  {renderDownloadZipButton('Build ZIP from this response')}
                </div>
              )}
            </>
          )}
        </div>

        <div className="message-meta">
          <span className={`message-mode mode-${message.mode}`}>{message.mode}</span>
          <span className="message-time">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      </div>
    </div>
  );
}

/** Derive syntax highlighting language from file extension */
function getLanguageFromPath(filePath) {
  const filename = filePath.split('/').pop()?.toLowerCase();
  if (filename === 'dockerfile') return 'dockerfile';
  if (filename === '.gitignore') return 'text';
  if (filename === '.env') return 'bash';

  const ext = filePath.split('.').pop()?.toLowerCase();
  const map = {
    py: 'python', js: 'javascript', jsx: 'jsx', ts: 'typescript', tsx: 'tsx',
    html: 'html', css: 'css', json: 'json', md: 'markdown', yaml: 'yaml',
    yml: 'yaml', sql: 'sql', sh: 'bash', bash: 'bash', txt: 'text',
    rs: 'rust', go: 'go', java: 'java', cpp: 'cpp', c: 'c', rb: 'ruby',
    php: 'php', xml: 'xml', toml: 'toml', ini: 'ini', env: 'bash',
  };
  return map[ext] || 'text';
}
