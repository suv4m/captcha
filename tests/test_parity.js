import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { extractFeatures, FEATURE_NAMES } from "../widget/features.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const fixturesPath = path.join(__dirname, "fixtures", "traces.json");
const fixtures = JSON.parse(fs.readFileSync(fixturesPath, "utf-8"));

test("Feature Parity: JS extractFeatures vs Python extract_features", (t) => {
  for (const item of fixtures) {
    const trace = item.trace;
    const pyFeatures = item.features;
    const jsFeatures = extractFeatures(trace);

    assert.strictEqual(
      jsFeatures.length,
      25,
      `Feature count mismatch for ${item.name}`
    );

    for (let i = 0; i < 25; i++) {
      const featName = FEATURE_NAMES[i];
      const pyVal = pyFeatures[i];
      const jsVal = jsFeatures[i];

      const diff = Math.abs(pyVal - jsVal);
      // Tolerance for floating point differences across engines
      const tol = 1e-3;

      assert.ok(
        diff <= tol,
        `Parity mismatch on ${item.name} for feature [${i}] ${featName}: Python=${pyVal}, JS=${jsVal}, diff=${diff}`
      );
    }
  }
});

