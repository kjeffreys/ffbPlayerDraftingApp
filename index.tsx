import React, { useState, useEffect, useMemo } from 'react';
import { createRoot } from 'react-dom/client';

// --- TYPE DEFINITIONS ---
interface Player
{
    id: number;
    name: string;
    team: string;
    position: 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DEF';
    adp: number;
    vor: number;
    bye: number;
}
type SortByType = 'adp' | 'vor';
type FilterByType = 'ALL' | 'FLEX' | Player['position'];
type ViewType = 'draft' | 'byes';
type ByeWeekCounts = Record<number, Player[]>;

// --- MOCK API CALL ---
async function fetchPlayers(): Promise<Player[]>
{
    const response = await fetch('./players.json');
    if (!response.ok)
    {
        throw new Error('Network response was not ok');
    }
    return response.json();
}

// --- UTILITY & HELPER FUNCTIONS ---
const POSITIONS: Player['position'][] = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];

const getPositionColor = (pos: Player['position']) => `var(--pos-${pos.toLowerCase()})`;

// --- REACT COMPONENTS ---

const Header: React.FC<{
    sortBy: SortByType;
    setSortBy: (s: SortByType) => void;
    filterBy: FilterByType;
    setFilterBy: (f: FilterByType) => void;
    view: ViewType;
    setView: (v: ViewType) => void;
    resetDraft: () => void;
}> = ({ sortBy, setSortBy, filterBy, setFilterBy, view, setView, resetDraft }) =>
{
    const filters: FilterByType[] = ['ALL', 'FLEX', 'QB', 'RB', 'WR', 'TE', 'K', 'DEF'];

    const buttonStyle = (active: boolean) => ({
        backgroundColor: active ? 'var(--color-accent)' : 'var(--color-surface)',
        color: 'var(--color-text-primary)',
    });

    return (
        <header style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem', backgroundColor: 'var(--color-surface)', borderRadius: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Fantasy Draft Assistant</h1>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={() => setView('draft')} style={buttonStyle(view === 'draft')}>Draft Board</button>
                    <button onClick={() => setView('byes')} style={buttonStyle(view === 'byes')}>Bye Weeks</button>
                    <button onClick={resetDraft} style={{ backgroundColor: 'var(--color-danger)', color: 'var(--color-text-primary)' }}>Reset Draft</button>
                </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div>
                    <span style={{ marginRight: '1rem', color: 'var(--color-text-secondary)' }}>Sort By:</span>
                    <button onClick={() => setSortBy('adp')} style={buttonStyle(sortBy === 'adp')}>ADP</button>
                    <button onClick={() => setSortBy('vor')} style={{ ...buttonStyle(sortBy === 'vor'), marginLeft: '0.5rem' }}>VOR</button>
                </div>
                <div>
                    <span style={{ marginRight: '1rem', color: 'var(--color-text-secondary)' }}>Filter:</span>
                    <div style={{ display: 'inline-flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {filters.map(f => (
                            <button key={f} onClick={() => setFilterBy(f)} style={buttonStyle(filterBy === f)}>{f}</button>
                        ))}
                    </div>
                </div>
            </div>
        </header>
    );
};

const PlayerCard: React.FC<{
    player: Player;
    onDraft: (id: number) => void;
    isDanger: boolean;
    sortBy: SortByType;
}> = ({ player, onDraft, isDanger, sortBy }) =>
{
    const { name, team, position, bye, adp, vor } = player;

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: 'var(--color-surface)',
            padding: '1rem',
            borderRadius: '0.5rem',
            borderLeft: `5px solid ${getPositionColor(position)}`,
            gap: '1rem',
            transition: 'background-color 0.2s',
        }}>
            <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem' }}>
                <div>
                    <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{name}</div>
                    <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>{`${team} · ${position} · Bye ${bye}`}</div>
                </div>
                <div style={{ fontWeight: sortBy === 'adp' ? 700 : 400, color: sortBy === 'adp' ? 'var(--color-accent)' : 'inherit' }}>
                    <div>ADP</div>
                    <div>{adp}</div>
                </div>
                <div style={{ fontWeight: sortBy === 'vor' ? 700 : 400, color: sortBy === 'vor' ? 'var(--color-accent)' : 'inherit', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div>
                        <div>VOR</div>
                        <div>{vor}</div>
                    </div>
                    {isDanger && (
                        <span title="Positional Scarcity Warning: Significant VOR drop-off to the next player at this position." style={{ color: 'var(--color-danger)', fontSize: '1.5rem' }}>🔥</span>
                    )}
                </div>
            </div>
            <button onClick={() => onDraft(player.id)} style={{ backgroundColor: 'var(--color-accent)', color: 'var(--color-text-primary)', whiteSpace: 'nowrap' }}>Draft</button>
        </div>
    );
};

const ByeWeekView: React.FC<{ byeCounts: ByeWeekCounts }> = ({ byeCounts }) =>
{
    const sortedWeeks = Object.keys(byeCounts).map(Number).sort((a, b) => a - b);

    if (sortedWeeks.length === 0)
    {
        return <div style={{ textAlign: 'center', padding: '2rem', backgroundColor: 'var(--color-surface)', borderRadius: '0.5rem' }}>No players drafted yet.</div>;
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem', backgroundColor: 'var(--color-surface)', borderRadius: '0.5rem' }}>
            <h2 style={{ marginTop: 0 }}>Drafted Player Bye Weeks</h2>
            {sortedWeeks.map(week => (
                <div key={week} style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '1rem' }}>
                    <h3 style={{ color: byeCounts[week].length > 2 ? 'var(--color-danger)' : 'var(--color-accent)' }}>Week {week} ({byeCounts[week].length} Players)</h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                        {byeCounts[week].map(p => (
                            <div key={p.id} style={{ backgroundColor: 'var(--color-bg)', padding: '0.5rem', borderRadius: '0.25rem', fontSize: '0.9rem' }}>
                                <span style={{ color: getPositionColor(p.position), marginRight: '0.5rem' }}>●</span>
                                {p.name} ({p.position})
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};


const App: React.FC = () =>
{
    const [allPlayers, setAllPlayers] = useState<Player[]>([]);
    const [draftedPlayerIds, setDraftedPlayerIds] = useState<Set<number>>(new Set());
    const [sortBy, setSortBy] = useState<SortByType>('adp');
    const [filterBy, setFilterBy] = useState<FilterByType>('ALL');
    const [view, setView] = useState<ViewType>('draft');
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() =>
    {
        fetchPlayers()
            .then(data =>
            {
                setAllPlayers(data);
                setIsLoading(false);
            })
            .catch(error =>
            {
                console.error("Failed to fetch players:", error);
                setIsLoading(false);
            });
    }, []);

    const handleDraftPlayer = (id: number) =>
    {
        setDraftedPlayerIds(prev => new Set(prev).add(id));
    };

    const handleResetDraft = () =>
    {
        setDraftedPlayerIds(new Set());
    };

    const availablePlayers = useMemo(() =>
    {
        return allPlayers.filter(p => !draftedPlayerIds.has(p.id));
    }, [allPlayers, draftedPlayerIds]);

    const filteredAndSortedPlayers = useMemo(() =>
    {
        const filtered = availablePlayers.filter(p =>
        {
            if (filterBy === 'ALL') return true;
            if (filterBy === 'FLEX') return p.position === 'RB' || p.position === 'WR';
            return p.position === filterBy;
        });
        const compare = {
            adp: (a: Player, b: Player) => a.adp - b.adp,  // ascending
            vor: (a: Player, b: Player) => b.vor - a.vor   // descending
        };

        return filtered.sort(compare[sortBy]);
    }, [availablePlayers, filterBy, sortBy]);

    const checkPositionalScarcity = useMemo(() =>
    {
        const playerScarcityMap = new Map<number, boolean>();

        // Pre-calculate VOR drop-offs for all positions from their best available player
        const baseDropoffs: Record<string, number> = {};
        for (const pos of POSITIONS)
        {
            const playersInPos = availablePlayers.filter(p => p.position === pos).sort((a, b) => b.vor - a.vor);
            if (playersInPos.length > 1)
            {
                baseDropoffs[pos] = playersInPos[0].vor - playersInPos[1].vor;
            } else
            {
                baseDropoffs[pos] = 0;
            }
        }

        const sortedByADP = [...availablePlayers].sort((a, b) => a.adp - b.adp);

        sortedByADP.forEach((player, index) =>
        {
            const window = sortedByADP.slice(index + 1, index + 31);
            const nextPlayerInPosition = window.find(p => p.position === player.position);

            if (!nextPlayerInPosition)
            {
                playerScarcityMap.set(player.id, false);
                return;
            }

            const targetDropoff = player.vor - nextPlayerInPosition.vor;

            const otherPositionDropoffs = POSITIONS
                .filter(p => p !== player.position)
                .map(p => baseDropoffs[p] ?? 0);

            const maxOtherDropoff = Math.max(...otherPositionDropoffs, 0);

            if (targetDropoff > maxOtherDropoff * 1.05 && targetDropoff > 0)
            {
                playerScarcityMap.set(player.id, true);
            } else
            {
                playerScarcityMap.set(player.id, false);
            }
        });

        return playerScarcityMap;
    }, [availablePlayers]);

    const byeWeekCounts = useMemo(() =>
    {
        const counts: ByeWeekCounts = {};
        const draftedPlayers = allPlayers.filter(p => draftedPlayerIds.has(p.id));
        draftedPlayers.forEach(player =>
        {
            if (!counts[player.bye])
            {
                counts[player.bye] = [];
            }
            counts[player.bye].push(player);
        });
        return counts;
    }, [draftedPlayerIds, allPlayers]);

    if (isLoading)
    {
        return <div>Loading players...</div>;
    }

    return (
        <>
            <Header
                sortBy={sortBy} setSortBy={setSortBy}
                filterBy={filterBy} setFilterBy={setFilterBy}
                view={view} setView={setView}
                resetDraft={handleResetDraft}
            />
            {view === 'draft' ? (
                <main style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {filteredAndSortedPlayers.map(player => (
                        <PlayerCard
                            key={player.id}
                            player={player}
                            onDraft={handleDraftPlayer}
                            isDanger={checkPositionalScarcity.get(player.id) || false}
                            sortBy={sortBy}
                        />
                    ))}
                </main>
            ) : (
                <ByeWeekView byeCounts={byeWeekCounts} />
            )}
        </>
    );
};

const container = document.getElementById('root');
if (container)
{
    const root = createRoot(container);
    root.render(<App />);
}
