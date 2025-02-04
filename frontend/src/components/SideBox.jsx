// SideBox.js
import React, { useState, useEffect } from "react";
import { FaCommentDots, FaChartBar } from "react-icons/fa";
import { Tooltip } from "react-tooltip";
import SlidingWindowCards from './SlidingWindowCards';
import ReactMarkdown from "react-markdown";
import "../styles/SideBox.css";

// Defining the SideBox component and its props
const SideBox = ({ isDarkMode, isTheaterMode, isFlipped, setIsFlipped, activeBox, setActiveBox, commentary, analysis, result, setResult, currentBuffer, currentSegmentIndex, current_game_context }) => {
  const [isBuffering, setIsBuffering] = useState(true);
  // Function to handle toggling the content
  const newSegName = currentBuffer[currentSegmentIndex] === undefined ? "segment_003.mp4" : currentBuffer[currentSegmentIndex];
  const handleToggle = () => {
    setIsFlipped(true);
    setTimeout(() => {
      setActiveBox((prev) => (prev === "B1" ? "B2" : "B1"));
      setIsFlipped(false);
    }, 500);
  };
  // Function to get the tooltip ID
  const getTooltipId = () => {
    return activeBox === 'B1' ? 'statistics-tooltip' : 'commentary-tooltip';
  };
  // Function to get the tooltip content
  const getTooltipContent = () => {
    return activeBox === 'B1' ? 'Click for Statistics' : 'Click for Commentary';
  };
  // Manage the buffering state using useEffect
  useEffect(() => {
    const bufferTimeout = setTimeout(() => {
      setIsBuffering(false);
    }, 5000);

    return () => clearTimeout(bufferTimeout);
  }, []);
  // Return the JSX for the SideBox component
 
  return (
    <div
      className={`side-box ${isDarkMode ? "dark" : "light"} ${isTheaterMode ? "theater-mode" : ""
        } ${isFlipped ? "flipping" : ""}`}>
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
          {/*Tooltip component*/}
          <Tooltip id={getTooltipId()} place="bottom-end" content={getTooltipContent()} />
          {/* Conditional rendering based on the active box */}
          {activeBox === 'B1' ? (
            <div className="commentary-content">
              
              <h4 className="headNote">Insights on {result && `${result.batterName} vs ${result.pitcherName}`}</h4>
              <div className="commentary-box">
                {commentary.map((comment, index) => (
                  <p key={index}>{comment}</p>
                ))}
                {/* Rendering the analysis section */}
                {analysis && (
                  <>
                    <div className="analysis-section">
                      <h4  className={isDarkMode ? "dark-mode" : "light-mode"}>Pattern Analysis</h4>
                      <div>
                        <ReactMarkdown className="vertical-spacing">{analysis.pattern_analysis.engagement_analysis}</ReactMarkdown>
                        <ReactMarkdown className="vertical-spacing">{analysis.pattern_analysis.pattern_analysis}</ReactMarkdown>
                      </div>
                    </div>
                    <div className="analysis-section">
                      <h4 className={isDarkMode ? "dark-mode" : "light-mode"}>Play Analysis</h4>
                      <div>
                        <ReactMarkdown className="vertical-spacing">{analysis.play_analysis.pitch_analysis}</ReactMarkdown>
                        <ReactMarkdown className="vertical-spacing">{analysis.play_analysis.play_analysis}</ReactMarkdown>
                        <ReactMarkdown className="vertical-spacing">{analysis.play_analysis.strategic_analysis}</ReactMarkdown>
                      </div>
                    </div>
                    <div className="analysis-section">
                      <h4  className={isDarkMode ? "dark-mode" : "light-mode"}>Strategic Prediction</h4>
                      <div>
                        <ReactMarkdown className="vertical-spacing">{analysis.strategic_prediction.strategic_prediction}</ReactMarkdown>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          ) : (
            // Conditional rendering for the B2 content
            <div className="b2-content">
              <div className="section">
                {result && (
                  <div>
                    <h2>Venue: {result.venueName}</h2>
                  </div>
                )}
                {/* Rendering the SlidingWindowCards component */}
                <SlidingWindowCards segmentName={newSegName} isDarkMode={isDarkMode} setResult={setResult} />
              </div>
              <div className="section">
                <h3>Previously on live stream</h3>
                <div className="analysis-section-2">
                  <ReactMarkdown className="vertical-spacing">{current_game_context?.current_context || "Loading Data...."}</ReactMarkdown>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SideBox;