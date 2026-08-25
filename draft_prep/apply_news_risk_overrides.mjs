import fs from "node:fs/promises";
import path from "node:path";

const root = path.resolve(process.cwd());
const overlayPath = path.join(root, "draft_prep", "news_risk_overrides_2026-08-25.json");
const publicBoardPath = path.join(root, "public", "passion-guillotine-1.json");
const snapshotPath = path.join(root, "draft_prep", "yahoo_exports", "passion_guillotine_i_snapshot.json");
const csvPath = path.join(root, "draft_prep", "yahoo_exports", "passion_guillotine_i_big_board.csv");

const overlay = JSON.parse(await fs.readFile(overlayPath, "utf8"));
const publicBoard = JSON.parse(await fs.readFile(publicBoardPath, "utf8"));
const snapshot = JSON.parse(await fs.readFile(snapshotPath, "utf8"));

const keysToApply = [
  "marketLabel",
  "lateRoundLabel",
  "joannaNote",
  "jeffNote",
  "status",
  "injuryType",
  "riskScore",
  "riskTags",
];

function normalize(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function applyToBoard(board) {
  const byName = new Map(board.map((player) => [normalize(player.name), player]));
  const missing = [];
  for (const override of overlay.overrides) {
    const player = byName.get(normalize(override.name));
    if (!player) {
      missing.push(override.name);
      continue;
    }
    for (const key of keysToApply) {
      if (Object.hasOwn(override, key)) player[key] = override[key];
    }
  }
  return missing;
}

const missingPublic = applyToBoard(publicBoard);
const missingSnapshot = applyToBoard(snapshot.board);
if (missingPublic.length || missingSnapshot.length) {
  console.warn("Missing overrides", { public: missingPublic, snapshot: missingSnapshot });
}

function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (!/[",\n\r]/.test(text)) return text;
  return `"${text.replaceAll('"', '""')}"`;
}

const csvHeaders = [
  "rank",
  "name",
  "team",
  "position",
  "bye",
  "adp",
  "hasMarketAdp",
  "fairRank",
  "marketDelta",
  "marketLabel",
  "lateRoundLabel",
  "week1Projection",
  "seasonProjection",
  "projectedGames",
  "riskScore",
  "riskTags",
  "joannaNote",
  "jeffNote",
];

const csvRows = snapshot.board.map((player) => [
  player.id,
  player.name,
  player.team,
  player.position,
  player.bye,
  player.adp,
  player.hasMarketAdp,
  player.fairRank,
  player.marketDelta,
  player.marketLabel,
  player.lateRoundLabel,
  player.week1Projection,
  player.seasonProjection,
  player.projectedGames,
  player.riskScore,
  player.riskTags,
  player.joannaNote,
  player.jeffNote,
]);

await fs.writeFile(publicBoardPath, `${JSON.stringify(publicBoard, null, 2)}\n`);
await fs.writeFile(snapshotPath, `${JSON.stringify(snapshot, null, 2)}\n`);
await fs.writeFile(csvPath, [
  csvHeaders.join(","),
  ...csvRows.map((row) => row.map(csvEscape).join(",")),
].join("\n") + "\n");

console.log(`Applied ${overlay.overrides.length} news-risk overrides.`);
