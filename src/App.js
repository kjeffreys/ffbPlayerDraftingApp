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

  const filteredPlayers = players.filter(player =>
  {
    if (selectedPosition === 'all') return true;
    if (selectedPosition === 'WR/RB') return player.position === 'WR' || player.position === 'RB';
    return player.position === selectedPosition;
  });

  const handlePick = (pickedPlayer) =>
  {
    setPlayers(players => players.filter(player => player.name !== pickedPlayer.name));
    setCurrentPick(currentPick + 1);
  };

  return (
    <div className="App">
      <h2>Current Draft Pick: {currentPick}</h2>
      <PositionSelector onChange={setSelectedPosition} />
      <PlayerList players={filteredPlayers} onPick={handlePick} />
    </div>
  );
}

export default App;
