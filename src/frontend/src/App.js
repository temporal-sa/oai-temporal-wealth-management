import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { API_BASE_URL } from './config';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [isChatActive, setIsChatActive] = useState(false);
  const [statusContent, setStatusContent] = useState('');
  const chatWindowRef = useRef(null);
  const eventCountRef = useRef(0);
  let [isPolling, setIsPolling] = useState(false);
  const [isWaitingForAIResponse, setIsWaitingForAIResponse] = useState(false);
  const defaultHeaderText = 'Chat session started.';

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

    // This useEffect hook manages the polling logic.
  useEffect(() => {
    let intervalId;

    if (isPolling) {
      // Define the polling function
      const pollApi = async () => {
        try {
           await fetchChatHistory(defaultHeaderText)
        } catch (error) {
          console.error('Error polling API:', error);
        }
      };

      // Call the function immediately on start
      pollApi();

      // Set up the interval with dynamic frequency:
      // 2 seconds when waiting for AI response, 5 seconds when waiting for user input
      const pollingInterval = isWaitingForAIResponse ? 2000 : 5000;
      console.log(`Setting polling interval to ${pollingInterval}ms (waiting for AI: ${isWaitingForAIResponse})`);
      intervalId = setInterval(pollApi, pollingInterval);
    }

    // The cleanup function is crucial for preventing memory leaks
    // It runs when the component unmounts or when the dependencies change
    return () => {
      clearInterval(intervalId);
      console.log('Polling stopped.');
    };
  }, [isPolling, isWaitingForAIResponse]); // The effect re-runs whenever the isPolling or isWaitingForAIResponse state changes

  const handleStartChat = async () => {
    try {
      let response;
      response = await fetch(`${API_BASE_URL}/start-workflow`, { method: 'POST' });
      if (response.ok) {
        const result = await response.json();
        const newSessionId = Math.random().toString(36).substring(2, 15);
        // check to see if it has truly been started
        if (result.message === 'Workflow started.') {
          setMessages([{text: defaultHeaderText, type: 'bot'}]);
          setIsChatActive(true);
          eventCountRef.current = 0;
        } else {
          // assume that the workflow is still running
          await fetchChatHistory('Previous history');
          setIsChatActive(true);
        }
        setSessionId(newSessionId);
        setIsPolling(true); // Start polling immediately when chat becomes active
        setIsWaitingForAIResponse(false); // Start with slower polling until user sends a message
      } else {
        setMessages( [{text: `Bad/invalid response from API: ${response.status}`, type: 'bot'}]);
      }
    } catch (error) {
      console.error('Error starting chat session:', error);
      setMessages([{ text: 'Failed to start chat session.', type: 'bot' }]);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !sessionId) {
      console.log('either nothing to send or session Id is empty');
      return;
    }

    const userMessage = { text: input, type: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsWaitingForAIResponse(true); // Switch to faster polling (2s) while waiting for AI response
    console.log("before sending the prompt, messages are ", messages);

    try {
      const encodedInput = encodeURIComponent(input);
      const response = await fetch(`${API_BASE_URL}/send-prompt?prompt=${encodedInput}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      // const data =
      await response.json();
      // if (data.response && data.response.length > 0) {
      //   console.log("data coming back is ", data.response[0].text_response)
      //   // nothing to do
      //   // const botMessage = { text: data.response[0].text_response, type: 'bot' };
      //   // setMessages(prev => [...prev, botMessage]);
      // }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = { text: 'Failed to get response from bot.', type: 'bot' };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleEndChat = async () => {
    console.log("Session id is ", sessionId);
    if (!sessionId) {
      return;
    }
    try {
      await fetch(`${API_BASE_URL}/end-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setIsPolling(false);
      setIsWaitingForAIResponse(false); // Reset polling state
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
      setStatusContent('');
    }
  };

  const fetchChatHistory = async (headerText) => {
    const currentEventCount = eventCountRef.current;
    console.log("fetching chat history, event count is ", currentEventCount);

    let data = null;
    // if (!sessionId) return;
    try {
      const response = await fetch(`${API_BASE_URL}/get-chat-history?from_index=${currentEventCount}`);
      data = await response.json();
    } catch (error) {
      console.error('Error fetching chat history:', error);
      return;
    }

    if (data === null || data.length === 0) {
      return;
    }

    const newEventCount = currentEventCount + data.length;
    console.log(`Processing ${data.length} new events, eventCount: ${currentEventCount} -> ${newEventCount}`);
    
    eventCountRef.current = newEventCount;

    const newMessages = [];
    let receivedBotResponse = false;
    data.forEach(item => {
      switch (item.type) {
        case 'chat_interaction':
          newMessages.push(
            { text: item.content.user_prompt, type: 'user' },
            { text: item.content.text_response, type: 'bot' }
          );
          receivedBotResponse = true;
          break;
        case 'status_update':
          setStatusContent(item.content.status);
          break;
      }
    });
    
    if (receivedBotResponse) {
      setIsWaitingForAIResponse(false);
    }
    if (newMessages.length > 0) {
      setMessages(prev => {
        // Check if first new message is duplicate of last existing message
        if (prev.length > 0 && 
            newMessages[0].type === prev[prev.length - 1].type && 
            newMessages[0].text === prev[prev.length - 1].text) {
          // Skip the duplicate first message
          return [...prev, ...newMessages.slice(1)];
        }
        
        return [...prev, ...newMessages];
      });
    }
  };

  return (
    <div className="App">
      <div className="header">Wealth Management Chatbot</div>
      {statusContent && (
        <div className="status-area">
          {statusContent}
        </div>
      )}
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

