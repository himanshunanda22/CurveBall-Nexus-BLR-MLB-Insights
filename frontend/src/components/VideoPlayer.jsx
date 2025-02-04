import React, { useEffect, useState, useCallback } from "react";
import { FaPlay, FaPause, FaFastBackward, FaExpand, FaCompress } from "react-icons/fa";
import '../styles/VideoPlayer.css';
// Defining the API_BASE_URL constant
const API_BASE_URL = "https://backend-apps-297236485671.asia-east1.run.app";
// Defining the VideoPlayer component and its props
const VideoPlayer = ({ videoRef, currentBuffer, currentSegmentIndex, setCurrentSegmentIndex, isPlaying, setIsPlaying, isTheaterMode, setIsTheaterMode, setVideoTime, segments, setCurrentBuffer }) => {
  const [isBuffering, setIsBuffering] = useState(true);
  // Manage the buffering state using useEffect
  useEffect(() => {
    const bufferTimeout = setTimeout(() => {
      setIsBuffering(false);
    }, 5000);

    return () => clearTimeout(bufferTimeout);
  }, []);
  // Function to handle playing or pausing the video
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
  // Function to handle rewinding the video
  const handleRewind = () => {
    const video = videoRef.current;
    if (video) {
      video.currentTime -= 10;
    }
  };
  // Function to load more segments
  const loadMoreSegments = useCallback(() => {
    const nextBufferStart = currentBuffer.length;
    const nextBuffer = segments.slice(nextBufferStart, nextBufferStart + 5);
    if (nextBuffer.length > 0) {
      setTimeout(() => {
        setCurrentBuffer((prevBuffer) => [...prevBuffer, ...nextBuffer]);
      }, 3000);
    }
  }, [currentBuffer, segments, setCurrentBuffer]);
  // Function to handle time update
  const handleTimeUpdate = useCallback(() => {
    const video = videoRef.current;
    if (video) {
      setVideoTime(video.currentTime);
    }
  }, [setVideoTime, videoRef]);
  // Function to handle the end of a segment
  const handleSegmentEnd = useCallback(() => {
    if (currentSegmentIndex < currentBuffer.length - 1) {
      setCurrentSegmentIndex((prevIndex) => prevIndex + 1);
    } else if (currentBuffer.length < segments.length) {
      loadMoreSegments();
    }
  }, [currentSegmentIndex, currentBuffer, segments, setCurrentSegmentIndex, loadMoreSegments]);
  // Manage the event listeners using useEffect
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
  }, [handleSegmentEnd, handleTimeUpdate, videoRef]);

  return (
    <div className={`video-section ${isTheaterMode ? "theater-mode" : ""}`}>
      {/* Buffering icon */}
      <div className="buffering-container" style={{ display: isBuffering ? "block" : "none" }}>
        <div className="buffering-icon"></div>
      </div>
      {/* Video player and controls */}
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
        {/* Video controls */}
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
            onClick={() => setIsTheaterMode(!isTheaterMode)}
            disabled={isBuffering}
            aria-label={isTheaterMode ? "Exit Theater Mode" : "Enter Theater Mode"}>
            {isTheaterMode ? <FaCompress /> : <FaExpand />}
          </button>
        </div>
      </div>
      {/* Loading video message */}
      {!currentBuffer[currentSegmentIndex] && <p>Loading video...</p>}
    </div>
  );
};

export default VideoPlayer;