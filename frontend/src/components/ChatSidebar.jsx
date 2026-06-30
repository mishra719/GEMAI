import { MessageSquarePlus, Trash2, MessageCircle, LogOut, Sparkles, X } from 'lucide-react';

export default function ChatSidebar({
  chats,
  activeChat,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onLogout,
  userEmail,
  sidebarOpen,
  onCloseSidebar,
}) {
  return (
    <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <div>
          <div className="sidebar-logo">
            <Sparkles size={20} />
            <span>Gem-AI</span>
          </div>
          <p className="sidebar-subtitle">Creative assistant workspace</p>
        </div>
        <div className="sidebar-header-actions">
          <button
            id="new-chat-btn"
            className="new-chat-btn"
            onClick={onNewChat}
            title="New Chat"
          >
            <MessageSquarePlus size={18} />
            <span>New</span>
          </button>
          <button
            className="sidebar-close-btn"
            onClick={onCloseSidebar}
            title="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="sidebar-callout">
        <p className="sidebar-callout-label">Current setup</p>
        <h3>Mode-aware chats with project export built in.</h3>
      </div>

      <div className="sidebar-chats">
        <div className="sidebar-section-head">
          <span>Recent chats</span>
          <small>{chats.length}</small>
        </div>

        {chats.length === 0 ? (
          <div className="sidebar-empty">
            <MessageCircle size={32} />
            <p>No chats yet</p>
            <span>Start a new conversation</span>
          </div>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              className={`sidebar-chat-item ${activeChat === chat.id ? 'active' : ''}`}
              onClick={() => onSelectChat(chat.id)}
            >
              <div className="sidebar-chat-icon">
                <MessageCircle size={15} />
              </div>
              <div className="sidebar-chat-copy">
                <span className="chat-title">{chat.title}</span>
                <span className="chat-timestamp">
                  {new Date(chat.created_at).toLocaleDateString([], {
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
              </div>
              <button
                className="chat-delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteChat(chat.id);
                }}
                title="Delete chat"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="user-avatar">
            {userEmail?.charAt(0)?.toUpperCase()}
          </div>
          <div className="sidebar-user-copy">
            <span className="user-label">Signed in</span>
            <span className="user-email">{userEmail}</span>
          </div>
        </div>
        <button
          id="logout-btn"
          className="logout-btn"
          onClick={onLogout}
          title="Logout"
        >
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
