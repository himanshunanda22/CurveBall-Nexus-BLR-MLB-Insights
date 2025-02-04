import React, { useState, useEffect, useRef } from "react";
// import "../App.css";
import {
    FaMicrophone,
    FaPlay,
    FaMoon,
    FaSun,
    FaPause,
    FaPaperPlane,
    FaFastBackward,
    FaExpand,
    FaCompress,
    FaChartBar,
    FaCommentDots
} from "react-icons/fa";
import { io } from "socket.io-client";
import { Tooltip } from 'react-tooltip'
import ReactMarkdown from "react-markdown";
import SlidingWindowCards from './SlidingWindowCards';
import axios from 'axios';
 
const API_BASE_URL = "http://localhost:7770";
const socket = io("http://localhost:7770");
const VideoPage = () => {
    const [isDarkMode, setIsDarkMode] = useState(true);
    const [segments, setSegments] = useState([]);
    const [currentBuffer, setCurrentBuffer] = useState([]);
    const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);
    const [isRecording, setIsRecording] = useState(false);
    const [activeBox, setActiveBox] = useState("B1");
    const [isFlipped, setIsFlipped] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const videoRef = useRef(null);
    const [chatMessages, setChatMessages] = useState([
        { sender: "agent", text: "Hey, I am here to help you with the video. Ask me anything related to the strategies used in the game above." }
    ]);
    const [chatInput, setChatInput] = useState("");
    const [isBuffering, setIsBuffering] = useState(true);
    const recognitionRef = useRef(null);
    const chatBodyRef = useRef(null);
    const [isTheaterMode, setIsTheaterMode] = useState(false);
    const sideBoxRef = useRef(null);
    // eslint-disable-next-line
    const [videoTime, setVideoTime] = useState(0);
    const [playedSegments, setPlayedSegments] = useState([]);
    const [isExpandMode, setIsExpandMode] = useState(false);
    // eslint-disable-next-line
    const [commentary, setCommentary] = useState([]);
    const [result, setResult] = useState(null);
    const [analysis, setAnalysis] = useState(null);
 
    const saveQuery = (query) => {
        const video = videoRef.current;
        if (video) {
            const currentTime = video.currentTime;
            const elapsedTime = calculateElapsedTime(currentTime, currentSegmentIndex);
            const currentSegmentPath = currentBuffer[currentSegmentIndex];
            console.log(`Saved query: "${query}" at timestamp: ${elapsedTime} seconds and segment: ${currentBuffer[currentSegmentIndex]}`);
            const requestData = {
                query: query,
                video: currentSegmentPath,
                current_time: elapsedTime
            };
            const response =  axios.post(`${API_BASE_URL}/analyze`, requestData)
            console.log(response)
            
        }
    };
   
 
    const calculateElapsedTime = (currentTime, segmentIndex) => {
        const elapsedTime = segments.slice(0, segmentIndex).reduce((acc, segment) => acc + 30, 0) + currentTime;
        return elapsedTime;
    };
 
    const handleToggle = (button) => {  
        setIsFlipped(true);
        setTimeout(() => {
            setActiveBox((prev) => (prev === "B1" ? "B2" : "B1"));
            setIsFlipped(false);
        }, 500);
    };
 
    // const toggleExpandMode = () => {
    //     setIsExpandMode(!isExpandMode);
    // };
    const toggleExpandMode = () => {
        // const video = videoRef.current;
        // if (video) {
        //     if (isPlaying) {
        //         video.pause();
        //         setIsPlaying(false);
        //     } else {
        //         video.play();
        //         setIsPlaying(true);
        //     }
        // }
        setIsExpandMode(!isExpandMode);
    };
    useEffect(() => {
        socket.on("initial-segment", (data) => {
            const { currentSegmentIndex, currentSegments, currentVideoTime, isPlaying, playedSegments, currentSegmentName } = data;
            setCurrentSegmentIndex(currentSegmentIndex);
            setCurrentBuffer(currentSegments);
            setIsPlaying(isPlaying);
            setPlayedSegments(playedSegments);
 
            if (videoRef.current) {
                videoRef.current.currentTime = currentVideoTime;
                if (isPlaying) {
                    videoRef.current.play();
                }
 
                if (playedSegments && currentSegmentName) {
                    if (!playedSegments.includes(currentSegmentName)) {
                        videoRef.current.src = `${API_BASE_URL}/stream-segment?segmentName=${currentSegmentName}`
                    }
                }
            }
 
 
        })
        socket.on("video-event", (data) => {
            const video = videoRef.current;
            if (video) {
                console.log("event received", data);
                if (data.type === "play") {
                    video.play();
                    setIsPlaying(true);
                } else if (data.type === "pause") {
                    video.pause();
                    setIsPlaying(false);
                } else if (data.type === "rewind") {
                    video.currentTime = data.timestamp;
                    setVideoTime(data.timestamp);
                }
            }
        });
        socket.on("segment-change", (data) => {
            const { currentSegmentIndex, currentSegments, currentSegmentName } = data;
            setCurrentSegmentIndex(currentSegmentIndex);
            setCurrentBuffer(currentSegments);
            if (videoRef.current && currentSegmentName) {
                if (!playedSegments.includes(currentSegmentName)) {
                    videoRef.current.src = `${API_BASE_URL}/stream-segment?segmentName=${currentSegmentName}`
                }
            }
        })
 
        return () => {
            socket.off("initial-segment");
            socket.off("video-event");
            socket.off("segment-change");
        };
        // eslint-disable-next-line
    }, [socket]);
 
 
    const handleTimeUpdate = () => {
        const video = videoRef.current;
        if (video) {
            setVideoTime(video.currentTime);
        }
    };
 
 
    useEffect(() => {
        fetch(`${API_BASE_URL}/list-segments?baseName=baseball_segment`)
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
 
    useEffect(() => {
        const video = videoRef.current;
        if (video) {
            video.addEventListener("ended", handleSegmentEnd);
            video.addEventListener("timeupdate", handleTimeUpdate);
        }
        return () => {
            if (video) {
                video.removeEventListener("ended", handleSegmentEnd);
                video.removeEventListener("timeupdate", handleTimeUpdate);
            }
        };
        // eslint-disable-next-line
    }, [currentSegmentIndex, currentBuffer]);
 
    useEffect(() => {
        if ("webkitSpeechRecognition" in window) {
            const SpeechRecognition =
                window.SpeechRecognition || window.webkitSpeechRecognition;
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;
            recognitionRef.current.lang = "en-US";
 
            recognitionRef.current.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                const newMessage = { sender: "user", text: transcript };
                setChatMessages((prevMessages) => [...prevMessages, newMessage]);
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
    }, []);
 
    useEffect(() => {
        if (chatBodyRef.current) {
            chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
        }
    }, [chatMessages]);
 
    const toggleTheaterMode = () => {
        setIsTheaterMode(!isTheaterMode);
    };
 
 
    const handlePlayPause = () => {
        const video = videoRef.current;
        if (video) {
            if (isPlaying) {
                video.pause();
            } else {
                video.play();
            }
            setIsPlaying(!isPlaying);
        }
    };
 
    const handleSegmentEnd = () => {
        if (currentSegmentIndex < currentBuffer.length - 1) {
            setCurrentSegmentIndex((prevIndex) => prevIndex + 1);
        } else if (currentBuffer.length < segments.length) {
            loadMoreSegments();
        }
    };
 
    const loadMoreSegments = () => {
        const nextBufferStart = currentBuffer.length;
        const nextBuffer = segments.slice(nextBufferStart, nextBufferStart + 5);
        if (nextBuffer.length > 0) {
            setTimeout(() => {
                setCurrentBuffer((prevBuffer) => [...prevBuffer, ...nextBuffer]);
            }, 3000);
        }
    };
 
    const handleRewind = () => {
        const video = videoRef.current;
        if (video) {
            video.currentTime -= 10;
        }
    };
 
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
 
    useEffect(() => {
        const bufferTimeout = setTimeout(() => {
            setIsBuffering(false);
        }, 5000);
        return () => clearTimeout(bufferTimeout);
    }, []);
 
    const saveSegment = async (videoBlob) => {
        try {
            const base64Data = await blobToBase64(videoBlob);
            //   console.log("Base64 Data:", base64Data);
 
            const requestBody = {
                videoData: base64Data,
            };
            //   console.log("Request Body:", requestBody);
 
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
                return result
            } else {
                console.error('Error saving segment:', result);
                return {}
            }
        } catch (error) {
            console.error('Error during save request:', error);
            return {}
        }
    };
 
    // Helper function to convert Blob to Base64
    const blobToBase64 = (blob) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    };
 
    const sendChatMessage = () => {
        if (chatInput.trim()) {
            const newMessage = { sender: "user", text: chatInput };
            setChatMessages((prevMessages) => [...prevMessages, newMessage]);
            saveQuery(chatInput);
            if (chatInput.toLowerCase() === "record") {
                handleRecording();
            }
            setChatInput("");
            setTimeout(() => {
                const botReply = { sender: "agent", text: "I'm here to help! Let me know if you have questions about the game." };
                setChatMessages((prevMessages) => [...prevMessages, botReply]);
            }, 1000);
        }
    };
 
    const handleRecording = async () => {
        const video = videoRef.current;
        if (video) {
            const currentTime = video.currentTime;
            const segmentDuration = 10;
            const videoElement = document.createElement("video");
            videoElement.src = video.src;
            videoElement.crossOrigin = "anonymous";
 
            const stream = videoElement.captureStream();
            const mediaRecorder = new MediaRecorder(stream);
            let chunks = [];
            mediaRecorder.ondataavailable = (e) => {
                chunks.push(e.data);
            };
            mediaRecorder.onstop = async () => {
                const videoBlob = new Blob(chunks, { type: "video/mp4" });
                console.log("Captured videoBlob:", videoBlob.size, videoBlob.type);
 
                const saveMessage = await saveSegment(videoBlob);
                // console.log(".....................saveMessage...................", saveMessage)
                if (saveMessage) {
                    const latestVideoFile = await fetchLatestVideo();
                    // console.log("......................latestVideoFile.................", latestVideoFile)
                    if (latestVideoFile) {
                        const newMessage = {
                            sender: "agent",
                            text: "",
                            videoUrl: `${API_BASE_URL}/saved_segments/${latestVideoFile}`,
                        };
                        // console.log("...........newMessage.........", newMessage)
                        setChatMessages((prevMessages) => [...prevMessages, newMessage]);
                    }
                }
            };
            videoElement.currentTime = currentTime;
            videoElement.onseeked = () => {
                mediaRecorder.start();
                videoElement.play();
            };
            setTimeout(() => {
                mediaRecorder.stop();
                videoElement.pause();
            }, segmentDuration * 1000);
        }
    };
 
    // Function to fetch the latest saved video
    const fetchLatestVideo = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/get-latest-video`);
            if (response.ok) {
                const videoData = await response.json();
                console.log(videoData.latestVideoFile);
                return videoData.latestVideoFile;
            } else {
                console.error("Error fetching the latest video");
            }
        } catch (error) {
            console.error("Error fetching the latest video:", error);
        }
 
        return null;
    };
 
 
    const getTooltipId = () => {
        return activeBox === 'B1' ? 'statistics-tooltip' : 'commentary-tooltip';
    };
 
    const getTooltipContent = () => {
        return activeBox === 'B1' ? 'Click for Statistics' : 'Click for Commentary';
    };
   
 
    // const fetchMatchOverview = async () => {
    //     try {
    //         const response = await fetch(`${API_BASE_URL}/match-overview`);
    //         if (response.ok) {
    //             const data = await response.json();
    //             setAnalysis(data);
    //         } else {
    //             console.error("Error fetching match overview");
    //         }
    //     } catch (error) {
    //         console.error("Error fetching match overview:", error);
    //     }
    // };
   
    useEffect(() => {
        fetchMatchOverview();
    }, []);
    const fetchMatchOverview = async () => {
        try {
            const currentSegmentPath = currentBuffer[currentSegmentIndex];
    
            const requestData = {
                chunk_number: currentSegmentPath
            };
    
            const response = await fetch(`${API_BASE_URL}/match-overview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
    
            if (response.ok) {
                const data = await response.json();
                console.log(data)
                setAnalysis(data);
            } else {
                console.error("Error fetching match overview");
            }
        } catch (error) {
            console.error("Error fetching match overview:", error);
        }
    };
 
    return (
        <div className={`app-container ${isDarkMode ? "dark" : "light"}`}>
            <h5 className={`app-name ${isDarkMode ? "dark" : "light"}`}>Curveball Nexus BLR</h5>
            <button
                className="theme-toggle"
                onClick={() => setIsDarkMode(!isDarkMode)}
                aria-label={
                    isDarkMode ? "Switch to light mode" : "Switch to dark mode"
                }>
                {isDarkMode ? <FaSun /> : <FaMoon />}
            </button>
            <div className={`video-section ${isTheaterMode ? "theater-mode" : ""}`}>
                <div
                    className="buffering-container"
                    style={{ display: isBuffering ? "block" : "none" }}>
                    <div className="buffering-icon"></div>
                </div>
                <div className="video-and-button">
                    <video
                        ref={videoRef}
                        autoPlay={!isBuffering}
                        src={
                            currentBuffer[currentSegmentIndex]
                                ? `${API_BASE_URL}/stream-segment?segmentName=${currentBuffer[currentSegmentIndex]}`
                                : ""
                        }
                        key={currentBuffer[currentSegmentIndex]}
                        className="react-player"
                        onPlay={() => setIsPlaying(true)}
                        onPause={() => setIsPlaying(false)}
                    />
 
                    <div className="video-controls">
                        <button
                            className={`pause-play ${isTheaterMode ? "theater-mode" : ""}`}
                            onClick={handlePlayPause}
                            disabled={isBuffering}
                            aria-label={isPlaying ? "Pause" : "Play"}>
                            {isPlaying ? <FaPause /> : <FaPlay />}
                        </button>
                        <button
                            className={`rewind ${isTheaterMode ? "theater-mode" : ""}`}
                            onClick={handleRewind}
                            disabled={isBuffering}
                            aria-label="Rewind 10 seconds">
                            <FaFastBackward />
                        </button>
                        <button
                            className={`theater-toggle ${isTheaterMode ? "theater-mode" : ""}`}
                            onClick={toggleTheaterMode}
                            disabled={isBuffering}
                            aria-label={
                                isTheaterMode ? "Exit Theater Mode" : "Enter Theater Mode"
                            }>
                            {isTheaterMode ? <FaCompress /> : <FaExpand />}
                        </button>
                    </div>
                </div>
 
                {!currentBuffer[currentSegmentIndex] && <p>Loading video...</p>}
 
            </div>
            {activeBox && (
                <div
                    ref={sideBoxRef}
                    className={`side-box ${isDarkMode ? "dark" : "light"} ${isTheaterMode ? "theater-mode" : ""
                        } ${isFlipped ? "flipping" : ""}`}
                >
                    {!isFlipped && (
                        <div className="side-box-content">
                            <button
                                onClick={handleToggle}
                                aria-label="Toggle content"
                                className={`toggle-button ${isDarkMode ? 'dark' : 'light'}`}
                                disabled={isBuffering}
                                data-tooltip-id={getTooltipId()}
                            >
                                {activeBox === 'B1' ? <FaCommentDots /> : <FaChartBar />}
                            </button>
                            <Tooltip id={getTooltipId()} place="bottom-end" content={getTooltipContent()} />
                            {activeBox === 'B1' ? (
                                <div className="commentary-content">
                                    <h3>Commentary</h3>
                                    <div className="commentary-box">
                                        {commentary.map((comment, index) => (
                                            <p key={index}>{comment}</p>
                                        ))}
                                        {analysis && (
                                            <>
                                                <h4>Pattern Analysis</h4>
                                                <div>
                                                    <ReactMarkdown>{analysis.pattern_analysis.engagement_analysis}</ReactMarkdown>
                                                    <ReactMarkdown>{analysis.pattern_analysis.pattern_analysis}</ReactMarkdown>
                                                </div>
 
                                                <h4>Play Analysis</h4>
                                                <div>
                                                    <ReactMarkdown>{analysis.play_analysis.pitch_analysis}</ReactMarkdown>
                                                    <ReactMarkdown>{analysis.play_analysis.play_analysis}</ReactMarkdown>
                                                    <ReactMarkdown>{analysis.play_analysis.strategic_analysis}</ReactMarkdown>
                                                </div>
 
                                                <h4>Strategic Prediction</h4>
                                                <div>
                                                    <ReactMarkdown>{analysis.strategic_prediction.strategic_prediction}</ReactMarkdown>
                                                </div>
                                            </>
                                    )}
                                    </div>
                                </div>
                            ) : (
                                <div className="b2-content">
                                    <div className="section">
                                        {result && (
                                                <div>
                                                    <h2>Venue: {result.venueName}</h2>
                                                </div>
                                        )}
                                        <SlidingWindowCards segmentName={currentBuffer[currentSegmentIndex]} setResult={setResult} />
                                    </div>
                                    <div className="section">
                                        <h3>Score-Stats</h3>
                                        {result && (
                                            <div>
                                                <p>Balls: {result.balls}</p>
                                                <p>Outs: {result.outs}</p>
                                                <p>Strikes: {result.strikes}</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
 
 
            <div className={`conversation-box ${isExpandMode ? "expand-mode" : ""}`}>
                <div className="conversation-header">
                    <span>Agent Chat</span>
                    <button onClick={toggleExpandMode} disabled={isBuffering} className={`expand-button ${isExpandMode ? "expand-mode" : ""}`}>
                        {isExpandMode ? <FaCompress /> : <FaExpand />}
                    </button>
                </div>
                <div className={`conversation-body ${isExpandMode ? "expand-mode" : ""}`} ref={chatBodyRef}>
                    {chatMessages.map((message, index) => (
                        <div
                            key={index}
                            className={`chat-message ${message.sender === "user" ? "user-message" : "agent-message"
                                }`}>
                            {message.text}
                            {/* {console.log("Displaying video with URL:", message)} */}
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
                    <div className="chat-message agent-message typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
                <div className="conversation-input">
                    <input
                        type="text"
                        value={chatInput}
                        className="styled-input"
                        onChange={(e) => setChatInput(e.target.value)}
                        placeholder="Type your question..."
                        disabled={isBuffering}
                        aria-label="Chat input"
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !isBuffering && chatInput.trim() !== "") {
                                sendChatMessage();
                            }
                        }}
                    />
                    <button
                        className={`audio ${isRecording ? "recording" : ""}`}
                        onClick={handleAudioInput}
                        disabled={isBuffering}
                        aria-label={isRecording ? "Stop recording" : "Start recording"}>
                        <FaMicrophone />
                    </button>
                    <button
                        className="plane"
                        onClick={sendChatMessage}
                        disabled={isBuffering || chatInput.trim() === ""}
                        aria-label="Send message">
                        <FaPaperPlane />
                    </button>
                </div>
            </div>
 
        </div>
    );
};
 
export default VideoPage;