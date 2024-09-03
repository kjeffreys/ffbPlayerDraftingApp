import React, { useState } from 'react';
import data from './data.json';
import PositionSelector from './PositionSelector';
import PlayerList from './PlayerList';
import './App.css';

function App()
{
  const [players, setPlayers] = useState(data);
  const [selectedPosition, setSelectedPosition] = useState('all');
  const [currentPick, setCurrentPick] = useState(1);
  const [sortByADP, setSortByADP] = useState(true); // state to toggle sorting by ADP or VOR

  const filteredPlayers = players.filter(player =>
  {
    if (selectedPosition === 'all') return true;
    if (selectedPosition === 'WR/RB') return player.position === 'WR' || player.position === 'RB';
    return player.position === selectedPosition;
  });

  const sortedPlayers = filteredPlayers.sort((a, b) => {
    if (sortByADP) {
      return a.adp - b.adp;
    } else {
      return b.VOR - a.VOR;
    }
  });

  const handlePick = (pickedPlayer) =>
  {
    setPlayers(players => players.filter(player => player.player_id !== pickedPlayer.player_id));
    setCurrentPick(currentPick + 1);
  };

  return (
    <div className="App">
      <h2>Current Draft Pick: {currentPick}</h2>
      <button onClick={() => setSortByADP(!sortByADP)}>
        Sort by {SsortByADP ? 'VOR' : 'ADP'}
      </button>
      <PositionSelector onChange={setSelectedPosition} />
      <PlayerList players={sortedPlayers} onPick={handlePick} />
    </div>
  );
}

export default App;
