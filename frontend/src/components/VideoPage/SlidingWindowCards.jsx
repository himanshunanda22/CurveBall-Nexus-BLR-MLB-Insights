import React, { useState, useEffect } from 'react';
import axios from 'axios';
 
 
const SlidingWindowCards = ({ segmentName, setResult }) => {
    const [data, setData] = useState(null);
    const [homeTeamDetails, setHomeTeamDetails] = useState(null);
    const [awayTeamDetails, setAwayTeamDetails] = useState(null);
    const [error, setError] = useState(null);
 
    useEffect(() => {
        const fetchData = async () => {
            try {
                const segmentResponse = await axios.post('http://localhost:7770/segment-description', { segmentName });
                const segmentData = segmentResponse.data;
                setData(segmentData);
                const homeTeamResponse = await axios.post('http://localhost:7770/team-details', { team_type: 'home' ,season:2024});
                const homeTeamData = homeTeamResponse.data;
                setHomeTeamDetails(homeTeamData);
                const awayTeamResponse = await axios.post('http://localhost:7770/team-details', { team_type: 'away',season: 2024 });
                const awayTeamData = awayTeamResponse.data;
                setAwayTeamDetails(awayTeamData);
                setResult({
                    homeScore: segmentData.result.homeScore,
                    awayScore: segmentData.result.awayScore,
                    balls: segmentData.count.balls,
                    outs: segmentData.count.outs,
                    strikes: segmentData.count.strikes,
                    venueName: homeTeamData.venue_name
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
   
    const { matchup } = data;
    const { result } = data;
    const homeScore = result.homeScore;
    const awayScore = result.awayScore;
    const batter = matchup.batter;
    const pitcher = matchup.pitcher;
 
    const getImageUrl = (id) => {
        return `https://securea.mlb.com/mlb/images/players/head_shot/${id}.jpg`;
    };
 
    const homeTeamName = homeTeamDetails.team_name;
    const awayTeamName = awayTeamDetails.team_name;
 
    return (
        <div className="sliding-window-cards">
            <div className="card">
                <h4>{homeTeamName}</h4>
                <h4>Batter</h4>
                <img className="round-image" src={getImageUrl(batter.id)} alt="Batter" />
                <p className="name">{batter.fullName}</p>
                <p>Score: {homeScore}</p>
            </div>
            <div className="vs">
                <p>vs</p>
            </div>
            <div className="card">
                <h4>{awayTeamName}</h4>
                <h4>Pitcher</h4>
                <img className="round-image" src={getImageUrl(pitcher.id)} alt="Pitcher" />
                <p className="name">{pitcher.fullName}</p>
                <p>Score: {awayScore}</p>
            </div>
        </div>
    );
};
 
export default SlidingWindowCards;
