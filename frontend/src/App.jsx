import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import VideoPlayer from "./components/VideoPlayer";
import SideBox from "./components/SideBox";
import Chat from "./components/Chat";
import Header from "./components/Header";
import axios from "axios";
// Defining the API_BASE_URL constant
const API_BASE_URL = "https://backend-apps-297236485671.asia-east1.run.app";
// Defining the App component
const App = () => {
  // Defining the state variables
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [segments, setSegments] = useState([]);
  const [currentBuffer, setCurrentBuffer] = useState([]);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeBox, setActiveBox] = useState("B2");
  const [isFlipped, setIsFlipped] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    { sender: "agent", text: "Hey, I am here to help you with the video. Ask me anything related to the strategies used in the game above." }
  ]);
  const [chatInput, setChatInput] = useState("");
  const recognitionRef = useRef(null);
  const videoRef = useRef(null);
  const [isTheaterMode, setIsTheaterMode] = useState(false);
  const [playedSegments, setPlayedSegments] = useState([]);
  const [isExpandMode, setIsExpandMode] = useState(false);
  const [commentary, setCommentary] = useState([]);
  const [result, setResult] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isBuffering, setIsBuffering] = useState(true);
  //eslint-disable-next-line
  const [videoTime, setVideoTime] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const [isVideoPlaying, setIsVideoPlaying] = useState(false); 
  const [current_game_context, setCurrentGameContext] = useState(null);
  useEffect(() => {
    document.body.className = isDarkMode ? 'dark' : 'light';
  }, [isDarkMode]);
  // Fetching the segments using useEffect
  useEffect(() => {
    fetch(`${API_BASE_URL}/list-segments`)
      .then((response) => response.json())
      .then((data) => {
        setSegments(data.segments);
        setCurrentBuffer(data.segments.slice(0, 5));
      })
      .catch((err) => {
        console.error("Error fetching segments:", err);
        alert("Failed to load video segments.");
      });
  }, []);
  // Function to save the query
  useEffect(() => {
    if ("webkitSpeechRecognition" in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = "en-US";

      recognitionRef.current.onresult = async (event) => {
        const transcript = event.results[0][0].transcript;
        setChatInput(transcript);
        await sendChatMessage(transcript, currentBuffer[currentSegmentIndex], calculateElapsedTime(currentSegmentIndex));
      };

      recognitionRef.current.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        setIsRecording(false);
        alert("Speech recognition failed. Please try again.");
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
    } else {
      alert("Speech recognition is not supported in this browser.");
    }
  }, [currentBuffer, currentSegmentIndex]);
  // Function to send a chat message
  const sendChatMessage =  async (input) => {
    const message = input || chatInput;
    if (message.trim()) {
      const newMessage = { sender: "user", text: message };
      setChatMessages((prevMessages) => [...prevMessages, newMessage]);
      setChatInput("");
      setIsTyping(true);
      // console.log("-----reached here in sendChatMessage-----");
      try {
        const answer =  await saveQuery(message);
        // console.log("Answer from sendchatmessage:", answer);
        if (answer.data.result) {
          const result = JSON.parse(answer.data.result);
          // console.log("Answer:", result);
          if (result.type === "realtime" && result.result.video) {
            const segmentName = result.result.video.split('/').pop();
            setIsVideoPlaying(true);
            handlePlay(segmentName);
            const agentResponse = { sender: "agent", text: result.result.response };
            setChatMessages((prevMessages) => [...prevMessages, agentResponse]);
          }else if(result.type === "historical"){
            const videoNames = result.result.citations.map(citation => 
              citation.split('/').pop().replace('.txt', '.mp4')
            );
            setIsVideoPlaying(true);
            // console.log("Video Names:", videoNames);
            const firstTwoVideos = videoNames.slice(0, 2);
            if(firstTwoVideos.length > 0){
              for (const video of firstTwoVideos) {
                handlePlay(video);
              }
            }else{
              setIsVideoPlaying(false);
            }
            const agentResponse = { sender: "agent", text: result.result.answer };
            setChatMessages((prevMessages) => [...prevMessages, agentResponse]);
          }else if(result.type === "search"){
            const agentResponse = { sender: "agent", text: result.result.answer };
            setChatMessages((prevMessages) => [...prevMessages, agentResponse]);
          }
        } else {
          const errorMessage = { sender: "agent", text: "Sorry, I couldn't process your query. Please try again." };
          setChatMessages((prevMessages) => [...prevMessages, errorMessage]);
        }
      } catch (error) {
        console.error("Error saving query:", error);
        const errorMessage = { sender: "agent", text: "An error occurred. Please try again later." };
        setChatMessages((prevMessages) => [...prevMessages, errorMessage]);
      } finally {
        setIsTyping(false);
      }
    }
  };
  // Function to save the query
  const saveQuery = async (query) => {
    const video = videoRef.current;
    if (video) {
      const elapsedTime = calculateElapsedTime(currentSegmentIndex);
      // console.log(`Saved query: "${query}" at timestamp: ${elapsedTime} seconds and segment: ${currentBuffer[currentSegmentIndex]}`);
      const requestBody = {
        query: query,
        video: currentBuffer[currentSegmentIndex],
        current_time: elapsedTime,
      };
      if (requestBody.video === undefined) {
        requestBody.video = "segment_003.mp4";
      }

      const response = await axios.post(`${API_BASE_URL}/analyze`, requestBody);
      // console.log("Response from server:", response);

      if (response.status === 200) {
        console.log("Query saved successfully");
      } else {
        console.error("Error saving query", error);
      }
      return response;
    }
    return { "response": "Try again later!😊" };
  };
  // Function to calculate the elapsed time
  const calculateElapsedTime = (segmentIndex) => {
    const segmentDuration = 30;
    const elapsedTime = (segmentIndex + 3) * segmentDuration;
    return elapsedTime;
  };
  // Function to handle playing the video
  const handlePlay = async (segmentName) => {
    const video = videoRef.current;
    if (video) {
      const segmentDuration = 20;
      video.src = `${API_BASE_URL}/stream-segment?segmentName=${segmentName}`;
      video.crossOrigin = "anonymous";

      const stream = video.captureStream();
      const mediaRecorder = new MediaRecorder(stream);
      let chunks = [];
      mediaRecorder.ondataavailable = (e) => {
        chunks.push(e.data);
      };
      mediaRecorder.onstop = async () => {
        const videoBlob = new Blob(chunks, { type: "video/mp4" });
        // console.log("Captured videoBlob:", videoBlob.size, videoBlob.type);

        const saveMessage = await saveSegment(videoBlob);
        if (saveMessage) {
          const latestVideoFile = await fetchLatestVideo();
          if (latestVideoFile) {
            const newMessage = {
              sender: "agent",
              text: "",
              videoUrl: `${API_BASE_URL}/saved_segments/${latestVideoFile}`,
            };
            setChatMessages((prevMessages) => [...prevMessages, newMessage]);
          }
        }
        setIsVideoPlaying(false);
      };

      video.onseeked = () => {
        mediaRecorder.start();
        video.play();
      };

      video.onloadedmetadata = () => {
        video.currentTime = 0;
      };

      setTimeout(() => {
        mediaRecorder.stop();
        video.pause();
      }, segmentDuration * 1000);
    }
  };
  // Function to save the segment
  const saveSegment = async (videoBlob) => {
    try {
      const base64Data = await blobToBase64(videoBlob);
      const requestBody = {
        videoData: base64Data,
      };
      const response = await fetch(`${API_BASE_URL}/save-segment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      const result = await response.json();
      if (response.ok) {
        console.log('Segment saved successfully:', result);
        return result;
      } else {
        console.error('Error saving segment:', result);
        return {};
      }
    } catch (error) {
      console.error('Error during save request:', error);
      return {};
    }
  };
  // Function to convert blob to base64
  const blobToBase64 = (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };
  
  const fetchLatestVideo = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/get-latest-video`);
      if (response.ok) {
        const videoData = await response.json();
        // console.log(videoData.latestVideoFile);
        return videoData.latestVideoFile;
      } else {
        console.error("Error fetching the latest video");
      }
    } catch (error) {
      console.error("Error fetching the latest video:", error);
    }

    return null;
  };
  // Function to handle audio input
  const handleAudioInput = () => {
    if (recognitionRef.current) {
      if (isRecording) {
        recognitionRef.current.stop();
      } else {
        setIsRecording(true);
        recognitionRef.current.start();
      }
    }
  };
  // Function to load more segments
  const fetchMatchOverview = async () => {
    try {
      const requestData = {
        chunk_number: currentBuffer[currentSegmentIndex]
      };
      if (requestData.chunk_number === undefined) {
        requestData.chunk_number = "segment_003.mp4";
      }

      const response = await axios.post(`${API_BASE_URL}/match-overview`, requestData);
      if (response.status === 200) {
        const data = await response.data;
        setAnalysis(data);
        setCurrentGameContext(data.current_game_context);
      } else {
        console.error("Error fetching match overview if response is not ok");
      }
    } catch (error) {
      console.error("Error fetching match overview catch block:", error);
    }
  };

  useEffect(() => {
    fetchMatchOverview();
  }, [currentSegmentIndex]);

  return (
    <div className={`app-container ${isDarkMode ? "dark" : "light"}`}>
      <Header isDarkMode={isDarkMode} setIsDarkMode={setIsDarkMode} />
      {/* Video player component */}
      <VideoPlayer
        videoRef={videoRef}
        currentBuffer={currentBuffer}
        currentSegmentIndex={currentSegmentIndex}
        setCurrentSegmentIndex={setCurrentSegmentIndex}
        isPlaying={isPlaying}
        setIsPlaying={setIsPlaying}
        isTheaterMode={isTheaterMode}
        setIsTheaterMode={setIsTheaterMode}
        segments={segments}
        setCurrentBuffer={setCurrentBuffer}
        isBuffering={isBuffering}
        setIsBuffering={setIsBuffering}
        setVideoTime={setVideoTime}
      />
      {/* SideBox component */}
      <SideBox
        isDarkMode={isDarkMode}
        isTheaterMode={isTheaterMode}
        isFlipped={isFlipped}
        setIsFlipped={setIsFlipped}
        activeBox={activeBox}
        setActiveBox={setActiveBox}
        commentary={commentary}
        analysis={analysis}
        result={result}
        setResult={setResult}
        currentBuffer={currentBuffer}
        currentSegmentIndex={currentSegmentIndex}
        isBuffering={isBuffering}
        setIsBuffering={setIsBuffering}
        current_game_context={current_game_context}
      />
      {/* Chat component */}
      <Chat
        chatMessages={chatMessages}
        setChatMessages={setChatMessages}
        chatInput={chatInput}
        setChatInput={setChatInput}
        isExpandMode={isExpandMode}
        setIsExpandMode={setIsExpandMode}
        isRecording={isRecording}
        handleAudioInput={handleAudioInput}
        sendChatMessage={sendChatMessage}
        isTyping={isTyping}
        isVideoPlaying={isVideoPlaying}
      />
    </div>
  );
};

export default App;