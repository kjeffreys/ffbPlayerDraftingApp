import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';

type Position = 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DEF';
type RosterSlot = Position | 'FLEX' | 'SUPERFLEX';
type Owner = 'me' | 'other';
type ViewType = 'classic' | 'cockpit' | 'board' | 'byes' | 'picks';
type SortByType = 'recommendation' | 'adp' | 'vor';
type FilterByType = 'ALL' | 'FLEX' | Position;
type Concern = 'injury' | 'role' | 'legal' | 'playoff' | 'bye' | 'fade';

interface Player {
    id: number;
    name: string;
    team: string;
    position: Position;
    adp: number;
    vor: number;
    ppg: number;
    bye: number;
    redraftEcr?: number | null;
    superflexEcr?: number | null;
    dynastyEcr?: number | null;
}

interface LeagueProfile {
    id: string;
    label: string;
    file: string;
    teams: number;
    mode: 'redraft' | 'guillotine' | 'champions';
    roster: Record<Position, number>;
    lineup?: Partial<Record<RosterSlot, number>>;
    notes: string;
    publicNotes: string;
}

interface DraftPick {
    playerId: number;
    owner: Owner;
    manager: string;
    pick: number;
    at: string;
}

interface PlayerAdjustment {
    avoid?: boolean;
    manual?: number;
    concerns?: Concern[];
}

interface DraftSession {
    drafted: DraftPick[];
    undone: DraftPick[];
    adjustments: Record<string, PlayerAdjustment>;
    pickingFor: Owner;
    currentManager: string;
    view: ViewType;
    sortBy: SortByType;
    filterBy: FilterByType;
    showTop10: boolean;
}

interface ScoreComponents {
    vor: number;
    adpValue: number;
    tierDropoff: number;
    availabilityNextPick: number;
    rosterFit: number;
    byeRisk: number;
    historyAdjustment: number;
    manualAdjustment: number;
    concernPenalty: number;
}

interface Recommendation {
    player: Player;
    totalScore: number;
    components: ScoreComponents;
    reasons: string[];
}

interface DataStatus {
    status: 'stale' | 'draft-ready' | 'unknown';
    generatedAt?: string;
    label?: string;
    message?: string;
}

const POSITIONS: Position[] = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
const FILTERS: FilterByType[] = ['ALL', 'FLEX', ...POSITIONS];
const STORAGE_PREFIX = 'draft-assistant-v2';

const LEAGUES: LeagueProfile[] = [
    {
        id: 'default',
        label: 'Default / Current',
        file: 'players.json',
        teams: 12,
        mode: 'redraft',
        roster: { QB: 2, RB: 4, WR: 4, TE: 1, K: 1, DEF: 1 },
        notes: 'Current generated player pool.',
        publicNotes: 'Draft board.',
    },
    {
        id: 'vany',
        label: 'VANY',
        file: 'vany.json',
        teams: 12,
        mode: 'redraft',
        roster: { QB: 1, RB: 4, WR: 4, TE: 1, K: 1, DEF: 1 },
        notes: 'Back to Yahoo this year; local history can learn team bias.',
        publicNotes: 'Yahoo draft board.',
    },
    {
        id: 'passion',
        label: 'Passion',
        file: 'passion.json',
        teams: 14,
        mode: 'redraft',
        roster: { QB: 1, RB: 3, WR: 4, TE: 1, K: 1, DEF: 1 },
        notes: '14-team redraft profile.',
        publicNotes: 'League draft board.',
    },
    {
        id: 'guillotine',
        label: 'Guillotine',
        file: 'guillotine.json',
        teams: 18,
        mode: 'guillotine',
        roster: { QB: 1, RB: 4, WR: 4, TE: 1, K: 1, DEF: 1 },
        notes: 'Floor and survival matter more than ceiling.',
        publicNotes: 'Draft board.',
    },
    {
        id: 'champions',
        label: 'Champions',
        file: 'champions.json',
        teams: 8,
        mode: 'champions',
        roster: { QB: 2, RB: 5, WR: 7, TE: 2, K: 1, DEF: 1 },
        lineup: { QB: 1, RB: 3, WR: 4, TE: 1, FLEX: 2, SUPERFLEX: 1, K: 1, DEF: 1 },
        notes: 'Live in-person: 1 QB, 3 RB, 4 WR, TE, 2 flex, 1 superflex, K, DEF, 6 bench.',
        publicNotes: 'Live draft board.',
    },
];

const CONCERN_LABELS: Record<Concern, string> = {
    injury: 'Injury',
    role: 'Role',
    legal: 'Legal',
    playoff: 'Playoff',
    bye: 'Bye',
    fade: 'Fade',
};

const EMPTY_SESSION: DraftSession = {
    drafted: [],
    undone: [],
    adjustments: {},
    pickingFor: 'me',
    currentManager: 'Me',
    view: 'cockpit',
    sortBy: 'recommendation',
    filterBy: 'ALL',
    showTop10: false,
};

function defaultSessionForLeague(leagueId: string): DraftSession {
    return {
        ...EMPTY_SESSION,
        view: leagueId === 'champions' ? 'classic' : 'cockpit',
    };
}

const getPositionColor = (pos: Position) => `var(--pos-${pos.toLowerCase()})`;
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const round = (value: number) => Number(value.toFixed(2));

function isPublicView(view: ViewType) {
    return view === 'classic' || view === 'picks';
}

async function fetchPlayers(profile: LeagueProfile): Promise<Player[]> {
    const res = await fetch(`./${profile.file}`);
    if (!res.ok) throw new Error(`Failed to fetch ${profile.file}`);
    return res.json();
}

async function fetchDataStatus(): Promise<DataStatus | null> {
    try {
        const res = await fetch('./data_status.json', { cache: 'no-store' });
        if (!res.ok) return null;
        return res.json();
    } catch {
        return null;
    }
}

function sessionKey(leagueId: string) {
    return `${STORAGE_PREFIX}:session:${leagueId}`;
}

function selectedLeagueKey() {
    return `${STORAGE_PREFIX}:selected-league`;
}

function loadSession(leagueId: string): DraftSession {
    try {
        const raw = window.localStorage.getItem(sessionKey(leagueId));
        const defaultSession = defaultSessionForLeague(leagueId);
        if (!raw) return defaultSession;
        return { ...defaultSession, ...JSON.parse(raw) };
    } catch {
        return defaultSessionForLeague(leagueId);
    }
}

function saveSession(leagueId: string, session: DraftSession) {
    window.localStorage.setItem(sessionKey(leagueId), JSON.stringify(session));
}

function draftedMap(drafted: DraftPick[]) {
    return new Map(drafted.map(pick => [pick.playerId, pick]));
}

function renumberPicks(picks: DraftPick[]) {
    return picks.map((pick, index) => ({ ...pick, pick: index + 1 }));
}

function playerMatches(player: Player, query: string) {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return [player.name, player.team, player.position].some(value =>
        value.toLowerCase().includes(q)
    );
}

function isFlexPosition(pos: Position) {
    return pos === 'RB' || pos === 'WR' || pos === 'TE';
}


function formatLineup(lineup: Partial<Record<RosterSlot, number>>) {
    const labels: Record<RosterSlot, string> = {
        QB: 'QB',
        RB: 'RB',
        WR: 'WR',
        TE: 'TE',
        FLEX: 'W/R/T',
        SUPERFLEX: 'Q/W/R/T',
        K: 'K',
        DEF: 'DEF',
    };
    return (['QB', 'WR', 'RB', 'TE', 'FLEX', 'SUPERFLEX', 'K', 'DEF'] as RosterSlot[])
        .flatMap(slot => {
            const count = lineup[slot] ?? 0;
            return count > 0 ? [`${count} ${labels[slot]}`] : [];
        })
        .join(', ');
}
function rosterCounts(players: Player[], picks: DraftPick[]) {
    const counts = Object.fromEntries(POSITIONS.map(pos => [pos, 0])) as Record<Position, number>;
    const pickedIds = new Set(picks.filter(pick => pick.owner === 'me').map(pick => pick.playerId));
    players.forEach(player => {
        if (pickedIds.has(player.id)) counts[player.position] += 1;
    });
    return counts;
}

function byeCounts(players: Player[], picks: DraftPick[]) {
    const pickedIds = new Set(picks.filter(pick => pick.owner === 'me').map(pick => pick.playerId));
    return players.reduce<Record<number, Player[]>>((counts, player) => {
        if (pickedIds.has(player.id)) {
            counts[player.bye] = [...(counts[player.bye] ?? []), player];
        }
        return counts;
    }, {});
}

function getLeagueHistoryAdjustment(profile: LeagueProfile, player: Player) {
    if (profile.id === 'vany' && (player.team === 'BUF' || player.team === 'LAR')) {
        return 0.9;
    }
    return 0;
}

function getRosterFit(profile: LeagueProfile, counts: Record<Position, number>, player: Player, currentPick: number) {
    const target = profile.roster[player.position] ?? 0;
    const count = counts[player.position] ?? 0;
    if ((player.position === 'K' || player.position === 'DEF') && currentPick < profile.teams * 10) {
        return -2.5;
    }
    if (profile.id === 'champions' && player.position === 'QB') {
        if (count < 2) return 2.6 - count * 0.45;
        if (count === 2 && currentPick >= profile.teams * 9) return 0.45;
        if (count >= 3) return -1.4;
    }
    if (count < target) return 2.4 - count * 0.35;
    if (isFlexPosition(player.position) && count < target + 2) return 0.65;
    if (count >= target + 3) return -1.2;
    return 0;
}


function getMarketRank(profile: LeagueProfile, player: Player) {
    if (profile.id === 'champions') {
        return player.superflexEcr ?? player.dynastyEcr ?? player.adp;
    }
    return player.adp;
}

function getMarketLabel(profile: LeagueProfile) {
    return profile.id === 'champions' ? 'SF' : 'ADP';
}
function getByeRisk(myByes: Record<number, Player[]>, player: Player) {
    const sameBye = myByes[player.bye] ?? [];
    const samePosition = sameBye.filter(p => p.position === player.position).length;
    return -(Math.max(0, sameBye.length - 1) * 0.75 + samePosition * 0.45);
}

function getTierDropoff(profile: LeagueProfile, player: Player, available: Player[], nextPick: number) {
    const samePosition = available.filter(p => p.position === player.position && p.id !== player.id);
    const laterOptions = samePosition.filter(p => getMarketRank(profile, p) > nextPick);
    const bestLaterVor = laterOptions.length ? Math.max(...laterOptions.map(p => p.vor)) : 0;
    return Math.max(0, player.vor - bestLaterVor);
}

function scorePlayer(
    profile: LeagueProfile,
    player: Player,
    available: Player[],
    myRoster: Record<Position, number>,
    myByes: Record<number, Player[]>,
    currentPick: number,
    adjustment: PlayerAdjustment | undefined
): Recommendation {
    const nextPick = currentPick + profile.teams;
    const marketRank = getMarketRank(profile, player);
    const adpGap = currentPick - marketRank;
    const tierDropoff = getTierDropoff(profile, player, available, nextPick);
    const concerns = adjustment?.concerns ?? [];
    const components: ScoreComponents = {
        vor: player.vor,
        adpValue: clamp(adpGap * 0.25, -3, 4),
        tierDropoff,
        availabilityNextPick: clamp((nextPick - marketRank) / 8, -2, 5),
        rosterFit: getRosterFit(profile, myRoster, player, currentPick),
        byeRisk: getByeRisk(myByes, player),
        historyAdjustment: getLeagueHistoryAdjustment(profile, player),
        manualAdjustment: adjustment?.manual ?? 0,
        concernPenalty: concerns.length * -0.85,
    };
    const totalScore =
        components.vor +
        components.adpValue +
        components.tierDropoff * 0.65 +
        components.availabilityNextPick +
        components.rosterFit +
        components.byeRisk +
        components.historyAdjustment +
        components.manualAdjustment +
        components.concernPenalty;

    return {
        player,
        totalScore: round(totalScore),
        components: {
            ...components,
            tierDropoff: round(components.tierDropoff),
        },
        reasons: buildReasons(profile, player, components, concerns),
    };
}

function buildReasons(
    profile: LeagueProfile,
    player: Player,
    components: ScoreComponents,
    concerns: Concern[]
) {
    const reasons: string[] = [];
    if (components.adpValue >= 1.5) reasons.push(`${getMarketLabel(profile)} value: ${round(components.adpValue)} points past market.`);
    if (components.tierDropoff >= 1.5) reasons.push(`Tier cliff: ${round(components.tierDropoff)} VOR drop if this ${player.position} tier dries up.`);
    if (components.availabilityNextPick >= 2) reasons.push('Likely gone before your next estimated pick.');
    if (components.rosterFit >= 1.5) reasons.push(`Roster fit: fills a ${player.position} need.`);
    if (components.historyAdjustment > 0) reasons.push(`${profile.label} history: ${player.team} players may go early.`);
    if (components.manualAdjustment > 0) reasons.push(`Manual boost: +${round(components.manualAdjustment)}.`);
    if (components.manualAdjustment < 0) reasons.push(`Manual fade: ${round(components.manualAdjustment)}.`);
    if (components.byeRisk < -0.5) reasons.push(`Bye risk: Week ${player.bye} is getting crowded.`);
    if (concerns.length) reasons.push(`Concern flags: ${concerns.map(c => CONCERN_LABELS[c]).join(', ')}.`);
    if (!reasons.length) reasons.push('Best balanced value across VOR, market rank, roster, and tier risk.');
    return reasons.slice(0, 4);
}

function buttonStyle(active = false): React.CSSProperties {
    return {
        background: active ? 'var(--color-accent)' : 'var(--color-surface-2)',
        color: 'var(--color-text-primary)',
        border: '1px solid var(--color-border)',
    };
}

const Header: React.FC<{
    profile: LeagueProfile;
    leagueId: string;
    onLeagueChange: (leagueId: string) => void;
    session: DraftSession;
    updateSession: (patch: Partial<DraftSession>) => void;
    currentPick: number;
    searchQuery: string;
    setSearchQuery: (value: string) => void;
    draftFirstMatch: () => void;
    undo: () => void;
    redo: () => void;
    resetDraft: () => void;
    canUndo: boolean;
    canRedo: boolean;
    exportSession: () => void;
    importSession: (file: File) => void;
}> = ({
    profile,
    leagueId,
    onLeagueChange,
    session,
    updateSession,
    currentPick,
    searchQuery,
    setSearchQuery,
    draftFirstMatch,
    undo,
    redo,
    resetDraft,
    canUndo,
    canRedo,
    exportSession,
    importSession,
}) => {
    const inputRef = useRef<HTMLInputElement | null>(null);
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const publicView = isPublicView(session.view);
    const headerTitle = session.view === 'picks' ? 'Drafted players' : session.view === 'classic' ? 'Draft board' : 'Draft cockpit';
    const headerNote = publicView ? profile.publicNotes : profile.notes;

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            const target = e.target as HTMLElement | null;
            const isTyping = target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
            if (!isTyping && e.key === '/') {
                e.preventDefault();
                inputRef.current?.focus();
            }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, []);

    return (
        <header className="header">
            <div className="headerTop">
                <div>
                    <div className="eyebrow">{headerTitle}</div>
                    <h1>Pick #{currentPick}</h1>
                    <div className="muted">{headerNote}</div>
                </div>
                <div className="headerActions">
                    <select value={leagueId} onChange={e => onLeagueChange(e.target.value)} aria-label="League">
                        {LEAGUES.map(league => <option key={league.id} value={league.id}>{league.label}</option>)}
                    </select>
                    <button onClick={undo} disabled={!canUndo}>Undo</button>
                    <button onClick={redo} disabled={!canRedo}>Redo</button>
                    <button className="danger" onClick={resetDraft}>Reset</button>
                </div>
            </div>

            <div className="toolbar">
                <div className="searchBox" onClick={() => inputRef.current?.focus()}>
                    <input
                        ref={inputRef}
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === 'Enter') draftFirstMatch();
                            if (e.key === 'Escape') setSearchQuery('');
                        }}
                        placeholder="Search player, team, or position"
                        type="search"
                        aria-label="Search players"
                    />
                    <button disabled={!searchQuery.trim()} onClick={draftFirstMatch}>Draft match</button>
                </div>
                <div className="viewControls">
                    <div className="segmented subtle" aria-label="View">
                        <span className="segmentLabel">View</span>
                        <button
                            style={buttonStyle(session.view === 'classic')}
                            onClick={() => updateSession({ view: 'classic', sortBy: 'recommendation' })}
                        >
                            Board
                        </button>
                        <button
                            style={buttonStyle(session.view === 'cockpit')}
                            onClick={() => updateSession({ view: 'cockpit' })}
                        >
                            Cockpit
                        </button>
                    </div>
                    <div className="segmented utilityViews">
                        <button
                            style={buttonStyle(session.view === 'board')}
                            onClick={() => updateSession({ view: 'board' })}
                        >
                            Details
                        </button>
                        <button
                            style={buttonStyle(session.view === 'byes')}
                            onClick={() => updateSession({ view: 'byes' })}
                        >
                            Byes
                        </button>
                        <button
                            style={buttonStyle(session.view === 'picks')}
                            onClick={() => updateSession({ view: 'picks' })}
                        >
                            Drafted
                        </button>
                    </div>
                </div>
            </div>

            <div className="toolbar compact">
                <label>
                    Picking for
                    <select
                        value={session.pickingFor}
                        onChange={e => updateSession({ pickingFor: e.target.value as Owner })}
                    >
                        <option value="me">Me</option>
                        <option value="other">Other</option>
                    </select>
                </label>
                <label>
                    Manager/team
                    <input
                        value={session.currentManager}
                        onChange={e => updateSession({ currentManager: e.target.value })}
                        placeholder="Manager name"
                    />
                </label>
                <label>
                    Sort
                    <select
                        value={session.sortBy}
                        onChange={e => updateSession({ sortBy: e.target.value as SortByType })}
                    >
                        <option value="recommendation">{publicView ? 'Rank' : 'Recommendation'}</option>
                        <option value="adp">ADP</option>
                        <option value="vor">VOR</option>
                    </select>
                </label>
                <label>
                    Filter
                    <select
                        value={session.filterBy}
                        onChange={e => updateSession({ filterBy: e.target.value as FilterByType })}
                    >
                        {FILTERS.map(filter => <option key={filter} value={filter}>{filter}</option>)}
                    </select>
                </label>
                <button onClick={exportSession}>Export session</button>
                <button onClick={() => fileInputRef.current?.click()}>Import session</button>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="application/json"
                    hidden
                    onChange={e => {
                        const file = e.target.files?.[0];
                        if (file) importSession(file);
                        e.currentTarget.value = '';
                    }}
                />
            </div>
        </header>
    );
};

const RecommendationCard: React.FC<{
    profile: LeagueProfile;
    rec: Recommendation;
    rank: number;
    featured?: boolean;
    onDraft: (id: number) => void;
    adjustment?: PlayerAdjustment;
    setAdjustment: (id: number, patch: Partial<PlayerAdjustment>) => void;
    toggleConcern: (id: number, concern: Concern) => void;
}> = ({ profile, rec, rank, featured = false, onDraft, adjustment, setAdjustment, toggleConcern }) => {
    const { player, components } = rec;
    const concerns = adjustment?.concerns ?? [];
    return (
        <section className={featured ? 'recCard featured' : 'recCard'}>
            <div className="recHeader">
                <div className="rankBadge">#{rank}</div>
                <div className="playerMain">
                    <h2>{player.name}</h2>
                    <div className="muted">
                        <span style={{ color: getPositionColor(player.position) }}>{player.position}</span>
                        {' '} {player.team} · Bye {player.bye} · {getMarketLabel(profile)} {getMarketRank(profile, player)}
                    </div>
                </div>
                <div className="scoreBlock">
                    <div className="score">{rec.totalScore}</div>
                    <div className="muted">score</div>
                </div>
            </div>
            <div className="reasonList">
                {rec.reasons.map(reason => <div key={reason}>{reason}</div>)}
            </div>
            <div className="componentGrid">
                <Metric label="VOR" value={components.vor} />
                <Metric label={getMarketLabel(profile)} value={components.adpValue} />
                <Metric label="Tier" value={components.tierDropoff} />
                <Metric label="Gone" value={components.availabilityNextPick} />
                <Metric label="Roster" value={components.rosterFit} />
                <Metric label="Bye" value={components.byeRisk} />
                <Metric label="History" value={components.historyAdjustment} />
                <Metric label="Manual" value={components.manualAdjustment + components.concernPenalty} />
            </div>
            <div className="cardActions">
                <button className="primary" onClick={() => onDraft(player.id)}>Draft</button>
                <button onClick={() => setAdjustment(player.id, { avoid: !adjustment?.avoid })}>
                    {adjustment?.avoid ? 'Unavoid' : 'Avoid'}
                </button>
                <button onClick={() => setAdjustment(player.id, { manual: (adjustment?.manual ?? 0) + 1 })}>Boost</button>
                <button onClick={() => setAdjustment(player.id, { manual: (adjustment?.manual ?? 0) - 1 })}>Fade</button>
                <button onClick={() => setAdjustment(player.id, { manual: 0, concerns: [] })}>Clear flags</button>
            </div>
            <div className="concernBar">
                {(Object.keys(CONCERN_LABELS) as Concern[]).map(concern => (
                    <button
                        key={concern}
                        style={buttonStyle(concerns.includes(concern))}
                        onClick={() => toggleConcern(player.id, concern)}
                    >
                        {CONCERN_LABELS[concern]}
                    </button>
                ))}
            </div>
        </section>
    );
};

const Metric: React.FC<{ label: string; value: number }> = ({ label, value }) => (
    <div>
        <div className="muted">{label}</div>
        <div>{round(value)}</div>
    </div>
);

const TopDrawer: React.FC<{
    profile: LeagueProfile;
    recommendations: Recommendation[];
    open: boolean;
    setOpen: (open: boolean) => void;
    onDraft: (id: number) => void;
}> = ({ profile, recommendations, open, setOpen, onDraft }) => (
    <section className="panel">
        <button className="drawerButton" onClick={() => setOpen(!open)}>
            {open ? 'Hide Top 10' : 'Show Top 10 backups'}
        </button>
        {open && (
            <div className="drawerList">
                {recommendations.map((rec, index) => (
                    <div key={rec.player.id} className="drawerRow">
                        <div className="rowRank">#{index + 1}</div>
                        <div>
                            <strong>{rec.player.name}</strong>
                            <div className="muted">{rec.player.team} · {rec.player.position} · {getMarketLabel(profile)} {getMarketRank(profile, rec.player)}</div>
                        </div>
                        <div className="score">{rec.totalScore}</div>
                        <button onClick={() => onDraft(rec.player.id)}>Draft</button>
                    </div>
                ))}
            </div>
        )}
    </section>
);

const BoardView: React.FC<{
    profile: LeagueProfile;
    rows: Recommendation[];
    adjustments: Record<string, PlayerAdjustment>;
    onDraft: (id: number) => void;
    setAdjustment: (id: number, patch: Partial<PlayerAdjustment>) => void;
}> = ({ profile, rows, adjustments, onDraft, setAdjustment }) => (
    <main className="stack">
        {rows.map(rec => {
            const player = rec.player;
            const adjustment = adjustments[String(player.id)];
            return (
                <div key={player.id} className={adjustment?.avoid ? 'playerRow avoided' : 'playerRow'}>
                    <div className="posStripe" style={{ background: getPositionColor(player.position) }} />
                    <div className="playerMain">
                        <strong>{player.name}</strong>
                        <div className="muted">{player.team} · {player.position} · Bye {player.bye}</div>
                    </div>
                    <Metric label="Score" value={rec.totalScore} />
                    <Metric label={getMarketLabel(profile)} value={getMarketRank(profile, player)} />
                    <Metric label="VOR" value={player.vor} />
                    <button onClick={() => onDraft(player.id)}>Draft</button>
                    <button onClick={() => setAdjustment(player.id, { avoid: !adjustment?.avoid })}>
                        {adjustment?.avoid ? 'Unavoid' : 'Avoid'}
                    </button>
                </div>
            );
        })}
        {!rows.length && <div className="empty">No matching players.</div>}
    </main>
);

const ClassicBoardView: React.FC<{
    profile: LeagueProfile;
    rows: Recommendation[];
    onDraft: (id: number) => void;
}> = ({ profile, rows, onDraft }) => (
    <main className="classicBoard">
        <div className="classicHeader">
            <div>Rank</div>
            <div>Player</div>
            <div>Team</div>
            <div>Pos</div>
            <div>Bye</div>
            <div>ADP</div>
            <div>VOR</div>
            <div />
        </div>
        {rows.map((rec, index) => {
            const player = rec.player;
            return (
                <div key={player.id} className="classicRow">
                    <div className="classicRank">{index + 1}</div>
                    <div className="classicPlayer">{player.name}</div>
                    <div>{player.team}</div>
                    <div>
                        <span className="positionPill" style={{ borderColor: getPositionColor(player.position) }}>
                            {player.position}
                        </span>
                    </div>
                    <div>{player.bye}</div>
                    <div>{getMarketRank(profile, player)}</div>
                    <div>{player.vor.toFixed(2)}</div>
                    <button onClick={() => onDraft(player.id)}>Draft</button>
                </div>
            );
        })}
        {!rows.length && <div className="empty">No matching players.</div>}
    </main>
);


const DraftLogView: React.FC<{
    picks: DraftPick[];
    playerById: Map<number, Player>;
    onUndoPick: (pick: number) => void;
}> = ({ picks, playerById, onUndoPick }) => {
    const rows = [...picks].sort((a, b) => b.pick - a.pick);
    return (
        <main className="draftLog">
            <div className="draftHeader">
                <div>Pick</div>
                <div>Player</div>
                <div>Manager</div>
                <div>Team</div>
                <div>Pos</div>
                <div>Bye</div>
                <div>Owner</div>
                <div />
            </div>
            {rows.map(pick => {
                const player = playerById.get(pick.playerId);
                return (
                    <div key={`${pick.pick}-${pick.playerId}-${pick.at}`} className="draftRow">
                        <div className="classicRank">#{pick.pick}</div>
                        <div className="classicPlayer">{player?.name ?? 'Unknown player'}</div>
                        <div>{pick.manager}</div>
                        <div>{player?.team ?? '-'}</div>
                        <div>
                            {player ? (
                                <span className="positionPill" style={{ borderColor: getPositionColor(player.position) }}>
                                    {player.position}
                                </span>
                            ) : '-'}
                        </div>
                        <div>{player?.bye ?? '-'}</div>
                        <div>{pick.owner === 'me' ? 'Me' : 'Other'}</div>
                        <button onClick={() => onUndoPick(pick.pick)}>Undo</button>
                    </div>
                );
            })}
            {!rows.length && <div className="empty">No picks marked yet.</div>}
        </main>
    );
};
const ByeWeekView: React.FC<{ byes: Record<number, Player[]> }> = ({ byes }) => {
    const weeks = Object.keys(byes).map(Number).sort((a, b) => a - b);
    if (!weeks.length) return <div className="empty">No players drafted for your roster yet.</div>;
    return (
        <main className="gridPanel">
            {weeks.map(week => (
                <section key={week} className="panel">
                    <h3>Week {week} ({byes[week].length})</h3>
                    <div className="chipWrap">
                        {byes[week].map(player => (
                            <span key={player.id} className="chip">
                                <span style={{ color: getPositionColor(player.position) }}>{player.position}</span>
                                {' '} {player.name}
                            </span>
                        ))}
                    </div>
                </section>
            ))}
        </main>
    );
};

const RosterSnapshot: React.FC<{
    profile: LeagueProfile;
    counts: Record<Position, number>;
    picks: DraftPick[];
}> = ({ profile, counts, picks }) => (
    <aside className="panel rosterPanel">
        <h3>My roster</h3>
        {profile.lineup && <div className="muted">Lineup: {formatLineup(profile.lineup)}</div>}
        <div className="muted">Soft draft targets</div>
        <div className="rosterGrid">
            {POSITIONS.map(pos => (
                <div key={pos}>
                    <div className="muted">{pos}</div>
                    <strong>{counts[pos]} / {profile.roster[pos]}</strong>
                </div>
            ))}
        </div>
        <div className="muted">{picks.filter(p => p.owner === 'me').length} of your players marked.</div>
    </aside>
);

const DataStatusBanner: React.FC<{ status: DataStatus | null }> = ({ status }) => {
    if (!status) {
        return (
            <section className="dataBanner warning">
                <strong>Data status unknown.</strong>
                <span>No source manifest was loaded. Verify player JSON before drafting.</span>
            </section>
        );
    }
    const isReady = status.status === 'draft-ready';
    return (
        <section className={`dataBanner ${isReady ? 'ready' : 'warning'}`}>
            <strong>{isReady ? 'Data draft-ready' : 'Data needs refresh'}</strong>
            <span>{status.label ?? status.generatedAt ?? 'No generation date'}.</span>
            {status.message && <span>{status.message}</span>}
        </section>
    );
};

const App: React.FC = () => {
    const initialLeagueId = window.localStorage.getItem(selectedLeagueKey()) ?? 'default';
    const [leagueId, setLeagueId] = useState(initialLeagueId);
    const profile = LEAGUES.find(league => league.id === leagueId) ?? LEAGUES[0];
    const [session, setSession] = useState<DraftSession>(() => loadSession(profile.id));
    const [allPlayers, setAllPlayers] = useState<Player[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [dataStatus, setDataStatus] = useState<DataStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const updateSession = (patch: Partial<DraftSession>) => {
        setSession(prev => ({ ...prev, ...patch }));
    };

    const handleLeagueChange = (nextLeagueId: string) => {
        saveSession(profile.id, session);
        window.localStorage.setItem(selectedLeagueKey(), nextLeagueId);
        setLeagueId(nextLeagueId);
        setSession(loadSession(nextLeagueId));
        setSearchQuery('');
    };

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (!event.ctrlKey || event.key !== '.') return;
            event.preventDefault();
            setSession(prev => ({
                ...prev,
                view: prev.view === 'cockpit' ? 'classic' : 'cockpit',
                sortBy: prev.view === 'cockpit' ? 'recommendation' : prev.sortBy,
            }));
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, []);

    useEffect(() => {
        saveSession(profile.id, session);
    }, [profile.id, session]);

    useEffect(() => {
        setLoading(true);
        setError(null);
        fetchPlayers(profile)
            .then(setAllPlayers)
            .catch(err => setError(err instanceof Error ? err.message : 'Unable to load players.'))
            .finally(() => setLoading(false));
    }, [profile]);

    useEffect(() => {
        fetchDataStatus().then(setDataStatus);
    }, []);

    const playerById = useMemo(() => new Map(allPlayers.map(player => [player.id, player])), [allPlayers]);
    const pickedMap = useMemo(() => draftedMap(session.drafted), [session.drafted]);
    const available = useMemo(
        () => allPlayers.filter(player => !pickedMap.has(player.id)),
        [allPlayers, pickedMap]
    );
    const myRoster = useMemo(() => rosterCounts(allPlayers, session.drafted), [allPlayers, session.drafted]);
    const myByes = useMemo(() => byeCounts(allPlayers, session.drafted), [allPlayers, session.drafted]);
    const currentPick = session.drafted.length + 1;

    const recommendations = useMemo(() => {
        return available
            .filter(player => !session.adjustments[String(player.id)]?.avoid)
            .map(player =>
                scorePlayer(
                    profile,
                    player,
                    available,
                    myRoster,
                    myByes,
                    currentPick,
                    session.adjustments[String(player.id)]
                )
            )
            .sort((a, b) => b.totalScore - a.totalScore);
    }, [available, currentPick, myByes, myRoster, profile, session.adjustments]);

    const visibleRows = useMemo(() => {
        const scored = available
            .filter(player => {
                if (session.filterBy === 'ALL') return true;
                if (session.filterBy === 'FLEX') return isFlexPosition(player.position);
                return player.position === session.filterBy;
            })
            .filter(player => {
                if (session.view !== 'classic') return true;
                return !session.adjustments[String(player.id)]?.avoid;
            })
            .filter(player => playerMatches(player, searchQuery))
            .map(player =>
                scorePlayer(
                    profile,
                    player,
                    available,
                    myRoster,
                    myByes,
                    currentPick,
                    session.adjustments[String(player.id)]
                )
            );

        return scored.sort((a, b) => {
            if (session.sortBy === 'adp') return getMarketRank(profile, a.player) - getMarketRank(profile, b.player);
            if (session.sortBy === 'vor') return b.player.vor - a.player.vor;
            return b.totalScore - a.totalScore;
        });
    }, [
        available,
        currentPick,
        myByes,
        myRoster,
        profile,
        searchQuery,
        session.adjustments,
        session.filterBy,
        session.sortBy,
        session.view,
    ]);

    const setAdjustment = (id: number, patch: Partial<PlayerAdjustment>) => {
        setSession(prev => {
            const key = String(id);
            const current = prev.adjustments[key] ?? {};
            return {
                ...prev,
                adjustments: {
                    ...prev.adjustments,
                    [key]: { ...current, ...patch },
                },
            };
        });
    };

    const toggleConcern = (id: number, concern: Concern) => {
        setSession(prev => {
            const key = String(id);
            const current = prev.adjustments[key] ?? {};
            const concerns = current.concerns ?? [];
            const nextConcerns = concerns.includes(concern)
                ? concerns.filter(item => item !== concern)
                : [...concerns, concern];
            return {
                ...prev,
                adjustments: {
                    ...prev.adjustments,
                    [key]: { ...current, concerns: nextConcerns },
                },
            };
        });
    };

    const draftPlayer = (playerId: number) => {
        const manager = session.currentManager.trim() || (session.pickingFor === 'me' ? 'Me' : 'Other');
        const pick: DraftPick = {
            playerId,
            owner: session.pickingFor,
            manager,
            pick: currentPick,
            at: new Date().toISOString(),
        };
        setSession(prev => ({
            ...prev,
            drafted: [...prev.drafted, pick],
            undone: [],
            pickingFor: prev.pickingFor === 'me' ? 'other' : prev.pickingFor,
            currentManager: prev.pickingFor === 'me' ? 'Other' : prev.currentManager,
        }));
        setSearchQuery('');
    };

    const draftFirstMatch = () => {
        const first = visibleRows[0];
        if (first) draftPlayer(first.player.id);
    };

    const undo = () => {
        setSession(prev => {
            const last = prev.drafted.at(-1);
            if (!last) return prev;
            return {
                ...prev,
                drafted: renumberPicks(prev.drafted.slice(0, -1)),
                undone: [last, ...prev.undone],
            };
        });
    };

    const redo = () => {
        setSession(prev => {
            const [next, ...rest] = prev.undone;
            if (!next) return prev;
            return {
                ...prev,
                drafted: [...prev.drafted, { ...next, pick: prev.drafted.length + 1 }],
                undone: rest,
            };
        });
    };


    const undoPick = (pickNumber: number) => {
        setSession(prev => {
            const removed = prev.drafted.find(pick => pick.pick === pickNumber);
            if (!removed) return prev;
            return {
                ...prev,
                drafted: renumberPicks(prev.drafted.filter(pick => pick.pick !== pickNumber)),
                undone: [removed, ...prev.undone],
            };
        });
    };
    const resetDraft = () => {
        if (window.confirm('Reset this league draft session?')) {
            setSession(defaultSessionForLeague(profile.id));
            setSearchQuery('');
        }
    };

    const exportSession = () => {
        const payload = JSON.stringify({ leagueId: profile.id, session }, null, 2);
        const url = URL.createObjectURL(new Blob([payload], { type: 'application/json' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `${profile.id}-draft-session.json`;
        link.click();
        URL.revokeObjectURL(url);
    };

    const importSession = (file: File) => {
        const reader = new FileReader();
        reader.onload = () => {
            try {
                const parsed = JSON.parse(String(reader.result));
                const nextSession = parsed.session ?? parsed;
                setSession({ ...defaultSessionForLeague(profile.id), ...nextSession });
            } catch {
                window.alert('Could not import that session JSON.');
            }
        };
        reader.readAsText(file);
    };

    if (loading) return <div className="empty">Loading {profile.label} players...</div>;
    if (error) return <div className="empty">{error}</div>;

    const primary = recommendations[0];
    const backups = recommendations.slice(1, 3);
    const topTen = recommendations.slice(0, 10);

    return (
        <>
            {!isPublicView(session.view) && <DataStatusBanner status={dataStatus} />}
            <Header
                profile={profile}
                leagueId={leagueId}
                onLeagueChange={handleLeagueChange}
                session={session}
                updateSession={updateSession}
                currentPick={currentPick}
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                draftFirstMatch={draftFirstMatch}
                undo={undo}
                redo={redo}
                resetDraft={resetDraft}
                canUndo={session.drafted.length > 0}
                canRedo={session.undone.length > 0}
                exportSession={exportSession}
                importSession={importSession}
            />

            {session.view === 'classic' && (
                <ClassicBoardView
                    profile={profile}
                    rows={visibleRows}
                    onDraft={draftPlayer}
                />
            )}

            {session.view === 'cockpit' && (
                <main className="cockpitLayout">
                    <div className="stack">
                        {primary ? (
                            <RecommendationCard
                                profile={profile}
                                rec={primary}
                                rank={1}
                                featured
                                onDraft={draftPlayer}
                                adjustment={session.adjustments[String(primary.player.id)]}
                                setAdjustment={setAdjustment}
                                toggleConcern={toggleConcern}
                            />
                        ) : (
                            <div className="empty">No recommendation available.</div>
                        )}
                        <div className="backupGrid">
                            {backups.map((rec, index) => (
                                <RecommendationCard
                                    key={rec.player.id}
                                    profile={profile}
                                    rec={rec}
                                    rank={index + 2}
                                    onDraft={draftPlayer}
                                    adjustment={session.adjustments[String(rec.player.id)]}
                                    setAdjustment={setAdjustment}
                                    toggleConcern={toggleConcern}
                                />
                            ))}
                        </div>
                        <TopDrawer
                            profile={profile}
                            recommendations={topTen}
                            open={session.showTop10}
                            setOpen={showTop10 => updateSession({ showTop10 })}
                            onDraft={draftPlayer}
                        />
                    </div>
                    <RosterSnapshot profile={profile} counts={myRoster} picks={session.drafted} />
                </main>
            )}

            {session.view === 'board' && (
                <BoardView
                    profile={profile}
                    rows={visibleRows}
                    adjustments={session.adjustments}
                    onDraft={draftPlayer}
                    setAdjustment={setAdjustment}
                />
            )}


            {session.view === 'picks' && (
                <DraftLogView
                    picks={session.drafted}
                    playerById={playerById}
                    onUndoPick={undoPick}
                />
            )}
            {session.view === 'byes' && <ByeWeekView byes={myByes} />}
        </>
    );
};

const container = document.getElementById('root');
if (container) createRoot(container).render(<App />);
