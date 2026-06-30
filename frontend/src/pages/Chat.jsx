import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import API from '../api/axios';
import ChatSidebar from '../components/ChatSidebar';
import ChatWindow from '../components/ChatWindow';

export default function Chat() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [mode, setMode] = useState('general');
  const [loading, setLoading] = useState(false);
  const [chatTitle, setChatTitle] = useState('New Chat');
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const getErrorMessage = (err, fallback) => (
    err?.response?.data?.detail
    || err?.message
    || fallback
  );

  // Load all chats
  const loadChats = useCallback(async () => {
    try {
      const res = await API.get('/chats');
      setChats(res.data);
      setError('');
    } catch (err) {
      console.error('Failed to load chats:', err);
      setError(getErrorMessage(err, 'Failed to load chat history.'));
    }
  }, []);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  // Load messages for active chat
  const loadMessages = useCallback(async (chatId) => {
    try {
      const res = await API.get(`/chats/${chatId}`);
      setMessages(res.data.messages);
      setChatTitle(res.data.title);
      setError('');
    } catch (err) {
      console.error('Failed to load messages:', err);
      setError(getErrorMessage(err, 'Failed to load this chat.'));
    }
  }, []);

  useEffect(() => {
    if (activeChat) {
      loadMessages(activeChat);
    } else {
      setMessages([]);
      setChatTitle('New Chat');
    }
  }, [activeChat, loadMessages]);

  // Create new chat
  const handleNewChat = async () => {
    setActiveChat(null);
    setMessages([]);
    setChatTitle('New Chat');
    setMode('general');
    setError('');
    setSidebarOpen(false);
  };

  // Select existing chat
  const handleSelectChat = (chatId) => {
    setActiveChat(chatId);
    setSidebarOpen(false);
  };

  // Delete chat
  const handleDeleteChat = async (chatId) => {
    try {
      await API.delete(`/chats/${chatId}`);
      if (activeChat === chatId) {
        setActiveChat(null);
        setMessages([]);
        setChatTitle('New Chat');
      }
      loadChats();
      setError('');
      setSidebarOpen(false);
    } catch (err) {
      console.error('Failed to delete chat:', err);
      setError(getErrorMessage(err, 'Failed to delete the chat.'));
    }
  };

  // Send message
  const handleSendMessage = async (content) => {
    let currentChatId = activeChat;

    // Create chat if none active
    if (!currentChatId) {
      try {
        const res = await API.post('/chats', {
          title: content.substring(0, 50) + (content.length > 50 ? '...' : ''),
        });
        currentChatId = res.data.id;
        setActiveChat(currentChatId);
        setChatTitle(res.data.title);
        setSidebarOpen(false);
      } catch (err) {
        console.error('Failed to create chat:', err);
        setError(getErrorMessage(err, 'Failed to create a new chat.'));
        return;
      }
    }

    // Optimistic UI — add user message immediately
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      chat_id: currentChatId,
      role: 'user',
      content,
      mode,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setLoading(true);
    setError('');

    try {
      const res = await API.post(`/chats/${currentChatId}/messages`, {
        content,
        mode,
      });

      // API now returns { user_message, ai_message }
      const { user_message, ai_message } = res.data;

      // Replace temp message with real data and add AI response
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...filtered, user_message, ai_message];
      });

      // Refresh chat list for title updates
      loadChats();
    } catch (err) {
      console.error('Failed to send message:', err);
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
      setError(getErrorMessage(err, 'Failed to send your message.'));
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="chat-layout">
      <div
        className={`sidebar-backdrop ${sidebarOpen ? 'visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden={!sidebarOpen}
      />
      <ChatSidebar
        chats={chats}
        activeChat={activeChat}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onLogout={handleLogout}
        userEmail={user?.email}
        sidebarOpen={sidebarOpen}
        onCloseSidebar={() => setSidebarOpen(false)}
      />
      <ChatWindow
        messages={messages}
        mode={mode}
        onModeChange={setMode}
        onSendMessage={handleSendMessage}
        loading={loading}
        chatTitle={chatTitle}
        error={error}
        chatCount={chats.length}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
      />
    </div>
  );
}
