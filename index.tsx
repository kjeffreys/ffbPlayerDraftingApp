import React, { useState, useEffect, useMemo, useRef } from 'react';
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

/** Centralized metrics/config */
const METRICS = {
    stealDiscountPicks: 5,  // 💰 shows when currentPick - ADP ≥ 3
    windowPicks: 30,         // 🔥 lookahead horizon
    superiorityPct: 0.04,    // 🔥 must beat next-best position by ≥ 4%
    includeKAndDef: true,    // 🔥 include K/DEF in cross-position comparison
    topKPositions: 3,        // 🔥 flag up to 3 positions if each clearly leads
    minAbsDrop: 1.0,         // 🔥 require at least this absolute VOR drop
};

const CONSIDERED_POSITIONS: Player['position'][] =
    METRICS.includeKAndDef ? POSITIONS : (['QB', 'RB', 'WR', 'TE'] as const);

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

    // Search
    searchQuery: string; setSearchQuery: (v: string) => void;
    onSearchEnter: () => void; // draft first visible match
}> = ({
    sortBy, setSortBy,
    filterBy, setFilterBy,
    view, setView,
    resetDraft,
    currentPick,
    pickingFor, setPickingFor,
    searchQuery, setSearchQuery, onSearchEnter
}) =>
    {
        const filters: FilterByType[] = ['ALL', 'FLEX', ...POSITIONS];
        const btn = (active: boolean) => ({
            backgroundColor: active ? 'var(--color-accent)' : 'var(--color-surface)',
            color: 'var(--color-text-primary)',
        });

        // Keyboard: "/" to focus search globally
        const inputRef = useRef<HTMLInputElement | null>(null);
        useEffect(() =>
        {
            const onKey = (e: KeyboardEvent) =>
            {
                const target = e.target as HTMLElement | null;
                const isTyping = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || (target as any).isContentEditable);
                if (!isTyping && e.key === '/')
                {
                    e.preventDefault();
                    inputRef.current?.focus();
                }
            };
            window.addEventListener('keydown', onKey);
            return () => window.removeEventListener('keydown', onKey);
        }, []);

        // Touch detection (for showing a Draft button)
        const isTouch = typeof window !== 'undefined'
            && !!window.matchMedia
            && window.matchMedia('(hover: none) and (pointer: coarse)').matches;

        const placeholder = isTouch
            ? 'Search players… (tap Draft to pick)'
            : 'Quick search…  ( / to focus, Enter to draft )';

        return (
            <header style={{
                position: 'sticky', top: 0, zIndex: 50, // ← sticky header
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

                    {/* Quick search (tap anywhere in the bar to focus) */}
                    <div
                        onClick={() => inputRef.current?.focus()}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            minWidth: 280, flex: 1, maxWidth: 420,
                            background: 'var(--color-bg)',
                            border: '1px solid var(--color-border)',
                            padding: 6, borderRadius: 8,
                            cursor: 'text'
                        }}
                    >
                        <input
                            ref={inputRef}
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            onKeyDown={e =>
                            {
                                if (e.key === 'Enter') onSearchEnter();
                                if (e.key === 'Escape') setSearchQuery('');
                            }}
                            type="search"
                            inputMode="text"
                            enterKeyHint="go"
                            autoCorrect="off"
                            autoCapitalize="none"
                            spellCheck={false}
                            placeholder={placeholder}
                            aria-label="Search players"
                            style={{
                                flex: 1,
                                padding: '8px 8px',
                                border: 'none',
                                outline: 'none',
                                background: 'transparent',
                                color: 'var(--color-text-primary)'
                            }}
                        />
                        {searchQuery && (
                            <button
                                onClick={(e) => { e.stopPropagation(); setSearchQuery(''); }}
                                title="Clear"
                                style={{ background: 'var(--color-surface)', color: 'var(--color-text-primary)', padding: '6px 10px', borderRadius: 6 }}
                            >
                                ×
                            </button>
                        )}
                        {isTouch && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onSearchEnter(); }}
                                disabled={!searchQuery.trim()}
                                style={{ background: 'var(--color-accent)', color: 'var(--color-text-primary)', padding: '6px 10px', borderRadius: 6 }}
                            >
                                Draft
                            </button>
                        )}
                    </div>

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
    dangerDrop?: number | null;
    isSteal: boolean;
}> = ({ player, onDraft, isDanger, dangerDrop, isSteal }) =>
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div>
                            <div style={{ color: 'var(--color-text-secondary)' }}>VOR</div><div>{vor.toFixed(2)}</div>
                        </div>
                        {isDanger && (
                            <span
                                style={{ fontSize: '1.25rem', color: 'var(--color-danger)' }}
                                title={
                                    `Cross-position tier risk: ${position}. ` +
                                    `If you wait ~${METRICS.windowPicks} picks, est. VOR drop ≈ ${dangerDrop?.toFixed(2) ?? '—'} ` +
                                    `(must beat others by ≥ ${(METRICS.superiorityPct * 100).toFixed(0)}%).`
                                }
                            >
                                🔥
                            </span>
                        )}
                        {isSteal && <span style={{ fontSize: '1.25rem' }} title={`Steal vs ADP (≥ ${METRICS.stealDiscountPicks} picks)`}>💰</span>}
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
    // who drafted each player
    const [draftedBy, setDraftedBy] = useState<Record<number, Owner>>({});
    const [pickingFor, setPickingFor] = useState<Owner>('me');

    const [sortBy, setSortBy] = useState<SortByType>('adp');
    const [filterBy, setFilterBy] = useState<FilterByType>('ALL');
    const [view, setView] = useState<ViewType>('draft');

    // Search
    const [searchQuery, setSearchQuery] = useState('');

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
        setSearchQuery('');
    };

    const currentPick = Object.keys(draftedBy).length + 1;

    /* Remaining pool */
    const available = useMemo(
        () => allPlayers.filter(p => !(p.id in draftedBy)),
        [allPlayers, draftedBy]
    );

    /* Cross-position VOR danger map (windowed lookahead) */
    const { dangerMap, dropMap } = useMemo(() =>
    {
        const map = new Map<number, boolean>();
        const drops = new Map<number, number>(); // for tooltip

        if (!available.length) return { dangerMap: map, dropMap: drops };

        const cutoff = currentPick + METRICS.windowPicks;

        type PosStat = { pos: Player['position']; bestNowId: number; drop: number };
        const posStats: PosStat[] = [];

        CONSIDERED_POSITIONS.forEach(pos =>
        {
            const pool = available.filter(p => p.position === pos);
            if (!pool.length) return;

            // Best now by VOR
            const bestNow = pool.reduce((a, b) => (a.vor >= b.vor ? a : b));
            const bestNowVor = bestNow.vor;

            // Best later (after window) by VOR
            const laterPool = pool.filter(p => p.adp > cutoff);
            const bestLaterVor = laterPool.length
                ? laterPool.reduce((a, b) => (a.vor >= b.vor ? a : b)).vor
                : 0;

            const drop = Math.max(0, bestNowVor - bestLaterVor);
            posStats.push({ pos, bestNowId: bestNow.id, drop });
        });

        if (!posStats.length) return { dangerMap: map, dropMap: drops };

        // Sort positions by drop desc
        posStats.sort((a, b) => b.drop - a.drop);

        // Iteratively pick up to K positions where each is ≥ 5% greater than next-best and ≥ minAbsDrop
        const picked: PosStat[] = [];
        let pool = [...posStats];

        while (picked.length < METRICS.topKPositions && pool.length > 0)
        {
            const [candidate, ...rest] = pool;
            const restMax = rest.length ? Math.max(...rest.map(r => r.drop)) : 0;

            const meetsRelative = rest.length === 0
                ? candidate.drop >= METRICS.minAbsDrop
                : candidate.drop >= (1 + METRICS.superiorityPct) * restMax;

            const meetsAbsolute = candidate.drop >= METRICS.minAbsDrop;

            if (meetsRelative && meetsAbsolute)
            {
                picked.push(candidate);
                pool = rest;
            } else
            {
                break;
            }
        }

        picked.forEach(p =>
        {
            map.set(p.bestNowId, true);
            drops.set(p.bestNowId, p.drop);
        });

        return { dangerMap: map, dropMap: drops };
    }, [available, currentPick]);

    /* Filter + sort for UI, then apply search */
    const visiblePlayers = useMemo(() =>
    {
        const filtered = available.filter(p =>
        {
            if (filterBy === 'ALL') return true;
            if (filterBy === 'FLEX') return p.position === 'RB' || p.position === 'WR' || p.position === 'TE';
            return p.position === filterBy;
        });

        const sorted = filtered.sort((a, b) =>
            sortBy === 'adp' ? a.adp - b.adp : b.vor - a.vor
        );

        const q = searchQuery.trim().toLowerCase();
        if (!q) return sorted;

        return sorted.filter(p =>
            p.name.toLowerCase().includes(q) ||
            p.team.toLowerCase().includes(q) ||
            p.position.toLowerCase().includes(q)
        );
    }, [available, filterBy, sortBy, searchQuery]);

    // Enter (or mobile Draft button) drafts the first visible result and clears the query
    const draftFirstMatch = () =>
    {
        const first = visiblePlayers[0];
        if (first)
        {
            onDraft(first.id);
            setSearchQuery('');
        }
    };

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
                searchQuery={searchQuery} setSearchQuery={setSearchQuery}
                onSearchEnter={draftFirstMatch}
            />

            {view === 'draft' ? (
                <main style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {visiblePlayers.map(p => (
                        <PlayerCard
                            key={p.id}
                            player={p}
                            onDraft={onDraft}
                            isDanger={!!dangerMap.get(p.id)}
                            dangerDrop={dropMap.get(p.id) ?? null}
                            isSteal={currentPick - p.adp >= METRICS.stealDiscountPicks}
                        />
                    ))}
                    {!visiblePlayers.length && (
                        <div style={{ padding: 16, textAlign: 'center', color: 'var(--color-text-secondary)' }}>
                            No matching players.
                        </div>
                    )}
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
