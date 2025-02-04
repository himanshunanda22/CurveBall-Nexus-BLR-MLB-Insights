// Chat.js
import React, { useState, useEffect, useRef } from "react";
import { FaMicrophone, FaPaperPlane, FaExpand, FaCompress } from "react-icons/fa";
import '../styles/Chat.css';
import ReactMarkdown from "react-markdown";
// Defining the Chat component and its props
const Chat = ({ chatMessages, isVideoPlaying, setChatMessages, isTyping, chatInput, setChatInput, isExpandMode, setIsExpandMode, isRecording, handleAudioInput, sendChatMessage }) => {
  // Defining the chatBodyRef and isBuffering state variables
  const chatBodyRef = useRef(null);
  const [isBuffering, setIsBuffering] = useState(true);
  // Manage the buffering state using useEffect
  useEffect(() => {
    const bufferTimeout = setTimeout(() => {
      setIsBuffering(false);
    }, 5000);

    return () => clearTimeout(bufferTimeout);
  }, []);
  // Manage the chatBodyRef using useEffect
  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [chatMessages]);
  // Function to handle sending a chat message
  const handleSendMessage =() => {
    sendChatMessage(chatInput);
  };

  return (
    <div className={`conversation-box ${isExpandMode ? "expand-mode" : ""}`}>
      <div className="conversation-header">
        <span>Nexus AI Assistant</span>
        <button onClick={() => setIsExpandMode(!isExpandMode)} disabled={isBuffering} className={`expand-button ${isExpandMode ? "expand-mode" : ""}`}>
          {isExpandMode ? <FaCompress /> : <FaExpand />}
        </button>
      </div>
      <div className={`conversation-body ${isExpandMode ? "expand-mode" : ""}`} ref={chatBodyRef}>
        {/* Mapping through the chatMessages array */}
        {chatMessages.map((message, index) => (
          <div
            key={index}
            className={`chat-message ${message.sender === "user" ? "user-message" : "agent-message"
              }`}>
            <ReactMarkdown>{message.text}</ReactMarkdown>
            {message.videoUrl && (
              <video
                controls
                width="300"
                src={message.videoUrl}
                onError={() => console.error("Error loading video")}
                className="small-video"
              />
            )}
          </div>
        ))}
        {(isTyping || isVideoPlaying) && (
          <div className="chat-message agent-message typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}
      </div>
      <div className="conversation-input">
        {/* Input field for chat messages */}
        <input
          type="text"
          value={chatInput}
          className="styled-input"
          onChange={(e) => setChatInput(e.target.value)}
          placeholder="Type your question..."
          disabled={isBuffering || isTyping || isVideoPlaying}
          aria-label="Chat input"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !isBuffering && chatInput.trim() !== "") {
              sendChatMessage();
            }
          }}
        />
        {/* Buttons for audio input and sending messages */}
        <button
          className={`audio ${isRecording ? "recording" : ""}`}
          onClick={handleAudioInput}
          disabled={isBuffering || isTyping || isVideoPlaying}
          aria-label={isRecording ? "Stop recording" : "Start recording"}>
          <FaMicrophone />
        </button>
        <button
          className="plane"
          onClick={handleSendMessage}
          disabled={isBuffering || chatInput.trim() === "" || isTyping || isVideoPlaying}
          aria-label="Send message">
          <FaPaperPlane />
        </button>
      </div>
    </div>
  );
};

export default Chat;