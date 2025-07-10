import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { API_BASE_URL } from './config';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [isChatActive, setIsChatActive] = useState(false);
  const chatWindowRef = useRef(null);

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  const handleStartChat = async () => {
    try {
      await fetch(`${API_BASE_URL}/start-workflow`, { method: 'POST' });
      const newSessionId = Math.random().toString(36).substring(2, 15);
      setSessionId(newSessionId);
      setMessages([{ text: 'Chat session started.', type: 'bot' }]);
      setIsChatActive(true);
    } catch (error) {
      console.error('Error starting chat session:', error);
      setMessages([{ text: 'Failed to start chat session.', type: 'bot' }]);
    }
  };

  // Commented out as it is not currently being used
  // const fetchChatHistory = async () => {
  //   if (!sessionId) return;
  //   try {
  //     const response = await fetch(`${API_BASE_URL}/get-chat-history?session_id=${sessionId}`);
  //     const data = await response.json();
  //     // Assuming the history is a list of strings.
  //     // We need to format it into our message structure.
  //     const formattedHistory = data.history.map((msg, index) => ({
  //       text: msg,
  //       type: index % 2 === 0 ? 'user' : 'bot' // This is a guess, adjust if needed
  //     }));
  //     setMessages(formattedHistory);
  //   } catch (error) {
  //     console.error('Error fetching chat history:', error);
  //   }
  // };


  const handleSend = async () => {
    if (!input.trim() || !sessionId) {
      console.log('either nothing to send or session Id is empty');
      return;
    }

    const userMessage = { text: input, type: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      const encodedInput = encodeURIComponent(input);
      const response = await fetch(`${API_BASE_URL}/send-prompt?prompt=${encodedInput}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();
      if (data.response && data.response.length > 0) {
        const botMessage = { text: data.response[0].text_response, type: 'bot' };
        setMessages(prev => [...prev, botMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = { text: 'Failed to get response from bot.', type: 'bot' };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleEndChat = async () => {
    if (!sessionId) {
      return;
    }
    try {
      await fetch(`${API_BASE_URL}/end-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setMessages(prev => [...prev, { text: 'Chat session ended.', type: 'bot' }]);
      setSessionId(null);
      setIsChatActive(false);
    } catch (error) {
        console.error('Error ending chat session:', error);
    }
  };

  const handleToggleChatState = () => {
    if (isChatActive) {
      handleEndChat();
    } else {
      handleStartChat();
    }
  };

  return (
    <div className="App">
      <div className="header">Wealth Management Chatbot</div>
      <div className="chat-window" ref={chatWindowRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.type}`}>
            {msg.text.split('\n').map((line, i) => (
              <span key={i}>
                {line}
                <br />
              </span>
            ))}
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type a message..."
          disabled={!isChatActive}
        />
        <button onClick={handleSend} disabled={!isChatActive}>Send</button>
      </div>
      <button
        onClick={handleToggleChatState}
        className={`end-chat-button ${!isChatActive ? 'start-chat-button' : ''}`}
      >
        {isChatActive ? 'End Chat' : 'Start Chat'}
      </button>
    </div>
  );
}

export default App;
