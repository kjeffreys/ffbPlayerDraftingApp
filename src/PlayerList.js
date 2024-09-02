import React from 'react';

function PlayerList({ players, onPick })
{
    return (
        <ul>
            {[...players].sort((a, b) => a.adp - b.adp).map(player => (
                <li key={player.name} className={player.position}>
                    {player.name} - {player.team} (ADP: {player.adp}) (VoR: {player.VOR})
                    <button onClick={() => onPick(player)}>Pick</button>
                </li>
            ))}
        </ul>
    );
}

export default PlayerList;
