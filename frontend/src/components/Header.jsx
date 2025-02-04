// Header.js
import React from "react";
import { FaMoon, FaSun } from "react-icons/fa";
import "../styles/Header.css";
// Defining the Header component and its props
const Header = ({ isDarkMode, setIsDarkMode }) => {
  //  Return the JSX for the Header component
  return (
    <div className="header">
      <h5 className={`app-name ${isDarkMode ? "dark" : "light"}`}>Curveball Nexus</h5>
      <button
        className="theme-toggle"
        onClick={() => setIsDarkMode(!isDarkMode)}
        aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}>
        {isDarkMode ? <FaSun /> : <FaMoon />}
      </button>
    </div>
  );
};

export default Header;