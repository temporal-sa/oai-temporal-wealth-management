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
  let [isPolling, setIsPolling] = useState(false);

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
           await fetchChatHistory()
        } catch (error) {
          console.error('Error polling API:', error);
        }
      };

      // Call the function immediately on start
      pollApi();

      // Set up the interval to poll every 2 second (1000 milliseconds)
      intervalId = setInterval(pollApi, 2000);
    }

    // The cleanup function is crucial for preventing memory leaks
    // It runs when the component unmounts or when the dependencies change
    return () => {
      clearInterval(intervalId);
      console.log('Polling stopped.');
    };
  }, [isPolling]); // The effect re-runs whenever the isPolling state changes

  useEffect(() => {
    // Create a new EventSource instance
    const eventSource = new EventSource(`${API_BASE_URL}/sse/status/stream`);

    // Listen for 'message' events from the server
    eventSource.onmessage = (event) => {
      // The data is a string, so parse it
      console.log('SSE: The raw data is ', event.data)
      const newStatus = JSON.parse(event.data);
      console.log('SSE: The new status is ', newStatus);
      setStatusContent(newStatus.status);
    };

    // Listen for errors
    eventSource.onerror = (err) => {
      console.error('EventSource failed:', err);
      eventSource.close();
    };

    // Clean up the connection when the component unmounts
    return () => {
      eventSource.close();
    };
  }, []);

  const handleStartChat = async () => {
    try {
      let response;
      response = await fetch(`${API_BASE_URL}/start-workflow`, { method: 'POST' });
      if (response.ok) {
        const result = await response.json();
        const newSessionId = Math.random().toString(36).substring(2, 15);
        // check to see if it has truly been started
        if (result.message === 'Workflow started.') {
          setMessages([{text: 'Chat session started.', type: 'bot'}]);
          setIsChatActive(true);
        } else {
          // assume that the workflow is still running
          await fetchChatHistory();
          setIsChatActive(true);
        }
        setSessionId(newSessionId);
      } else {
        setMessages( [{text: `Bad/invalid response from API: ${response.status}`, type: 'bot'}]);
      }
    } catch (error) {
      console.error('Error starting chat session:', error);
      setMessages([{ text: 'Failed to start chat session.', type: 'bot' }]);
    }
  };


  const fetchChatHistory = async () => {
    // if (!sessionId) return;
    try {
      console.log("Getting ready to get the chat history...")
      const response = await fetch(`${API_BASE_URL}/get-chat-history`);
      const data = await response.json();
      if (data === null || data.length === 0) {
        return;
      }
      // console.log("data is ", data);
      // console.log("messages are ", messages)
      // console.log("len of messages is ", messages.length, " length of data is ", data.length);
      // data is an array of
      // { "user_prompt": "what the user typed", "text_response": "resulting text" }
      // We need to format it into our message structure.
      // which looks like this:
      // { text: 'Text goes here', type: 'either user or bot' }
      let headerArray = [{text: 'Previous history', type: 'bot'}];
      const formattedHistory = headerArray.concat(data.flatMap(item => [
            { text: item.user_prompt, type: 'user' },
            { text: item.text_response, type: 'bot' }
         ]));
      // console.log("formattedHistory is ", formattedHistory);
      if (messages.length < formattedHistory.length) {
         setMessages(formattedHistory);
      }
    } catch (error) {
      console.error('Error fetching chat history:', error);
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
    console.log("before sending the prompt, messages are ", messages);

    try {
      setIsPolling(false);
      const encodedInput = encodeURIComponent(input);
      const response = await fetch(`${API_BASE_URL}/send-prompt?prompt=${encodedInput}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      // const data =
      await response.json();
      setIsPolling(true);
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
      setIsPolling(false);
    } else {
      handleStartChat();
      setStatusContent('');
      // won't start polling until we send the first message
    }
  };

  const handleUpdateStatus = () => {
    // This is a mock function to simulate updating the status.
    // In a real application, this would be triggered by some background process.
    if (statusContent === '') {
      setStatusContent('This is a sample status message.');
    } else {
      setStatusContent('');
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

