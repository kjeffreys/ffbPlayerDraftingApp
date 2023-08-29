import React from 'react';

function PlayerList({ players, onPick })
{
    return (
        <ul>
            {players.sort((a, b) => a.adp - b.adp).map(player => (
                <li key={player.name}>
                    {player.name} - {player.team} (ADP: {player.adp})
                    <button onClick={() => onPick(player)}>Pick</button>
                </li>
            ))}
        </ul>
    );
}

export default PlayerList;
