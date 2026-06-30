import { useState, useRef, useEffect } from 'react';
import { Menu, Send, Sparkles, WandSparkles, Code2, Image as ImageIcon } from 'lucide-react';
import MessageBubble from './MessageBubble';
import ModeSelector from './ModeSelector';

const suggestions = [
  {
    icon: Sparkles,
    title: 'Quick explainer',
    text: 'Explain quantum computing in simple terms',
  },
  {
    icon: Code2,
    title: 'Build a project',
    text: 'Build a full-stack todo app with React and Node.js',
  },
  {
    icon: ImageIcon,
    title: 'Generate a visual',
    text: 'Generate an image of a futuristic cyberpunk city at night',
  },
  {
    icon: WandSparkles,
    title: 'Analyze data',
    text: 'Write a Python script to analyze CSV data',
  },
];

export default function ChatWindow({
  messages,
  mode,
  onModeChange,
  onSendMessage,
  loading,
  chatTitle,
  error,
  chatCount,
  onToggleSidebar,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [mode]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e) => {
    // Submit on Enter, but allow Shift+Enter for newline intent (future textarea)
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSend(e);
    }
  };

  const handleSuggestionClick = (text) => {
    setInput(text);
    inputRef.current?.focus();
  };

  return (
    <main className="chat-window">
      <div className="chat-header">
        <div className="chat-header-main">
          <button
            className="sidebar-toggle-btn"
            onClick={onToggleSidebar}
            title="Open sidebar"
          >
            <Menu size={18} />
          </button>
          <div>
            <p className="chat-header-eyebrow">Gem workspace</p>
            <h2>{chatTitle || 'New Chat'}</h2>
          </div>
        </div>

        <div className="chat-header-controls">
          <div className="chat-header-meta">
            <span>{chatCount} saved chats</span>
          </div>
          <ModeSelector mode={mode} onModeChange={onModeChange} />
        </div>
      </div>

      <div className="chat-messages">
        {error && <div className="chat-error-banner">{error}</div>}

        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-badge">
              <Sparkles size={16} />
              <span>Fresh conversation</span>
            </div>
            <h3>What are we making today?</h3>
            <p>Use a mode to steer the response, then start with a short goal, spec, or idea.</p>
            <div className="chat-suggestions">
              {suggestions.map((suggestion) => {
                const Icon = suggestion.icon;
                return (
                  <button
                    key={suggestion.title}
                    className="chat-suggestion-card"
                    onClick={() => handleSuggestionClick(suggestion.text)}
                  >
                    <div className="chat-suggestion-icon">
                      <Icon size={16} />
                    </div>
                    <div>
                      <strong>{suggestion.title}</strong>
                      <span>{suggestion.text}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}

        {loading && (
          <div className="message message-ai">
            <div className="message-avatar">
              <Sparkles size={18} className="thinking-icon" />
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-bar" onSubmit={handleSend}>
        <div className="chat-input-wrap">
          <label htmlFor="chat-input" className="chat-input-label">
            Message
          </label>
          <input
            ref={inputRef}
            id="chat-input"
            type="text"
            placeholder={
              mode === 'coding'
                ? '💻 Describe the project you want to build...'
                : mode === 'image'
                ? '🎨 Describe the image you want to generate...'
                : '✨ Type your message...'
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            autoComplete="off"
          />
        </div>
        <button
          id="send-btn"
          type="submit"
          className="send-btn"
          disabled={loading || !input.trim()}
          title="Send message"
        >
          <Send size={18} />
        </button>
      </form>
    </main>
  );
}
