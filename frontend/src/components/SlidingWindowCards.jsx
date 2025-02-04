import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/SlidingWindowCards.css';

// Defining the SlidingWindowCards component and its props
const SlidingWindowCards = ({ segmentName, isDarkMode, setResult }) => {
    // Defining the state variables
    const [data, setData] = useState(null);
    const [homeTeamDetails, setHomeTeamDetails] = useState(null);
    const [awayTeamDetails, setAwayTeamDetails] = useState(null);
    const [awayTeamLogo, setAwayTeamLogo] = useState(null);
    const [homeTeamLogo, setHomeTeamLogo] = useState(null);
    const [error, setError] = useState(null);
    // Fetching the data using useEffect
    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetching the segment description
                const segmentResponse = await axios.post('https://backend-apps-297236485671.asia-east1.run.app/segment-description', { segmentName });
                const segmentData = segmentResponse.data;
                setData(segmentData);
                // Fetching the team details
                const homeTeamResponse = await axios.post('https://backend-apps-297236485671.asia-east1.run.app/team-details', { team_type: 'home', season: "2024" });
                var homeTeamData = homeTeamResponse.data;
                var players = homeTeamData.players;   
                var awayTeamResponse = await axios.post('https://backend-apps-297236485671.asia-east1.run.app/team-details', { team_type: 'away', season: "2024" });
                var awayTeamData = awayTeamResponse.data;
                for(const player of players){
                    if(player.person.id === segmentData.matchup.batter.id){
                        homeTeamData.batter = player.person.fullName;
                        awayTeamData.pitcher = segmentData.matchup.pitcher.fullName;
                        homeTeamData.id = player.person.id;
                        awayTeamData.id = segmentData.matchup.pitcher.id;
                        break;
                    }
                }
                if(homeTeamData.battter === undefined){
                    homeTeamData.pitcher = segmentData.matchup.pitcher.fullName;
                    awayTeamData.batter = segmentData.matchup.batter.fullName;
                    homeTeamData.id = segmentData.matchup.pitcher.id;
                    awayTeamData.id = segmentData.matchup.batter.id;
                }
                setHomeTeamDetails(homeTeamData);
                setAwayTeamDetails(awayTeamData);
                // Fetching the team logos
                const homeLogoResponse = await axios.post('https://backend-apps-297236485671.asia-east1.run.app/team-logo', { team_id: homeTeamData.team_id });
                setHomeTeamLogo(homeLogoResponse.data);
                const awayLogoResponse = await axios.post('https://backend-apps-297236485671.asia-east1.run.app/team-logo', { team_id: awayTeamData.team_id });
                setAwayTeamLogo(awayLogoResponse.data);
                // Setting the result state to pass the data to the parent component
                setResult({
                    homeScore: segmentData.result.homeScore,
                    awayScore: segmentData.result.awayScore,
                    balls: segmentData.count.balls,
                    outs: segmentData.count.outs,
                    strikes: segmentData.count.strikes,
                    venueName: homeTeamData.venue_name,
                    batterName: segmentData.matchup.batter.fullName,
                    pitcherName: segmentData.matchup.pitcher.fullName,
                });
            } catch (err) {
                setError(err);
            }
        };

        fetchData();
    }, [segmentName, setResult]);

    if (error) {
        return <div>Error: {error.message}</div>;
    }

    if (!data || !homeTeamDetails || !awayTeamDetails) {
        return <div>Loading...</div>;
    }
    // Destructuring the data object
    const { matchup } = data;
    const { result } = data;
    // const homeScore = result.homeScore;
    // const awayScore = result.awayScore;
    var homeType = null;
    var homePlayer = null;

    var awayType = null;
    var awayPlayer = null;

    if(homeTeamDetails.batter === undefined){
        homeType = 'Pitcher';
        awayType = 'Batter';
        homePlayer = homeTeamDetails.pitcher;
        awayPlayer = awayTeamDetails.batter;
    }else{
        homeType = 'Batter';
        awayType = 'Pitcher';
        homePlayer = homeTeamDetails.batter;
        awayPlayer = awayTeamDetails.pitcher;        
    }
    const batter = matchup.batter; //batter is the id of the batter
    const pitcher = matchup.pitcher; //pitcher is the id of the pitcher
    // Function to get the image URL
    const getImageUrl = (id) => {
        return `https://securea.mlb.com/mlb/images/players/head_shot/${id}.jpg`;
    };
    // Destructuring the team details
    const homeTeamName = homeTeamDetails.team_name;
    const awayTeamName = awayTeamDetails.team_name;

    return (
        <div className="sliding-window-cards">
            {/* Rendering the cards */}
            <div className="card">
                <img className="team-logo" src={homeTeamLogo} alt={`${homeTeamName} logo`} style={isDarkMode ? { filter: 'brightness(0) invert(1)' } : {}}/>
                <h5>{homeTeamName}</h5>
                <h4>{homeType}</h4>
                <img className="round-image" src={getImageUrl(homeTeamDetails.id)} alt="Batter" />
                <p className="name">{homePlayer}</p>
            </div>
            {/* Rendering the vs section */}
            <div className="vs">
                <p>vs</p>
            </div>
            {/* Rendering the cards */}
            <div className="card">
                <img className="team-logo" src={awayTeamLogo} alt={`${awayTeamName} logo`} style={isDarkMode ? { filter: 'brightness(0) invert(1)' } : {}} />
                <h5>{awayTeamName}</h5>
                <h4>{awayType}</h4>
                <img className="round-image" src={getImageUrl(awayTeamDetails.id)} alt="Pitcher" />
                <p className="name">{awayPlayer}</p>
            </div>
        </div>
    );
};

export default SlidingWindowCards;