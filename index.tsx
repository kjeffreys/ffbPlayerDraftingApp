import React, { useState, useEffect, useMemo } from 'react';
import { createRoot } from 'react-dom/client';

/* ────────────────────
   TYPE DEFINITIONS
────────────────────── */
interface Player
{
    id: number;
    name: string;
    team: string;
    position: 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DEF';
    adp: number;
    vor: number;
    ppg: number;
    bye: number;
}

type SortByType = 'adp' | 'vor';
type FilterByType = 'ALL' | 'FLEX' | Player['position'];
type ViewType = 'draft' | 'byes';
type ByeWeekCounts = Record<number, Player[]>;
type Owner = 'me' | 'other';

/* ────────────────────
   DATA FETCH
────────────────────── */
async function fetchPlayers(): Promise<Player[]>
{
    const res = await fetch('./players.json');
    if (!res.ok) throw new Error('Failed to fetch players.json');
    return res.json();
}

/* ────────────────────
   CONSTANTS & UTILS
────────────────────── */
const POSITIONS: Player['position'][] = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
const getPositionColor = (pos: Player['position']) => `var(--pos-${pos.toLowerCase()})`;
const VOR_THRESHOLD = 10;

/* ────────────────────
   HEADER
────────────────────── */
const Header: React.FC<{
    sortBy: SortByType; setSortBy: (s: SortByType) => void;
    filterBy: FilterByType; setFilterBy: (f: FilterByType) => void;
    view: ViewType; setView: (v: ViewType) => void;
    resetDraft: () => void;
    currentPick: number;
    pickingFor: Owner; setPickingFor: (o: Owner) => void;
}> = ({
    sortBy, setSortBy,
    filterBy, setFilterBy,
    view, setView,
    resetDraft,
    currentPick,
    pickingFor, setPickingFor
}) =>
    {
        const filters: FilterByType[] = ['ALL', 'FLEX', ...POSITIONS];
        const btn = (active: boolean) => ({
            backgroundColor: active ? 'var(--color-accent)' : 'var(--color-surface)',
            color: 'var(--color-text-primary)',
        });

        return (
            <header style={{
                display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem',
                background: 'var(--color-surface)', borderRadius: 8
            }}>
                <div style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    flexWrap: 'wrap', gap: 16
                }}>
                    <h1 style={{ margin: 0, fontSize: '1.5rem' }}>
                        Fantasy Draft Assistant
                        <span style={{ fontSize: '1rem', fontWeight: 400, color: 'var(--color-text-secondary)', marginLeft: 8 }}>
                            · Pick #{currentPick}
                        </span>
                    </h1>

                    {/* Picking-for toggle */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ color: 'var(--color-text-secondary)' }}>Picking for:</span>
                        <div style={{ display: 'inline-flex', background: 'var(--color-bg)', padding: 2, borderRadius: 10 }}>
                            <button
                                style={{ ...btn(pickingFor === 'me'), padding: '6px 10px', borderRadius: 8 }}
                                onClick={() => setPickingFor('me')}
                            >
                                Me
                            </button>
                            <button
                                style={{ ...btn(pickingFor === 'other'), padding: '6px 10px', borderRadius: 8, marginLeft: 4 }}
                                onClick={() => setPickingFor('other')}
                            >
                                Other
                            </button>
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: 8 }}>
                        <button style={btn(view === 'draft')} onClick={() => setView('draft')}>Draft Board</button>
                        <button style={btn(view === 'byes')} onClick={() => setView('byes')}>Bye Weeks</button>
                        <button style={{ background: 'var(--color-danger)', color: 'var(--color-text-primary)' }}
                            onClick={resetDraft}>Reset Draft</button>
                    </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                        <span style={{ marginRight: 16, color: 'var(--color-text-secondary)' }}>Sort By:</span>
                        <button style={btn(sortBy === 'adp')} onClick={() => setSortBy('adp')}>ADP</button>
                        <button style={{ ...btn(sortBy === 'vor'), marginLeft: 8 }} onClick={() => setSortBy('vor')}>VOR</button>
                    </div>
                    <div>
                        <span style={{ marginRight: 16, color: 'var(--color-text-secondary)' }}>Filter:</span>
                        {filters.map(f => (
                            <button key={f} style={{ ...btn(filterBy === f), marginRight: 4 }} onClick={() => setFilterBy(f)}>{f}</button>
                        ))}
                    </div>
                </div>
            </header>
        );
    };

/* ────────────────────
   PLAYERCARD
────────────────────── */
const PlayerCard: React.FC<{
    player: Player;
    onDraft: (id: number) => void;
    isDanger: boolean;
    isSteal: boolean;
}> = ({ player, onDraft, isDanger, isSteal }) =>
    {
        const { name, team, position, bye, adp, vor, ppg } = player;

        return (
            <div style={{
                display: 'flex', alignItems: 'center', background: 'var(--color-surface)',
                padding: 16, borderRadius: 8, borderLeft: `5px solid ${getPositionColor(position)}`, gap: 16
            }}>
                <div style={{
                    flex: 1, display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit,minmax(100px,1fr))', gap: 16
                }}>
                    <div>
                        <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{name}</div>
                        <div style={{ color: 'var(--color-text-secondary)', fontSize: 14 }}>
                            {team} · {position} · Bye {bye}
                        </div>
                    </div>
                    <div>
                        <div style={{ color: 'var(--color-text-secondary)' }}>ADP</div><div>{adp}</div>
                    </div>
                    <div>
                        <div style={{ color: 'var(--color-text-secondary)' }}>PPG</div><div>{ppg.toFixed(2)}</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <div>
                            <div style={{ color: 'var(--color-text-secondary)' }}>VOR</div><div>{vor.toFixed(2)}</div>
                        </div>
                        {isDanger && <span style={{ fontSize: '1.25rem', color: 'var(--color-danger)' }} title={`VOR drop-off > ${VOR_THRESHOLD}`}>🔥</span>}
                        {isSteal && <span style={{ fontSize: '1.25rem' }} title='Steal vs ADP'>💰</span>}
                    </div>
                </div>

                <button style={{ background: 'var(--color-accent)', color: 'var(--color-text-primary)' }}
                    onClick={() => onDraft(player.id)}>Draft</button>
            </div>
        );
    };

/* ────────────────────
   BYE WEEK VIEW
────────────────────── */
const ByeWeekView: React.FC<{ byeCounts: ByeWeekCounts }> = ({ byeCounts }) =>
{
    const weeks = Object.keys(byeCounts).map(Number).sort((a, b) => a - b);
    if (!weeks.length)
        return <div style={{ textAlign: 'center', padding: 32, background: 'var(--color-surface)', borderRadius: 8 }}>
            No players drafted yet.
        </div>;

    return (
        <div style={{
            display: 'flex', flexDirection: 'column', gap: 16, padding: 16,
            background: 'var(--color-surface)', borderRadius: 8
        }}>
            <h2 style={{ margin: 0 }}>Drafted Player Bye Weeks</h2>
            {weeks.map(w => (
                <div key={w} style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 16 }}>
                    <h3 style={{ color: byeCounts[w].length > 2 ? 'var(--color-danger)' : 'var(--color-accent)' }}>
                        Week {w} ({byeCounts[w].length})
                    </h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {byeCounts[w].map(p => (
                            <div key={p.id} style={{
                                background: 'var(--color-bg)', padding: '4px 8px',
                                borderRadius: 4, fontSize: 14
                            }}>
                                <span style={{ color: getPositionColor(p.position) }}>●</span> {p.name} ({p.position})
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};

/* ────────────────────
   MAIN APP
────────────────────── */
const App: React.FC = () =>
{
    const [allPlayers, setAllPlayers] = useState<Player[]>([]);
    // NEW: who drafted each player
    const [draftedBy, setDraftedBy] = useState<Record<number, Owner>>({});
    const [pickingFor, setPickingFor] = useState<Owner>('me');

    const [sortBy, setSortBy] = useState<SortByType>('adp');
    const [filterBy, setFilterBy] = useState<FilterByType>('ALL');
    const [view, setView] = useState<ViewType>('draft');

    const [loading, setLoading] = useState(true);

    /* Fetch once */
    useEffect(() =>
    {
        fetchPlayers()
            .then(setAllPlayers)
            .finally(() => setLoading(false));
    }, []);

    /* Helpers */
    const onDraft = (id: number) =>
    {
        setDraftedBy(prev => ({ ...prev, [id]: pickingFor }));
        if (pickingFor === 'me') setPickingFor('other'); // auto-swap only after my pick
    };

    const resetDraft = () =>
    {
        setDraftedBy({});
        setPickingFor('me');
    };

    const currentPick = Object.keys(draftedBy).length + 1;

    /* Remaining pool */
    const available = useMemo(
        () => allPlayers.filter(p => !(p.id in draftedBy)),
        [allPlayers, draftedBy]
    );

    /* Build per-position VOR danger map */
    const dangerMap = useMemo(() =>
    {
        const map = new Map<number, boolean>();
        const VOR_DANGER_THRESHOLD = 2.0;

        POSITIONS.forEach(pos =>
        {
            const list = available
                .filter(p => p.position === pos)
                .sort((a, b) => b.vor - a.vor);

            for (let i = 0; i < list.length - 1; i++)
            {
                if (list[i].vor - list[i + 1].vor > VOR_DANGER_THRESHOLD)
                {
                    map.set(list[i].id, true);
                }
            }
        });

        return map;
    }, [available]);

    /* Filter + sort for UI */
    const visiblePlayers = useMemo(() =>
    {
        const filtered = available.filter(p =>
        {
            if (filterBy === 'ALL') return true;
            if (filterBy === 'FLEX') return p.position === 'RB' || p.position === 'WR' || p.position === 'TE';
            return p.position === filterBy;
        });

        return filtered.sort((a, b) =>
            sortBy === 'adp' ? a.adp - b.adp : b.vor - a.vor
        );
    }, [available, filterBy, sortBy]);

    /* Bye week counts – ONLY my players */
    const byeCounts = useMemo(() =>
    {
        const counts: ByeWeekCounts = {};
        allPlayers
            .filter(p => draftedBy[p.id] === 'me')
            .forEach(p =>
            {
                (counts[p.bye] = counts[p.bye] || []).push(p);
            });
        return counts;
    }, [draftedBy, allPlayers]);

    if (loading) return <div>Loading players...</div>;

    return (
        <>
            <Header
                sortBy={sortBy} setSortBy={setSortBy}
                filterBy={filterBy} setFilterBy={setFilterBy}
                view={view} setView={setView}
                resetDraft={resetDraft}
                currentPick={currentPick}
                pickingFor={pickingFor} setPickingFor={setPickingFor}
            />

            {view === 'draft' ? (
                <main style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {visiblePlayers.map(p => (
                        <PlayerCard
                            key={p.id}
                            player={p}
                            onDraft={onDraft}
                            isDanger={!!dangerMap.get(p.id)}
                            isSteal={currentPick - p.adp >= 20}
                        />
                    ))}
                </main>
            ) : (
                <ByeWeekView byeCounts={byeCounts} />
            )}
        </>
    );
};

/* ────────────────────
   BOOTSTRAP
────────────────────── */
const container = document.getElementById('root');
if (container)
{
    createRoot(container).render(<App />);
}
