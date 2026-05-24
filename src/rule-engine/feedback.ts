/**
 * Append-only rule feedback log (JSONL). Concurrent writers are MVP-unsafe;
 * use a proper DB or file lock for production / multi-process setups.
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { dirname } from "path";
import { fileURLToPath } from "url";
import { join } from "path";

export interface FeedbackEntry {
  timestamp: string;
  rule_id: string;
  design_hash: string;
  issue_was_real: boolean;
  notes?: string;
}

function repoRootFeedbackPath(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  return join(here, "..", "..", "feedback.json");
}

export function getFeedbackFilePath(): string {
  return process.env.RULE_ENGINE_FEEDBACK_PATH ?? repoRootFeedbackPath();
}

function readLines(path: string): string[] {
  if (!existsSync(path)) return [];
  const raw = readFileSync(path, "utf-8").trim();
  if (!raw) return [];
  return raw.split("\n").filter((line: string) => line.length > 0);
}

function parseJsonl(lines: string[]): FeedbackEntry[] {
  const out: FeedbackEntry[] = [];
  for (const line of lines) {
    try {
      out.push(JSON.parse(line) as FeedbackEntry);
    } catch {
      /* skip corrupt line */
    }
  }
  return out;
}

export function logFeedback(entry: FeedbackEntry): void {
  const path = getFeedbackFilePath();
  const dir = dirname(path);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  const line = `${JSON.stringify(entry)}\n`;
  const existing = readLines(path);
  writeFileSync(path, [...existing, line.trimEnd()].join("\n") + "\n", "utf-8");
}

export function readAllFeedback(): FeedbackEntry[] {
  return parseJsonl(readLines(getFeedbackFilePath()));
}

export function getEntryCount(rule_id: string): number {
  return readAllFeedback().filter((e) => e.rule_id === rule_id).length;
}

export function getSuccessRate(rule_id: string): number {
  const rows = readAllFeedback().filter((e) => e.rule_id === rule_id);
  if (rows.length === 0) return 1;
  const ok = rows.filter((e) => e.issue_was_real === true).length;
  return ok / rows.length;
}

export function getRulesWithLowSuccessRate(threshold = 0.4): string[] {
  const byRule = new Map<string, FeedbackEntry[]>();
  for (const e of readAllFeedback()) {
    const list = byRule.get(e.rule_id) ?? [];
    list.push(e);
    byRule.set(e.rule_id, list);
  }
  const out: string[] = [];
  for (const [id, rows] of byRule) {
    if (rows.length < 5) continue;
    const ok = rows.filter((e) => e.issue_was_real === true).length;
    if (ok / rows.length < threshold) out.push(id);
  }
  return out;
}
