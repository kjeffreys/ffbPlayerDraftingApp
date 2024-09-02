import React from 'react';

function PositionSelector({ onChange })
{
    return (
        <select onChange={(e) => onChange(e.target.value)}>
            <option value="all">All</option>
            <option value="QB">QB</option>
            <option value="RB">RB</option>
            <option value="WR">WR</option>
            <option value="TE">TE</option>
            <option value="WR/RB">WR/RB</option>
            <option value="K">K</option>
            <option value="DST">DEF</option>
        </select>
    );
}

export default PositionSelector;
