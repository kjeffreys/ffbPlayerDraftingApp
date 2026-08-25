import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(process.cwd());
const snapshotPath = path.join(
  root,
  "draft_prep",
  "yahoo_exports",
  "passion_guillotine_i_snapshot.json",
);
const outputDir = path.join(root, "outputs", "guillotine-draft-prep-2026-08-24");
const outputPath = path.join(outputDir, "passion-guillotine-i-draft-prep.xlsx");

const snapshot = JSON.parse(await fs.readFile(snapshotPath, "utf8"));
const board = snapshot.board;

const workbook = Workbook.create();

const palette = {
  ink: "#13201C",
  muted: "#4B5B57",
  line: "#D4DDD8",
  soft: "#EEF4F1",
  header: "#174D3C",
  header2: "#255F8A",
  cream: "#FFF8E7",
  buy: "#DDF3E8",
  fair: "#E9F0F7",
  fall: "#FFF1D6",
  discount: "#FBE3D6",
  trap: "#F5D7DC",
  late: "#EAE6F8",
};

function makeSheet(name) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  return sheet;
}

function setTitle(sheet, title, subtitle = "") {
  sheet.getRange("A1:H1").merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = {
    fill: palette.header,
    font: { bold: true, color: "#FFFFFF", size: 16 },
  };
  sheet.getRange("A1").format.rowHeightPx = 34;
  if (subtitle) {
    sheet.getRange("A2:H2").merge();
    sheet.getRange("A2").values = [[subtitle]];
    sheet.getRange("A2").format = {
      fill: palette.soft,
      font: { color: palette.muted, italic: true },
    };
    sheet.getRange("A2").format.rowHeightPx = 28;
  }
}

function writeTable(sheet, startCell, rows, tableName) {
  const headers = Object.keys(rows[0] || {});
  const matrix = [headers, ...rows.map((row) => headers.map((header) => row[header] ?? ""))];
  sheet.getRange(startCell).write(matrix);
  const start = cellToIndexes(startCell);
  const endRow = start.row + matrix.length - 1;
  const endCol = start.col + headers.length - 1;
  const range = `${startCell}:${indexesToCell(endRow, endCol)}`;
  const table = sheet.tables.add(range, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  sheet.freezePanes.freezeRows(start.row + 1);
  return { headers, range, rowCount: matrix.length, colCount: headers.length, start };
}

function cellToIndexes(cell) {
  const match = cell.match(/^([A-Z]+)(\d+)$/);
  const letters = match[1];
  let col = 0;
  for (const letter of letters) col = col * 26 + (letter.charCodeAt(0) - 64);
  return { row: Number(match[2]) - 1, col: col - 1 };
}

function indexesToCell(row, col) {
  let n = col + 1;
  let letters = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    letters = String.fromCharCode(65 + rem) + letters;
    n = Math.floor((n - 1) / 26);
  }
  return `${letters}${row + 1}`;
}

function setWidths(sheet, widthsPx) {
  widthsPx.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, 1, 1).format.columnWidthPx = width;
  });
}

function labelFill(label) {
  if (label === "Buy Ahead") return palette.buy;
  if (label === "Risk Discount Needed") return palette.discount;
  if (label === "Discount With Reason") return palette.discount;
  if (label === "Let Fall") return palette.fall;
  if (label === "Trap") return palette.trap;
  if (label === "Late Only") return palette.late;
  return palette.fair;
}

const quick = makeSheet("Quick Start");
setTitle(
  quick,
  "Passion Guillotine I Draft Prep",
  "League-specific prep for Jeffreys and Blitz Squad Joanna. Yahoo data captured from league 602515 on 2026-08-24.",
);
quick.getRange("A4:B15").values = [
  ["League", snapshot.league.name],
  ["Draft", snapshot.league.draftTime],
  ["Room", "18 teams, 13 rounds, 1-minute picks"],
  ["Roster", "QB, 2 RB, 2 WR, TE, 2 W/R/T flex, 5 bench, IR"],
  ["Scoring", "0.5 PPR, 4-point pass TD, 40+ yard bonuses, no K/DEF"],
  ["Survival idea", "Win Week 1 stability first, then use FAAB after eliminations."],
  ["ADP rule", "ADP is acquisition cost and timing, not talent."],
  ["Jeffreys mode", "Use fair rank, ADP delta, VOR, Week 1, and risk notes together."],
  ["Joanna mode", "Use the label plus the Joanna note; avoid chasing stories without a role."],
  ["Draft order", "Yahoo says order is random about 30 minutes before draft."],
  ["Shared history", "Last-season roster page is sparse; use it lightly, not as a ranking input."],
  ["Source", snapshot.source.leagueHome],
];
quick.getRange("A4:A15").format = { fill: palette.soft, font: { bold: true, color: palette.ink } };
quick.getRange("A4:B15").format.borders = { preset: "insideHorizontal", style: "thin", color: palette.line };
quick.getRange("D4:F11").values = [
  ["Market label", "Meaning", "Action"],
  ["Buy Ahead", "Our fair value beats the market and the role/risk supports it.", "Take a little before ADP if roster fit is right."],
  ["Fair At Cost", "Price and value are aligned.", "Draft for roster construction, not arbitrage."],
  ["Risk Discount Needed", "The market still likes the player, but injury/discipline/Week 1 uncertainty matters more in guillotine.", "Draft only after safer anchors or at a meaningful room discount."],
  ["Let Fall", "Good player, but the room is paying for most of the upside.", "Take only if he slips."],
  ["Discount With Reason", "Value exists, but injury/role/team context explains the fall.", "Only take after your floor is protected."],
  ["Trap", "Market price is ahead of fair value or the risk is not worth it.", "Do not chase."],
  ["Late Only", "Yahoo has little or no usable ADP signal for the player.", "Review late, but do not chase before roster need demands it."],
];
quick.getRange("D4:F4").format = { fill: palette.header2, font: { bold: true, color: "#FFFFFF" } };
quick.getRange("D5:D11").format.borders = { preset: "insideHorizontal", style: "thin", color: palette.line };
setWidths(quick, [150, 520, 24, 165, 430, 300]);
quick.getRange("A4:F15").format.wrapText = true;

const boardSheet = makeSheet("Big Board");
setTitle(boardSheet, "Big Board", "Fair rank is model value. ADP delta is ADP minus fair rank; positive means possible discount.");
const boardRows = board.slice(0, 320).map((p) => ({
  Rank: p.id,
  Player: p.name,
  Team: p.team,
  Pos: p.position,
  Bye: p.bye,
  ADP: p.adp,
  "Fair Rank": p.fairRank,
  "ADP Delta": "",
  Label: p.marketLabel,
  "Late Tag": p.lateRoundLabel,
  "Week 1": p.week1Projection,
  "Season Pts": p.seasonProjection,
  Risk: p.riskTags,
  "Joanna Note": p.joannaNote,
  "Jeffreys Note": p.jeffNote,
}));
writeTable(boardSheet, "A4", boardRows, "BigBoard");
boardSheet.getRange(`H5:H${boardRows.length + 4}`).formulas = boardRows.map((_, index) => [[`=F${index + 5}-G${index + 5}`]]).flat();
boardSheet.getRange(`F5:H${boardRows.length + 4}`).setNumberFormat("0.0");
boardSheet.getRange(`K5:L${boardRows.length + 4}`).setNumberFormat("0.0");
setWidths(boardSheet, [54, 170, 54, 48, 45, 56, 75, 75, 142, 132, 64, 76, 150, 430, 430]);
boardSheet.getRange(`A4:O${boardRows.length + 4}`).format.wrapText = true;
for (let i = 0; i < boardRows.length; i += 1) {
  boardSheet.getRange(`I${i + 5}`).format = {
    fill: labelFill(boardRows[i].Label),
    font: { bold: true, color: palette.ink },
  };
}

const joanna = makeSheet("Joanna Primer");
setTitle(joanna, "Joanna Primer", "A skim-first guide: pick usable Week 1 roles, understand why players fall, and avoid hype traps.");
joanna.getRange("A4:C16").values = [
  ["Rule", "What It Means", "Draft Timer Translation"],
  ["Start with role", "In guillotine, a clear workload is worth more than a fragile ceiling.", "If unsure, prefer the player with clearer touches or targets."],
  ["ADP is price", "A player can be great and still be a bad pick if the room is overpaying.", "Let Fall means do not reach just because you like the name."],
  ["Discounts need a reason", "Falling players usually have injury, role, or team-context baggage.", "Discount With Reason means read the note before clicking draft."],
  ["Week 1 matters", "You can win later with waivers only if you survive the first cut.", "Avoid luxury stashes before the starting lineup is stable."],
  ["Late-round bins", "Playable now beats bench clog in this format, unless upside is truly asymmetric.", "Hidden Floor is usually better than random camp hype."],
  ["QB patience", "Only one QB starts and 18 teams draft 13 players; do not force QB over RB/WR/TE volume.", "Take QB value, not QB panic."],
  ["TE cliffs", "Elite TE can matter, but TE guesses without targets are bench-clog risk.", "If the note says Bench clog, pass unless desperate."],
  ["Two-team reality", "You and Jeffreys both want strong teams, so use the same board but separate roster needs.", "The best available player can differ by team after round 3."],
  ["Panic pick", "If the timer is dying, sort Big Board by Rank and avoid Trap unless it fills a critical need.", "Draft the highest fair-rank non-trap who fits the lineup."],
  ["Week 1 lineup", "Favor healthy players with projected touches/targets and no role ambiguity.", "Do not start a questionable excitement pick over a boring role."],
  ["Review cadence", "Skim this, then use Week 1 Watch and Late Rounds for the names likely to surprise you.", "Do the story work before the clock starts."],
  ["Mental model", "Exciting is not the same thing as startable.", "A luxury stash is not a survival pick."],
];
joanna.getRange("A4:C4").format = { fill: palette.header2, font: { bold: true, color: "#FFFFFF" } };
joanna.getRange("A5:A16").format = { fill: palette.soft, font: { bold: true, color: palette.ink } };
joanna.getRange("A4:C16").format.wrapText = true;
joanna.getRange("A4:C16").format.borders = { preset: "insideHorizontal", style: "thin", color: palette.line };
setWidths(joanna, [170, 470, 430]);

const watch = makeSheet("Week 1 Watch");
setTitle(watch, "Week 1 Watch", "Draft-relevant injury/status and role checks. Sort by Risk Score or ADP.");
const watchRows = board
  .filter((p) => (p.riskTags || p.status || p.injuryType) && (p.fairRank <= 220 || p.adp <= 220))
  .slice(0, 120)
  .map((p) => ({
    Rank: p.fairRank,
    Player: p.name,
    Team: p.team,
    Pos: p.position,
    ADP: p.adp,
    Label: p.marketLabel,
    "Week 1": p.week1Projection,
    "Risk Score": p.riskScore,
    "Risk Tags": p.riskTags,
    "Draft Note": p.joannaNote,
  }));
writeTable(watch, "A4", watchRows, "WeekOneWatch");
watch.getRange(`E5:H${watchRows.length + 4}`).setNumberFormat("0.0");
watch.getRange(`A4:J${watchRows.length + 4}`).format.wrapText = true;
setWidths(watch, [60, 170, 55, 48, 60, 150, 65, 75, 180, 520]);

const late = makeSheet("Late Rounds");
setTitle(late, "Late Rounds", "Round 8+ review for an 18-team room: playable now, hidden floor, contingent upside, stash, or bench-clog risk.");
const lateRows = board
  .filter((p) => p.fairRank >= 125)
  .slice(0, 170)
  .map((p) => ({
    Rank: p.fairRank,
    Player: p.name,
    Team: p.team,
    Pos: p.position,
    ADP: p.adp,
    "Late Tag": p.lateRoundLabel,
    Label: p.marketLabel,
    "Week 1": p.week1Projection,
    "Season PPG": p.seasonPpg,
    "Role Volume": p.seasonVolume,
    Risk: p.riskTags,
    Note: p.joannaNote,
  }));
writeTable(late, "A4", lateRows, "LateRounds");
late.getRange(`E5:J${lateRows.length + 4}`).setNumberFormat("0.0");
late.getRange(`A4:L${lateRows.length + 4}`).format.wrapText = true;
setWidths(late, [60, 170, 55, 48, 62, 138, 140, 65, 78, 78, 155, 500]);

const teams = makeSheet("Teams");
setTitle(teams, "Teams And History", "Current teams are from Yahoo Managers; emails intentionally omitted. Last-season roster evidence is sparse.");
writeTable(
  teams,
  "A4",
  snapshot.teams.map((team) => ({
    Team: team.teamName,
    Manager: team.manager,
    "Waiver Budget": team.waiverBudget,
    Moves: team.moves,
    Trades: team.trades,
    "Last Activity": team.lastLeagueActivity,
  })),
  "LeagueTeams",
);
teams.getRange("H4:K4").values = [["Last-season page finding", "Player", "2025 Draft Position", "Current O-Rank"]];
const historyRows = snapshot.lastSeason
  .flatMap((section) => section.players.map((player) => ({
    team: section.teamHeading,
    player: player.player,
    draft: player.draftPosition2025,
    orank: player.currentORank,
  })))
  .slice(0, 40);
teams.getRange(`H5:K${Math.max(5, historyRows.length + 4)}`).values =
  historyRows.length
    ? historyRows.map((row) => [row.team, row.player, row.draft, row.orank])
    : [["No usable rows", "", "", ""]];
teams.getRange("H4:K4").format = { fill: palette.header2, font: { bold: true, color: "#FFFFFF" } };
teams.getRange("A4:K60").format.wrapText = true;
setWidths(teams, [230, 140, 100, 60, 60, 150, 24, 210, 260, 140, 110]);

const sources = makeSheet("Sources");
setTitle(sources, "Sources", "Plain URLs used for the Yahoo league snapshot.");
const sourceRows = Object.entries(snapshot.source).map(([key, value]) => ({ Source: key, URL: value }));
writeTable(sources, "A4", sourceRows, "SourceUrls");
sources.getRange("A4:B20").format.wrapText = true;
setWidths(sources, [220, 760]);

for (const sheet of [quick, boardSheet, joanna, watch, late, teams, sources]) {
  sheet.getUsedRange(true).format.autofitRows();
}

await fs.mkdir(outputDir, { recursive: true });
for (const sheetName of ["Quick Start", "Big Board", "Joanna Primer", "Week 1 Watch", "Late Rounds", "Teams", "Sources"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(
    path.join(outputDir, `${sheetName.replace(/[^A-Za-z0-9]+/g, "_").toLowerCase()}_preview.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const check = await workbook.inspect({
  kind: "table",
  range: "Big Board!A4:O14",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 15,
});
console.log(check.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
